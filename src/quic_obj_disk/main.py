# import time
# import json
# import hashlib

# from typing import Dict, Optional, Any, List, Tuple
# from enum import Enum
# import os


# class StorageNode:
#     """
#     The Kernel that manages RocksDB, Routing (DHT Logic), and CLI requests.
#     """
#     def __init__(self, node_id: str, db: PersistenceLayer):
#         self.node_id = node_id
#         self.db = db

#     def _get_current_metadata(self, is_deleted=False) -> CRDTMetadata:
#         return CRDTMetadata(
#             timestamp=time.time(),
#             node_id=self.node_id,
#             is_deleted=is_deleted
#         )

#     def _hash_key(self, key_str: str) -> bytes:
#         """
#         Simulates DHT hashing.
#         Maps a string key to a location in RocksDB.
#         """
#         return hashlib.sha256(key_str.encode('utf-8')).digest()

#     # --- Bucket Operations ---

#     def create_bucket(self, bucket_name: str):
#         """AWS: aws s3 mb s3://bucket_name"""
#         meta = self._get_current_metadata()
#         bucket = Bucket(bucket_name, meta)

#         # Prefix 'b:' for buckets namespace in RocksDB
#         db_key = self._hash_key(f"bucket:{bucket_name}")
#         self.db.put(db_key, bucket.serialize())
#         print(f"[{self.node_id}] Created Bucket: {bucket_name}")

#     def delete_bucket(self, bucket_name: str):
#         """AWS: aws s3 rb s3://bucket_name"""
#         # CRDT Tombstone - don't actually delete, just mark deleted
#         meta = self._get_current_metadata(is_deleted=True)
#         bucket = Bucket(bucket_name, meta)

#         db_key = self._hash_key(f"bucket:{bucket_name}")
#         self.db.put(db_key, bucket.serialize())
#         print(f"[{self.node_id}] Deleted Bucket (Tombstoned): {bucket_name}")

#     # --- Object Operations ---

#     def put_object(self, bucket_name: str, key: str, data: bytes, content_type: str = "text/plain"):
#         """AWS: aws s3 cp file s3://bucket/key"""

#         # 1. Check if bucket exists and is not deleted
#         b_key = self._hash_key(f"bucket:{bucket_name}")
#         b_val = self.db.get(b_key)

#         if not b_val:
#             raise Exception("Bucket does not exist")

#         existing_bucket = Bucket.deserialize(b_val)
#         if existing_bucket.crdt_meta.is_deleted:
#             raise Exception("Bucket is deleted")

#         # 2. Create Object
#         meta = self._get_current_metadata()
#         obj = Object(bucket_name, key, data, meta, content_type)

#         # 3. Store in RocksDB
#         # We prefix with 'o:' + bucket to group them logically if we were doing range scans
#         # But for DHT, we just hash the full path.
#         storage_key = self._hash_key(f"obj:{bucket_name}/{key}")

#         # 4. CRDT Check (Read-Repair/Merge on Write)
#         existing_bytes = self.db.get(storage_key)
#         if existing_bytes:
#             existing_obj = Object.deserialize(existing_bytes)
#             # Merge: Only overwrite if new object is "newer"
#             final_obj = existing_obj.merge(obj)
#             if final_obj is existing_obj:
#                 print(f"[{self.node_id}] Write rejected: Existing data is newer.")
#                 return

#         self.db.put(storage_key, obj.serialize())
#         print(f"[{self.node_id}] Put Object: {bucket_name}/{key} (Size: {obj.size})")

#     def get_object(self, bucket_name: str, key: str) -> Optional[Object]:
#         """AWS: aws s3 cp s3://bucket/key local_file"""
#         storage_key = self._hash_key(f"obj:{bucket_name}/{key}")
#         val = self.db.get(storage_key)

#         if not val:
#             return None

#         obj = Object.deserialize(val)
#         if obj.crdt_meta.is_deleted:
#             return None # Return 404

#         return obj

#     def delete_object(self, bucket_name: str, key: str):
#         """AWS: aws s3 rm s3://bucket/key"""
#         # Fetch existing to preserve data but mark deleted (optional, usually we just overwrite metadata)
#         # Here we create a lightweight tombstone object
#         meta = self._get_current_metadata(is_deleted=True)
#         # We store empty data for the tombstone to save space
#         obj = Object(bucket_name, key, b"", meta)

#         storage_key = self._hash_key(f"obj:{bucket_name}/{key}")
#         self.db.put(storage_key, obj.serialize())
#         print(f"[{self.node_id}] Deleted Object: {bucket_name}/{key}")

# # ---------------------------------------------------------
# # 6. Simulation / Testing
# # ---------------------------------------------------------

# if __name__ == "__main__":
#     # Initialize DB and Node
#     rocks_adapter = PersistenceLayer()
#     node = StorageNode(node_id="node_alpha_1", db=rocks_adapter)

#     print("\n--- Scenario 1: Basic Workflow ---")
#     node.create_bucket("my-photos")
#     node.put_object("my-photos", "vacation.jpg", b"\xFF\xD8\xFF\xE0..IMAGE_DATA..", "image/jpeg")

#     retrieved = node.get_object("my-photos", "vacation.jpg")
#     if retrieved:
#         print(f"Retrieved: {retrieved.object_key} | ETag: {retrieved.etag} | LastModified: {retrieved.last_modified_iso}")

#     print("\n--- Scenario 2: CRDT Conflict Resolution ---")
#     # Simulate a sync from another node ("node_beta_2") that has OLDER data
#     # 1. Create an object manually that is OLD (time.time() - 1000)
#     old_meta = CRDTMetadata(timestamp=time.time() - 1000, node_id="node_beta_2")
#     old_obj = Object("my-photos", "vacation.jpg", b"OLD_DATA", old_meta)

#     # 2. Try to "write" this old data to our current node (as if syncing)
#     # The node should check the timestamp, see it's older than what we just wrote in Scenario 1, and IGNORE it.
#     print("Attempting to overwrite with older data...")
#     storage_key = node._hash_key(f"obj:my-photos/vacation.jpg")

#     # Manual merge simulation for demonstration
#     current_bytes = node.db.get(storage_key)
#     current_obj = Object.deserialize(current_bytes)

#     result_obj = current_obj.merge(old_obj)

#     if result_obj.data == b"OLD_DATA":
#         print("FAIL: Old data won.")
#     else:
#         print("SUCCESS: Current (newer) data persisted. CRDT logic worked.")

#     print("\n--- Scenario 3: Deletion (Tombstone) ---")
#     node.delete_object("my-photos", "vacation.jpg")

#     check_deleted = node.get_object("my-photos", "vacation.jpg")
#     if check_deleted is None:
#         print("Object successfully hidden (404).")

#         # Verify strictly that it is physically there but marked deleted
#         raw_bytes = node.db.get(storage_key)
#         raw_obj = Object.deserialize(raw_bytes)
#         print(f"Internal DB State: is_deleted={raw_obj.crdt_meta.is_deleted}")
