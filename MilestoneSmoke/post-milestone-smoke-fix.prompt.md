---
description: Action ❌ Fail findings from the most recent post-milestone smoke-test report. Commits locally; does not push or open a PR.
related: [post-milestone-smoke-test-api, post-milestone-smoke-test-cli, post-milestone-smoke-test-ios, post-milestone-smoke-test-web]
---

# Post-milestone smoke fix

Action the in-scope ❌ Fail entries from the most recent
smoke-test report. Commit locally; do not push or open a PR.

This is the behavioural counterpart to
`MilestoneAudit/post-milestone-fix.prompt.md` — that one fixes
static drift from the audit, this one fixes runtime regressions
from the smoke test.

---

## Inputs

The user supplies:

- **Flows in scope** — typically `all-fails`. Alternatives:
  specific flow numbers (e.g. `1, 3, 5`), or `all` to also include
  flows the user has separately reclassified.
- **Cross-cutting failures in scope** — yes / no. Default yes
  unless the user says otherwise.

If the user hasn't specified, ask before doing anything else.
Don't guess scope.

---

## Step 1 — Locate the smoke report

Read the most recent smoke-test report. Files are named
`docs/smoke-tests/<tag>-<timestamp>.md` (e.g.
`docs/smoke-tests/v1.6.0-20260519T143022.md`); pick the latest by
sorting lexicographically — both `<tag>` and the `YYYYMMDDTHHMMSS`
suffix sort correctly
(`ls -1 docs/smoke-tests/*.md 2>/dev/null | sort | tail -1`). If
the user named a specific tag, restrict to that tag first
(`ls -1 docs/smoke-tests/<tag>-*.md | sort | tail -1`). If the
directory or any report doesn't exist, surface that and stop —
there's nothing to action.

While you're there, note the **Variant** field (`web` / `api` /
`cli` / `ios`) — Step 5 needs it for the re-run recommendation.

---

## Step 2 — Filter to scope

Action only:

- Smoke flows with `Outcome: ❌ Fail` matching the user's flow
  filter.
- Cross-cutting observations marked ❌, if cross-cutting is in
  scope.

Skip everything else. In particular:

- **Skip ⏸ Blocked entries.** Blocked means the flow couldn't
  run because of a setup gap (missing data, server 503, tool
  error). That's environment work, not a code fix. Note them in
  the final report.
- **Skip ✅ Pass entries.** Obvious, but: don't go hunting for
  "while we're in here" tweaks. Scope creep is the failure mode
  this prompt is defending against.

---

## Step 3 — Cluster failures by suspected root cause

Before diving into fixes, group the in-scope failures by likely
shared root cause. A single regression often surfaces in multiple
flows (e.g. broken auth shows up in every flow that signs in). One
fix per root cause beats one fix per failure entry.

Use the smoke report's **Steps run**, **Observations**, and
**Artefact** (screenshot / response log / command transcript
under `docs/smoke-tests/<tag>-<timestamp>/`) to judge whether two failures
share a cause.

Output the cluster list before doing any code editing — even
just inline in your reply — so the user can see the grouping.

---

## Step 4 — Diagnose and fix each cluster

For each cluster, in priority order (highest-impact first —
flows that block other flows, then headline-feature flows, then
edge cases):

1. **Read the failure context** — flow steps run, observations,
   artefact, draft fix-now issue title from the smoke report.
2. **Locate the suspect code** — use the issue refs (`#N`) to
   find the originating commits, and trace from the user-facing
   entry point (page / endpoint / command / screen) inward.
3. **Confirm the diagnosis.** Three honest outcomes:
   - **Real code regression** — proceed to fix.
   - **Smoke-test artefact issue** — the smoke step itself
     drifted (stale selector, wrong fixture, outdated
     credential). Skip with a note. Editing the smoke prompts
     is out of scope for this playbook.
   - **Environmental flake** — intermittent network, race in
     the test harness, dependency on external state. Skip with
     a note; recommend re-running the smoke flow before
     declaring it a regression.
4. **Make the change.** Targeted fix, no surrounding cleanup.
5. **Verify with the project's mechanical checks** — type-check,
   lint, the relevant unit / integration tests (e.g.
   `pnpm check-types && pnpm lint`, `npm run test`,
   `pytest -q`, `dotnet test`, `swift test`). Infer commands
   from the project manifest.

   **Be honest about what this proves.** Mechanical checks
   confirm the code compiles and existing tests still pass.
   They do *not* confirm the broken flow now works end-to-end
   — only re-running the smoke variant does that. Step 5 makes
   this explicit in the report.

6. **Stage and commit** with a conventional commit message that
   references the flow title and the file path. One commit per
   cluster (= per root cause), not per failure entry.

If a cluster needs more than mechanical work — architectural
change, ambiguous root cause, multi-day investigation — surface
it and skip with a note. Do not silently ignore. Do not
half-implement.

---

## Step 5 — Run the full check suite

When all in-scope clusters are committed, run the project's full
check suite. The standard sequence is:

- Type-check
- Lint
- Test
- Build (scoped to the primary app if the project is a monorepo)

Infer commands from the project manifest and any documented
scripts.

---

## Step 6 — Report

Output a short summary:

- **Clusters fixed** — for each: cluster description, flows it
  resolved (`#1, #4`), file paths touched, commit hash.
- **Clusters skipped within scope** — with reason (smoke-test
  artefact issue / environmental flake / requires deeper
  investigation / no longer reproduces).
- **Blocked entries noted** — list of ⏸ Blocked flows from the
  report so the human knows the setup-gap backlog still exists.
- **Mechanical check result** — type-check / lint / test /
  build, pass / fail per command.
- **Required next step — re-run the smoke variant.** State
  explicitly: "Mechanical checks passed but cannot prove the
  failed flows now succeed. Re-run
  `post-milestone-smoke-test-<variant>` against the same tag to
  verify." Use the variant from Step 1.
- **Suggested PR title and body summary** — draft for a human
  to paste, not to open.

---

## Constraints

- Do not push to the remote.
- Do not open a PR.
- Do not modify the smoke report itself — it's a snapshot of
  what was observed at smoke-test time. If a fix invalidates a
  finding, that shows up in the next smoke run, not by editing
  history.
- Do not modify the smoke-test prompts (`post-milestone-smoke-test.*`).
  If a failure is caused by the smoke step itself drifting,
  surface it and skip — fixing smoke prompts is a separate
  concern.
- Do not action ⏸ Blocked entries. Setup gaps need environment
  work, not code edits.
- Do not action failures outside the user-supplied scope, even
  if they look quick. Mechanical checks here cannot verify
  end-to-end behaviour; widening scope widens what you can't
  actually verify.
- Stop after committing locally so the changes can be reviewed
  and the smoke re-run before pushing.
