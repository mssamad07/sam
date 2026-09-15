"""
FastAPI Server and WebSocket IPC Gateway for Sam Core.
Provides health endpoints, truthful status reporting, and WebSocket JSON-RPC.
"""
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from sam_capabilities.registry import skill_registry
from sam_core.api.rpc_handler import rpc_handler
from sam_core.config import settings
from sam_core.events.bus import event_bus
from sam_core.events.types import BaseEvent
from sam_core.logger import get_logger, setup_logging

logger = get_logger("api.server")

# Active connected WebSocket clients
connected_clients: set[WebSocket] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and graceful shutdown."""
    setup_logging(level=settings.log_level, logs_dir=settings.logs_dir)
    logger.info("==================================================")
    logger.info(f"  {settings.app_name} Core Starting Up (v{settings.version})")
    logger.info(f"  Environment : {settings.environment}")
    logger.info(f"  Host/Port   : {settings.host}:{settings.port}")
    logger.info("  Binding     : Localhost only (Phase 1)")
    logger.info("==================================================")

    async def broadcast_event_to_clients(event: BaseEvent):
        """Broadcast bus events as JSON-RPC notifications to connected clients."""
        if not connected_clients:
            return
        payload = {
            "jsonrpc": "2.0",
            "method": f"event.{type(event).__name__}",
            "params": event.model_dump(mode="json"),
        }
        dead_clients = set()
        for client in list(connected_clients):
            try:
                await client.send_json(payload)
            except Exception:
                dead_clients.add(client)

        for dead in dead_clients:
            connected_clients.discard(dead)

    event_bus.subscribe_all(broadcast_event_to_clients)
    yield

    logger.info("Sam Core shutting down...")
    await event_bus.shutdown()
    dead_clients = list(connected_clients)
    for client in dead_clients:
        with suppress(Exception):
            await client.close(code=status.WS_1000_NORMAL_CLOSURE)
    connected_clients.clear()
    logger.info("Sam Core shutdown complete.")


app = FastAPI(
    title=f"{settings.app_name} Core API",
    description="Core daemon and IPC gateway for Sam personal AI assistant",
    version=settings.version,
    lifespan=lifespan,
)

# Phase 1 CORS: Local development origins only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://127.0.0.1:{settings.port}",
        f"http://localhost:{settings.port}",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root info endpoint."""
    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "status": "operational",
    }


@app.get("/health")
async def health_check():
    """
    Truthful health endpoint.
    Reports operational status for core and truthfully reports not-implemented subsystems.
    """
    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "status": "operational",
        "subsystems": {
            "core": "ready",
            "ipc": "ready",
            "event_bus": "ready",
            "skill_registry": "ready",
            "ai_engine": "not_implemented",
            "voice_engine": "not_implemented",
            "memory_system": "not_implemented",
            "windows_automation": "not_implemented",
            "android_client": "not_implemented",
        },
        "registered_skills_count": skill_registry.count,
    }


async def _handle_websocket(websocket: WebSocket, token: str | None):
    """Internal WebSocket connection handler."""
    # Optional token authentication
    if settings.auth_token and token != settings.auth_token:
        logger.warning("Rejected unauthorized WebSocket connection attempt.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"Client connected to WebSocket. Total active clients: {len(connected_clients)}")

    try:
        while True:
            raw_text = await websocket.receive_text()
            response_json = await rpc_handler.handle_payload(raw_text)
            if response_json is not None:
                await websocket.send_text(response_json)
    except WebSocketDisconnect:
        logger.info("Client disconnected normally from WebSocket")
    except Exception as exc:
        logger.error(f"Error on WebSocket connection: {exc}", exc_info=True)
    finally:
        connected_clients.discard(websocket)
        logger.debug(f"Client removed. Remaining active clients: {len(connected_clients)}")


@app.websocket(settings.ws_path)
async def websocket_ipc_endpoint(
    websocket: WebSocket,
    token: str | None = Query(default=None),
):
    """Primary WebSocket endpoint for JSON-RPC 2.0 communication."""
    await _handle_websocket(websocket, token)


# Alias endpoint for backward compatibility (/ws/rpc)
if settings.ws_path != "/ws/rpc":
    @app.websocket("/ws/rpc")
    async def websocket_rpc_alias_endpoint(
        websocket: WebSocket,
        token: str | None = Query(default=None),
    ):
        await _handle_websocket(websocket, token)
