---
description: Read-only audit of how a codebase logs, traces, and surfaces errors — swallowed errors, missing correlation IDs, log-level mismatches, PII in logs, dishonest health checks.
related: [observability-fix]
---

# Observability audit

Read-only audit of how the codebase logs, traces, and surfaces
errors at runtime. Asks the questions a static-type checker can't:
*does production speak when something goes wrong, and does it tell
the truth?*

Stack-agnostic — the questions are universal, only the syntax
differs. Adapt the greps below to the project's language (`try`/
`catch` for JS/TS/Java/C#, `try`/`except` for Python, `result.Err()`
for Rust, etc.).

## Inputs

Scope is load-bearing — a whole-repo observability audit and a "just
the payments service" audit produce different reports.

If the user hasn't named a scope, **ask before starting**. Offer them
three options:

1. **Name a specific scope** — a service, package, or feature area
   (e.g. `services/payments/`, `lib/queue/`, "the auth flow").
2. **Run against the whole repo** — confirm they want the wide scan.
3. **Infer it yourself** — pick the service or package that most
   directly handles external requests or background work, where
   observability matters most. State your choice before proceeding.

Also ask whether test files are in scope (default: excluded — test
logging follows different rules from production).

Don't guess silently.

---

## Step 0 — Convention sourcing

Read every file the project uses to document conventions, in
priority order:

- `CLAUDE.md` at the repo root and any nested ones.
- `AGENTS.md`.
- `.github/copilot-instructions.md`, `.github/instructions/**/*.md`.
- `.cursor/rules/**/*` (or `.cursorrules`).
- Any `docs/logging.md`, `docs/observability.md`, runbooks, or
  on-call docs that document conventions.
- `README.md` — skim for telemetry conventions.

Enumerate the rules you'll be checking before scanning. If the repo
has none of these, fall back to the generic categories below — but
note in the report that the spine of the audit (project-specific
rules) is missing. A short, opinionated logging doc is usually a
higher-leverage investment than tuning the audit itself.

---

## Step 1 — Identify the telemetry stack

Detect what's already in use by reading manifests and a sample of
source files:

- **Logging**: Winston / Pino / Bunyan (JS), `logging` module /
  structlog / loguru (Python), Serilog / Microsoft.Extensions.Logging
  (.NET), `log` / `slog` (Go), Logback / Log4j2 (Java), `os_log` /
  `Logger` (Swift), `tracing` (Rust).
- **Tracing**: OpenTelemetry SDK, Datadog APM, New Relic, Sentry
  Performance, Honeycomb beelines.
- **Metrics**: Prometheus client, OpenTelemetry metrics, StatsD,
  Datadog metrics, CloudWatch EMF.
- **Error reporting**: Sentry, Rollbar, Bugsnag, Airbrake.
- **Aggregator / collector**: vector, fluentbit, otel-collector,
  agent-installed integrations.

Report the stack in the audit header. The findings that follow only
make sense in context of the SDK in use.

If the project has **no telemetry stack at all**, that is the
finding — surface it in the Summary as ⚠️ HIGH, then proceed with
the generic categories (the patterns are still detectable; the
remediations just look different).

---

## Step 2 — Error handling

For each language in the repo, scan for the project's catch syntax:

```sh
# JS / TS
grep -rnE '\bcatch\s*\(' --include='*.ts' --include='*.tsx' --include='*.js' .
# Python
grep -rnE '\bexcept\b' --include='*.py' .
# C#
grep -rnE '\bcatch\s*\(' --include='*.cs' .
# Swift
grep -rnE '\bdo\s*\{|\bcatch\b' --include='*.swift' .
```

For each catch site, classify:

- ⚠️ **Empty catch** — body is empty, a comment, `pass`, or just
  `return null/undefined/None`. The error is silently swallowed.
- ⚠️ **Log-and-swallow** — body logs the error but doesn't rethrow,
  return an Error result, or set a failure flag. Downstream sees
  success.
- ⚠️ **Catch too broad** — `catch (e)` / `except Exception:` /
  `catch Exception` that wraps too many statements, hiding which
  one actually failed.
- ⚠️ **Generic re-throw** — `throw new Error(e.message)` or
  equivalent that loses the cause chain. Downstream loses the
  stack and the type.
- 💡 **Catch without context** — caught and rethrown with no added
  context about what was being attempted. Not strictly wrong, but
  the resulting trace is hard to triage.

Empty catches and log-and-swallow are ⚠️ ISSUE. Report each with
file path, line, and the one-sentence reason it's a problem.

Special case worth scanning explicitly:

```sh
# Promise rejections without .catch / try-await
grep -rnE '\.then\(' --include='*.ts' --include='*.tsx' --include='*.js' . \
  | grep -v '\.catch\|\.finally'
# `await` outside try blocks (heuristic)
grep -rnE '^\s*(const|let|var)?\s*\w+\s*=\s*await ' --include='*.ts' .
```

