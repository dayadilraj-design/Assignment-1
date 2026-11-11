# CLI Contract

## Invocation

```text
python -m reminder_agent "<text>" --now YYYY-MM-DDTHH:MM:SS
```

- Exactly one positional reminder text is accepted.
- `--now` is required and must be a valid ISO local datetime without a UTC offset. It is the only reference time for interpreting relative dates.
- Empty or whitespace-only text and invalid or offset-aware `--now` values are rejected before a model call.
- The process uses `GEMINI_API_KEY` and `LLM_MODEL` from the environment, with missing values optionally loaded from a git-ignored `.env`. Environment values take precedence. Neither value appears in the reminder JSON or routine CLI output.

## Successful result

For `ok`, `needs_clarification`, and `refused`, stdout contains exactly one compact JSON object followed by a newline. It has exactly the seven fields in [reminder-result.schema.json](./reminder-result.schema.json), and it passes both the structural schema and the cross-field invariants in the specification.

## Exit and stream contract

| Exit code | Meaning | stdout | stderr |
|---:|---|---|---|
| `0` | Valid result produced, including clarification or refusal | Exactly one compact JSON object | No credential or routine model details |
| `1` | Invalid input or application/model-response error | No result object | Safe diagnostic; never the API key |
| `2` | Service/network failure, including timeout or exhausted HTTP 429/503 retries | No result object | Safe service-failure diagnostic; never the API key |

Invalid CLI syntax (including missing `--now` or extra positional arguments), empty text, and invalid `--now` use exit 1 rather than argparse's default exit code 2.

## Empty-input evaluation outcome

The evaluation harness recognizes the empty-text case as `invalid_input` only when all of the following hold: exit code 1, stdout is empty, and stderr has a safe diagnostic. The invariants layer separately verifies that the transport was not called.

## Evaluation invocation

The harness invokes `cli.main(argv)` once per case and captures stdout, stderr, and the returned exit code. It does not call `core.run` directly. A returned exit code 2 is recorded as case `ERROR` with no result JSON; any such case makes the run `INCONCLUSIVE`. Unit tests call the CLI with an injected fake transport and do not access the network.

## Time interpretation

- `remind_at` is a local wall-clock datetime with seconds and no UTC offset.
- Relative expressions are calculated from `--now`.
- With a date, `morning`, `afternoon`, `evening`, and `night` map to 09:00, 14:00, 18:00, and 21:00.
- `later` or `soon` without a specified time and any requested time at or before `--now` produce clarification, not a guessed executable reminder.
