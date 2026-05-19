# Stack upgrade fix — core

Shared scaffold for the stack-upgrade-fix action. Not invoked
directly — the framework-specific variants
(`stack-upgrade-fix.nextjs.prompt.md`,
`stack-upgrade-fix.python.prompt.md`, etc.) reference this file for
the workflow shape and reuse the generic sections.

A variant supplies the framework-specific content for:

- Codemod commands (run + verify shape per codemod).
- Version-bump commands (which manifest, which command, peer-dep
  co-bumps).
- Mechanical-edit patterns the codemods don't cover but that have a
  documented one-to-one replacement.
- Verification commands (typecheck, lint, build, test).
- Hand-off target — which `post-milestone-audit-<framework>` to run
  for residual drift.

Everything else below is shared.

---

## Context

A framework / runtime / language major bump is the highest-risk
mechanical change in the library. Codemods cover 60–90% of an
upgrade; the long tail is judgment calls per call site. Bumping the
version pin before the call sites are ready breaks the build;
bumping after the codemods have run is the canonical safe order.

This prompt is conservative by default. It actions one category at
a time, verifies the build between, and commits per category so a
broken category can be reverted without losing the others.

It does **not** push and does **not** open a PR. The companion
audit (`stack-upgrade-audit-<framework>`) is the input; the
follow-up drift catcher (`post-milestone-audit-<framework>`) is
the output.

---

## Inputs

The user supplies:

- **Categories in scope** — any combination of:
  - `codemods` — run the codemods the audit identified, one at a
    time, verify between.
  - `mechanical-edits` — apply documented one-to-one breaking-change
    edits (renamed imports, deprecated config keys with one-line
    replacements) that aren't covered by a codemod.
  - `version-bump` — bump the version pin (and any required peer-
    dep co-bumps the audit identified).
  - `post-bump` — apply mechanical edits that only make sense *after*
    the version pin moves (e.g. new APIs that didn't exist on the
    old version).

  Default scope is `codemods` + `version-bump`. `mechanical-edits`
  and `post-bump` are opt-in because they touch source code in
  patterns that vary in quality and per-framework codemod coverage
  — the user picks them per upgrade.

- **Risk tolerance** — `risk:low` (default), `risk:med`, `risk:high`.
  - `risk:low` — codemods only; surface every mechanical-edit
    finding as a TODO. Best for upgrades where the codebase has
    significant manual-review surface area.
  - `risk:med` — codemods + mechanical edits with high audit
    confidence. Stop-and-ask on anything the audit marked as
    judgment-heavy.
  - `risk:high` — apply everything the audit recommended without
    stopping. Only choose when you've reviewed the audit and accept
    its judgment calls in advance.

- **Excluded paths** — optional, comma-separated list of file globs
  or directories to skip even within an in-scope category. Use for
  legacy modules mid-rewrite, vendored code, or directories the
  upgrade explicitly defers.

- **Included paths** — optional, mutually exclusive with excluded.
  Narrows action to just those paths within the in-scope categories.

If the user hasn't specified scope, ask before doing anything else.
Don't guess. The audit is the survey; the fix should be deliberate,
especially for major-version upgrades.

---

## Step 1 — Locate the audit

The audit writes to `docs/upgrades/<stack>-<from>-<to>.md`. Look for
the file first; if no report exists there, ask the user whether they
have an inline report to paste, or whether they need to run the
audit.

If multiple reports exist (different upgrade paths from different
runs), use the one matching the user's stated `<from>` and `<to>`.
If still ambiguous, ask before proceeding — running the wrong fix
against the wrong plan is much worse than asking.

If neither a file nor an inline report is available, stop and
recommend running `/playbook stack-upgrade-audit-<framework>` first.

---

## Step 1.5 — Apply the include / exclude filter

Before any action, build the final action list:

1. Start with every codemod, mechanical edit, and version-bump
   instruction in the audit's plan.
