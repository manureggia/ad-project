# AD Project - P2P File Sharing

Progetto Python per sistemi distribuiti: una piccola rete peer-to-peer in cui ogni nodo condivide file, scopre altri peer, cerca file e li scarica via TCP.

Il branch `dht-search` aggiunge una ricerca basata su **Chord** tramite Distributed Hash Table (DHT).

## Funzionalita

- Avvio di nodi P2P indipendenti.
- Join tramite nodo bootstrap.
- Tabella dei peer conosciuti.
- Ricerca classica con flooding e TTL.
- Ricerca DHT con Chord semplificato.
- Download dei file trovati.
- Script per avviare una rete locale di test.

## File principali

- `main.py`: CLI del nodo.
- `node.py`: logica principale del nodo P2P.
- `network_manager.py`: comunicazione TCP.
- `protocol.py`: messaggi del protocollo.
- `peer_table.py`: gestione dei peer conosciuti.
- `file_manager.py`: scansione, hash e download dei file.
- `dht_manager.py`: hashing e indice DHT per Chord semplificato.
- `scripts/dht_network.py`: avvio di una rete locale di prova.

## Avvio manuale

Nodo bootstrap:

```bash
python main.py --port 8001 --shared shared_1
```

Secondo nodo:

```bash
python main.py --port 8002 --shared shared_2 --bootstrap 127.0.0.1:8001
```

Terzo nodo:

```bash
python main.py --port 8003 --shared shared_3 --bootstrap 127.0.0.1:8001
```

## Comandi CLI

Dentro un nodo:

```text
help
status
peers
files
search <filename>
dht_search <filename>
dht_index
results
download <request_id> <index>
exit
```

`search` usa il flooding, mentre `dht_search` usa Chord.

## Rete di test

Per creare cartelle, file di prova e avviare 6 nodi locali:

```bash
python scripts/dht_network.py start
```

Controllo stato:

```bash
python scripts/dht_network.py status
```

Spegnimento:

```bash
python scripts/dht_network.py stop
```

Log dei nodi:

```bash
tail -f runtime/dht_network/logs/node_9001.log
```

Per entrare nella rete con un nodo manuale:

```bash
python main.py --port 9010 --shared runtime/dht_network/manual/shared --bootstrap 127.0.0.1:9001 --no-peer-sync
```