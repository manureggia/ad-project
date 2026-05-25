# protocol.py

MSG_JOIN = 'JOIN'
MSG_JOIN_REPLY = "JOIN_REPLY"
MSG_PING = "PING"
MSG_PONG = "PONG"
MSG_ERROR = "ERROR"
MSG_SEARCH = "SEARCH"
MSG_SEARCH_REPLY = "SEARCH_REPLY"
MSG_DOWNLOAD_REQUEST = "DOWNLOAD_REQUEST"
MSG_DOWNLOAD_HEADER = "DOWNLOAD_HEADER"
MSG_DHT_PUT = "DHT_PUT"
MSG_DHT_PUT_REPLY = "DHT_PUT_REPLY"
MSG_DHT_GET = "DHT_GET"
MSG_DHT_GET_REPLY = "DHT_GET_REPLY"

REQUIRED_FIELDS = {
    "type",
    "sender_id",
    "sender_host",
    "sender_port",
    "payload",
}


def create_base_message(msg_type, node, payload=None):
    """
    Crea la struttura comune di ogni messaggio.
    """
    if payload is None:
        payload = {}

    return {
        "type": msg_type,
        "sender_id": node.node_id,
        "sender_host": node.host,
        "sender_port": node.port,
        "payload": payload,
    }


def create_ping(node):
    return create_base_message(MSG_PING, node)
    


def create_pong(node):
    return create_base_message(MSG_PONG, node)



def create_join(node):
    return create_base_message(MSG_JOIN, node)



def create_join_reply(node, peers):
    """
    Crea un messaggio JOIN_REPLY.

    peers deve essere una lista di dizionari, non una lista di oggetti Peer.
    Esempio:
    [
        {"node_id": "node_8001", "host": "127.0.0.1", "port": 8001},
        {"node_id": "node_8002", "host": "127.0.0.1", "port": 8002}
    ]
    """
    return create_base_message(MSG_JOIN_REPLY, node, {"peers": peers})

def create_error(node, reason):
    return create_base_message(
        MSG_ERROR,
        node,
        {"reason": reason}
    )


def is_valid_message(message):
    if not isinstance(message, dict):
        return False

    if not REQUIRED_FIELDS.issubset(message.keys()):
        return False

    if not isinstance(message["payload"], dict):
        return False

    return True


def create_search(node, filename, request_id, ttl):
    return create_base_message(
        MSG_SEARCH,
        node,
        {
            "filename": filename,
            "request_id": request_id,
            "origin_id": node.node_id,
            "origin_host": node.host,
            "origin_port": node.port,
            "ttl": ttl,
        }
    )

def forward_search(node, original_message):
    payload = original_message["payload"]

    return create_base_message(
        MSG_SEARCH,
        node,
        {
            "filename": payload["filename"],
            "request_id": payload["request_id"],
            "origin_id": payload["origin_id"],
            "origin_host": payload["origin_host"],
            "origin_port": payload["origin_port"],
            "ttl": int(payload["ttl"]) - 1,
        }
    )


def create_search_reply(node, request_id, file_info):
    return create_base_message(
        MSG_SEARCH_REPLY,
        node,
        {
            "request_id": request_id,
            "file": file_info,
        }
    )

def create_download_request(node, filename, file_hash):
    return create_base_message(
        MSG_DOWNLOAD_REQUEST,
        node,
        {
            "filename": filename,
            "file_hash": file_hash,
        }
    )


def create_download_header(node, status, filename=None, file_size=0, file_hash=None, reason=None):
    payload = {
        "status": status,
        "filename": filename,
        "file_size": file_size,
        "file_hash": file_hash,
        "reason": reason,
    }

    return create_base_message(
        MSG_DOWNLOAD_HEADER,
        node,
        payload
    )


def create_dht_put(node, filename, file_key, provider):
    return create_base_message(
        MSG_DHT_PUT,
        node,
        {
            "filename": filename,
            "file_key": file_key,
            "provider": provider,
        }
    )


def create_dht_put_reply(node, filename, stored=True, reason=None):
    return create_base_message(
        MSG_DHT_PUT_REPLY,
        node,
        {
            "filename": filename,
            "stored": stored,
            "reason": reason,
        }
    )


def create_dht_get(node, filename, file_key, request_id):
    return create_base_message(
        MSG_DHT_GET,
        node,
        {
            "filename": filename,
            "file_key": file_key,
            "request_id": request_id,
        }
    )


def create_dht_get_reply(node, filename, request_id, providers):
    return create_base_message(
        MSG_DHT_GET_REPLY,
        node,
        {
            "filename": filename,
            "request_id": request_id,
            "providers": providers,
        }
    )
