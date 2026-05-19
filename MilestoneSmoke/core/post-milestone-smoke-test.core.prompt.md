# Post-milestone smoke test — core

Shared scaffold for the post-milestone smoke test. Not invoked
directly — the platform variants (`.web`, `.api`, `.cli`, etc.)
reference this file for the workflow shape and reuse the generic
sections.

A variant supplies:

- **Scope** — what medium the variant targets and what it doesn't.
- **Prerequisites** — runtime / tools / fixtures the variant needs.
- **Test data / accounts** — how the variant gets credentials,
  fixtures, or seed data.
- **Step 3 step-shape note** — what counts as a "step" in this
  medium (browser action vs HTTP request vs shell invocation).
- **Step 4 mechanics** — how flows execute and what to capture
  while they run.
- **Step 5 cross-cutting checks** — the universal hygiene checks
  for this medium.
- **Per-flow artefact convention** — what to save (screenshot,
  response log, command transcript) and where.

Everything else below is shared.

Do not modify any code. The smoke run is observation and execution
— fixes belong in a separate follow-up.

---

## Context

This smoke test runs immediately after a milestone tag is cut,
before the post-milestone audit. The audit catches static drift;
it does not run the code. This step does — by exercising the
milestone's headline behaviour against a running instance, so
regressions surface before they propagate into the next milestone.

The deliverable is a single markdown report written to
`docs/smoke-tests/<latest-tag>-<timestamp>.md` (see Step 6). Each
run produces a new file so re-running for the same tag accumulates
an ordered history instead of overwriting. The `docs/` folder
should be gitignored (or whichever working-artefact directory the
project uses) — the report is a working artefact, not a tracked
file.

---

## Step 1 — Establish the milestone window

Run these and use the output to scope the run:

- `git describe --tags --abbrev=0` — the latest tag (the milestone
  being tested).
- `git tag --sort=-creatordate | sed -n '2p'` — the previous tag,
  as the baseline.
- Identify the milestone / sprint / ticket batch matching the
  latest tag. The default mechanism is GitHub milestones:
  - `gh api repos/:owner/:repo/milestones --jq '.[] | select(.title | startswith("v<latest-tag-base>"))'`
  - `gh issue list --state closed --milestone "<milestone title>" --limit 100 --json number,title,labels,closedAt`
  If the project uses Linear, Jira, or another tracker, swap in
  the equivalent: pull the list of completed tickets associated
  with the milestone tag.

If the milestone can't be inferred from the tag, surface that and
ask before proceeding.

---

## Step 2 — Bucket closed issues by feature surface

Read each closed issue's body and bucket it into one of:

- **User-facing feature** — surfaces the variant's medium exposes
  to users (the variant defines what counts — page / modal / button
  for web, endpoint / parameter for API, command / flag for CLI).
  These become smoke flows.
- **Behind-the-scenes** — schema migrations, refactors, build / CI
  changes, internal utilities, dependency upgrades, copy edits.
  These do not need their own flows; they will be exercised
  transitively.
- **Process / docs** — issue housekeeping, README / wiki updates,
  milestone-gate audits. Skip entirely.

Skipped items go in an "Excluded from smoke test" section of the
report so a reviewer can sanity-check the bucketing.

---

## Step 3 — Plan each smoke flow

For each user-facing feature, write a numbered flow plan with:

- **Title** — short imperative.
- **Issue refs** — `#N` links to the closed issues this flow
  exercises.
- **Setup** — accounts, fixtures, prior state, starting point.
- **Steps** — concrete, executable actions. The variant defines
  what counts (browser actions, HTTP requests, shell invocations,
  etc.). Each step must be executable without follow-up
  interpretation. Avoid narrative ("then the user signs in") —
  every step is an action the tool will perform.
- **Pass criteria** — observable conditions that indicate success.
  Be specific.
- **Probe** — 0–2 short bullets identifying a regression worth
  specifically checking during the flow. Each probe is a sub-flow
  that gets its own pass / fail.

Order flows from highest-value (closest to the milestone's
headline) to lowest. Authentication / setup flows go first;
obscure edge cases go last. Cap the list at ~10 flows; combine
related sub-flows into a single multi-step entry rather than
splitting.

---

## Step 4 — Execute each flow

For each planned flow, in order:

