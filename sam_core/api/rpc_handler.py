"""
Typed JSON-RPC 2.0 protocol dispatcher for Sam Core IPC.
Validates requests using Pydantic IPC models and maps them to registered handlers.
"""
from collections.abc import Callable, Coroutine
from typing import Any

from sam_capabilities.registry import skill_registry
from sam_core.ai.router import llm_router
from sam_core.api.ipc_models import (
    JsonRpcErrorCode,
    JsonRpcNotification,
    JsonRpcResponse,
    parse_ipc_message,
)
from sam_core.config import settings
from sam_core.conversation.orchestrator import agent_orchestrator
from sam_core.logger import clear_correlation_id, get_logger, set_correlation_id
from sam_core.permissions.manager import permission_manager

logger = get_logger("api.rpc")


class JsonRpcHandler:
    """Dispatches JSON-RPC 2.0 methods with strict validation."""

    def __init__(self):
        self._methods: dict[str, Callable[[dict[str, Any]], Coroutine[Any, Any, Any]]] = {}
        self._register_core_methods()

    def register_method(
        self, method_name: str, handler: Callable[[dict[str, Any]], Coroutine[Any, Any, Any]]
    ) -> None:
        """Register an async RPC method handler."""
        self._methods[method_name] = handler
        logger.debug(f"Registered RPC method '{method_name}'")

    def _register_core_methods(self) -> None:
        """Register built-in system RPC methods."""
        self.register_method("sam.ping", self._method_ping)
        self.register_method("sam.status", self._method_status)
        self.register_method("sam.list_skills", self._method_list_skills)
        self.register_method("sam.list_providers", self._method_list_providers)
        self.register_method("sam.send_message", self._method_send_message)
        self.register_method("sam.resolve_permission", self._method_resolve_permission)

    async def _method_ping(self, params: dict[str, Any]) -> dict[str, Any]:
        """Simple liveness probe."""
        return {"pong": True, "app": settings.app_name}

    async def _method_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """Truthful system status reporting."""
        active_provider = llm_router.get_provider()
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
                "ai_engine": f"ready ({active_provider.name})",
                "conversation_engine": "ready",
                "voice_engine": "ready",
                "vision_engine": "ready",
                "windows_automation": "ready",
                "memory_system": "not_implemented",
                "android_client": "not_implemented",
            },
            "registered_skills_count": skill_registry.count,
            "active_provider": active_provider.name,
        }

    async def _method_list_skills(self, params: dict[str, Any]) -> dict[str, Any]:
        """List registered skills."""
        skills = [
            {"name": s.name, "description": s.description, "version": s.version}
            for s in skill_registry.list_skills()
        ]
        return {"count": len(skills), "skills": skills}

    async def _method_list_providers(self, params: dict[str, Any]) -> dict[str, Any]:
        """List registered LLM providers and their availability."""
        statuses = [s.model_dump() for s in llm_router.list_statuses()]
        return {"count": len(statuses), "providers": statuses}

    async def _method_send_message(self, params: dict[str, Any]) -> dict[str, Any]:
        """Send a message into Sam's conversational agent orchestrator."""
        text = params.get("text", "").strip()
        session_id = params.get("session_id")
        provider_name = params.get("provider")
        confirmation_token = params.get("confirmation_token")

        if not text:
            raise ValueError("Parameter 'text' cannot be empty.")

        res = await agent_orchestrator.process_user_turn(
            user_text=text,
            session_id=session_id,
            provider_name=provider_name,
            confirmation_token=confirmation_token,
        )

        return {
            "response": res.response_text,
            "task_id": res.task_id,
            "task_state": res.task_state.value if res.task_state else None,
            "confirmation_required": res.confirmation_required,
            "confirmation_token": res.confirmation_token,
            "tool_results": res.tool_results,
        }

    async def _method_resolve_permission(self, params: dict[str, Any]) -> dict[str, Any]:
        """Approve or deny a pending authorization token."""
        token = params.get("token")
        approved = params.get("approved", False)
        reason = params.get("reason")

        if not token:
            raise ValueError("Missing required parameter 'token'.")

        success = await permission_manager.resolve_permission(
            token=token,
            approved=approved,
            reason=reason,
        )
        return {"success": success, "token": token, "approved": approved}

    async def handle_payload(self, raw_data: str) -> str | None:
        """
        Parse raw incoming JSON string, validate, route method, and return JSON-RPC response.
        Returns None for notifications.
        """
        try:
            msg = parse_ipc_message(raw_data)
        except (ValueError, TypeError) as exc:
            logger.warning(f"Invalid IPC payload received: {exc}")
            resp = JsonRpcResponse.failure(
                req_id=None,
                code=JsonRpcErrorCode.PARSE_ERROR,
                message=str(exc),
            )
            return resp.model_dump_json()

        # Handle Notification
        if isinstance(msg, JsonRpcNotification):
            if msg.method in self._methods:
                try:
                    await self._methods[msg.method](msg.params or {})
                except Exception as exc:
                    logger.error(f"Error handling notification '{msg.method}': {exc}", exc_info=True)
            return None

        # Handle Request
        req_id = msg.id
        set_correlation_id(str(req_id))
        try:
            if msg.method not in self._methods:
                logger.warning(f"Method not found: '{msg.method}' (Request ID: {req_id})")
                resp = JsonRpcResponse.failure(
                    req_id=req_id,
                    code=JsonRpcErrorCode.METHOD_NOT_FOUND,
                    message=f"Method '{msg.method}' not found.",
                )
            else:
                result = await self._methods[msg.method](msg.params or {})
                resp = JsonRpcResponse.success(req_id=req_id, result=result)
        except ValueError as exc:
            resp = JsonRpcResponse.failure(
                req_id=req_id,
                code=JsonRpcErrorCode.INVALID_PARAMS,
                message=str(exc),
            )
        except Exception as exc:
            logger.error(f"Internal error executing '{msg.method}': {exc}", exc_info=True)
            resp = JsonRpcResponse.failure(
                req_id=req_id,
                code=JsonRpcErrorCode.INTERNAL_ERROR,
                message="Internal error occurred while processing request.",
            )
        finally:
            clear_correlation_id()

        return resp.model_dump_json()


# Global singleton instance
rpc_handler = JsonRpcHandler()
