import json

from obj_kernel.base import CRDTBase, CRDTMetadata


class Bucket(CRDTBase):
    """
    Represents a container for objects.
    """

    def __init__(self, name: str, crdt_meta: CRDTMetadata, owner: str = "admin"):
        super().__init__(name, crdt_meta)
        self.name = name
        self.owner = owner
        # In a pure KV store, the bucket doesn't physically contain objects.
        # It just exists to validate the namespace exists.

    def serialize(self) -> bytes:
        payload = {
            "name": self.name,
            "owner": self.owner,
            "crdt": self.crdt_meta.to_dict(),
        }
        return json.dumps(payload).encode("utf-8")

    @classmethod
    def deserialize(cls, json_bytes: bytes) -> "Bucket":
        d = json.loads(json_bytes.decode("utf-8"))
        meta = CRDTMetadata(**d["crdt"])
        return cls(name=d["name"], crdt_meta=meta, owner=d["owner"])
