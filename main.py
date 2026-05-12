import argparse
from node import Node


def parse_bootstrap(bootstrap):
    """
    Converte una stringa tipo:
        127.0.0.1:8001
    in:
        ("127.0.0.1", 8001)
    """
    if bootstrap is None:
        return None, None

    host, port = bootstrap.split(":")
    return host, int(port)


def print_help():
    print("""
Comandi disponibili:

  help
      Mostra questo aiuto.

  status
      Mostra lo stato del nodo.

  peers
      Mostra i peer conosciuti.

  ping <host> <port>
      Manda un PING a un peer.

  join <host> <port>
      Esegue JOIN verso un peer.
 
  search <filename>
      Esegue una ricerca con metodo Flooding per trovare un file nei peers.
  
  results
      Restituisce i risultati delle ricerce precedenti.
  
  download <request_id> <index>
      Scarica un file da un risultato di ricerca.

  exit
      Spegne il nodo.
""")


def print_status(node):
    status = node.status()

    print("\n--- STATUS ---")
    for key, value in status.items():
        print(f"{key}: {value}")
    print("--------------\n")


def print_peers(node):
    peers = node.peer_table.to_list()

    print("\n--- PEERS ---")

    if not peers:
        print("Nessun peer conosciuto.")
    else:
        for peer in peers:
            print(
                f"{peer['node_id']} "
                f"{peer['host']}:{peer['port']} "
                f"fail_count={peer['fail_count']}"
            )

    print("-------------\n")


def cli_loop(node):
    print(f"[{node.node_id}] CLI ready. Type 'help' for commands.")

    while node.running:
        try:
            command = input("> ").strip()

            if command == "":
                continue

            parts = command.split()
            cmd = parts[0]

            if cmd == "help":
                print_help()

            elif cmd == "status":
                print_status(node)

            elif cmd == "peers":
                print_peers(node)

            elif cmd == "ping":
                if len(parts) != 3:
                    print("Uso: ping <host> <port>")
                    continue

                host = parts[1]
                port = int(parts[2])
                node.ping(host, port)

            elif cmd == "join":
                if len(parts) != 3:
                    print("Uso: join <host> <port>")
                    continue

                host = parts[1]
                port = int(parts[2])
                node.join(host, port)
            
            elif cmd == "files":
                files = node.file_manager.list_files()

                print("\n--- LOCAL FILES ---")

                if not files:
                    print("Nessun file condiviso.")
                else:
                    for file in files:
                        print(
                            f"{file['filename']} "
                            f"size={file['size']} "
                            f"hash={file['hash']}"
                        )

                print("-------------------\n")

            elif cmd == "search":
                if len(parts) != 2:
                    print("Uso: search <filename>")
                    continue

                filename = parts[1]
                node.search(filename)

            elif cmd == "results":
                node.show_search_results()
            
            elif cmd == "download":
                if len(parts) != 3:
                    print("Uso: download <request_id> <index>")
                    continue

                request_id = parts[1]

                try:
                    index = int(parts[2])
                except ValueError:
                    print("Index must be an integer")
                    continue

                node.download_from_result(request_id, index)

            elif cmd == "exit":
                node.stop()
                break

            else:
                print(f"Comando sconosciuto: {cmd}")
                print("Scrivi 'help' per vedere i comandi disponibili.")

        except KeyboardInterrupt:
            node.stop()
            break

        except Exception as error:
            print(f"Errore: {error}")


def main():
    parser = argparse.ArgumentParser(
        description="Simple P2P node"
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host su cui il nodo ascolta"
    )

    parser.add_argument(
        "--port",
        required=True,
        type=int,
        help="Porta su cui il nodo ascolta"
    )

    parser.add_argument(
        "--shared",
        required=True,
        help="Cartella condivisa del nodo"
    )

    parser.add_argument(
        "--bootstrap",
        default=None,
        help="Nodo bootstrap nel formato host:port"
    )

    args = parser.parse_args()

    node_id = f"node_{args.port}"

    node = Node(
        node_id=node_id,
        host=args.host,
        port=args.port,
        shared_folder=args.shared
    )

    node.start()

    bootstrap_host, bootstrap_port = parse_bootstrap(args.bootstrap)

    if bootstrap_host is not None:
        print(
            f"[{node.node_id}] joining bootstrap "
            f"{bootstrap_host}:{bootstrap_port}"
        )
        node.join(bootstrap_host, bootstrap_port)

    cli_loop(node)


if __name__ == "__main__":
    main()