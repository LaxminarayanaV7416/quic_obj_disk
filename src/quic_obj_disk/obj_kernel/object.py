"""
Author: Laxminarayana Vadnala
Date: 2024-06-20
Description: This is base building block defination for Object Storage Kernel.
Email: lvadnala@nd.edu
"""

import hashlib
import time
import json

from obj_kernel.base import CRDTBase, CRDTMetadata


class Object(CRDTBase):
    """
    Represents a file/object in the system.
    Mimics AWS S3 Object structure.
    """

    def __init__(
        self,
        bucket_name: str,
        key: str,
        data: bytes,
        crdt_meta: CRDTMetadata,
        content_type: str = "application/octet-stream",
        user_meta: dict[str, str] | None = None,
    ):
        # Unique identification for DHT: bucket/key
        unique_key = f"{bucket_name}/{key}"
        super().__init__(unique_key, crdt_meta)

        self.bucket_name = bucket_name
        self.object_key = key
        self.data = data
        self.size = len(data)
        self.content_type = content_type
        self.user_meta = user_meta if user_meta else {}

        # AWS S3 Specific Attributes
        self.etag = hashlib.md5(data).hexdigest()  # Standard S3 ETag

    @property
    def last_modified_iso(self):
        """Returns AWS CLI compatible ISO 8601 timestamp"""
        return time.strftime(
            "%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(self.crdt_meta.timestamp)
        )

    def serialize(self) -> bytes:
        """
        Serialize object state to JSON (for RocksDB value).
        Note: In production, large 'data' blobs might be stored
        separately on disk, with only metadata in RocksDB.
        """
        payload = {
            "bucket": self.bucket_name,
            "key": self.object_key,
            "data_hex": self.data.hex(),  # Storing binary as hex for JSON safety
            "size": self.size,
            "content_type": self.content_type,
            "etag": self.etag,
            "crdt": self.crdt_meta.to_dict(),
            "user_meta": self.user_meta,
        }
        return json.dumps(payload).encode("utf-8")

    @classmethod
    def deserialize(cls, json_bytes: bytes) -> "Object":
        d = json.loads(json_bytes.decode("utf-8"))
        meta = CRDTMetadata(**d["crdt"])

        return cls(
            bucket_name=d["bucket"],
            key=d["key"],
            data=bytes.fromhex(d["data_hex"]),
            crdt_meta=meta,
            content_type=d["content_type"],
            user_meta=d["user_meta"],
        )
