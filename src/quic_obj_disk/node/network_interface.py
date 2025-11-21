from abc import ABC, abstractmethod
from typing import Any, Optional


class NetworkLayer(ABC):
    """
    Interface for P2P communication.
    In the Flask implementation (server.py), this will make HTTP requests to peers.
    """

    @abstractmethod
    def send_message(self, target_node_address: str, message: dict[str, Any]):
        # This is a stub. The actual HTTP implementation is injected in server.py
        pass


class DHTRouter:
    """
    Logic to map Hash -> Node Address.
    """

    def __init__(self, my_node_id: str, peers: dict[str, str]):
        self.my_node_id = my_node_id
        # Map of node_id -> http_address (e.g., "node2:5000")
        self.peer_map = peers

    def add_peer(self, node_id: str, address: str):
        self.peer_map[node_id] = address

    def get_all_peers(self):
        return self.peer_map

    def get_owner(self, key_hash: str) -> str:
        """
        Consistent Hashing (Simplified Modulo for demo)
        """
        # Include self in the ring
        all_nodes = sorted(list(self.peer_map.keys()) + [self.my_node_id])
        hash_int = int(key_hash, 16)
        node_index = hash_int % len(all_nodes)
        return all_nodes[node_index]

    def get_address(self, node_id: str) -> Optional[str]:
        return self.peer_map.get(node_id)
