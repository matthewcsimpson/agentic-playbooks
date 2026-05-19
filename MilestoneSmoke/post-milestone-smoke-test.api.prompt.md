---
description: Drive a running HTTP API after a milestone tag is cut — hit headline endpoints with concrete requests, assert response shape and auth behaviour, write a pass/fail/blocked report.
---

# Post-milestone smoke test — API variant

Drive a running HTTP API after a milestone tag is cut. Hit the
milestone's headline endpoints with concrete requests, assert
status / response shape / auth behaviour, and write a
pass/fail/blocked report.

**This prompt extends [`core/post-milestone-smoke-test.core.prompt.md`](./core/post-milestone-smoke-test.core.prompt.md).**
Read the core file first for the workflow shape (Step 1 milestone
window, Step 2 bucketing, Step 3 flow planning, Step 4 execution
loop, Step 5 cross-cutting concept, Step 6 report shape, and the
Constraints). This file supplies the API-specific bits.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Scope

This variant is **HTTP API only**. It assumes:

- The service exposes HTTP endpoints (REST, GraphQL, RPC over
  HTTP).
- A running instance is reachable from the agent (typically
  `http://localhost:<port>`).
- Auth requires either an API key, a bearer token, an OAuth
  client credentials grant, or a seeded test user the agent can
  authenticate as.

For browser-driven web flows, see `.web`. For CLI binaries, see
`.cli`. For mobile / desktop / daemon surfaces, no variant exists
yet.

---

## Prerequisites

The session running this prompt must have:

- A running API instance, reachable from where the agent runs
  shell commands. Default expectation: `http://localhost:<port>`.
  If the service isn't running, surface that as a blocker and
  stop — do not attempt to start it from this prompt.
- An HTTP client available — usually `curl` (always present) or
  `httpie` if the project prefers a higher-level CLI.
- The project's test credentials documented (API key, bearer
  token, OAuth client / secret, seeded user credentials with a
  way to obtain an access token).

If the service is not reachable or the credentials aren't
documented, surface that and stop.

---

## Test credentials

The project must document how the smoke test authenticates. The
expected shape is one of:

- **API key**: a header or query-parameter convention with a
  test-only key.
- **Bearer token**: a documented test user whose credentials
  produce a token via the project's login endpoint, plus the
  flow to obtain that token.
- **OAuth client credentials**: a documented test client ID +
  secret that grants a service-scope token via the project's
  token endpoint.
- **Cookie session**: a test user whose login produces a session
  cookie the smoke test can re-use.

Sample / mock data — if the API depends on seeded fixtures
(specific user IDs, organisation IDs, etc.), the project should
document those IDs in a known location
(`docs/test-data.md`, a section in `CLAUDE.md`, or passed into
this prompt directly).

If credentials are missing, surface that and stop. Guessing
credentials produces unreliable runs and may lock accounts.

---

## §2 — What "user-facing" means (API)

An API user-facing surface is: a new endpoint, a new optional
parameter or query filter on an existing endpoint, a new
response field, a new error code, a new auth requirement, a new
webhook / event emission.

Schema migrations, internal refactors, observability changes,
infra changes are "behind-the-scenes" per the core's §2.

---

## §3 — Step shape (API)

Steps must be concrete HTTP requests. Each step lists:

- **Method + path**: `POST /api/v1/users`, `GET /api/v1/orders/:id`.
- **Headers** (where they matter): `Authorization`,
  `Content-Type`, `Idempotency-Key`, etc.
- **Body** (for POST / PUT / PATCH): JSON payload as a literal
  example.
- **Expected response**: status code + the response fields the
  step relies on for the next step (don't enumerate every
  field; just the ones the next step reads).

Avoid narrative ("create a user") — every step is an
executable request. Format the step in a way the agent can
translate directly to `curl`:

```
POST /api/v1/users
Authorization: Bearer <token>
Content-Type: application/json

{ "email": "smoke+1@example.com", "name": "Smoke Test" }

→ expect 201, body.id present
```

---

## §4 — Execute mechanics (API)

**Reset state**: typically nothing — APIs are stateless from the
caller's perspective per request. If a flow creates resources
that would conflict on re-run, either:

- Use unique identifiers per run (timestamp / UUID in the body).
- Or document a cleanup step at the end of the flow.

If the project has a test-data reset endpoint, call it between
flows that need clean state.

**Walk the steps** using `curl` (or the project's preferred
HTTP client). For each step:

1. Issue the request.
2. Capture the status code, response headers (especially
   `Content-Type`, `Location`, rate-limit headers), and
   response body.
3. Confirm the expected status code matches.
4. If the step's "expected response" lists fields, confirm
   they're present and shape-compatible with what the next
   step needs.

If a step fails (wrong status, missing field, network error),
record where it failed and stop the flow.

**Observe during execution**:

- **Status codes** — every non-success in a flow that should
  succeed is a finding.
- **Response time** — note responses taking >1.5s without an
  obvious reason (cold start, real upload, paginated bulk).
- **Server logs** (if the agent has access to them via a tail
  command the project documents) — new errors / warnings
  during the run.

**Capture an artefact**: a `.txt` or `.json` file containing the
full request / response trace for the flow. Save under
`docs/smoke-tests/<tag>-<timestamp>/<flow-number>.log` and link from the
report.

---

## §5 — Cross-cutting checks (API)

After the per-feature flows, do one targeted run for:

- **Health endpoint** — `GET /health` (or whatever the project
  exposes) returns 200 with the documented body shape.
- **Auth required** — pick a known protected endpoint, hit it
  without credentials, expect 401 (not 500, not 200).
- **Forbidden vs not-found** — when hitting a protected
  resource as the wrong user, expect 403 (not 404) per the
  project's documented contract.
- **404 path** — hit `GET /api/v1/this-route-does-not-exist`,
  expect 404 with the project's documented error shape (not
  500, not HTML).
- **CORS preflight** (if the API is browser-callable) — an
  `OPTIONS` request to a CORS-relevant endpoint returns the
  expected headers.
- **OpenAPI / Swagger doc renders** — `GET /docs` (or the
  project's path) returns the expected schema or HTML.

Each is its own pass / fail row.

---

## §6 — Report observation fields (API)

In the per-flow report block, fill in:

- **Observations**:
  - Status codes: <list per step, e.g. "201, 200, 200">
  - Slow responses: <"none" | "GET /api/foo took 2.4s">
  - Server log findings: <"none" | "1 new error: ...">
- **Artefact**: `docs/smoke-tests/<tag>-<timestamp>/<flow-number>.log`
