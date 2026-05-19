---
description: Action findings from observability-audit. Fix log levels, redact sensitive data, repair swallowed errors, propagate correlation IDs. Verify build, commit per category. Local only.
related: [observability-audit]
---

# Observability fix

Action findings from an `observability-audit` report against the
codebase. Fixes log-level mismatches, redacts sensitive data,
repairs swallowed-error patterns, adds correlation-ID propagation,
fixes high-cardinality metric tags, and tightens health checks.
Verifies the build between categories and commits per category so a
regression can be reverted without losing the others.

This prompt is conservative by default. Several observability
findings are judgment-heavy (is this swallowed error a bug or
intentional? is this metric cardinality a real risk or theoretical?)
— those surface as TODOs or stop-and-ask rather than auto-apply.
Mechanical fixes (log level wrong for the content, credential in a
log line, missing `await` in an async error path) auto-apply.

It does **not** push and does **not** open a PR.

---

## Context

Observability fixes are riskier than they look. A "fix" to a
swallowed error can turn a quietly-degraded code path into a noisy
crash. A "fix" to a log level can page on-call for the first time on
an event that was already happening. A "fix" to a health check can
cause the orchestrator to restart healthy pods that were lying.

The mechanical fixes — redact a logged password, correct an
obviously-wrong log level, propagate a trace ID — are safe. The
structural ones — change error-handling semantics, add new spans
across async boundaries, reshape health checks — need a human
decision per site.

This prompt biases hard toward the mechanical side. Structural
changes are opt-in via category flags, and even then the prompt
prefers to surface a TODO over guessing.

---

## Inputs

The user supplies:

- **Categories in scope** — any combination of:
  - `sensitive-data` — redact credentials, tokens, PII from log
    calls; add field patterns to existing redaction middleware.
  - `log-levels` — fix obvious level mismatches (`error` on routine
    events, `info` on caught exceptions); convert string-interpolated
    log calls to structured logging.
  - `error-handling` — repair empty catches, log-and-swallow
    patterns, and re-throws that drop the cause chain.
  - `correlation` — propagate request / trace / user IDs through
    async boundaries; add missing logger context fields.
  - `tracing` — wrap untraced outbound calls (DB, HTTP, queue) in
    spans; add spans to background jobs.
  - `metrics` — drop high-cardinality tags; normalise metric names
    to the project's convention.
  - `health-checks` — convert shallow health checks to check real
    downstream dependencies; split liveness from readiness.

  Default scope is `sensitive-data` + `log-levels` + `health-checks`.
  Everything else requires explicit opt-in — `error-handling`,
  `correlation`, `tracing`, and `metrics` all change runtime
  behaviour in ways that need a deliberate decision.

  `health-checks` is in the default scope because a dishonest health
  check (returns 200 while the DB is down) is the same severity
  class as a swallowed error and the fix is mechanical given the
  audit's findings — add a downstream-dependency check, split
  liveness from readiness. The blast radius is real (orchestrators
  consume the endpoint and may restart pods) but bounded; the fix
  prompt's Step 8 guards against breaking the orchestrator probe by
  requiring manifest updates when endpoint names change.

- **Excluded paths** — optional, comma-separated list of file globs
  or directories to skip even within an in-scope category. Use for
  code the user wants to handle by hand (a legacy module mid-
  rewrite, a vendored third-party library, etc.).

- **Included paths** — optional, mutually exclusive with excluded.
  Narrows action to just those paths within the in-scope categories.

If the user hasn't specified scope, ask before doing anything else.
Don't guess. The audit is the survey; the fix should be deliberate.

---

## Step 1 — Locate the audit

The audit writes to `<root>/observability-<timestamp>.md`. Resolve
`<root>` in this order: `.playbook-audits/` if it exists, else
`docs/audits/` if that exists (legacy convention). Look for files
matching `<root>/observability-*.md` and pick the most recent
(`ls -1 <root>/observability-*.md 2>/dev/null | sort | tail -1` —
the `YYYYMMDDTHHMMSS` suffix sorts lexicographically). If neither
root exists or no report is found, ask the user whether they have
an inline report to paste, or whether they need to run the audit.

