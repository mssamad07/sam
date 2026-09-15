"""
Asynchronous, typed EventBus for Sam Core.
Allows completely decoupled pub-sub communication between components.
"""
import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from sam_core.events.types import BaseEvent
from sam_core.logger import get_logger

logger = get_logger("events.bus")

T = TypeVar("T", bound=BaseEvent)
EventHandler = Callable[[T], Coroutine[Any, Any, None]]


class EventBus:
    """Async event bus for dispatching and handling system events."""

    def __init__(self):
        self._subscribers: dict[type[BaseEvent], list[EventHandler]] = defaultdict(list)
        self._global_subscribers: list[EventHandler] = []
        self._active_tasks: set[asyncio.Task] = set()
        self._is_shutting_down: bool = False

    def subscribe(self, event_type: type[T], handler: EventHandler) -> None:
        """Subscribe an async callback to a specific event type."""
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            logger.debug(f"Subscribed handler '{handler.__name__}' to event '{event_type.__name__}'")

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to all events across the entire system (useful for logging/tracing)."""
        if handler not in self._global_subscribers:
            self._global_subscribers.append(handler)

    def unsubscribe(self, event_type: type[T], handler: EventHandler) -> None:
        """Remove a previously registered handler."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    def subscriber_count(self, event_type: type[BaseEvent] | None = None) -> int:
        """Count number of subscribers for an event type or total across all types."""
        if event_type:
            return len(self._subscribers.get(event_type, []))
        return sum(len(h) for h in self._subscribers.values()) + len(self._global_subscribers)

    async def publish(self, event: BaseEvent) -> None:
        """Publish an event to all interested subscribers concurrently with error isolation."""
        if self._is_shutting_down:
            logger.warning(f"EventBus is shutting down; dropping event '{type(event).__name__}'")
            return

        event_cls = type(event)
        handlers = list(self._subscribers.get(event_cls, []))
        global_handlers = list(self._global_subscribers)

        all_handlers = handlers + global_handlers
        if not all_handlers:
            return

        tasks = [asyncio.create_task(self._safe_execute(handler, event)) for handler in all_handlers]
        for t in tasks:
            self._active_tasks.add(t)
            t.add_done_callback(self._active_tasks.discard)

        # Wait for all handlers to complete; return_exceptions=True guarantees isolation
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_execute(self, handler: EventHandler, event: BaseEvent) -> None:
        """Executes a single event handler and catches exceptions so others are unaffected."""
        try:
            await handler(event)
        except Exception as exc:
            logger.error(
                f"Error in event handler '{getattr(handler, '__name__', str(handler))}' "
                f"for '{type(event).__name__}': {exc}",
                exc_info=True,
            )

    async def shutdown(self, timeout: float = 2.0) -> None:
        """Gracefully shut down the event bus, waiting for in-flight tasks to complete."""
        self._is_shutting_down = True
        logger.info("EventBus shutting down...")

        if self._active_tasks:
            pending = list(self._active_tasks)
            try:
                await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=timeout)
            except TimeoutError:
                logger.warning(f"EventBus shutdown timed out; cancelling {len(pending)} pending tasks")
                for task in pending:
                    task.cancel()

        self._subscribers.clear()
        self._global_subscribers.clear()
        self._active_tasks.clear()
        self._is_shutting_down = False
        logger.info("EventBus shutdown complete")


# Global singleton instance
event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get the global EventBus instance."""
    return event_bus


__all__ = ["EventBus", "event_bus", "get_event_bus"]
