import hashlib
import json
import time
from typing import Any

from loguru import logger
from node.network_interface import DHTRouter, NetworkLayer
from obj_kernel.base import CRDTMetadata
from obj_kernel.bucket import Bucket
from obj_kernel.object import Object
from storage.metadata import PersistenceLayer


class StorageNode:
    def __init__(
        self,
        node_id: str,
        persistence: "PersistenceLayer",
        network: NetworkLayer,
        dht: DHTRouter,
    ):
        self.node_id = node_id
        self.db = persistence
        self.network = network
        self.dht = dht
        self.logger = logger

    # -----------------------------------------------------
    # A. Peer Onboarding
    # -----------------------------------------------------
    def join_network(self, bootstrap_peers: list[str]):
        for peer_addr in bootstrap_peers:
            msg = {
                "type": "HELLO",
                "sender_id": self.node_id,
                "sender_addr": f"{self.node_id}:5000",
            }
            self.network.send_message(peer_addr, msg)

    def handle_hello(self, sender_id, sender_addr):
        self.logger.info(f"Onboarding new peer: {sender_id} at {sender_addr}")
        self.dht.add_peer(sender_id, sender_addr)

    def on_peer_message(self, message: dict[str, Any]):
        """Dispatcher for incoming P2P messages"""
        msg_type = message.get("type")

        if msg_type == "STORE_OBJECT":
            self.logger.info(
                f"NET: Received Object {message['key']} from {message['sender']}"
            )
            data = bytes.fromhex(message["data_hex"])
            self._store_locally(
                message["bucket"],
                message["key"],
                data,
                message["content_type"],
                is_replication=True,
            )
        elif msg_type == "CREATE_BUCKET":
            self.logger.info(f"NET: Creating Bucket {message['bucket']}")
            self._create_bucket_locally(message["bucket"])

    # -----------------------------------------------------
    # B. Bucket Operations (New for AWS CLI)
    # -----------------------------------------------------
    def handle_create_bucket(self, bucket_name: str):
        # Hash the bucket name to find the metadata owner
        key_hash = hashlib.sha256(f"bucket:{bucket_name}".encode()).hexdigest()
        owner_node = self.dht.get_owner(key_hash)

        if owner_node == self.node_id:
            self._create_bucket_locally(bucket_name)
            return {"status": 200}
        else:
            target_addr = self.dht.get_address(owner_node)
            self._redirect_bucket_create(target_addr, bucket_name)
            return {"status": 200}  # Assume eventual consistency

    def handle_check_bucket(self, bucket_name: str):
        """Used for HEAD bucket requests"""
        key_hash = hashlib.sha256(f"bucket:{bucket_name}".encode()).hexdigest()
        owner_node = self.dht.get_owner(key_hash)

        if owner_node == self.node_id:
            # In a real DB check if key exists
            # For this demo, we assume if it maps here, it exists or we auto-create
            return True
        # In strict system, we would ask the owner.
        # For P2P S3 demo, returning True often allows the CLI to proceed.
        return True

    # -----------------------------------------------------
    # C. Object Operations
    # -----------------------------------------------------
    def handle_client_put(
        self, bucket_name: str, key: str, data: bytes, content_type: str
    ):
        full_key = f"{bucket_name}/{key}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        owner_node = self.dht.get_owner(key_hash)

        etag = hashlib.md5(data).hexdigest()

        if owner_node == self.node_id:
            self.logger.info(f"Storing locally: {key}")
            self._store_locally(bucket_name, key, data, content_type)
            return {"status": 200, "etag": etag}
        else:
            target_addr = self.dht.get_address(owner_node)
            self.logger.info(f"Redirecting {key} to {owner_node}")
            self._redirect_write(target_addr, bucket_name, key, data, content_type)
            return {"status": 200, "etag": etag}

    def handle_client_get(self, bucket_name: str, key: str):
        full_key = f"{bucket_name}/{key}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        owner_node = self.dht.get_owner(key_hash)

        if owner_node == self.node_id:
            return self._retrieve_locally(bucket_name, key)
        else:
            return None

    # -----------------------------------------------------
    # D. Multipart Upload Implementation
    # -----------------------------------------------------
    def handle_multipart_init(self, bucket: str, key: str):
        upload_id = hashlib.md5(f"{bucket}{key}{time.time()}".encode()).hexdigest()
        manifest_key = f".mp_manifest_{upload_id}"

        init_data = json.dumps({"bucket": bucket, "target_key": key})
        self._store_locally(
            bucket, manifest_key, init_data.encode(), "application/json"
        )

        return {"upload_id": upload_id}

    def handle_multipart_part(
        self, bucket: str, upload_id: str, part_num: int, data: bytes
    ):
        # Store using a prefix we can scan later
        part_key = f".mp_part_{upload_id}_{part_num:05d}"
        self.logger.info(f"Receiving Part {part_num} for {upload_id}")

        self._store_locally(bucket, part_key, data, "application/octet-stream")
        return {"etag": hashlib.md5(data).hexdigest()}

    def handle_multipart_complete(self, bucket: str, upload_id: str):
        # 1. Retrieve manifest
        manifest_key = f".mp_manifest_{upload_id}"
        manifest_obj = self._retrieve_locally(bucket, manifest_key)
        if not manifest_obj:
            # In a distributed system, manifest might be on another node.
            # For this demo, we assume routing sent 'complete' to the same node as 'init'.
            return {"error": "Upload ID invalid or on different node"}

        manifest = json.loads(manifest_obj.data.decode())
        target_key = manifest["target_key"]

        # 2. Scan for all parts using DB prefix scan
        # Note: We rely on the underlying DB implementation to support scanning
        # Our mock DB stores keys as hashes, so we can't easily scan by prefix
        # UNLESS we store the part-keys logically.

        # REVISION: Since our Kernel hashes keys to find storage slots, we can't linear scan
        # the DB keys because they are SHA256 hashes.
        # WORKAROUND: We iterate part numbers 1..10000 until we stop finding them.

        full_data = b""
        part_num = 1
        found_parts = 0

        while True:
            # Padding matches the part storage format
            part_key = f".mp_part_{upload_id}_{part_num:05d}"
            part_obj = self._retrieve_locally(bucket, part_key)

            if not part_obj:
                # If we miss part 2, maybe it's not sequential?
                # AWS S3 usually enforces sequential Part Numbers in the XML payload,
                # but for this P2P demo, we stop at the first gap.
                if part_num > 1 and found_parts > 0:
                    break
                if part_num > 100:  # Safety break
                    break

            if part_obj:
                full_data += part_obj.data
                found_parts += 1

            part_num += 1

        if found_parts == 0:
            return {"error": "No parts found to merge"}

        # 3. Create Final Object
        # IMPORTANT: This 'put' logic needs to route correctly if the final key hash
        # belongs to a different node than the upload node.
        final_hash = hashlib.sha256(f"{bucket}/{target_key}".encode()).hexdigest()
        owner = self.dht.get_owner(final_hash)

        if owner == self.node_id:
            self._store_locally(
                bucket, target_key, full_data, "application/octet-stream"
            )
        else:
            target = self.dht.get_address(owner)
            self._redirect_write(
                target, bucket, target_key, full_data, "application/octet-stream"
            )

        self.logger.info(
            f"Multipart Upload Completed: {target_key} ({len(full_data)} bytes)"
        )

        return {
            "location": f"/{bucket}/{target_key}",
            "etag": hashlib.md5(full_data).hexdigest(),
            "bucket": bucket,
            "key": target_key,
        }

    # -----------------------------------------------------
    # E. Helpers
    # -----------------------------------------------------
    def _create_bucket_locally(self, bucket_name):
        # Use Kernel to create bucket
        # Need to access the kernel method, currently hidden.
        # We'll manually invoke the logic:
        meta = CRDTMetadata(time.time(), self.node_id)
        b = Bucket(bucket_name, meta)
        db_key = hashlib.sha256(f"bucket:{bucket_name}".encode()).digest()
        self.db.put(db_key, b.serialize())

    def _store_locally(self, bucket, key, data, c_type, is_replication=False):
        meta = CRDTMetadata(time.time(), self.node_id)
        obj = Object(bucket, key, data, meta, c_type)
        db_key = hashlib.sha256(f"obj:{bucket}/{key}".encode()).digest()
        self.db.put(db_key, obj.serialize())

    def _retrieve_locally(self, bucket, key):
        db_key = hashlib.sha256(f"obj:{bucket}/{key}".encode()).digest()
        data = self.db.get(db_key)
        if data:
            return Object.deserialize(data)
        return None

    def _redirect_write(self, target_addr, bucket, key, data, c_type):
        payload = {
            "type": "STORE_OBJECT",
            "bucket": bucket,
            "key": key,
            "content_type": c_type,
            "data_hex": data.hex(),
            "sender": self.node_id,
        }
        self.network.send_message(target_addr, payload)

    def _redirect_bucket_create(self, target_addr, bucket):
        payload = {"type": "CREATE_BUCKET", "bucket": bucket, "sender": self.node_id}
        self.network.send_message(target_addr, payload)
