# tool-effect-check

A small Python helper that checks whether a tool call that says "success" actually did what it was meant to do.

No dependencies. Python 3.9+. MIT licensed.

## The problem

An agent calls a tool. The tool returns `{"status": "success"}`. The agent marks the step done and moves on. Later, someone finds that the effect never happened: the message was never delivered, the record was never written.

The tool's "success" was a claim. Nothing checked it. Agents that read only the return value treat completion as success, and that gap is where silent failures live.

## The question

When should an agent be allowed to say "done"?

## The approach

Three rules:

1. **A tool's claim is not evidence.** Success from the tool says the call returned, not that the effect exists.
2. **Evidence is an independent observation of the effect.** For example, look for the message in the destination, or read the record back.
3. **No way to observe means "unverifiable", never "success".** A missing or broken verifier must not read as a pass.

`check_effect` compares the tool's claim with the observation and returns one of four verdicts:

| Verdict | Meaning |
|---|---|
| `confirmed` | The tool claimed success and the effect was observed. |
| `not_confirmed` | The tool claimed success and the effect was not observed before the timeout. |
| `unverifiable` | The tool claimed success but there is no way to observe the effect, or the verifier itself failed. |
| `tool_reported_failure` | The tool did not claim success. |

Only `confirmed` is safe to report as done (`verdict.safe_to_report_success`).

## Usage

```python
from effect_check import check_effect

result = send_notification(msg_id="approval-1", to="approver")   # returns {"status": "success"}

verdict = check_effect(
    result,
    verify=lambda: inbox.has("approval-1", "approver"),  # an independent look at the destination
    timeout_s=2.0,
    interval_s=0.1,
)

if verdict.safe_to_report_success:
    ...  # the step is done
else:
    ...  # escalate, retry, or tell the user: verdict.status and verdict.detail say why
```

## Results

Six simulated tool calls. Every tool claims success. A naive agent reports success every time. A checked agent compares the claim with a look at the destination. Run it yourself:

```
python -m examples.scenarios
```

| Scenario | Effect really happened | Naive agent says | Checked agent says | Checked agent right? |
|---|---|---|---|---|
| silent no-op | no | success | not_confirmed | yes |
| wrong recipient | no | success | not_confirmed | yes |
| delayed, window long enough | yes | success | confirmed | yes |
| delayed, window too short | yes | success | not_confirmed | NO (false alarm) |
| works | yes | success | confirmed | yes |
| works, no verifier supplied | yes | success | unverifiable | abstained |

Naive agent wrong: 2/6
Checked agent wrong: 1/6, abstained: 1/6

What this shows:

- The naive agent reports success in all six cases and is wrong in two: the silent no-op and the wrong recipient.
- The checked agent catches both.
- The window length is a real trade-off. When the effect is slow and the window is too short, the checked agent raises a false alarm.
- With no verifier, the checked agent declines to claim success instead of guessing.

What this does not show: how any of this performs on real systems. These are deterministic simulations with a fake clock. They illustrate the mechanism, not a measured rate.

## Design decisions and trade-offs

- **Timeout window: false alarms versus latency.** A short window flags slow-but-working systems as failures. A long window delays every step. Set it from how long the destination normally takes.
- **Verifier independence.** If the verifier asks the same system that made the claim, it can repeat the same mistake. Prefer a different path to the same fact.
- **Cost.** Every check adds a read. Use it on steps where a silent failure costs something, such as notifications, approvals, and writes, and skip it for cheap, reversible steps.
- **A broken verifier is not a pass.** If the verifier raises, the verdict is `unverifiable`.

## Non-goals

- Not a security tool and not a prompt injection defense.
- Does not judge whether the effect was the right business outcome, only whether the intended effect is observable.
- No real integrations. Bring your own verifier.

## Tests

```
python -m unittest discover -s tests -t .
```

## Background

Related article: [Agent Failure Moves Up the Stack](https://prajwalshet.substack.com/p/agent-failure-moves-up-the-stack?r=n5aqx).

## License

MIT. See `LICENSE`.
