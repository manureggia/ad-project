import time


class Peer:
    def __init__(self, node_id, host, port):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.last_seen = None
        self.fail_count = 0
    
    def mark_seen(self):
        self.last_seen = time.time()
        self.fail_count = 0

    def mark_failed(self):
        self.fail_count += 1

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port,
            "last_seen": self.last_seen,
            "fail_count": self.fail_count,
        }

class PeerTable:

    def __init__(self):
        self.table = {}

    def add_peer(self, peer):
        self.table[peer.node_id] = peer

    def remove_peer(self, node_id):
        if node_id in self.table:
            self.table.pop(node_id)

    def get_peer(self, node_id):
        return self.table.get(node_id)

    def get_all_peers(self):
        return list(self.table.values())

    def has_peer(self, node_id):
        return node_id in self.table

    def count(self):
        return len(self.table)

    def mark_seen(self, node_id):
        peer = self.get_peer(node_id)
        if peer is not None:
            peer.mark_seen()

    def mark_failed(self, node_id):
        peer = self.get_peer(node_id)
        if peer is not None:
            peer.mark_failed()

    def join_table(self, peertable, self_node_id=None):
        if isinstance(peertable, PeerTable):
            entries = peertable.get_all_peers()
        else:
            entries = peertable

        for entry in entries:
            if isinstance(entry, Peer):
                peer = entry

            elif isinstance(entry, dict):
                peer = Peer(
                    entry["node_id"],
                    entry["host"],
                    entry["port"]
                )
                peer.last_seen = entry.get("last_seen")
                peer.fail_count = entry.get("fail_count", 0)

            else:
                continue

            if self_node_id is not None and peer.node_id == self_node_id:
                continue

            if not self.has_peer(peer.node_id):
                self.add_peer(peer)

    def to_list(self):
        return [peer.to_dict() for peer in self.table.values()]