Async error handling is the most common silent-failure shape;
worth its own sub-section.

---

## Step 3 — Log levels

Scan for log calls and check level alignment with content:

```sh
grep -rnE 'log(ger)?\.(debug|info|warn|error|fatal|trace)\b' \
  --include='*.ts' --include='*.tsx' --include='*.js' \
  --include='*.py' --include='*.cs' --include='*.go' --include='*.rs' .
```

Find:

- ⚠️ **`error` on routine events** — `logger.error("user logged in")`.
  Pages on-call for nothing.
- ⚠️ **`info` on actual errors** — exception caught, logged at
  `info`. Won't trigger alerts.
- ⚠️ **`warn` for normal control flow** — used as a "noisy info";
  noise pollution.
- 💡 **`debug` left over from troubleshooting** — high-cardinality
  fields at `info` level that should be `debug`.
- 💡 **No structured fields** — `logger.info(\`user ${userId} did
  ${action}\`)` instead of `logger.info("user action", { userId,
  action })`. Strings are unfilterable.

For each finding, include the file path, line, and what the level
should be.

If the project uses a logging framework that supports it, also
check:

- Logger naming / namespacing — is the same logger used for
  unrelated concerns? Per-module loggers make log-routing easier.
- Sampling configuration — high-volume debug paths sampled?

---

## Step 4 — Correlation / tracing

A request flowing through the system should be traceable end-to-end.
Look for breaks.

```sh
# Request / trace / correlation ID propagation
grep -rnE '(requestId|correlationId|traceId|trace_id|x-request-id|x-correlation-id)' .

# Span creation
grep -rnE '(startSpan|tracer\.start|span\s*=|with\s+tracer\.)' .

# Outbound HTTP without span context (heuristic — common clients)
grep -rnE '(fetch|axios|httpx|requests\.(get|post|put|delete)|HttpClient|net/http)' \
  --include='*.ts' --include='*.tsx' --include='*.js' \
  --include='*.py' --include='*.cs' --include='*.go' .

# Logger calls in async handlers without `traceId` field
# (manual scan — heuristic: look at request handlers and check log fields)
```

Find:

- ⚠️ **Outbound call outside a span** — DB queries, HTTP fetches,
  queue publishes that aren't wrapped in a span. Trace tree has
  gaps; root-cause analysis becomes guesswork.
- ⚠️ **No correlation ID on log lines** — log events emitted from
  an async context that don't carry the request / trace ID
  forward.
- ⚠️ **Correlation ID dropped across async boundary** — request ID
  attached to logs in the handler but absent from logs in a
  background job triggered by it.
- 💡 **User ID not on log lines** — for user-initiated actions,
  user ID alongside request ID dramatically speeds triage.

For tracing specifically, check that:

- Inbound HTTP requests start a server span (or inherit one from
  upstream).
- Outbound HTTP / DB / queue calls are children of the current
  span.
- Long-running background jobs create a span (otherwise the trace
  ends silently).

---

## Step 5 — Sensitive data in logs

```sh
# Common offenders — adapt to the project's domain
grep -rnE '(password|secret|token|api[_-]?key|authorization|cookie|jwt)' \
  --include='*.ts' --include='*.tsx' --include='*.js' \
  --include='*.py' --include='*.cs' --include='*.go' . \
  | grep -iE 'log|console|print'

# Full request / response body logging
grep -rnE 'log.*req(uest)?\.body|log.*res(ponse)?\.body' .

# Stringifying the whole payload
grep -rnE 'JSON\.stringify\([a-zA-Z_]+\.(body|payload|params|user|account)' .
```

For each, classify:

