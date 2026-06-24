---
description: Find code that's used but more complex than it needs to be — needless indirection, collapsible control flow, reinvented stdlib, redundant derived state, over-parameterization. Read-only.
related: [complexity-fix, dead-code-audit, duplicate-logic-audit]
---

# Complexity audit

Find code that is used and singular, but more complex than it needs
to be: needless indirection, control flow that could collapse,
hand-rolled logic the standard library already provides, state kept
in sync that could be derived, parameters no caller varies. Read-only
audit — does not change anything; surfaces findings so the user can
act.

This is the third refactoring lens, distinct from its siblings:

- **dead-code-audit** finds code that isn't *used* → it gets deleted.
- **duplicate-logic-audit** finds the same job done in two places →
  they get merged to one winner.
- **complexity-audit** finds code that *is* used and singular but
  over-built → it gets *reduced in place*.

The LLM's value-add over linters is *semantic*. Static tools already
flag mechanical style (cognitive-complexity thresholds, `no-useless-*`,
`prefer-const`). What they can't see: that a 40-line hand-rolled
accumulation is a `reduce` / `groupBy`, that an abstraction has
exactly one implementation and adds no real seam, or that a stored
flag is fully derivable from existing state. Surface semantic
reductions, not formatting.

## Inputs

Scope is load-bearing — a whole-repo complexity audit and a "just the
checkout flow" audit produce very different reports.

If the user hasn't named a scope, **ask before starting**. Offer them
three options:

1. **Name a specific scope** — a directory, package, or feature
   area (e.g. `apps/web/`, `lib/pricing/`, "the report builder").
2. **Run against the whole repo** — confirm they want the wide
   scan; the resulting list will be longer and the judgment-call
   findings will be a larger share of it.
3. **Infer it yourself** — pick a scope based on the project's
   structure. Default heuristic: the largest non-test source
   directory, or an area the project's instruction files flag as
   complex / legacy. State your choice before proceeding.

Don't guess silently.

## Step 1 — Establish scope and conventions

Read:

- The project manifest to identify language and framework — the
  available standard library and the idioms it makes idiomatic differ
  by stack.
