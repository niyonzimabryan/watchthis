from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def _request_json(method: str, url: str, payload: dict | None = None, timeout: float = 90) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return int(response.status), json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        return int(exc.code), parsed


def _wait_for_health(base_url: str, timeout_seconds: float = 20) -> None:
    started = time.time()
    while time.time() - started < timeout_seconds:
        try:
            status, payload = _request_json("GET", f"{base_url}/health", timeout=2)
            if status == 200 and payload.get("status") == "ok":
                return
        except Exception:
            pass
        time.sleep(0.25)

    raise RuntimeError("API did not become healthy in time")


def main() -> int:
    if not (PROJECT_ROOT / ".venv").exists():
        print("Missing .venv. Create it and install requirements first.", file=sys.stderr)
        return 1

    port = _free_port()
    base_url = f"http://{HOST}:{port}"
    session_id = f"smoke-{int(time.time())}"

    env = os.environ.copy()
    python_bin = str(PROJECT_ROOT / ".venv" / "bin" / "python")
    command = [
        python_bin,
        "-m",
        "uvicorn",
        "api.server:app",
        "--host",
        HOST,
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]

    server = subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )

    try:
        _wait_for_health(base_url)
        print("Health: ok")

        status1, rec1 = _request_json(
            "POST",
            f"{base_url}/recommend",
            {
                "session_id": session_id,
                "mood_input": "I had a brutal day and want something cozy and funny",
                "format": "any",
                "length": "any",
            },
        )
        if status1 != 200:
            raise RuntimeError(f"/recommend failed ({status1}): {rec1}")

        req1_id = rec1.get("request_id")
        title1 = rec1.get("recommendation", {}).get("title")
        print(f"Recommend: request_id={req1_id} title={title1}")

        status2, rec2 = _request_json(
            "POST",
            f"{base_url}/recommend",
            {
                "session_id": session_id,
                "mood_input": "I had a brutal day and want something cozy and funny",
                "format": "any",
                "length": "any",
                "reroll_of": req1_id,
            },
        )
        if status2 != 200:
            raise RuntimeError(f"reroll /recommend failed ({status2}): {rec2}")

        req2_id = rec2.get("request_id")
        title2 = rec2.get("recommendation", {}).get("title")
        print(f"Reroll: request_id={req2_id} title={title2}")
        if title1 == title2:
            print("Warning: reroll returned same title (possible in narrow candidate pools)")

        status3, roulette = _request_json(
            "POST",
            f"{base_url}/roulette",
            {
                "session_id": session_id,
                "format": "any",
                "length": "any",
            },
        )
        if status3 != 200:
            raise RuntimeError(f"/roulette failed ({status3}): {roulette}")

        req3_id = roulette.get("request_id")
        title3 = roulette.get("recommendation", {}).get("title")
        source_count = len(roulette.get("streaming_sources", []))
        print(f"Roulette: request_id={req3_id} title={title3} sources={source_count}")

        print("Smoke test complete.")
        return 0

    except Exception as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        return 1

    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
