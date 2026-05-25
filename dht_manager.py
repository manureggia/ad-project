import hashlib
import threading

HASH_BITS = 160
HASH_SPACE = 2 ** HASH_BITS


def hash_key(value):
    digest = hashlib.sha1(str(value).encode("utf-8")).hexdigest()
    return int(digest, 16)


class DHTManager:
    def __init__(self, node):
        self.node = node
        self.index = {}
        self.lock = threading.Lock()

    def get_node_key(self, node_id=None):
        if node_id is None:
            node_id = self.node.node_id
        return hash_key(node_id)

    def get_file_key(self, filename):
        return hash_key(filename)

    def get_ring(self):
        nodes = [
            {
                "node_id": self.node.node_id,
                "host": self.node.host,
                "port": self.node.port,
                "key": self.get_node_key(),
            }
        ]

        for peer in self.node.peer_table.get_all_peers():
            nodes.append({
                "node_id": peer.node_id,
                "host": peer.host,
                "port": peer.port,
                "key": self.get_node_key(peer.node_id),
            })

        return sorted(nodes, key=lambda item: item["key"])

    def find_successor(self, key):
        ring = self.get_ring()

        for node in ring:
            if node["key"] >= key:
                return node

        return ring[0]

    def is_local_successor(self, key):
        successor = self.find_successor(key)
        return successor["node_id"] == self.node.node_id

    def add_provider(self, filename, provider):
        with self.lock:
            providers = self.index.setdefault(filename, [])

            provider_key = (
                provider["node_id"],
                provider["file"]["hash"],
            )

            for index, existing in enumerate(providers):
                existing_key = (
                    existing["node_id"],
                    existing["file"]["hash"],
                )

                if existing_key == provider_key:
                    providers[index] = provider
                    return

            providers.append(provider)

    def get_providers(self, filename):
        with self.lock:
            return list(self.index.get(filename, []))

    def to_list(self):
        with self.lock:
            rows = []

            for filename, providers in self.index.items():
                rows.append({
                    "filename": filename,
                    "key": self.get_file_key(filename),
                    "providers": list(providers),
                })

            return rows