- LLM instruction files (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules/**`)
  for documented style preferences. If the project says it avoids a
  given language feature or prefers an explicit style, honour that —
  don't propose a "simplification" the project has deliberately ruled
  out.
- Workspace structure: which directories are sources, which are
  generated, which are vendored, which are tests.

Skip vendored / generated / build output. List what you're treating
as in-scope.

## Step 2 — Survey for over-complexity

Read the in-scope code and look for the following classes. For each
finding, the test is: **can the same behaviour be expressed with less
code or fewer concepts, with no change to what the code does?** If a
"simplification" would alter behaviour or edge-case handling, it is
not a finding.

- **Needless indirection / over-abstraction** — a wrapper, factory,
  adapter, or layer with exactly one implementation and no second
  caller, that adds no real seam (no test boundary, no swappable
  backend, no published extension point). Could be inlined.
- **Collapsible control flow** — deeply nested conditionals that
  flatten to guard clauses / early returns; redundant `else` after a
  `return`; boolean expressions that reduce; a chain of `if`s that is
  really a lookup table or `switch`.
- **Reinvented stdlib / already-imported library** — hand-rolled
  loops or utilities the language or an in-use dependency already
  provides (manual grouping vs `Object.groupBy` / lodash `groupBy`,
  hand-written clamp / dedupe / range, a manual `for` loop that is a
  `map` / `filter` / `reduce`). The duplicated thing is a *library*,
  not another spot in this repo — if it duplicates another in-repo
  symbol, that's a `duplicate-logic-audit` finding, not this.
- **Redundant / derived state** — a value stored and manually kept in
  sync that could be computed on read; a boolean flag fully derivable
  from existing state; a cache with no measured need behind it.
- **Over-parameterization / speculative generality** — a parameter,
  option, or generic that every caller passes identically, or whose
  flexibility no caller exercises; a config knob with a single value;
  an interface generalised for a second case that never arrived. Note
  the distinction from dead code: the parameter *is* passed — it's
  just always the same — so the type system won't flag it.
- **Verbose language patterns** — manual null / undefined checks where
  optional chaining or nullish coalescing reads cleaner, manual
  clone / spread, verbose type guards where the language has sugar.
  Stack-aware, and gated by the project's documented style from
  Step 1.

## Step 3 — Classify findings

For each finding, assign a band by how much judgment the change needs
— mirroring how taste-laden simplification is:

- **Clear win** — behaviour-identical, strictly smaller or more
  idiomatic, with no plausible reason to keep the longer form. Safe
  to apply mechanically.
- **Judgment call** — a real reduction, but it trades against
  something: readability is subjective here, or the extra structure
  buys future flexibility someone may want. Worth surfacing; needs a
  human to choose.
- **Risky** — touches edge-case handling, a hot path where the
  verbose form may be deliberate for performance, or public API
  surface. Flag, don't assume.

Be honest about the band. A reduction you find elegant but that a
reasonable maintainer would push back on is a **Judgment call**, not a
**Clear win**.

## Step 4 — Report

Output to `<root>/audits/complexity-<timestamp>.md`, where:

- `<root>` resolves in this order: `.playbook-audits/` if it
  exists, else `docs/` if `docs/audits/` exists (legacy
  convention), else create `.playbook-audits/` and append
  `.playbook-audits/` to `.gitignore` (creating `.gitignore` if
  absent — these are working artefacts, not tracked history).
  Create `<root>/audits/` if it doesn't exist.
- `<timestamp>` is current UTC time in basic ISO 8601 format
  `YYYYMMDDTHHMMSS` — generate with `date -u +%Y%m%dT%H%M%S`
  (e.g. `20260519T143022`).

Always write a new file; do not overwrite prior runs — the
directory is an ordered history. Structure:

```
# Complexity audit

Date: <today>
Scope: <whole repo | directory>
Files scanned: <count>
Findings: <count> (Clear win: <n>, Judgment call: <n>, Risky: <n>)

## Needless indirection

- `path/to/file.ts:wrapFoo` — single-impl wrapper around `foo`, one
  caller, no test seam. Inline it. [Clear win]

## Collapsible control flow

- `path/to/handler.ts:route` — four-deep nesting; invert the first
  two checks into guard clauses. [Clear win]

## Reinvented stdlib

- `path/to/util.ts:group` — manual loop building a `Record`; this is
  `Object.groupBy(items, x => x.key)`. [Judgment call — supported on
  the project's target runtime?]

## Redundant / derived state

- ...

## Over-parameterization

- `path/to/svc.ts:fetch(opts.retry)` — `retry` is `3` at every one of
  4 call sites; drop the parameter, hardcode the default. [Judgment
  call]

## Verbose language patterns

- ...

## Pattern observations

If a single category produced many findings, list count + top 3.
```

End with a summary:

- Approximate LOC reduced if all **Clear win** findings were applied.
- The top 3 highest-payoff findings (largest reduction or biggest
  clarity gain) and why.

## Constraints

- Do not change any code. Surface findings; let the user pick which
  to action and run a focused pass.
- Stay in your lane. Unused or unreachable code is a
  `dead-code-audit` finding; the same job duplicated across files is a
  `duplicate-logic-audit` finding. If you notice one, cross-reference
  it in a one-line note — don't re-report it as complexity.
- Never propose a change that alters behaviour or edge-case handling.
  "Smaller but subtly different" is a bug, not a simplification.
- No pure formatting or lint-territory findings (spacing, quote style,
  `prefer-const`). Those belong to the linter; this audit is for
  semantic reductions the linter can't reason about.
- Respect the project's documented style. If the instruction files
  rule out a feature or pattern, don't propose it — note it as
  "considered but out of policy" at most.
- Simplification is taste-laden. Default conservative: when unsure
  whether a reduction is worth it, file it as **Judgment call**, not
  **Clear win**, and rank by confidence × payoff.
