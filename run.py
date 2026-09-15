from __future__ import annotations

import signal
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def start_process(args: list[str]) -> subprocess.Popen:
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    return subprocess.Popen(
        args,
        cwd=str(PROJECT_ROOT),
        creationflags=creationflags,
    )


def terminate_processes(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is not None:
            continue

        try:
            if sys.platform.startswith("win"):
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                process.terminate()
        except Exception:
            pass

    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def main() -> None:
    backend_command = [sys.executable, "-m", "uvicorn", "src.api.main:app", "--port", "8000"]
    frontend_command = [sys.executable, "-m", "streamlit", "run", "src/ui/app.py"]

    processes = [start_process(backend_command), start_process(frontend_command)]

    try:
        while True:
            for process in processes:
                try:
                    return_code = process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    continue

                if return_code is not None:
                    print(f"Child process exited with code {return_code}. Stopping remaining processes...")
                    terminate_processes(processes)
                    raise SystemExit(return_code)
    except KeyboardInterrupt:
        print("KeyboardInterrupt received, stopping child processes...")
        terminate_processes(processes)


if __name__ == "__main__":
    main()