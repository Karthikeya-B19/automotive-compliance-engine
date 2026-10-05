from __future__ import annotations

import signal
import secrets
import socket
import subprocess
import sys
import time
import os
import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parent


def start_process(args: list[str], *, env: dict[str, str] | None = None) -> subprocess.Popen:
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    return subprocess.Popen(
        args,
        cwd=str(PROJECT_ROOT),
        creationflags=creationflags,
        env=env,
    )


def find_available_port(preferred_port: int, *, attempts: int = 50) -> int:
    """Return the first available localhost TCP port at or above the preference."""
    for port in range(preferred_port, preferred_port + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                candidate.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                candidate.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(
        f"No free localhost port found between {preferred_port} and "
        f"{preferred_port + attempts - 1}."
    )


def wait_for_backend(process: subprocess.Popen, health_url: str, timeout: float = 20.0) -> None:
    """Wait until the API is healthy or fail with a useful startup error."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        return_code = process.poll()
        if return_code is not None:
            raise RuntimeError(f"The API process exited during startup with code {return_code}.")
        try:
            with urlopen(health_url, timeout=1.0) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            time.sleep(0.2)
    raise RuntimeError(f"The API did not become healthy within {timeout:.0f} seconds.")


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
    preferred_api_port = int(os.getenv("REVIEW_API_PORT", "8000"))
    preferred_ui_port = int(os.getenv("REVIEW_UI_PORT", "8501"))
    api_port = find_available_port(preferred_api_port)
    ui_port = find_available_port(preferred_ui_port)

    backend_command = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(api_port),
    ]
    frontend_command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "src/ui/app.py",
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(ui_port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]

    child_env = os.environ.copy()
    child_env.setdefault("REVIEW_API_KEY", secrets.token_urlsafe(32))
    child_env.setdefault("REVIEW_AUTH_USER", "local-reviewer")
    child_env.setdefault("REVIEW_REQUIRE_AUTH", "true")
    child_env.setdefault(
        "REVIEW_REPOSITORY_PERMISSIONS",
        json.dumps(
            {
                "local-reviewer": {
                    "repositories": {
                        "automotive-ecu-demo": ["automotive_ecu_demo/"],
                        "clean-speed-monitor": ["clean_speed_monitor/"],
                        "mixed-sensor-network": ["mixed_sensor_network/"],
                    }
                }
            }
        ),
    )
    child_env["REVIEW_API_URL"] = f"http://127.0.0.1:{api_port}/api/v1/review"
    processes: list[subprocess.Popen] = []

    try:
        backend = start_process(backend_command, env=child_env)
        processes.append(backend)
        wait_for_backend(backend, f"http://127.0.0.1:{api_port}/health")

        frontend = start_process(frontend_command, env=child_env)
        processes.append(frontend)
        print("\nAutomotive Secure Code Review Assistant is ready:")
        print(f"  Dashboard:     http://127.0.0.1:{ui_port}")
        print(f"  API docs:      http://127.0.0.1:{api_port}/docs")
        print(f"  Health check:  http://127.0.0.1:{api_port}/health")
        if api_port != preferred_api_port or ui_port != preferred_ui_port:
            print("  Note: an occupied preferred port was skipped automatically.")
        print("  Press Ctrl+C once here to stop both services.\n")

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
    except Exception as exc:
        print(f"Startup failed: {exc}")
        terminate_processes(processes)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
