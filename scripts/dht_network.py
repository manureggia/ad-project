#!/usr/bin/env python3
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "runtime" / "dht_network"
PID_DIR = RUNTIME_DIR / "pids"
LOG_DIR = RUNTIME_DIR / "logs"

HOST = "127.0.0.1"
BASE_PORT = 9001
NODE_COUNT = 6

TOPOLOGY = {
    9001: None,
    9002: 9001,
    9003: 9001,
    9004: 9002,
    9005: 9002,
    9006: 9003,
}


def node_name(index):
    return f"node_{index:02d}"


def node_dir(index):
    return RUNTIME_DIR / node_name(index)


def shared_dir(index):
    return node_dir(index) / "shared"


def pid_path(port):
    return PID_DIR / f"node_{port}.pid"


def log_path(port):
    return LOG_DIR / f"node_{port}.log"


def is_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def create_file(path):
    path.write_text(f"{path.name}\n", encoding="utf-8")


def prepare_folders():
    PID_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    (RUNTIME_DIR / "manual" / "shared").mkdir(parents=True, exist_ok=True)

    for index in range(1, NODE_COUNT + 1):
        current_shared_dir = shared_dir(index)
        current_shared_dir.mkdir(parents=True, exist_ok=True)

        create_file(current_shared_dir / f"file_node_{index:02d}.txt")
        create_file(current_shared_dir / f"notes_node_{index:02d}.md")

    for index in (1, 3, 5):
        create_file(shared_dir(index) / "common.txt")


def start_node(index):
    port = BASE_PORT + index - 1
    bootstrap_port = TOPOLOGY[port]
    current_pid_path = pid_path(port)

    if current_pid_path.exists():
        pid = int(current_pid_path.read_text(encoding="utf-8").strip())

        if is_running(pid):
            print(f"node on port {port} already running pid={pid}")
            return

        current_pid_path.unlink()

    command = [
        sys.executable,
        "-u",
        str(ROOT / "main.py"),
        "--host",
        HOST,
        "--port",
        str(port),
        "--shared",
        str(shared_dir(index)),
        "--no-peer-sync",
        "--no-cli",
    ]

    if bootstrap_port is not None:
        command.extend(["--bootstrap", f"{HOST}:{bootstrap_port}"])

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    log_file = log_path(port).open("a", encoding="utf-8")
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    current_pid_path.write_text(f"{process.pid}\n", encoding="utf-8")
    print(f"started node_{port} pid={process.pid} log={log_path(port)}")


def start_network():
    prepare_folders()

    for index in range(1, NODE_COUNT + 1):
        start_node(index)
        time.sleep(0.4)

    print()
    print("Network ready.")
    print("Topology:")

    for port, bootstrap_port in TOPOLOGY.items():
        if bootstrap_port is None:
            print(f"  {port}: bootstrap")
        else:
            print(f"  {port}: joins {bootstrap_port}")

    print()
    print("Useful commands:")
    print("  python scripts/dht_network.py status")
    print("  python scripts/dht_network.py stop")
    print("  tail -f runtime/dht_network/logs/node_9001.log")
    print(
        "  python main.py --port 9010 "
        "--shared runtime/dht_network/manual/shared "
        "--bootstrap 127.0.0.1:9001 --no-peer-sync"
    )


def stop_network():
    if not PID_DIR.exists():
        print("No PID directory found.")
        return

    for current_pid_path in sorted(PID_DIR.glob("*.pid")):
        pid = int(current_pid_path.read_text(encoding="utf-8").strip())

        if not is_running(pid):
            current_pid_path.unlink()
            continue

        print(f"stopping pid={pid}")
        os.killpg(pid, signal.SIGINT)

        for _ in range(20):
            if not is_running(pid):
                break
            time.sleep(0.1)

        if is_running(pid):
            os.killpg(pid, signal.SIGTERM)

        current_pid_path.unlink(missing_ok=True)


def show_status():
    if not PID_DIR.exists():
        print("No nodes started.")
        return

    pid_files = sorted(PID_DIR.glob("*.pid"))

    if not pid_files:
        print("No nodes running.")
        return

    for current_pid_path in pid_files:
        port = current_pid_path.stem.split("_")[-1]
        pid = int(current_pid_path.read_text(encoding="utf-8").strip())
        state = "running" if is_running(pid) else "stopped"
        print(f"node_{port}: {state} pid={pid} log={log_path(port)}")


def main():
    parser = argparse.ArgumentParser(description="Manage a local sparse DHT network")
    parser.add_argument(
        "command",
        choices=("start", "stop", "restart", "status"),
        help="Action to execute",
    )
    args = parser.parse_args()

    if args.command == "start":
        start_network()
    elif args.command == "stop":
        stop_network()
    elif args.command == "restart":
        stop_network()
        start_network()
    elif args.command == "status":
        show_status()


if __name__ == "__main__":
    main()
