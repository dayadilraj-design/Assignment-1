# Research: Natural-Language Reminder Agent

## Decisions

### Gemini REST integration

- **Decision**: Use the Gemini `generateContent` HTTPS endpoint with the model identifier supplied by `LLM_MODEL`; send authentication in the `x-goog-api-key` header. Request JSON output with `responseMimeType: "application/json"` and include `responseJsonSchema` only for a selected model that supports structured JSON output. Parse the candidate text and validate it locally before use.
- **Rationale**: This is the documented REST interface, works with the standard-library `urllib` constraint, keeps credentials out of URLs and request bodies, and makes generation constraints an aid rather than a replacement for local validation.
- **Alternatives considered**: A third-party SDK would add a runtime dependency; URL query-key authentication would expose credentials in URLs and logs; trusting schema-constrained output would not verify business invariants or semantic correctness.
- **Sources**:
  - [GenerateContent REST reference](https://ai.google.dev/api/generate-content/generate-content)
  - [Structured outputs guide](https://ai.google.dev/gemini-api/docs/structured-output)
  - [API key and security documentation](https://ai.google.dev/gemini-api/docs/api-key)

### Model selection

- **Decision**: Do not hard-code a model or silently choose a default. Require `LLM_MODEL`; record its value in evaluation metadata as required by the specification, but do not include it in CLI output or routine logs.
- **Rationale**: The project contract makes model selection an operator setting. A documented model page lists Gemini 4 Argon as supporting structured output, but the model remains configurable and model capabilities may vary.
- **Alternatives considered**: Pinning one model would conflict with `LLM_MODEL`; inferring model capabilities from an unverified name or silently falling back would make behavior harder to reproduce.

### Credential loading

- **Decision**: Read `GEMINI_API_KEY` and `LLM_MODEL` from the process environment first, then fill missing values from the project-local `.env`; an explicit environment value takes precedence. Parse only the two supported keys, and never include the key in exceptions, output, or evidence.
- **Rationale**: This supports local setup and automated environments without introducing a dotenv dependency. The repository `.gitignore` already excludes `.env`.
- **Alternatives considered**: A third-party dotenv package conflicts with the runtime constraint; reading credentials from a command-line argument would expose them in shell history and process listings.

### Error and retry mapping

- **Decision**: Make at most three total HTTP attempts, retrying only HTTP 429 and 503. Do not retry other HTTP errors, malformed responses, timeouts, or network errors. Exhausted 429/503 and network/timeout failures raise `ServiceError`; other HTTP, decoding, and contract errors are application failures.
- **Rationale**: This directly preserves the constitution’s bounded retry policy and the CLI’s distinct exit codes.
- **Alternatives considered**: Retrying all failures can repeat invalid requests and hide configuration errors; unbounded retries violate the explicit service boundary.

### Test and evaluation boundary

- **Decision**: Define a small callable transport boundary used by `core.run`; unit tests inject deterministic fake transports and never make network calls. The evaluation harness invokes `cli.main(argv)` once per dataset case and captures stdout, stderr, and exit code. The empty-input case is validated against its separate CLI outcome contract; a returned exit code 2 is recorded as `ERROR`.
- **Rationale**: Driving the actual CLI entry point verifies argument parsing, stream behavior, and both application/service exit codes instead of bypassing them. Fake transports keep tests deterministic while actual evaluation exercises the configured client.
- **Alternatives considered**: Mocking global `urllib` state couples tests to implementation details; live calls in unit tests are unreliable, costly, and unsuitable for service-error testing.

### Empty-input scoring and committed evidence

- **Decision**: The `invalid_input` case uses a separate CLI outcome contract as its schema-layer contract: exit code 1, empty stdout, and a safe stderr diagnostic. Its invariant layer verifies zero transport calls. It still receives schema/contract, applicable-invariant, and semantic scores under the fixed weights. Commit `evidence/eval-results.json` with the model name, non-secret settings, per-case results, and overall `PASS`/`FAIL`/`INCONCLUSIVE`; never include the API key.
- **Rationale**: This reconciles the required no-JSON behavior for empty text with the all-case evaluation workflow without pretending that an absent JSON object conforms to the reminder-result schema. Committed evidence makes the full evaluation outcome reviewable while preserving the credential boundary.
- **Alternatives considered**: Counting the case as an unconditional schema failure would make the schema-validity gate impossible to pass; omitting it from the dataset would contradict the requested evaluation case.

### Project README

- **Decision**: Update only the Git-root `README.md` when implementing documentation. Document both assignment parts and add Part-1B setup, run, evaluation, and quality-check commands.
- **Rationale**: Part-1B is a subdirectory, while the repository has one shared README at its root.
- **Alternatives considered**: A new Part-1B README would duplicate project documentation and is not required.

## Design Notes

- A model response is untrusted even when JSON mode or a response schema is used. Reject missing/extra fields, invalid types, invalid local datetimes, invariant violations, and unusable candidate content before stdout.
- Keep reminder text in a separate user-content part and state in the system instruction that it is data, never an instruction source.
- Use the supplied naive local `now` as the sole date anchor. Encode the fixed time-of-day defaults in the prompt and evaluation cases.
- Do not add a persistence layer, SDK, retry framework, or asynchronous job system; none is required for one request per process.
