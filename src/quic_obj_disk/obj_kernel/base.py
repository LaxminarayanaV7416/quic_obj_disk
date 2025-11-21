import dataclasses

@dataclasses.dataclass
class CRDTMetadata:
    """
    Metadata required for Conflict-free resolution (LWW).
    """
    timestamp: float  # Physical timestamp (or HLC)
    node_id: str      # ID of the node that performed the write (tiebreaker)
    is_deleted: bool = False # Tombstone flag

    def to_dict(self):
        return dataclasses.asdict(self)

class CRDTBase:
    """
    Base class for Buckets and Objects ensuring Last-Write-Wins logic.
    """
    def __init__(self, key: str, metadata: CRDTMetadata):
        self.key = key
        self.crdt_meta = metadata

    def merge(self, other: 'CRDTBase') -> 'CRDTBase':
        """
        The Core CRDT Merge function.
        Returns the instance with the newer timestamp.
        """
        if other.crdt_meta.timestamp > self.crdt_meta.timestamp:
            return other
        elif other.crdt_meta.timestamp < self.crdt_meta.timestamp:
            return self
        else:
            # Tiebreaker: Compare Node IDs lexicographically
            if other.crdt_meta.node_id > self.crdt_meta.node_id:
                return other
            return self