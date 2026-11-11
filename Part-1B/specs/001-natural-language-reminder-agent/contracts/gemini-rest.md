# Gemini REST Contract

## Request

- **Method and URL**: `POST https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent`
- **Authentication**: `x-goog-api-key: <GEMINI_API_KEY>` request header. Never put the key in a URL, request body, logs, or diagnostics.
- **Content type**: `application/json`.
- **Timeout and retries**: 30-second timeout per request; at most three total attempts, retrying only HTTP 429 and 503.
- **Generation settings**: temperature `0.2`; request `responseMimeType: "application/json"`. Include the locally defined response JSON schema only when the configured model supports it.

The request uses Gemini's system instruction for agent policy and puts the untrusted reminder text in a separate user-content part. The system instruction includes the supplied `--now`, output constraints, safety rules, and fixed vague-time defaults; user text is never interpolated into the system instruction.

## Response handling

Extract candidate text from the `generateContent` response and parse it as JSON. Empty, blocked, malformed, or otherwise unusable candidate content is an application/model-response error. The local validator remains authoritative even if Gemini returns schema-constrained JSON.

## Failure mapping

- HTTP 429/503: retry up to the three-attempt total; after exhaustion raise `ServiceError`.
- Timeout, DNS, connection, or other network failure: raise `ServiceError` without retry.
- Other HTTP errors, invalid response envelope, or invalid generated JSON/result: application error; do not retry.
- `ServiceError` maps to CLI exit code 2 and no JSON result. Application errors map to exit code 1 and no JSON result.

## Transport boundary

`core.run(text, now, transport)` receives a callable transport. The production implementation accepts the system instruction and user text and returns candidate text; tests supply a fake callable and do not access the network.
