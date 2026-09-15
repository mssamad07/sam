"""
Unit tests for asynchronous event bus.
"""
import asyncio

import pytest

from sam_core.events.bus import EventBus
from sam_core.events.types import UserInputEvent


@pytest.mark.asyncio
async def test_event_bus_publish_and_subscribe():
    bus = EventBus()
    received = []

    async def on_user_input(event: UserInputEvent):
        received.append(event.text)

    bus.subscribe(UserInputEvent, on_user_input)

    event = UserInputEvent(text="Test message", channel="test")
    await bus.publish(event)

    assert len(received) == 1
    assert received[0] == "Test message"


@pytest.mark.asyncio
async def test_event_bus_multiple_subscribers():
    bus = EventBus()
    results = []

    async def sub_one(event: UserInputEvent):
        results.append(f"one:{event.text}")

    async def sub_two(event: UserInputEvent):
        results.append(f"two:{event.text}")

    bus.subscribe(UserInputEvent, sub_one)
    bus.subscribe(UserInputEvent, sub_two)

    await bus.publish(UserInputEvent(text="broadcast"))

    assert len(results) == 2
    assert "one:broadcast" in results
    assert "two:broadcast" in results


@pytest.mark.asyncio
async def test_event_bus_handler_failure_isolation():
    """Verify that a failing subscriber does not prevent other subscribers from executing."""
    bus = EventBus()
    executed = []

    async def broken_handler(event: UserInputEvent):
        raise RuntimeError("Simulated unhandled exception in subscriber")

    async def healthy_handler(event: UserInputEvent):
        executed.append(event.text)

    bus.subscribe(UserInputEvent, broken_handler)
    bus.subscribe(UserInputEvent, healthy_handler)

    # Publishing should complete cleanly without raising the exception to publisher
    await bus.publish(UserInputEvent(text="safe_execution"))

    assert len(executed) == 1
    assert executed[0] == "safe_execution"


@pytest.mark.asyncio
async def test_event_bus_shutdown():
    bus = EventBus()
    ran = False

    async def slow_handler(event: UserInputEvent):
        nonlocal ran
        await asyncio.sleep(0.01)
        ran = True

    bus.subscribe(UserInputEvent, slow_handler)
    await bus.publish(UserInputEvent(text="before_shutdown"))
    assert ran is True

    await bus.shutdown()
    assert bus.subscriber_count() == 0

    # Publishing after shutdown should be dropped safely
    ran_after = False
    await bus.publish(UserInputEvent(text="after_shutdown"))
    assert ran_after is False
