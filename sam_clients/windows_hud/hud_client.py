"""
Async WebSocket JSON-RPC Client for Sam Windows HUD.
Communicates with Sam Core at ws://127.0.0.1:8765/ws/ipc.
"""
import asyncio
import json
import uuid
from collections.abc import Callable
from typing import Any

import websockets

from sam_core.logger import get_logger

logger = get_logger("client.hud")


class HUDClient:
    """Manages WebSocket IPC connection, message dispatch, and event listeners."""

    def __init__(self, server_url: str = "ws://127.0.0.1:8765/ws/ipc") -> None:
        self.server_url = server_url
        self._ws = None
        self._is_connected = False
        self._pending_requests: dict[str, asyncio.Future[Any]] = {}
        self._receive_task: asyncio.Task[Any] | None = None
        self._event_listeners: dict[str, list[Callable[[dict[str, Any]], None]]] = {}

        # Default HUD state tracking
        self.current_state = "idle"
        self.last_transcription = ""
        self.last_response = ""
        self.active_permission_request: dict[str, Any] | None = None

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def on(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register an event listener."""
        self._event_listeners.setdefault(event_type, []).append(callback)

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        for cb in self._event_listeners.get(event_type, []):
            try:
                cb(data)
            except Exception as e:
                logger.error(f"Error in HUD callback for {event_type}: {e}")

    async def connect(self) -> bool:
        """Establish WebSocket connection to Sam Core IPC."""
        try:
            self._ws = await websockets.connect(self.server_url)
            self._is_connected = True
            self._receive_task = asyncio.create_task(self._listen_loop())
            logger.info(f"Connected to Sam Core IPC at {self.server_url}")
            return True
        except Exception as e:
            logger.warning(f"Unable to connect to Sam Core IPC: {e}")
            self._is_connected = False
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self._is_connected = False
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("Disconnected from Sam Core IPC")

    async def call(self, method: str, params: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
        """Send JSON-RPC request and await response."""
        if not self._is_connected or not self._ws:
            raise ConnectionError("HUDClient is not connected to IPC server.")

        req_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self._pending_requests[req_id] = future

        msg = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        await self._ws.send(json.dumps(msg))

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending_requests.pop(req_id, None)

    async def send_message(self, text: str, confirmation_token: str | None = None) -> dict[str, Any]:
        """Send a conversational user prompt."""
        params: dict[str, Any] = {"text": text}
        if confirmation_token:
            params["confirmation_token"] = confirmation_token
        return await self.call("sam.send_message", params)

    async def resolve_permission(self, token: str, approved: bool) -> dict[str, Any]:
        """Resolve a pending confirmation token."""
        return await self.call("sam.resolve_permission", {"token": token, "approved": approved})

    async def get_status(self) -> dict[str, Any]:
        """Fetch system status."""
        return await self.call("sam.status")

    async def ping(self) -> dict[str, Any]:
        """Ping server."""
        return await self.call("sam.ping")

    async def _listen_loop(self) -> None:
        """Receive messages and notifications from the server."""
        try:
            while self._is_connected and self._ws:
                raw_msg = await self._ws.recv()
                data = json.loads(raw_msg)

                # Check if it's a response to a pending request
                msg_id = data.get("id")
                if msg_id and msg_id in self._pending_requests:
                    future = self._pending_requests[msg_id]
                    if not future.done():
                        if "error" in data and data["error"]:
                            future.set_exception(RuntimeError(data["error"]))
                        else:
                            future.set_result(data.get("result", {}))
                    continue

                # Server-pushed notification / event
                method = data.get("method")
                params = data.get("params", {})

                if method == "sam.event":
                    event_type = params.get("event_type", "")
                    payload = params.get("payload", {})
                    self._handle_server_event(event_type, payload)
                elif method == "permission_requested":
                    self.active_permission_request = params
                    self._emit("permission_requested", params)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"HUD connection closed: {e}")
            self._is_connected = False

    def _handle_server_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if event_type == "voice.state_changed":
            self.current_state = payload.get("new_state", "idle")
            self._emit("state_changed", payload)
        elif event_type == "voice.transcription":
            self.last_transcription = payload.get("text", "")
            self._emit("transcription", payload)
        elif event_type == "voice.tts_started":
            self.last_response = payload.get("text", "")
            self._emit("response", payload)
        elif event_type == "camera_state_changed":
            self._emit("camera_state_changed", payload)

        self._emit(event_type, payload)
