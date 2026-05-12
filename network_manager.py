import json
import socket
import struct
import threading
import protocol

HEADER_SIZE = 4
ENCODING = "utf-8"
MAX_MESSAGE_SIZE = 1024 * 1024

class NetworkManager:
    def __init__(self, node, timeout=3):
        self.node = node
        self.timeout = timeout

        self.server_socket = None
        self.running = False
        self.server_thread = None


    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.server_socket.bind((self.node.host, self.node.port))
        self.server_socket.listen()

        self.running = True

        self.server_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.server_thread.start()

        print(f"[{self.node.node_id}] listening on {self.node.host}:{self.node.port}")

    def stop(self):
        self.running = False

        if self.server_socket is not None:
            try:
                self.server_socket.close()
            except OSError:
                pass
        print(f"[{self.node.node_id}] network stopped")

    def send_request(self, host, port, message, expect_response=True):

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:

            sock.settimeout(self.timeout)
            sock.connect((host, int(port)))
            
            self.send_message(sock, message)

            if expect_response:
                return self.receive_message(sock)
            
            return None

    def send_message(self, sock, message):
        """
        il messaggio è del tipo
        message = {
            "type": "PING",
            "sender_id": "node_8002",
            "sender_host": "127.0.0.1",
            "sender_port": 8002,
            "payload": {}
        }
        """
        json_bytes = json.dumps(message).encode(ENCODING)
        header = struct.pack("!I", len(json_bytes))
        sock.sendall(header + json_bytes)

    def _recive_exact(self, sock, n):
        data = b""

        while len(data) < n:
            chunk = sock.recv(n - len(data))

            if chunk == b"":
                raise ConnectionError("Connection closed before receiving all data")
            data += chunk
        
        return data
    
    def receive_message(self, sock):
        header = self._recive_exact(sock, HEADER_SIZE)
        length = struct.unpack("!I", header)[0]
        if length <= 0:
            raise ValueError("Invalid message length")
        if length > MAX_MESSAGE_SIZE:
            raise ValueError("Message too large")
        json_data = self._recive_exact(sock, length).decode(ENCODING)
        return json.loads(json_data)


    def _accept_loop(self):

        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()

                worker = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                worker.start()

            except OSError:
                break
    

    def _handle_client(self, client_socket, client_address):
        with client_socket:
            client_socket.settimeout(self.timeout)

            try:
                message = self.receive_message(client_socket)

                if message is None:
                    return

                if message["type"] == protocol.MSG_DOWNLOAD_REQUEST:
                    self._handle_download_request(client_socket, message)
                    return

                response = self.node.handle_message(message, client_address)

                if response is not None:
                    self.send_message(client_socket, response)

            except socket.timeout:
                print(f"[{self.node.node_id}] timeout from {client_address}")

            except ConnectionError as error:
                print(f"[{self.node.node_id}] connection error from {client_address}: {error}")

            except Exception as error:
                print(f"[{self.node.node_id}] error handling client {client_address}: {error}")
    

    def _handle_download_request(self, client_socket, message):
        result = self.node.prepare_download(message)

        if result["status"] != "OK":
            header = protocol.create_download_header(
                self.node,
                status="ERROR",
                reason=result["reason"]
            )
            self.send_message(client_socket, header)
            return

        file_info = result["file_info"]

        header = protocol.create_download_header(
            self.node,
            status="OK",
            filename=file_info["filename"],
            file_size=file_info["size"],
            file_hash=file_info["hash"],
        )

        self.send_message(client_socket, header)

        with open(file_info["path"], "rb") as file:
            while True:
                chunk = file.read(65536)

                if not chunk:
                    break

                client_socket.sendall(chunk)

        print(
            f"[{self.node.node_id}] sent file "
            f"{file_info['filename']} to {message['sender_id']}"
        )
    
    def download_file(self, host, port, request_message, destination_path, expected_hash=None):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(self.timeout)
            sock.connect((host, int(port)))

            self.send_message(sock, request_message)

            header = self.receive_message(sock)

            if header is None:
                print("Download failed: no header received")
                return False

            if header["type"] != protocol.MSG_DOWNLOAD_HEADER:
                print("Download failed: invalid header")
                return False

            payload = header["payload"]

            if payload["status"] != "OK":
                print(f"Download failed: {payload.get('reason')}")
                return False

            file_size = int(payload["file_size"])
            received_hash = payload["file_hash"]

            bytes_received = 0

            with open(destination_path, "wb") as output:
                while bytes_received < file_size:
                    chunk_size = min(65536, file_size - bytes_received)
                    chunk = sock.recv(chunk_size)

                    if chunk == b"":
                        raise ConnectionError("Connection closed during file download")

                    output.write(chunk)
                    bytes_received += len(chunk)

            if expected_hash is not None and received_hash != expected_hash:
                print("Download warning: header hash differs from expected hash")
                return False

            return True