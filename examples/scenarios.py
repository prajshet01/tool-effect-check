"""Run six simulated tool calls through a naive agent and a checked agent.

    python -m examples.scenarios

All six tools claim success. A naive agent reports success every time. A checked
agent compares the claim with an independent look at the destination.
"""
from __future__ import annotations

from effect_check import Status, check_effect
from examples.mock_notify import (
    FakeClock,
    Inbox,
    notify_delayed,
    notify_silent_noop,
    notify_works,
    notify_wrong_recipient,
)

MSG, TO = "approval-1", "approver"

# name, tool, tool kwargs, check kwargs, whether a verifier is supplied
SCENARIOS = [
    ("silent no-op",                notify_silent_noop,     {},            {"timeout_s": 1.0}, True),
    ("wrong recipient",             notify_wrong_recipient, {},            {"timeout_s": 1.0}, True),
    ("delayed, window long enough", notify_delayed,         {"delay": 0.3}, {"timeout_s": 1.0}, True),
    ("delayed, window too short",   notify_delayed,         {"delay": 0.3}, {"timeout_s": 0.1}, True),
    ("works",                       notify_works,           {},            {"timeout_s": 1.0}, True),
    ("works, no verifier supplied", notify_works,           {},            {"timeout_s": 1.0}, False),
]


def run() -> list[dict]:
    rows = []
    for name, tool, tool_kwargs, check_kwargs, has_verifier in SCENARIOS:
        clock = FakeClock()
        inbox = Inbox(clock)
        result = tool(inbox, MSG, TO, **tool_kwargs)
        verify = (lambda: inbox.has(MSG, TO)) if has_verifier else None
        verdict = check_effect(
            result, verify, interval_s=0.1, clock=clock.now, sleep=clock.sleep, **check_kwargs
        )
        clock.sleep(10.0)  # let everything settle, then read the ground truth
        happened = inbox.has(MSG, TO)
        if verdict.status is Status.CONFIRMED:
            right = "yes" if happened else "NO"
        elif verdict.status is Status.NOT_CONFIRMED:
            right = "yes" if not happened else "NO (false alarm)"
        else:
            right = "abstained"
        rows.append({"name": name, "happened": happened, "verdict": verdict.status.value, "right": right})
    return rows


def main() -> None:
    rows = run()
    print("| Scenario | Effect really happened | Naive agent says | Checked agent says | Checked agent right? |")
    print("|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['name']} | {'yes' if r['happened'] else 'no'} | success | {r['verdict']} | {r['right']} |")
    n = len(rows)
    naive_wrong = sum(1 for r in rows if not r["happened"])
    checked_wrong = sum(1 for r in rows if r["right"].startswith("NO"))
    abstained = sum(1 for r in rows if r["right"] == "abstained")
    print()
    print(f"Naive agent wrong: {naive_wrong}/{n}")
    print(f"Checked agent wrong: {checked_wrong}/{n}, abstained: {abstained}/{n}")


if __name__ == "__main__":
    main()
