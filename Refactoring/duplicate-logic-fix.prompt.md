---
description: Action user-selected clusters from the most recent duplicate-logic-audit report. Migrate callers to the recommended winner, delete losers, verify, commit per cluster. Local commits only.
related: [duplicate-logic-audit]
---

# Duplicate code fix

Action the user-selected clusters from the most recent
`duplicate-logic-audit` report. Migrate callers to the recommended winner,
delete the losers, verify the build still passes, commit locally per
cluster. Do not push or open a PR.

Refactoring is riskier than dead-code removal — every consolidation
changes call sites that compile and pass tests today. The bias of
this prompt is **per-cluster, with verification between each**.
Bulk-applying every cluster the audit recommended is not the goal.

---

## Inputs

The user supplies:

- **Clusters in scope** — by cluster number, by file glob, or by
  risk band (`risk:low` actions only clusters the audit labelled
  Risk = low or omitted). Default is `risk:low`. Never bulk-action
  Risk = medium / high without explicit user opt-in per cluster.
- **Override the recommended winner per cluster** — optional. The
  audit's recommendation is a default, not a decision; if the user
  named a different winner for a cluster, follow that.

If the user hasn't specified, list the clusters from the report
(numbered, with risk band) and ask which to action. Don't guess
scope. Don't action anything before the user has answered.

---

## Step 1 — Locate the audit

The audit writes to `<root>/duplicate-logic-<timestamp>.md`.
Resolve `<root>` in this order: `.playbook-audits/` if it exists,
else `docs/audits/` if that exists (legacy convention). Look for
files matching `<root>/duplicate-logic-*.md` and pick the most
recent (`ls -1 <root>/duplicate-logic-*.md 2>/dev/null | sort | tail -1`
— the `YYYYMMDDTHHMMSS` suffix sorts lexicographically). If
neither root exists or no report is found, ask the user whether
they have an inline report to paste, or whether they need to run
the audit.

If the user named a specific report file, use that one instead of the
most recent.

If neither a file nor an inline report is available, stop and
recommend running `/playbook duplicate-logic-audit` first.

---

## Step 2 — Per cluster: verify the audit is still valid

For each in-scope cluster, before changing any code:

- Confirm each member listed in the cluster still exists at the
  path / symbol the audit recorded. Code moves; the audit may be
  stale.
- Re-read the bodies. The audit's "behaviourally identical" claim
  is the load-bearing assumption — if a member has diverged since
  the audit, abort this cluster and record under "Skipped — audit
  stale".
- List the callers of each loser (grep across the repo). If a loser
  has zero callers, treat that as a dead-code finding, not a
  consolidation — delete it directly without migration work.

---

## Step 3 — Per cluster: migrate callers, then delete

For each cluster (one at a time, in the order the user requested):

1. **Confirm the winner.** Use the user's override if given,
   otherwise the audit's recommendation.
2. **For each loser**: update its call sites to call the winner
   instead. Match the winner's signature — if parameter names or
   return shape differ, transform at the call site. Don't change
   the winner's signature mid-migration; that turns one cluster
   into N.
3. **Delete the loser** (and any private helpers only it used).
4. **Run the type-check, lint, and test suite**. Infer commands
   from the project manifest. A passing type-check with failing
   tests means the migration changed observable behaviour
   somewhere — that's the failure mode this verification exists
   to catch.
5. **If any check fails:** revert this cluster's changes in the
   working tree (do not commit), record under "Skipped — broke
   checks" with the failing command and a one-line guess at why.
   Move on to the next cluster.
6. **If checks pass:** stage and commit. One commit per cluster.
   Conventional message naming the winner and the migrated callers
   ("consolidate `formatDate` helpers — drop `dateFormatter`,
   `prettyDate`; migrate 4 callers").

---

## Step 4 — Special cases

- **Public API in a cluster.** If any member of a cluster is
  exported from the package (referenced in a published `.d.ts`,
  surfaced in the package's `exports` map, or imported by code
  outside this repo), stop the cluster and flag for human review.
  Deleting a public export is a breaking change, not a refactor.
- **Generated or vendored members.** Code in `generated/`,
  `vendor/`, `node_modules/`, build output, or files marked with
  `@generated` headers must not be edited as part of this pass. If
  the cluster's winner needs the generator to change, skip and flag.
- **Test fixtures.** Two test fixtures that look similar are often
  similar by design (testing different shapes of the same input).
  If a cluster is composed entirely of test-only code, default to
  skipping unless the user explicitly asked for it.

---

## Step 5 — Run the full check suite

When all in-scope clusters are actioned, run the project's full
check suite from a clean state:

- Type-check
- Lint
- Test
- Build (scoped to the primary app if the project is a monorepo)

If the per-cluster checks all passed, this should pass too — but
run it as the gate before declaring the pass complete. Catches
issues that only show at link / build time.

---

## Step 6 — Report

Output a short summary:

- **Clusters actioned** — list with winner + count of callers
  migrated + LOC delta.
- **Clusters skipped within scope** — with reason per cluster
  ("broke checks: `pnpm test` failed on `<test name>`", "audit
  stale: `path/to/file.ts:foo` no longer matches the audit's
  claim", "public API — flagged for human review").
- **Approximate LOC removed** — sum across commits.
- **Final check result** — pass / fail with the failing command.
- **Suggested PR title and body summary** — draft for a human to
  paste, not to open.

---

## Constraints

- Do not push to the remote.
- Do not open a PR.
- Do not action Risk = medium / high clusters unless the user
  explicitly opted in. They exist as a separate risk band in the
  audit precisely because they need human judgment.
- Do not action more than one cluster between verifications.
  Bundled migrations make it impossible to attribute a test
  failure to a specific cluster.
- Do not change the winner's signature during the migration. If
  the winner needs to evolve to absorb the losers' behaviour, that
  is a separate change to be reviewed on its own.
- Do not "improve" code adjacent to the migration (rename
  unrelated symbols, tidy formatting beyond what the migration
  forced, restructure imports). Scope creep here amplifies review
  burden.
- If a migration leaves the codebase with a new duplicate (because
  the audit clustered three items but you only consolidated two of
  them per user scope), record that in the report — don't silently
  leave a partial result.