If the user named a specific report file, use that one instead of the
most recent.

If neither a file nor an inline report is available, stop and
recommend running `/playbook observability-audit` first.

---

## Step 1.5 — Apply the include / exclude filter

Before any action, build the final action list:

1. Start with every audit finding under the in-scope categories.
2. If `Included paths` is set, drop everything except those paths.
3. If `Excluded paths` is set, drop those paths.
4. Surface the filtered list to the user before proceeding ("After
   filtering, X findings remain in scope: ..."). If the filter
   removed everything, stop.

---

## Step 2 — Verify the audit is still valid

Observability findings can go stale fast — a log call may have been
edited between audit and fix; a catch block may have already been
repaired. Before acting on any finding:

- The file still exists at the path the audit cited.
- The reported line still has the issue (re-grep the specific
  pattern).
- The fix is still applicable given the surrounding code (a log
  call that now has `if (env !== 'prod')` around it may not need
  the same fix).

If a finding no longer applies, record under "Skipped — no longer
applies" and move on.

---

## Step 3 — Action `sensitive-data`

This category runs first when in scope. A credential in a log line
is a security incident waiting to happen; nothing else competes.

For each sensitive-data finding:

**Credential / token / password / authorization header logged**:

- Remove the sensitive field from the log call.
- If the surrounding context still needs *something* logged,
  replace with a redacted form (`logger.info("auth attempt", { user: email, status: 'ok' })`,
  not `logger.info("auth attempt", { user, password, token })`).
- If the log call is `JSON.stringify(req)` or similar wholesale
  serialisation, replace with explicit field selection (
  `logger.info("request", { method: req.method, path: req.path, userId: req.user?.id })`).

**Full request / response body logged**:

- Replace with a field-selected log call. Surface a TODO if it's
  unclear which fields the team actually needs to debug from logs.

**Redaction middleware exists but field isn't on the redaction
list**:

- Add the field name to the redaction config. Examples:
  - Pino: `pino({ redact: ['req.headers.authorization', 'password', '*.token'] })`
  - Winston: a custom format that scrubs known field names.
  - structlog: a processor that elides matching keys.
- Read the existing redaction config to find its shape — don't
  scaffold a new one.

**Wildcard semantics matter for path-style redactors.** Pino's
`redact: ['password']` does **not** redact `body.user.password` —
only top-level `password` keys. Use `'*.password'` to match any
object's `password` key at the first level, `'**.password'` for
deep wildcards (where supported by the version in use), or specific
paths like `'body.user.password'`. After adding a pattern, run the
affected log call locally (or in a unit test) and confirm the
redacted output before committing — a pattern that doesn't match
ships as a silent leak. Other SDKs have similar gotchas; check the
SDK's redaction docs for path syntax before adding.

**No redaction middleware exists at all**:

- This is bigger than a fix pass. Surface as a recommendation in
  the report ("Add a redaction processor to the logger pipeline —
  see `<link to logger SDK redaction docs>`"). Do not scaffold a
  redaction layer from scratch; that's a design decision.

After all sensitive-data findings are actioned, run the verification
(Step 9). Commit with message like:

- `obs: redact authorization headers and passwords from logs`
- `obs: add password / token field patterns to logger redaction`

Sensitive-data fixes get their own commit (or small batch of
commits) ahead of every other category — the trail must show the
security-relevant changes distinctly.

---

## Step 4 — Action `log-levels`

For each level mismatch:

**`logger.error("user logged in")` — routine event at `error`**:

- Demote to `logger.info`.
- If the event is genuinely informational and high-volume, consider
  `debug`. The audit's recommendation drives the target level.

**`logger.info(exception)` — exception caught and logged at `info`**:

- Promote to `logger.error` (or `logger.warn` if the exception is
  expected and handled, like an upstream 404 the caller can retry).
- The audit should have indicated which; if unclear, prefer `error`
  for unhandled-class exceptions and surface as a TODO for the
  rest.

**`logger.warn` used as a noisy `info`**:

- Demote to `info` or `debug` per the audit's recommendation.

**String-interpolated log calls (`logger.info(\`user ${id} did ${action}\`)`)**:

- Convert to structured: `logger.info("user action", { userId: id, action })`.
- Preserve the human-readable message portion as the first
  argument; the structured fields go second.
- If the project's logger doesn't accept a structured second
  argument, match the project's existing structured-log convention
  (some use `{ msg, ...fields }`, some use a context object).

After all log-level findings are actioned, run verification (Step
9). Commit message examples:

- `obs: correct log levels on caught exceptions`
- `obs: convert string-interpolated log calls to structured`

---

## Step 5 — Action `error-handling`

Each finding here is judgment-heavy. The default behaviour is: fix
the mechanical cases, surface the rest as TODOs.

**Empty catch blocks**:

The decision shape — log only, log + rethrow, log + return failure
result, leave alone — depends on whether downstream callers should
see the failure. That's a behavioural decision; the fix prompt
doesn't make it.

- **Default: stop and ask.** For every empty catch the audit
  flagged, surface the finding with the file path and the
  surrounding function's signature, and ask the user which shape to
  apply (log-only / log + rethrow / log + return-failure / leave).
  Group similar catches and ask once per group.
- **Auto-apply path:** only when the audit's recommendation for the
  specific catch is unambiguous — i.e. the audit text literally
  specifies "add log + rethrow" or "add log + return failure
  result" for that site. In that case, apply the specified shape:
  add the `logger.error("<context>", { error: e })` plus the
  failure-propagation form. One commit per fix; verify between.
- **Never auto-apply a silent `logger.warn`-only fix.** Turning a
  silent swallow into a quietly-logged swallow is a real change
  (downstream still sees success, but on-call now gets noise) and
  needs the same deliberation as a rethrow.

**Log-and-swallow**:

Same shape as empty catch. The catch already logs, so the question
is only "should this also propagate the failure?" That's still a
behavioural decision.

- **Default: stop and ask.** Group similar sites; ask once per
  group whether to add `throw e` / `return failureResult` after the
  existing log call.
- **Auto-apply path:** only when the audit explicitly recommends
  propagating the failure for that specific site.

**Generic re-throws (`throw new Error(e.message)`)**:

- Replace with cause-preserving form:
  - JS/TS: `throw new Error('context-message', { cause: e })`
  - Python: `raise NewError("context") from e`
  - C#: `throw new ServiceError("context", innerException: e)`
  - Go: `return fmt.Errorf("context: %w", err)`
  - Rust: with `anyhow` / `thiserror`, `.context("context")?`
- The mechanical fix is safe — adding the cause doesn't change
  behaviour, just enriches it.

**Catch-too-broad (`catch (e)` wrapping 20 lines)**:

- This is structural. Splitting the catch into narrower scopes is a
  refactor, not a fix. Surface as TODO in the report.

**Async error gaps (missing `.catch` on a `.then` chain, `await`
outside a `try`)**:

- Add a `.catch(err => logger.error(...))` to dangling promise
  chains. If the surrounding code already has an unhandled-
  rejection handler at the process level, the `.catch` is still
  worth adding to attach context to the log line.
- For unwrapped `await`, add the surrounding `try` / `catch`. The
  catch body should at minimum `logger.error` with context.

After all error-handling findings are actioned (or surfaced as
TODOs), run verification. Commit examples:

- `obs: log and re-throw in previously empty catches`
- `obs: preserve cause chain in generic re-throws`
- `obs: handle dangling promise rejections in worker/jobs.ts`

---

## Step 6 — Action `correlation`

This category changes the shape of every log call in the affected
modules. Action only on opt-in.

**Logger context missing `requestId` / `traceId` / `userId`**:

- If the project has a logger-context utility (a request-scoped
  logger wrapper, an `AsyncLocalStorage` setup, OpenTelemetry's
  `context.active()`), use it — don't pass IDs through every
  function signature by hand.
- If no context utility exists, the fix is bigger than a pass.
  Surface as a recommendation: "Add an `AsyncLocalStorage`-backed
  request-context module; populate from middleware; consume from
  the logger factory."

**Correlation ID dropped across an async boundary**:

- The fix is to capture the context at the await / enqueue site
  and restore it on the receiving side. Specific shapes:
  - `setTimeout` / `setInterval` callbacks: wrap with the context
    propagator the project uses.
  - Background-queue publishes: attach the trace context to the
    message metadata; restore on consumer.
  - Worker threads / child processes: propagate via spawn options
    or an explicit message envelope.
- If the project uses OpenTelemetry, prefer
  `context.with(context.active(), () => ...)` patterns over hand-
  rolled IDs.

**No correlation ID on log lines emitted from a request handler**:

- If a request-scoped logger exists, swap the bare `logger` import
  for the request-scoped one in the affected file. Mechanical.

After action, run verification. Commits:

- `obs: propagate trace context through queue publishes`
- `obs: switch payments handler to request-scoped logger`

---

## Step 7 — Action `tracing`

**Outbound HTTP / DB / queue call outside a span**:

- If the project uses OpenTelemetry auto-instrumentation, the fix
  is usually "import the instrumentation package and register it
  at startup" — one-time setup, not per-call.
- If auto-instrumentation is already wired but specific clients
  (custom HTTP wrappers, queue libraries without an OTEL plugin)
  aren't covered, wrap the call site:

  ```ts
  const tracer = trace.getTracer('outbound-http');
  return tracer.startActiveSpan('http.post /upstream/foo', async (span) => {
    try {
      const result = await client.post(...);
      span.setStatus({ code: SpanStatusCode.OK });
      return result;
    } catch (e) {
      span.recordException(e);
      span.setStatus({ code: SpanStatusCode.ERROR });
      throw e;
    } finally {
      span.end();
    }
  });
  ```

- For background jobs missing a top-level span: wrap the job
  function body in `startActiveSpan` with the job name.

**Long-running jobs with no span**:

- Wrap the job body. Use the job's natural name as the span name.

After action, run verification. Commits:

- `obs: instrument custom HTTP wrapper with OTEL spans`
- `obs: wrap nightly billing job in a top-level span`

---

## Step 8 — Action `metrics`, `health-checks`

**Metrics — high-cardinality tag**:

- Drop the high-cardinality field (user ID, request ID, full URL)
  from the metric tags. Move it to a log field if the value is
  still useful for debugging.
- For URL: replace the full URL with the route template
  (`/users/:id` not `/users/12345`).

**Metrics — naming drift**:

- Rename to match the project's convention. If the convention is
  unwritten, surface as a recommendation and stop — picking a
  convention is a design decision.

**Metrics — critical path with no metrics**:

- Adding new metrics is *not* in scope for a fix pass. Surface as
  a recommendation; the user picks what to instrument.

**Health checks — shallow**:

- Add a real downstream check for each critical dependency:
  - Database: a `SELECT 1` (or framework equivalent).
  - Cache: a `PING` (Redis) / equivalent.
  - Queue: a connection check, not a publish.
- Set a short timeout per check (1-2 seconds) so a slow dependency
  doesn't hang the health endpoint forever.
- For non-critical dependencies (an optional cache, a third-party
  enrichment service), do not include them in liveness — failing
  liveness on an optional dep causes pointless restarts.

**Health checks — liveness vs readiness conflation**:

- Split into two endpoints:
  - `/livez` — process is running. No downstream dependency
    checks. Used by the orchestrator to decide whether to restart.
  - `/readyz` — process is ready to serve. Downstream dependency
    checks belong here. Used by the orchestrator to decide whether
    to route traffic.
- If Kubernetes manifests reference the existing endpoint, update
  them to reference the new split — `livenessProbe` to `/livez`,
  `readinessProbe` to `/readyz`. Manifest edits are in scope when
  the audit flagged the endpoint mismatch.

After action, run verification. Commits:

- `obs: drop user-id tag from request-duration histogram`
- `obs: check database connectivity in /readyz`
- `obs: split /healthz into /livez and /readyz`

---

## Step 9 — Verification per category

After **each** category's action:

```sh
# Typecheck (if TS)
<project's typecheck command>

# Lint
<project's lint command>

# Build
<project's build command>

# Unit + integration tests — especially relevant for error-handling
# changes, where a previously swallowed error may now cause a test
# to surface a real failure (which is the point — but it still
# needs human review).
<project's test command>
```

Infer exact commands from the project's `package.json` / `pyproject.toml`
/ `Cargo.toml` / `*.csproj` / `Makefile`.

**In a monorepo**, scope verification to the affected workspace:

```sh
turbo run build --filter=<workspace>
pnpm --filter <workspace> build
npm run build -w <workspace>
yarn workspace <workspace> build
nx run <workspace>:build
```

If checks fail: revert the category's edits, record under "Skipped
— broke checks" with the failing command and a one-line guess.

If checks pass: stage and commit with a per-category message
prefixed `obs:`. One commit per category keeps a broken category
revertible.

---

## Step 10 — Run the full check suite

When all in-scope categories are actioned, run from a clean state:

- Typecheck.
- Lint.
- Build.
- Test (unit + integration).
- If the project has an end-to-end test against a real telemetry
  pipeline (rare but valuable): run it.

A passing check suite is the gate.

---

## Step 11 — Report

Output a short summary:

- **Categories actioned** — count per category, with file paths.
- **Edits applied** — list grouped by category.
- **TODOs surfaced** — judgment-call empty catches, swallowed
  errors that need a behavioural decision, missing metrics on
  critical paths, missing redaction middleware. Count + sample.
- **Skipped within scope** — with reason per item (no longer
  applies, broke checks, structural rather than mechanical).
- **Out-of-scope follow-ups** — adding new metrics, scaffolding a
  redaction layer, adopting OpenTelemetry auto-instrumentation,
  picking a metric naming convention.
- **Final check result** — pass / fail with the failing command.
- **Suggested PR title and body** — draft for a human to paste, not
  to open.

---

## Constraints

- Do not push to the remote.
- Do not open a PR.
- Do not action categories outside the user's stated scope. The
  default (`sensitive-data` + `log-levels`) is deliberately narrow.
- Do not "fix" a swallowed error by re-throwing without confirming
  with the user. A previously-quiet code path suddenly crashing in
  production is a worse outcome than the original silent failure.
  Surface as TODO if the audit didn't mark it as a bug.
- Do not scaffold a redaction layer, an `AsyncLocalStorage` context
  module, or OpenTelemetry auto-instrumentation from scratch as
  part of a fix pass. Each is a design decision with its own
  rollout plan.
- Do not add metrics that don't already exist. Removing tags or
  renaming is mechanical; instrumenting a new code path is design.
- Do not rename log fields adjacent to a fix. The fix prompt is a
  surgical pass; downstream alerting / dashboards may key on
  field names.
- Do not change health-check endpoints without also updating the
  orchestrator manifests that reference them — a healthy app that
  the orchestrator can no longer probe is worse than a dishonest
  one.
- Do not edit vendored / third-party code, even when the audit
  flagged a finding there. Vendoring exists for reasons that won't
  be in the audit; the fix lives upstream or in a wrapper.
- Sensitive-data fixes commit ahead of every other category, even
  when batched. The git log must let a reviewer answer "which
  commit was the security fix" without reading bodies.
- Do not log the value you are removing in the commit message
  ("redacted `Authorization: Bearer abc123`"). Treat the redaction
  itself as sensitive.
