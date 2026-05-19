# ObservabilityAudit

A read-only audit of how the codebase logs, traces, and surfaces
errors at runtime. Asks the questions a static-type checker can't:
*does production speak when something goes wrong, and does it tell
the truth?*

Stack-agnostic — the audit's questions (swallowed errors, missing
correlation IDs, log-level mismatches, PII in logs, unhealthy health
checks) are universal across languages and runtimes. The prompt
adapts to whichever logging / tracing / metrics SDK the project
uses.

| Prompt | Scope |
|---|---|
| `observability-audit.prompt.md` | Read-only audit. Errors, logging, tracing, metrics, health, sensitive data. One audit, one report. |
| `observability-fix.prompt.md` | Actions findings from the audit. Redacts sensitive data, corrects log levels, tightens health checks, repairs swallowed errors, propagates correlation IDs, instruments outbound calls. Default scope is `sensitive-data` + `log-levels` + `health-checks`; `error-handling`, `correlation`, `tracing`, and `metrics` are opt-in. Commits per category. Does not push. |

## What the audit looks for

- **Swallowed errors** — empty catches, catch-and-log-only patterns
  that hide failure from downstream callers.
- **Inconsistent log levels** — `error` for routine events, `info`
  for things that should be `warn`.
- **Missing correlation** — request IDs / trace IDs / user IDs not
  propagated through async boundaries.
- **Sensitive data in logs** — credentials, tokens, full request
  bodies containing PII.
- **Unstructured logging** — string interpolation where structured
  fields would let downstream tools filter.
- **Unhealthy health checks** — endpoints that return 200 without
  actually checking downstream dependencies.
- **Untraced outbound calls** — DB / HTTP / queue calls outside a
  span, so the trace tree has gaps.
- **Metrics emitted but unused** — cost without value.
- **Critical paths emitting nothing** — value without cost.

## What the fix actions

The fix prompt's categories map onto the audit's sections:

- `sensitive-data` (default) — strip credentials / tokens / PII
  from log calls; add field patterns to existing redaction
  middleware. Does **not** scaffold a redaction layer from scratch
  — that's a design decision.
- `log-levels` (default) — correct obvious level mismatches;
  convert string-interpolated log calls to structured.
- `health-checks` (default) — add real downstream-dependency
  checks; split liveness from readiness; update orchestrator
  manifests that reference the endpoints. In the default scope
  because a dishonest health check is the same severity class as a
  swallowed error and the audit's findings are mechanical to apply.
- `error-handling` (opt-in) — preserve cause chain in generic
  re-throws; add `.catch` on dangling promise chains. Empty
  catches and log-and-swallow sites stop and ask by default — the
  decision shape (log-only / log + rethrow / log + return-failure)
  is behavioural and belongs with the human; auto-apply only when
  the audit's recommendation for the specific site is unambiguous.
- `correlation` (opt-in) — swap bare-logger imports for the
  project's request-scoped logger; propagate context across async
  boundaries when the project has a context utility. Does **not**
  scaffold an `AsyncLocalStorage` module from scratch.
- `tracing` (opt-in) — wrap untraced outbound HTTP / DB / queue
  calls in spans; add top-level spans to background jobs. Prefers
  OpenTelemetry auto-instrumentation where it's already wired.
- `metrics` (opt-in) — drop high-cardinality tags, rename for
  convention. Does **not** add new metrics — that's design.

Sensitive-data fixes always commit ahead of every other category
so the security-relevant changes are distinguishable in the git
log.

## Required tool capabilities

- File read across the repo.
- Shell execution for grep / static analysis.
- Git for the fix prompt's per-category commits.
- No runtime access needed — both prompts are static. (A companion
  prompt that exercises behaviour at runtime would belong in
  [`MilestoneSmoke/`](../MilestoneSmoke/).)

Designed for Claude Code and Codex CLI; anything with the same
capability set should work.

## Output discipline

The audit writes to `docs/audits/observability-<timestamp>.md`
(e.g. `docs/audits/observability-20260519T143022.md`). Each run
produces a new file so the directory accumulates an ordered
history; the fix prompt picks the most recent. The `docs/audits/`
folder should be gitignored — these are working artefacts, not
tracked history.

The fix prompt reads that file, actions per category with a
verify-and-commit gate between categories, and writes its own
summary to the conversation (not to a file). Commits are local;
the prompt does not push or open a PR.

## Invocation

See the [root README](../README.md#invocation) for the three
supported patterns. No core / variant split — both prompts are
single files.
