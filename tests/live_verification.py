"""
Live end-to-end verification script for Sam Core server.
Spawns the server as a subprocess, verifies HTTP and WebSocket endpoints, then terminates cleanly.
"""
import json
import subprocess
import sys
import time

import httpx
from websockets.sync.client import connect

SERVER_URL = "http://127.0.0.1:8765"
WS_URL = "ws://127.0.0.1:8765/ws/ipc"


def run_verification():
    print("[1/5] Launching Sam Core daemon subprocess...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "sam_core.main"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Wait for server to bind
        print("[2/5] Waiting for server to become ready...")
        ready = False
        for _ in range(30):
            try:
                resp = httpx.get(f"{SERVER_URL}/health", timeout=1.0)
                if resp.status_code == 200:
                    ready = True
                    break
            except Exception:
                time.sleep(0.3)

        if not ready:
            stdout, stderr = proc.communicate(timeout=2)
            print(f"FAILED: Server did not respond. Stderr: {stderr}")
            sys.exit(1)

        print("  -> Server is UP and responding!")

        # Verify HTTP Health
        print("[3/5] Verifying HTTP /health endpoint...")
        resp = httpx.get(f"{SERVER_URL}/health")
        data = resp.json()
        print(f"  -> Health response: status={data.get('status')}, app={data.get('app_name')}")
        assert data.get("status") == "operational", "Status is not operational"
        assert data.get("subsystems", {}).get("ai_engine") == "not_implemented", "Truthfulness check failed"

        # Verify WebSocket JSON-RPC
        print("[4/5] Verifying WebSocket JSON-RPC endpoint at /ws/ipc...")
        with connect(WS_URL, close_timeout=3) as ws:
            ping_payload = {
                "jsonrpc": "2.0",
                "method": "sam.ping",
                "params": {},
                "id": "live-verification-1",
            }
            ws.send(json.dumps(ping_payload))
            raw_reply = ws.recv(timeout=3)
            reply = json.loads(raw_reply)
            print(f"  -> WebSocket reply: {reply}")
            assert reply.get("id") == "live-verification-1"
            assert reply.get("result", {}).get("pong") is True

            # Check status RPC
            status_payload = {
                "jsonrpc": "2.0",
                "method": "sam.status",
                "params": {},
                "id": "live-verification-2",
            }
            ws.send(json.dumps(status_payload))
            raw_status = ws.recv(timeout=3)
            status_reply = json.loads(raw_status)
            print(f"  -> Status reply: app_name={status_reply.get('result', {}).get('app_name')}")
            assert status_reply.get("result", {}).get("status") == "operational"

        print("  -> WebSocket JSON-RPC verification passed!")

    finally:
        print("[5/5] Stopping development server cleanly...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
            print("  -> Server stopped cleanly.")
        except subprocess.TimeoutExpired:
            proc.kill()
            print("  -> Server process killed.")

    print("\n[SUCCESS] All live server verifications PASSED!")


if __name__ == "__main__":
    run_verification()
