from peer_table import PeerTable, Peer
from network_manager import NetworkManager
from file_manager import FileManager
import protocol
import uuid

class Node: 
    
    def __init__(self, node_id, host, port, shared_folder):
        self.node_id = node_id
        self.host = host
        self.port = int(port)
        self.shared_folder = shared_folder
    
        self.running = False
        self.peer_table = PeerTable()
        self.network_manager = NetworkManager(self)
        self.file_manager = FileManager(shared_folder)
        self.seen_requests = set()

        self.search_results = {}

    def start(self):

        self.running = True
        print(f'Starting Node {self.node_id}')
        self.network_manager.start()
        self.file_manager.scan_files()

    def stop(self):
        self.running = False
        print(f'Stopping Node {self.node_id}')
        self.network_manager.stop()
    
    def join(self, bootstrap_host, bootstrap_port):
        
        join_message = protocol.create_join(self)
        response = self.network_manager.send_request(bootstrap_host, bootstrap_port, join_message, True)
        
        if not response:
            print(f'Faild Join with node {bootstrap_host}:{bootstrap_port}')
            return False
        
        if response["type"] != protocol.MSG_JOIN_REPLY:
            print(f'Error, message unexpected, expected {protocol.MSG_JOIN_REPLY}, recived {response}')
            return False
        
        peers = response["payload"]["peers"]
        self.peer_table.join_table(peers, self_node_id=self.node_id)

        print(
        f"[{self.node_id}] JOIN successful with "
        f"{response['sender_id']} at {response['sender_host']}:{response['sender_port']}"
        )

        print(f"[{self.node_id}] known peers: {self.peer_table.count()}")

        return True

    def ping(self, bootstrap_host, bootstrap_port):
        ping = protocol.create_ping(self)
        response = self.network_manager.send_request(bootstrap_host, bootstrap_port, ping, True)

        if response is None:
            print("Ping failed")
            return False

        if response["type"] == protocol.MSG_PONG:
            print("PONG received")
            return True

    def handle_message(self, message, client_address):

        if not protocol.is_valid_message(message):
            return protocol.create_error(self, "Invalid message")
        

        if message["type"] == protocol.MSG_JOIN:
            return self.handle_join(message)
            
        if message["type"] == protocol.MSG_PING:
            return self.handle_ping(message)
        
        if message["type"] == protocol.MSG_SEARCH:
            return self.handle_search(message)
        
        if message["type"] == protocol.MSG_SEARCH_REPLY:
            return self.handle_search_reply(message)
        
        return protocol.create_error(self, "Unknown message type")
    
    def handle_join(self, message):
        new_peer = Peer(
            message["sender_id"], 
            message["sender_host"], 
            message["sender_port"]
            )
        new_peer.mark_seen()
        self.peer_table.add_peer(new_peer)
        peers = self.peer_table.to_list()
        peers.append({
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port
        })
        
        return protocol.create_join_reply(self, peers)
    
    def handle_ping(self, message):
        pong = protocol.create_pong(self)
        return pong
    
    def status(self):
        return {
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port,
            "shared_folder": self.shared_folder,
            "running": self.running,
            "known_peers": self.peer_table.count(),
        }
    
    def search(self, filename, ttl=3):
        request_id = str(uuid.uuid4())
        self.seen_requests.add(request_id)
        
        peers = self.peer_table.get_all_peers()

        if not peers:
            print(f"[{self.node_id}] No peers known")
            return None

        print(
            f"[{self.node_id}] Starting search for {filename} "
            f"request_id={request_id} ttl={ttl}"
        )

        for peer in peers:
            search_message = protocol.create_search(
                self,
                filename,
                request_id,
                ttl
            )

            self.network_manager.send_request(
                peer.host,
                peer.port,
                search_message,
                expect_response=False
            )

        return request_id
    

    def handle_search(self, message):
        payload = message["payload"]

        filename = payload.get("filename")
        request_id = payload.get("request_id")
        ttl = int(payload.get("ttl", 0))

        origin_host = payload.get("origin_host")
        origin_port = payload.get("origin_port")
        origin_id = payload.get("origin_id")

        if filename is None:
            return protocol.create_error(self, "Missing filename")

        if request_id is None:
            return protocol.create_error(self, "Missing request_id")

        if request_id in self.seen_requests:
            print(f"[{self.node_id}] Duplicate SEARCH ignored: {request_id}")
            return None

        self.seen_requests.add(request_id)

        print(
            f"[{self.node_id}] SEARCH {filename} "
            f"from {message['sender_id']} ttl={ttl}"
        )

        if self.file_manager.has_file(filename):
            file_info = self.file_manager.get_file_info(filename)

            public_file_info = {
                "filename": file_info["filename"],
                "size": file_info["size"],
                "hash": file_info["hash"],
            }

            print(
                f"[{self.node_id}] SEARCH hit for {filename}, "
                f"sending reply to {origin_host}:{origin_port}"
            )

            reply = protocol.create_search_reply(
                self,
                request_id,
                public_file_info
            )

            self.network_manager.send_request(
                origin_host,
                origin_port,
                reply,
                expect_response=False
            )

        if ttl <= 0:
            return None

        sender_id = message["sender_id"]

        for peer in self.peer_table.get_all_peers():
            if peer.node_id == sender_id:
                continue

            if peer.node_id == origin_id:
                continue

            if peer.node_id == self.node_id:
                continue

            forward_message = protocol.forward_search(self, message)

            self.network_manager.send_request(
                peer.host,
                peer.port,
                forward_message,
                expect_response=False
            )

        return None
    

    def handle_search_reply(self, message):
        payload = message["payload"]

        request_id = payload.get("request_id")
        file_info = payload.get("file")

        if request_id is None:
            return protocol.create_error(self, "Missing request_id")

        if file_info is None:
            return protocol.create_error(self, "Missing file info")

        result = {
            "node_id": message["sender_id"],
            "host": message["sender_host"],
            "port": message["sender_port"],
            "file": file_info,
        }

        if request_id not in self.search_results:
            self.search_results[request_id] = []

        self.search_results[request_id].append(result)

        print(
            f"\n[{self.node_id}] SEARCH RESULT "
            f"request_id={request_id}\n"
            f"  index: {len(self.search_results[request_id]) - 1}\n"
            f"  from: {result['node_id']} "
            f"{result['host']}:{result['port']}\n"
            f"  file: {file_info['filename']}\n"
            f"  size: {file_info['size']}\n"
            f"  hash: {file_info['hash']}\n"
        )

        return None
    
    def get_search_result(self, request_id, index):
        if request_id not in self.search_results:
            return None

        results = self.search_results[request_id]

        if index < 0 or index >= len(results):
            return None

        return results[index]
    
    def show_search_results(self):
        if not self.search_results:
            print(f"[{self.node_id}] No search results available")
            return

        print("\n--- SEARCH RESULTS ---")

        for request_id, results in self.search_results.items():
            print(f"request_id={request_id}")

            for index, result in enumerate(results):
                file_info = result["file"]

                print(
                    f"  [{index}] "
                    f"{result['node_id']} "
                    f"{result['host']}:{result['port']} "
                    f"file={file_info['filename']} "
                    f"size={file_info['size']} "
                    f"hash={file_info['hash']}"
                )

        print("----------------------\n")
    
    def prepare_download(self, message):
        payload = message["payload"]

        filename = payload.get("filename")
        expected_hash = payload.get("file_hash")

        if filename is None:
            return {
                "status": "ERROR",
                "reason": "Missing filename",
                "file_info": None,
            }

        if not self.file_manager.has_file(filename):
            return {
                "status": "ERROR",
                "reason": "File not found",
                "file_info": None,
            }

        file_info = self.file_manager.get_file_info(filename)

        if expected_hash is not None and file_info["hash"] != expected_hash:
            return {
                "status": "ERROR",
                "reason": "Hash mismatch",
                "file_info": None,
            }

        return {
            "status": "OK",
            "reason": None,
            "file_info": file_info,
        }
    
    def download_from_result(self, request_id, index):
        result = self.get_search_result(request_id, index)

        if result is None:
            print(f"[{self.node_id}] Invalid search result")
            return False

        file_info = result["file"]

        filename = file_info["filename"]
        file_hash = file_info["hash"]

        destination_path = self.file_manager.get_download_path(filename)

        request = protocol.create_download_request(
            self,
            filename,
            file_hash
        )

        print(
            f"[{self.node_id}] Downloading {filename} "
            f"from {result['node_id']} {result['host']}:{result['port']}"
        )

        ok = self.network_manager.download_file(
            result["host"],
            result["port"],
            request,
            destination_path,
            expected_hash=file_hash
        )

        if not ok:
            print(f"[{self.node_id}] Download failed")
            return False

        downloaded_hash = self.file_manager.compute_hash(destination_path)

        if downloaded_hash != file_hash:
            print(f"[{self.node_id}] Download corrupted: hash mismatch")
            return False

        print(
            f"[{self.node_id}] Download completed: {destination_path}"
        )
        print(f"[{self.node_id}] Hash verified: {downloaded_hash}")

        return True
    
    