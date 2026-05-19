---
description: Action the in-scope findings from the most recent dead-code-audit report. Deletes dead code, verifies the build, commits locally per category. Does not push or open a PR.
related: [dead-code-audit]
---

# Dead code fix

Action the in-scope findings from the most recent `dead-code-audit`
report. Delete the dead code, verify the build still passes, commit
locally per category. Do not push or open a PR.

---

## Inputs

The user supplies:

- **Categories in scope** — any combination of `hard`, `likely`,
  `conditionally`. Default is `hard` only — the audit's "Hard dead"
  bucket is where the LLM was confident enough that mechanical
  deletion is safe. Action `likely` only when the user explicitly
  opts in; treat `conditionally` as opt-in plus a confirmation that
  the dependent deprecated path is also being removed.
- **Specific findings to skip** — optional. The user may have
  triaged the report manually and flagged some entries as
  load-bearing despite the audit's recommendation.

If the user hasn't specified, ask before doing anything else. Don't
guess scope. The audit is opinionated; the fix should be conservative.

---

## Step 1 — Locate the audit

The audit writes to `<root>/audits/dead-code-<timestamp>.md`.
Resolve `<root>` in this order: `.playbook-audits/` if it exists,
else `docs/` if `docs/audits/` exists (legacy convention). Look
for files matching `<root>/audits/dead-code-*.md` and pick the
most recent
(`ls -1 <root>/audits/dead-code-*.md 2>/dev/null | sort | tail -1`
— the `YYYYMMDDTHHMMSS` suffix sorts lexicographically). If
neither root exists or no report is found, ask the user whether
they have an inline report to paste, or whether they need to run
the audit.

If the user named a specific report file, use that one instead of the
most recent.

If neither a file nor an inline report is available, stop and
recommend running `/playbook dead-code-audit` first.

---

## Step 2 — Filter to scope

For each finding in the report, action it only if **all** of:

- It's under a section matching the in-scope categories (`Hard dead`,
  `Likely dead`, `Conditionally dead`).
- It's not in the user-supplied skip list.
- A pre-deletion grep still confirms zero callers. Re-verify — the
  audit may have been written days ago and the codebase may have
  moved.

Skip anything under `Test-only production code` and `Pattern
observations` — those are diagnostic, not deletion candidates.

---

## Step 3 — Action findings, category by category

Findings are grouped by **category** (exports, components, env vars,
branches, deprecated paths). Each category produces **one commit**.
Verification runs per finding so a broken deletion doesn't poison the
rest of the category.

For each category:

1. For each finding in this category:
   a. Make the deletion. Remove the symbol and any now-orphaned
      imports it pulled in. Don't leave commented-out code or
      "removed because…" trail comments — the commit message
      carries the why.
   b. Run the project's type-check and lint commands (e.g.
      `pnpm check-types && pnpm lint`, `npm run typecheck`,
      `mypy . && ruff check`, `cargo check && cargo clippy`).
      Infer the exact commands from the project manifest.
   c. Run the test suite. A passing build with failing tests is
      not acceptable — dead code that the type checker accepted
      may still have been runtime-exercised by tests.
   d. If any check fails: revert this finding's edits in the
      working tree (do not stage them), record under "Skipped —
      broke checks" with the failing command and a one-line guess
      at why. Move on to the next finding.
   e. If checks pass: `git add` the changes. **Do not commit yet.**
2. When every finding in the category has been processed (actioned
   or skipped), commit the staged changes as one category-level
   commit. Conventional commit message referencing what was removed
   ("remove deprecated session helpers", "drop unused exports from
   `lib/legacy/`").
3. If every finding in the category was skipped, there's nothing
   staged — move to the next category without committing.

If five unused exports across five files all fell out of the same
dead deprecated path, they go in one commit. If two unused exports
come from unrelated features, they belong in different categories
and thus different commits.

---

## Step 4 — Env vars and config

Env-var findings (variables in `.env.example` / config schemas never
read) need separate handling — there's no compile-time check that
proves they're dead:

- Grep the variable name across the **whole** repo, including
  deployment configs (`docker-compose*.yml`, `terraform/`, `k8s/`,
  CI workflow files). A var read by deploy infrastructure but not
  application code is not dead.
- If the var is referenced anywhere outside source code, skip it and
  record under "Skipped — referenced outside application code".

Only delete env vars when grep across the whole tree comes back
empty.

---

## Step 5 — Run the full check suite

When all in-scope findings are actioned, run the project's full check
suite from a clean state:

- Type-check
- Lint
- Test
- Build (scoped to the primary app if the project is a monorepo)

A passing check suite is the gate for declaring the fix pass complete.

---

## Step 6 — Report

Output a short summary:

- **Findings actioned** — count per category, with file paths.
- **Findings skipped within scope** — with reason per finding
  ("broke checks: `mypy` reported …", "referenced outside application
  code", "user opted to keep").
- **Approximate LOC removed** — sum across commits.
- **Final check result** — pass / fail with the failing command.
- **Suggested PR title and body summary** — draft for a human to
  paste, not to open.

---

## Constraints

- Do not push to the remote.
- Do not open a PR.
- Do not action `Likely dead` or `Conditionally dead` unless the user
  explicitly opted in. They exist as separate buckets in the audit
  precisely because they need human judgment.
- Do not "improve" code adjacent to the deletion (rename remaining
  symbols, tidy formatting, restructure imports beyond what the
  deletion forced). Scope creep here turns a low-risk fix pass into
  a review burden.
- Do not delete re-export barrels, even if no internal caller imports
  them — they define a public API surface.
- Do not delete stub functions that raise `NotImplemented` /
  `unimplemented!()` / `todo!()` — they're intentional placeholders.
- If a deletion requires changing a public API (exported from the
  package, referenced in a published `.d.ts`, surfaced in OpenAPI),
  stop and flag for human review rather than completing the change.