2. If `Included paths` is set, drop edits outside those paths.
3. If `Excluded paths` is set, drop edits inside those paths.
4. Drop categories the user didn't include in scope.
5. Surface the filtered list to the user before proceeding ("After
   filtering, X codemods + Y mechanical edits + 1 version bump
   remain in scope: ..."). If the filter removed everything, stop.

---

## Step 2 — Verify the audit is still valid

Audit reports for upgrades go stale fast — upstream can ship a new
patch the same day, the codebase can move between audit and fix.
Before acting:

- The variant supplies a re-check command for the current pinned
  version. If it has changed since the audit, stop and re-run the
  audit; the plan is no longer aligned.
- Confirm the codemod versions the audit cited are still current.
- Re-grep for one or two of the audit's "patterns to fix" findings
  to confirm the line numbers are still accurate.

If the audit is stale, do **not** patch around it — re-run
`stack-upgrade-audit-<framework>` and start over with the fresh
plan. Acting on a stale plan is how upgrades go sideways.

---

## Step 3 — Action `codemods`

Codemods are the safest mechanical step in an upgrade — they run
against the current state, transform code to be compatible with the
target, and have idempotent semantics on a clean tree.

For each codemod the audit recommended, in the audit's stated
order:

1. Confirm the project's working tree is clean (no unstaged
   changes). If not, stop — codemods on a dirty tree produce
   un-revertable diffs.
2. Run the codemod with the variant's command. The variant
   specifies dry-run vs apply syntax; this prompt always **applies**
   (the audit already did dry-run).
3. Run the variant's verification command set: typecheck, lint,
   build. Tests come later (Step 7); per-codemod verification is the
   build gate.
4. If verification fails: `git restore` the codemod's changes,
   record under "Skipped — codemod broke checks" with the failing
   command and a one-line guess. Continue to the next codemod
   (codemods are independent in well-designed toolchains; if they
   aren't in this one, the audit should have noted it).
5. If verification passes: stage the codemod's changes and commit
   with a per-codemod message:
   - `upgrade(<framework>): apply codemod <codemod-name>`
   - Include the upstream codemod source in the commit body so a
     reviewer can look it up.

After all codemods are processed, run the variant's full check suite
once before moving to mechanical edits.

---

## Step 4 — Action `mechanical-edits`

These are edits the audit flagged as having a documented one-to-one
replacement — a renamed import, a deprecated config key with a
known new name, a removed flag with a documented replacement. The
audit's plan should list each with a concrete from→to pair.

For each mechanical edit, grouped by category:

1. Read the audit's from→to specification for the category. If the
   specification is ambiguous (the audit said "rewrite this call"
   rather than "replace X with Y"), surface it as a TODO and skip.
   The fix prompt does **not** improvise rewrites — that's a
   judgment call.
2. Apply the edit across every site the audit flagged in this
   category. Do **not** sweep beyond the audit's findings — if the
   audit found 4 call sites and a 5th matches the pattern, ask
   before including it.
3. Run the variant's verification.
4. If checks fail: revert the category's edits, record under
   "Skipped — broke checks". Move on.
5. If checks pass: commit per category:
   - `upgrade(<framework>): rename <oldImport> to <newImport>`
   - `upgrade(<framework>): replace <deprecatedConfigKey> with <newKey>`

If the user opted in to `risk:low`, every `mechanical-edits`
finding stops and asks before applying. `risk:med` applies edits
the audit marked as high-confidence; `risk:high` applies all of
them.

---

## Step 5 — Action `version-bump`

The version pin moves after codemods and mechanical edits have
prepared the codebase. The variant supplies the per-ecosystem bump
command and any required peer-dep co-bumps from the audit.

1. Apply the bump using the variant's command. The variant updates
   both the manifest and the lockfile in one operation — do not
   hand-edit.
2. Apply required peer-dep co-bumps the audit identified (e.g. Next
   15 needs React 19; Expo SDK upgrades pin specific React Native
   versions). Each co-bump is a separate manifest edit; let the
   variant's command handle the lockfile re-resolution.
3. Run the variant's verification.
4. If verification fails after the bump: this is the high-stakes
   failure case. Do **not** silently revert and continue — surface
   the failure, list the categories already applied, and stop. The
   user decides whether to investigate, roll back, or push through
   with a TODO list.
5. If verification passes: stage and commit:
   - `upgrade(<framework>): bump <framework> from <old> to <new>`
   - Include any peer-dep co-bumps in the same commit (they're
     atomic; reverting needs to take all of them).

---

## Step 6 — Action `post-bump`

Edits that only make sense after the version pin moves — new APIs
that didn't exist on the old version, default-value adjustments
that require the new behaviour to be present.

Same shape as `mechanical-edits` (Step 4): one category at a time,
verify, commit per category. `risk:low` surfaces as TODO; `risk:med`
applies high-confidence; `risk:high` applies all.

---

## Step 7 — Full check suite

When all in-scope categories are actioned, run the project's full
check suite from a clean state:

- Typecheck.
- Lint.
- Build.
- Tests (unit + integration if both exist).
- The variant's framework-health command — `next build` walks the
  whole route tree; `dotnet build` walks every project; `pytest`
  exercises code paths static checks miss.

A passing full check suite is the gate.

If checks fail at this stage but passed per-category, the failure
is usually an interaction between categories (a codemod + a
manual edit + the bump combining in a way no single step caught).
Surface as a TODO for the user; do not attempt to debug or revert
selectively.

---

## Step 8 — Hand off to post-milestone-audit

The fix prompt doesn't catch everything a real upgrade introduces.
Things that escape:

- Runtime behaviour changes the codemods didn't touch (new default
  values, async/sync boundary shifts, cache invalidation timing).
