from typing import Optional

class PersistenceLayer:
    """
    Wrapper for RocksDB. 
    In a real deployment, import rocksdb and use the C++ bindings.
    Here, we use a dictionary/json emulation for portability.
    """
    def __init__(self, db_path: str = "./data_store"):
        self.db_path = db_path
        # MOCK implementation. Replace with:
        # self.db = rocksdb.DB(db_path, rocksdb.Options(create_if_missing=True))
        self._mem_db: dict[bytes, bytes] = {}
        print(f"[System] Storage initialized at {db_path}")

    def put(self, key: bytes, value: bytes):
        # REAL: self.db.put(key, value)
        self._mem_db[key] = value

    def get(self, key: bytes) -> Optional[bytes]:
        # REAL: return self.db.get(key)
        return self._mem_db.get(key)

    def delete(self, key: bytes):
        # REAL: self.db.delete(key)
        if key in self._mem_db:
            del self._mem_db[key]
            
    def scan_prefix(self, prefix: bytes) -> list[tuple[bytes, bytes]]:
        # REAL: Use rocksdb.Iterator
        results = []
        for k, v in self._mem_db.items():
            if k.startswith(prefix):
                results.append((k, v))
        return results