- ⚠️ **Credential logged** — secret, token, password, full
  authorization header. Treat as ⚠️ HIGH regardless of severity
  context (it's a leak waiting to happen).
- ⚠️ **PII logged** — email, full name, address, phone, payment
  details. Severity depends on jurisdiction / data classification;
  treat as ⚠️ MODERATE by default.
- 💡 **Full request body logged** — even if no immediate PII,
  unstructured body logging will eventually capture PII once a
  caller starts including it. Worth flagging.

For each finding, also note any redaction middleware that *should*
have caught it — if redaction is configured but the field isn't on
the redaction list, that's a redaction-list finding, not a logging
finding.

---

## Step 6 — Metrics

```sh
# Metric emission
grep -rnE '(counter|gauge|histogram|metric|statsd|prometheus)\.' .
```

For each metric:

- 💡 **Tag explosion risk** — metrics tagged with high-cardinality
  fields (user ID, request ID, full URL). Cost blows up; metrics
  become unusable.
- 💡 **Inconsistent naming** — `user_signup_count` vs `signups` vs
  `user.signups`. Convention drift fragments dashboards.
- 💡 **No unit suffix** — `latency` vs `latency_ms` vs `latency_seconds`.
  The Prometheus convention is to put the unit in the name; other
  systems vary.

Then check the inverse: critical code paths emitting *no* metrics.
For each request handler / job / scheduled task:

- ⚠️ **Critical path with no metrics** — handler that runs in
  production with no counter, no latency histogram, no error
  metric. Failures only surface as user complaints.

If the project has an existing dashboard / alert config in the
repo (e.g. `dashboards/`, Datadog Terraform, Grafana JSON),
cross-reference:

- 💡 **Metric emitted but no alert / dashboard** — cost without
  value.
- ⚠️ **Alert references a metric that doesn't exist in the code** —
  paging on something that will never fire.

---

## Step 7 — Health checks

```sh
grep -rnE '(/health|/healthz|/ready|/readyz|/live|/livez|healthCheck)' .
```

For each health endpoint, classify:

- ⚠️ **Shallow health check** — returns 200 without actually
  checking downstream dependencies (database, cache, queue). The
  service answers "yes" while broken.
- ⚠️ **Health check probes a dependency that isn't critical** —
  liveness fails when an optional dep is down, causing
  unnecessary restarts.
- 💡 **No distinction between liveness and readiness** — single
  endpoint covers both; orchestrator can't differentiate "restart
  me" from "don't route to me yet."

If the project deploys to Kubernetes / similar, also check the
manifests (`Deployment`, `StatefulSet`, etc.) for `livenessProbe`
/ `readinessProbe` / `startupProbe` definitions referencing the
endpoints.

---

## Step 8 — Report

Output to `docs/audits/observability-<timestamp>.md`, where
`<timestamp>` is current UTC time in basic ISO 8601 format
`YYYYMMDDTHHMMSS` — generate with `date -u +%Y%m%dT%H%M%S` (e.g.
`20260519T143022`). Always write a new file; do not overwrite prior
runs — the directory is an ordered history. Structure:

```
# Observability audit

Date: <today>
Scope: <whole repo | service/package>
Telemetry stack detected: <logging | tracing | metrics | error-reporting>
Convention sources read: <list>

## Summary

<2-3 sentence verdict. Biggest concern. Lowest-effort highest-impact fix.>

## Error handling

### Empty catches
### Log-and-swallow
### Generic re-throws / catch-too-broad
### Promise / async error gaps

## Logging

### Level mismatches
### Unstructured logging
### Logger naming / namespacing

## Correlation / tracing

### Outbound calls outside spans
### Correlation ID propagation gaps
### Background jobs untraced

## Sensitive data in logs

### Credentials
### PII
### Full request body logging

## Metrics

### Emitted but unused
### Critical paths with no metrics
### Cardinality / naming issues

## Health checks

### Shallow / dishonest
### Liveness vs readiness conflation

## Pattern observations

<For categories with many similar findings: count + top 3 worst
examples. Don't enumerate all 40 instances of the same issue.>

## Recommendations

<5-10 ranked actions. Concrete, with file paths. "Add a try/catch
around the publish call in worker/jobs.ts:142 — currently a network
hiccup silently drops the job." beats "Improve error handling.">
```

Each finding entry uses this shape:

- ⚠️ ISSUE — `path/to/file:42` — Description in one sentence.
  **Suggested:** `fix-now` / `fix-soon` / `defer` / `accept`.
- 💡 CANDIDATE — `path/to/file:42` — Description in one sentence.
  **Suggested:** `defer`.

If a section has no findings, mark it ✅ PASS.

---

## Constraints

- Do not modify any code. Surface findings; the user picks which to
  fix. `observability-fix` is the action companion — it consumes
  this audit's report.
- Every ⚠️ ISSUE must include a file path and line number. "The
  codebase logs sensitive data" is not acceptable — pick the worst
  offender.
- When the project has no telemetry stack at all, do not invent
  one. Report the absence as ⚠️ HIGH in the Summary and recommend
  a starting point (one logging library, one tracing SDK), not a
  full platform migration.
- Sensitive-data findings should never quote the actual sensitive
  value. "Logs the full `authorization` header at `auth.ts:42`" is
  the finding — don't paste the token even if it's clearly a test
  fixture.
- Don't flag a structured log call that includes a `secret`-shaped
  field name as a leak without checking — many SDKs redact fields
  matching common patterns. Verify the redaction config before
  reporting.
- Pattern observations must include a count and the 3 worst
  examples. Don't enumerate every instance.
- Health check / metric findings that depend on external config
  (alerting rules in a separate repo, infrastructure-managed
  dashboards) should note the limitation — the audit only sees the
  code repo.
