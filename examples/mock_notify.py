"""Deterministic mocks for the notification scenarios. No network and no real clock."""
from __future__ import annotations

from dataclasses import dataclass, field


class FakeClock:
    def __init__(self) -> None:
        self._t = 0.0

    def now(self) -> float:
        return self._t

    def sleep(self, seconds: float) -> None:
        self._t += seconds


@dataclass
class Inbox:
    """A destination that messages are delivered to, possibly after a delay."""

    clock: FakeClock
    _items: list = field(default_factory=list)  # (visible_at, msg_id, to)

    def deliver(self, msg_id: str, to: str, delay: float = 0.0) -> None:
        self._items.append((self.clock.now() + delay, msg_id, to))

    def has(self, msg_id: str, to: str) -> bool:
        now = self.clock.now()
        return any(v <= now and m == msg_id and t == to for v, m, t in self._items)


# Every tool below returns a success claim. They differ in what actually happened.

def notify_silent_noop(inbox: Inbox, msg_id: str, to: str) -> dict:
    return {"status": "success"}  # claims success, delivers nothing


def notify_works(inbox: Inbox, msg_id: str, to: str) -> dict:
    inbox.deliver(msg_id, to)
    return {"status": "success"}


def notify_delayed(inbox: Inbox, msg_id: str, to: str, delay: float = 0.3) -> dict:
    inbox.deliver(msg_id, to, delay)
    return {"status": "success"}


def notify_wrong_recipient(inbox: Inbox, msg_id: str, to: str) -> dict:
    inbox.deliver(msg_id, "someone-else")  # delivered, but not to the intended person
    return {"status": "success"}
