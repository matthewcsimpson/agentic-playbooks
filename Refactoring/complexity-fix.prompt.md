---
description: Action user-selected findings from the most recent complexity-audit report. Apply the reduction in place, verify the build, commit per category. Local commits only.
related: [complexity-audit]
---

# Complexity fix

Action the user-selected findings from the most recent
`complexity-audit` report. Apply each reduction in place, verify the
build still passes, commit locally per category. Do not push or open a
PR.

Simplification edits live, passing code — every change rewrites
something that compiles and passes tests today, with no dead-code
safety net of "nothing referenced it anyway." The bias of this prompt
is **per-finding, with verification between each**, defaulting to the
findings the audit was most confident about. Bulk-applying every
finding the audit listed is not the goal.

---

## How to ask

When a step needs the user to choose or answer — picking findings to
action, resolving an ambiguity, confirming a decision — present it as
a structured selection: the `AskUserQuestion` tool in Claude Code
(multi-select when more than one item can be chosen), or an
equivalent numbered list in a harness without that tool. Never ask as
a free-form prose question. Put the recommended option first, marked
"(Recommended)".

---

## Inputs

The user supplies:

- **Findings in scope** — by finding number, by file glob, or by
  band (`band:clear` actions only findings the audit labelled Clear
  win). Default is `band:clear`. Never bulk-action Judgment call or
  Risky findings without explicit user opt-in per finding.
- **Specific findings to skip** — optional. The user may have triaged
  the report and decided some reductions aren't worth it, or that the
  extra structure earns its keep.

If the user hasn't specified, list the findings from the report
(numbered, with band) and ask which to action. Don't guess scope.
Don't action anything before the user has answered.

---

## Step 1 — Locate the audit

The audit writes to `<root>/audits/complexity-<timestamp>.md`.
Resolve `<root>` in this order: `.playbook-audits/` if it exists,
else `docs/` if `docs/audits/` exists (legacy convention). Look
for files matching `<root>/audits/complexity-*.md` and pick the
most recent
(`ls -1 <root>/audits/complexity-*.md 2>/dev/null | sort | tail -1`
— the `YYYYMMDDTHHMMSS` suffix sorts lexicographically). If
neither root exists or no report is found, ask the user whether
they have an inline report to paste, or whether they need to run
the audit.

If the user named a specific report file, use that one instead of the
most recent.

If neither a file nor an inline report is available, stop and
recommend running `/playbook complexity-audit` first.

---

## Step 2 — Per finding: verify the audit is still valid

For each in-scope finding, before changing any code:

- Confirm the code still exists at the path / symbol the audit
  recorded, and still looks the way the audit described. Code moves
  and changes; the audit may be stale. If it has diverged, record
  under "Skipped — audit stale" and move on.
- Re-confirm the reduction is genuinely behaviour-preserving *now*.
  The audit's "same behaviour, less code" claim is the load-bearing
  assumption. If re-reading reveals an edge case the reduction would
  drop (a null path, an ordering guarantee, a side effect), abort
  this finding and record under "Skipped — would change behaviour".

---

## Step 3 — Action findings, category by category

Findings are grouped by the audit's **category** (needless
indirection, collapsible control flow, reinvented stdlib, redundant
state, over-parameterization, verbose patterns). Each category
produces **one commit**. Verification runs per finding so a broken
reduction doesn't poison the rest of the category.

For each category, for each finding in it (one at a time):

1. **Apply the single reduction** the audit named — and only that.
   Inline the wrapper, flatten the branch, swap in the stdlib call,
   derive the state, drop the parameter. Don't leave commented-out
   code or "simplified from…" trail comments — the commit message
   carries the why.
2. **Run the type-check and lint commands** (e.g.
   `pnpm check-types && pnpm lint`, `npm run typecheck`,
   `mypy . && ruff check`, `cargo check && cargo clippy`). Infer the
   exact commands from the project manifest.
3. **Run the test suite.** A passing type-check with failing tests
   means the reduction changed observable behaviour — that's the
   failure mode this verification exists to catch.
4. **If any check fails:** revert this finding's edits in the working
   tree (do not stage them), record under "Skipped — broke checks"
   with the failing command and a one-line guess at why. Move on to
   the next finding.
5. **If checks pass:** `git add` the changes. **Do not commit yet.**

When every finding in the category has been processed, commit the
staged changes as one category-level commit. Conventional message
naming what was reduced ("flatten nested guards in the auth handlers",
"replace hand-rolled grouping with `Object.groupBy`"). If every
finding in the category was skipped, there's nothing staged — move to
the next category without committing.

---

## Step 4 — Special cases

- **Public API in a finding.** If the reduction would change a symbol
  exported from the package (referenced in a published `.d.ts`,
  surfaced in the `exports` map, imported by code outside this repo) —
  e.g. dropping a parameter from an exported function — stop the
  finding and flag for human review. That's a breaking change, not a
  refactor.
- **Hot paths.** If a verbose form sits in a measured hot path and may
  be deliberate for performance, don't assume the cleaner form is
  free. Skip and flag unless the user confirmed it.
- **Generated or vendored code.** Code in `generated/`, `vendor/`,
  `node_modules/`, build output, or files marked `@generated` must not
  be edited. Skip and flag.

---

## Step 5 — Run the full check suite

When all in-scope findings are actioned, run the project's full check
suite from a clean state:

- Type-check
- Lint
- Test
- Build (scoped to the primary app if the project is a monorepo)

If the per-finding checks all passed, this should pass too — but run
it as the gate before declaring the pass complete. Catches issues that
only show at link / build time.

---

## Step 6 — Report

Output a short summary:

- **Findings actioned** — count per category, with file paths.
- **Findings skipped within scope** — with reason per finding
  ("broke checks: `pnpm test` failed on `<test name>`", "audit stale:
  `path/to/file.ts` no longer matches", "would change behaviour:
  drops a null guard", "public API — flagged for human review").
- **Approximate LOC delta** — sum across commits (net reduction).
- **Final check result** — pass / fail with the failing command.
- **Suggested PR title and body summary** — draft for a human to
  paste, not to open.

---

## Constraints

- Do not push to the remote.
- Do not open a PR.
- Do not action Judgment call or Risky findings unless the user
  explicitly opted in. They exist as separate bands in the audit
  precisely because they need human judgment.
- Do not action more than one finding between verifications. Bundled
  reductions make it impossible to attribute a test failure to a
  specific change.
- A reduction that isn't strictly behaviour-preserving is out of
  scope. If applying it cleanly requires changing what the code does,
  skip and record — that's a feature change, reviewed on its own.
- Do not "improve" code adjacent to the finding (rename unrelated
  symbols, tidy formatting, restructure imports beyond what the
  reduction forced). Scope creep here amplifies review burden — the
  whole point of this pass is small, individually-obvious diffs.
