"""Confirm that a tool call that claims success actually caused its effect.

A tool's own "success" is a claim, not evidence. Evidence is an independent
observation of the effect, such as a message that can be found in the
destination or a record that can be read back. This module compares the two.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class Status(str, Enum):
    CONFIRMED = "confirmed"                        # claim made, effect observed
    NOT_CONFIRMED = "not_confirmed"                # claim made, effect not observed in time
    UNVERIFIABLE = "unverifiable"                  # claim made, no way to observe the effect
    TOOL_REPORTED_FAILURE = "tool_reported_failure"  # the tool itself did not claim success


@dataclass(frozen=True)
class Verdict:
    status: Status
    attempts: int
    elapsed_s: float
    detail: str = ""

    @property
    def safe_to_report_success(self) -> bool:
        """Only a confirmed effect is safe to report as done."""
        return self.status is Status.CONFIRMED


def default_claims_success(result: Any) -> bool:
    """Treat {"status": "success" | "ok" | "completed"} or any truthy value as a success claim."""
    if isinstance(result, dict):
        return str(result.get("status", "")).lower() in {"success", "ok", "completed"}
    return bool(result)


def check_effect(
    result: Any,
    verify: Optional[Callable[[], bool]],
    *,
    timeout_s: float = 2.0,
    interval_s: float = 0.1,
    claims_success: Callable[[Any], bool] = default_claims_success,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> Verdict:
    """Compare a tool's claim with an independent observation of its effect.

    result:     what the tool returned.
    verify:     a function that returns True once the intended effect is observable,
                or None if there is no way to observe it.
    timeout_s:  how long to keep looking before giving up. Short windows raise false
                alarms on slow systems. Long windows add latency.
    clock, sleep: injectable so tests and simulations do not need real time.
    """
    if timeout_s < 0:
        raise ValueError("timeout_s must be >= 0")
    if interval_s <= 0:
        raise ValueError("interval_s must be > 0")

    if not claims_success(result):
        return Verdict(Status.TOOL_REPORTED_FAILURE, 0, 0.0, "tool did not claim success")
    if verify is None:
        return Verdict(Status.UNVERIFIABLE, 0, 0.0, "no effect verifier supplied")

    start = clock()
    attempts = 0
    while True:
        attempts += 1
        try:
            observed = bool(verify())
        except Exception as exc:  # a broken verifier must never read as success
            return Verdict(
                Status.UNVERIFIABLE,
                attempts,
                clock() - start,
                f"verifier raised {type(exc).__name__}: {exc}",
            )
        if observed:
            return Verdict(Status.CONFIRMED, attempts, clock() - start, "effect observed")
        if clock() - start >= timeout_s:
            return Verdict(
                Status.NOT_CONFIRMED,
                attempts,
                clock() - start,
                "effect not observed before timeout",
            )
        sleep(interval_s)