1. **Reset state** for the run. The variant specifies what reset
   means in its medium (clear cookies, recreate fixtures, reset
   working directory, etc.).
2. **Walk the steps** using the variant's execution mechanism.
   After each step, confirm the expected state before the next.
   If a step fails (target missing, expected output absent,
   unexpected error), record where it failed and **stop the flow**
   — do not work around. Move on to the next flow.
3. **Observe during execution**. The variant specifies what to
   capture (console / network for web, request and response body
   for API, exit code / stdout / stderr for CLI, etc.).
4. **Evaluate pass criteria** at flow end: pass / fail / blocked.
   - **Pass** — every step ran, every pass criterion held, no new
     findings in observations.
   - **Fail** — a pass criterion didn't hold, or a step couldn't
     complete because of a behavioural defect.
   - **Blocked** — a step couldn't complete because of a setup gap
     (data missing, server returned 503, tool error). Distinct
     from fail; not a regression in the milestone.
5. **Capture an artefact** at the moment of decision (success
   state for pass, last-good-state for fail / blocked) and link
   it from the report. The variant specifies the artefact type
   and storage path.

For each probe (Step 3 sub-bullet), run it as its own mini-flow
against the same setup. Probes get their own pass / fail row in
the report.

---

## Step 5 — Cross-cutting observations

After the per-feature flows, do one targeted run for the
cross-cutting concerns the per-feature runs don't cover well on
their own. The variant specifies which checks apply.

Every observation is its own pass / fail row.

---

## Step 6 — Write the report

Write the report to `docs/smoke-tests/<latest-tag>-<timestamp>.md`,
where `<timestamp>` is current UTC time in basic ISO 8601 format
`YYYYMMDDTHHMMSS` — generate with `date -u +%Y%m%dT%H%M%S` (e.g.
`20260519T143022`). Always write a new file; do not overwrite prior
runs (even for the same tag) — the directory is an ordered history.
Use the same `<timestamp>` for variant-specific artefact paths
(`docs/smoke-tests/<tag>-<timestamp>/<flow>.log`, etc.) so each run
is self-contained. The shape is:

```
# Smoke Test — <tag>

Date: <today>
Variant: <web | api | cli | …>
Milestone: <milestone title>
Tag window: <previous-tag>..<latest-tag>
Closed issues in window: <count>

## Summary

<2-3 sentence verdict — overall health, biggest concern, biggest
win since last milestone>

| Result | Count |
|---|---|
| ✅ Pass | N |
| ❌ Fail | N |
| ⏸ Blocked | N |

## Smoke flows

### 1. <Title>

- Issue refs: #N, #M
- Setup: ...
- Steps run: <numbered list of what was actually executed>
- Outcome: ✅ Pass / ❌ Fail / ⏸ Blocked
- Observations: <variant-specific observation fields>
- Artefact: <variant-specific path>
- Probes:
  - <probe description> — ✅/❌

### 2. <Title>
...

## Cross-cutting observations

<variant-specific checks, each ✅/❌ with details>

## Excluded from smoke test

<List of closed issues bucketed as behind-the-scenes / process /
docs, with a one-line reason for each.>

## Recommended follow-ups

For every ❌ Fail and every cross-cutting failure, list the flow
title and a one-sentence repro so a human (or follow-up prompt)
can act on it.

- ❌ <flow title> — <one-sentence repro>
```

---

## Constraints

- Do not modify any code. The smoke test only observes and
  executes.
- Do not write findings to any file other than
  `docs/smoke-tests/<latest-tag>-<timestamp>.md` and any
  variant-specific artefact paths (which must also live under
  `docs/smoke-tests/`, scoped to the run's `<tag>-<timestamp>/`
  folder).
- If `docs/smoke-tests/` does not exist, create it.
- Each flow must reference at least one issue / ticket from the
  milestone — that's the trace from "we shipped this" to "we
  tested this."
- Steps must be specific, executable actions in the variant's
  medium. Narrative steps are not acceptable; rewrite them or
  surface that the flow can't be executed.
- A flow that can't be executed because of a setup gap is
  **blocked**, not failed. Do not mark it pass to keep the run
  clean.
- Do not modify code, file issues, or take any action on
  failures. The report is observation-only; follow-up actions
  belong in separate prompts.
