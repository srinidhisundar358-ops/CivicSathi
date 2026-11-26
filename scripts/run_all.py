import argparse
from pathlib import Path
import subprocess
import sys
from threading import Thread
from time import sleep


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.ports import BACKEND

COMMANDS = {
    "backend": [
        "uvicorn", "p1_core_backend.main:app", "--host", "0.0.0.0",
        "--port", str(BACKEND),
    ],
    "documents": ["p2_documents.documents_mcp.server"],
    "digilocker": ["p2_documents.digilocker_mcp.server"],
    "formfill": ["p2_documents.formfill_mcp.server"],
    "services": ["p3_services_inbox.services_mcp.server"],
    "inbox": ["p3_services_inbox.inbox_mcp.server"],
    "deadlines": ["p1_core_backend.deadlines_mcp.server"],
}


def forward_logs(name, stream):
    with stream:
        for line in stream:
            print(f"[{name}] {line.rstrip()}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Comma-separated names to start")
    args = parser.parse_args()
    names = list(dict.fromkeys(args.only.split(","))) if args.only else list(COMMANDS)
    unknown = set(names) - COMMANDS.keys()
    if unknown:
        parser.error(f"Unknown process names: {', '.join(sorted(unknown))}")

    processes = {}
    threads = []
    try:
        for name in names:
            process = subprocess.Popen(
                [sys.executable, "-u", "-m", *COMMANDS[name]],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
            )
            processes[name] = process
            thread = Thread(target=forward_logs, args=(name, process.stdout), daemon=True)
            threads.append(thread)
            thread.start()

        while True:
            for name, process in processes.items():
                status = process.poll()
                if status is not None:
                    print(f"[{name}] exited with status {status}", file=sys.stderr)
                    return status or 1
            sleep(0.2)
    except KeyboardInterrupt:
        return 0
    finally:
        for process in processes.values():
            if process.poll() is None:
                process.terminate()
        for process in processes.values():
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for thread in threads:
            thread.join(timeout=1)


if __name__ == "__main__":
    raise SystemExit(main())
