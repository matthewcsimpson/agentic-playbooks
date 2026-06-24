# Refactoring

Read-only audits that surface refactor opportunities, paired with
opt-in fix prompts that action the in-scope findings.

| Audit | What it finds | Action prompt |
|---|---|---|
| `dead-code-audit.prompt.md` | Exports never imported, components never rendered, env vars never read, branches the type system can't reach, code hiding behind permanently-on / off feature flags. Classified Hard / Likely / Conditionally dead. | `dead-code-fix.prompt.md` |
| `duplicate-logic-audit.prompt.md` | Functions / modules / components doing the same job under different names. Clusters them, recommends a winner per cluster, and notes the migration risk. | `duplicate-logic-fix.prompt.md` |
| `complexity-audit.prompt.md` | Code that's used and singular but more complex than it needs to be — needless indirection, collapsible control flow, reinvented stdlib, redundant derived state, over-parameterization. Classified Clear win / Judgment call / Risky. | `complexity-fix.prompt.md` |

The three audits partition cleanly — each finds a different problem
and proposes a different action:

| Audit | Target | Action |
|---|---|---|
| `dead-code-audit` | code that isn't *used* | delete it |
| `duplicate-logic-audit` | the same job done in two *places* | merge to one winner |
| `complexity-audit` | code that *is* used and singular but over-built | reduce it in place |

Each audit stays in its lane and cross-references the others rather
than double-reporting a finding.

The fix prompts deliberately default to a **narrow** scope:

- `dead-code-fix` defaults to `Hard dead` only. Action `Likely` /
  `Conditionally dead` only when the user explicitly opts in.
- `duplicate-logic-fix` defaults to `risk:low` clusters and asks the
  user which to action. It verifies the build between each cluster
  rather than bulk-applying all of them.
- `complexity-fix` defaults to `band:clear` (Clear win) findings and
  asks the user which to action. It verifies the build between each
  finding rather than bulk-applying all of them.

All three fix prompts commit locally only — they don't push or open a
PR. The intended flow is: run the audit, read the report, decide which
findings are worth acting on, invoke the fix prompt with that scope.

## Running all three

When you want to do a full refactoring sweep, run them in this order:

1. **`dead-code`** — delete what isn't used.
2. **`duplicate-logic`** — merge each cluster to one winner.
3. **`complexity`** — reduce what's left.

Each pass shrinks the input to the next, so you never spend effort on
code a later step would remove anyway: no point clustering or
simplifying a function that's about to be deleted, and no point
simplifying two copies of something that's about to be merged into
one. The order also runs lowest-risk (delete unreferenced code) to
highest (taste-laden simplification). It's self-reinforcing, too —
`complexity-audit` defers unused-code and cross-file-duplication
findings to the other two, so running it last means it operates on a
surface those passes have already settled.

**Action each cycle before auditing the next** — i.e.
`dead-code-audit` → `dead-code-fix` → `duplicate-logic-audit` → … —
rather than running all three audits up front and then fixing. The
audits are read-only snapshots; if you batch them, the later reports
will reference code an earlier fix has since deleted or moved. (The
fix prompts re-verify every finding against the current tree before
editing, so a moderately stale report degrades gracefully — it skips
findings that no longer match rather than doing the wrong thing — but
a fresh audit per cycle gives the cleanest result.)

## LLM value-add over static tools

These prompts pair well with the project's existing static tools
(`knip`, `ts-prune`, `vulture`, `unused`, etc.) rather than
replacing them. The LLM adds:

- **Semantic similarity** that text-based dedup tools miss.
- **Dead branches** the type system can prove unreachable but the
  static tool flagged "in use."
- **Deprecated-path-only callers** — code that's "used" but only
  by code that's itself dead.

## Invocation

See the [root README](../README.md#invocation) for the three
supported patterns and the assumed tool capabilities. Both prompts
need file read and shell execution; git is optional.