- Removed-but-still-imported types that surface only at runtime.
- Documentation drift — README install commands, env vars,
  deployment notes the upgrade rendered stale.
- Convention drift — established patterns in the codebase that the
  upgrade subtly contradicts.

Recommend `/playbook post-milestone-audit-<framework>` as the
next step in the report. The audit catches what survived the fix
pass; `post-milestone-fix` actions whatever it surfaces.

---

## Step 9 — Report

Output a short summary:

- **Categories actioned** — codemods run, mechanical edits applied,
  version bump (with peer-dep co-bumps), post-bump edits.
- **Codemods applied** — list with the upstream codemod name and
  number of files each changed.
- **Mechanical edits applied** — grouped by category.
- **Version moved** — `<old>` → `<new>` (and peer-dep co-bumps).
- **TODOs surfaced** — codemods that broke checks, judgment-call
  edits the user opted to defer (`risk:low`), categories the audit
  flagged but the user excluded.
- **Skipped within scope** — with reason per item.
- **Final check result** — pass / fail with the failing command.
- **Recommended next step** — `post-milestone-audit-<framework>` to
  catch what the fix missed.
- **Suggested PR title and body** — draft for a human to paste, not
  to open.

---

## Constraints

- Do not push to the remote.
- Do not open a PR.
- Do not action categories outside the user's stated scope. The
  default (`codemods` + `version-bump`) is deliberately narrow.
- Do not bump the version pin before codemods and in-scope
  mechanical edits have run. The canonical safe order is
  prepare → bump → finalize.
- Do not run codemods on a dirty working tree. Stage / stash first
  or stop.
- Do not improvise rewrites for findings the audit flagged
  ambiguously. The fix prompt actions documented from→to pairs;
  judgment calls surface as TODOs.
- Do not sweep beyond the audit's findings. If the audit found 4
  call sites and a 5th matches the pattern, ask before including —
  the audit's site list is the authoritative scope.
- Do not silently revert a failed version-bump and continue.
  Failure after the bump is the high-stakes path; stop and surface.
- Do not action a stale audit. If the pinned version has changed
  since the audit was written, re-run the audit rather than
  patching.
- Do not "improve" code adjacent to a fix (reformat, reorder
  imports, rename variables). Scope creep turns an upgrade pass
  into a review burden.
- Do not edit CI / deploy config as part of the fix unless the
  audit flagged a specific change. Pipeline drift from an upgrade
  is a separate concern.
- If the upgrade affects deploy-time behaviour (build output,
  runtime requirements, environment variables), surface in the
  report but do **not** edit the deploy config — that change
  belongs in its own PR with infra review.
