# Post-milestone audit — core

Shared scaffold for the post-milestone audit. Not invoked directly —
the framework-specific variants
(`post-milestone-audit.nextjs.prompt.md`,
`post-milestone-audit.python.prompt.md`) reference this file for the
workflow shape and reuse the generic sections.

A variant supplies the framework-specific content for:

- Per-rule sweep examples (the *kinds* of conventions to look for).
- Milestone diff focus categories (what new code to scrutinise).
- Full-sweep regression categories (what drift to look for).
- Extraction signals (what "right altitude" looks like for this
  stack).
- Drift counter rules (the numeric table at the end).

Everything else below is shared.

---

## Context

This audit runs after every milestone. The goals are:

1. Catch issues introduced by the latest milestone before they
   compound.
2. Catch slow drift in the rest of the codebase that would otherwise
   go unnoticed.
3. Track convention compliance against the project's documented rules
   (typically `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`,
   or `.cursor/rules/**`) so the rules stay enforced.
4. Produce a delta against the previous audit so triaged-and-deferred
   findings don't keep resurfacing as if they were new.

The deliverable is a single markdown report written to
`<root>/<latest-tag>-<timestamp>.md` (see the Output format step
for how to resolve `<root>`). Each run produces a new file so
re-auditing the same tag accumulates an ordered history instead
of overwriting. The working folder is gitignored — the report is
for reference, not for the repo history.

Do not make any code changes — investigate and report only.

---

## Step 1 — Establish the audit window

Run these and use the output to scope the audit:

- `git describe --tags --abbrev=0` — the latest tag (this is the
  milestone being audited).
- `git describe --tags --abbrev=0 HEAD~1 2>/dev/null` or
  `git tag --sort=-creatordate | sed -n '2p'` — the previous tag, as
  the baseline.
- `git diff <previous-tag>..<latest-tag> --stat` — the milestone's
  changed files.
- `ls .playbook-audits/ 2>/dev/null || ls docs/audits/ 2>/dev/null`
  — list any prior audit reports (the new convention is
  `.playbook-audits/`; `docs/audits/` is the legacy fallback).

If a prior audit report exists, read the most recent one before
starting. The new report must include a delta section: what was
resolved, what's still present, what's newly introduced.

If no prior audit exists, note that and treat this as the baseline.

---

## Step 2 — Convention compliance check (highest priority)

This is the spine of the audit. Read every rule the project documents
and check each one explicitly. Report violations as ⚠️ ISSUE with file
path and line number.

### Sourcing the rules

Read every file the project uses to document conventions, in priority
order:

- `CLAUDE.md` at the repo root, and any nested `CLAUDE.md` files
  closer to the code you'll touch.
- `AGENTS.md`.
- `.github/copilot-instructions.md`.
- `.github/instructions/**/*.md`.
- `.cursor/rules/**/*` (or `.cursorrules`).
- `README.md` — skim for contribution conventions.
- Stack-specific config files that often carry inline conventions
  (the variant lists which ones).

State which files you found and which rules you'll be checking.
Enumerate them as a checklist before scanning the code, so the audit
can be inspected for completeness later.

If the repo has none of these files, say so explicitly. You'll still
proceed with the variant's regression categories, but the spine of
the audit collapses — the user should know that.

### Per-rule sweep

For each documented rule, do a targeted sweep across the codebase and
report every violation. The variant lists the *common categories* a
project at this stack tends to document — use them as a starting
point, but always pivot to what the project's own docs actually say.

Some rules are mechanically checkable with grep/AST; some require
reading and judgment. Use the same ⚠️ ISSUE / 💡 CANDIDATE / 💡 EXTRACT
markers as the rest of the audit. A judgment-call placement is a
candidate, not an issue.

---

## Step 3 — Milestone diff focus

Run a deeper look at files changed in this milestone
(`git diff <previous-tag>..<latest-tag> --name-only`). The variant
lists the categories to check.

This section gets the most attention because milestone-fresh code is
where mistakes are most fixable.

---

## Step 4 — Full-sweep regression check

For the rest of the codebase (files unchanged this milestone), do a
lighter pass for slow drift. Use the two-tier reporting model:

- **Actionable findings**: list in full. These are specific issues
  with a specific fix at a specific location.
- **Pattern observations**: when a single rule produces many
  instances of the same kind, report the count and the 3 worst
  examples rather than enumerating every instance. The drift counter
  in Step 5 captures the totals; this section captures the worst
  offenders.

A finding goes in "actionable" if a follow-up prompt could plausibly
fix it in isolation. A finding goes in "pattern observations" if
fixing it would mean a sweep across many files — those are better
handled as a single sweep prompt than as 40 individual entries.

The variant lists the regression categories appropriate to this
stack.

---

## Step 4.5 — Extraction

This section asks "is this code at the right altitude?" — independent
of whether it works correctly. The goal is to surface refactor
opportunities that the other sections miss because they pass the
mechanical rules.

For each finding, name the specific candidate (file path, function /
module / component name, line range) and describe what should be
extracted, where it should go, and why.

The variant lists the signals that indicate misplaced code in this
stack (e.g. oversized components for a UI framework, oversized
modules / classes for a backend stack).

Use ⚠️ ISSUE only when the current placement is a documented-rule
violation. Otherwise, extraction recommendations are 💡 CANDIDATE /
💡 EXTRACT — they're judgment calls, not rule violations.

Output format for entries in this section:

- 💡 **EXTRACT** — `path/to/file:120-180`, `function_or_component_name` — Describe what's there, what it should become, and where it should live. **Suggested:** `fix-soon` / `defer`.

---

## Step 5 — Convention drift counter

Produce a small numeric table at the end of the report. The variant
specifies the rule rows; the structure is the same:

| Rule | Violations |
|---|---|
| <rule from variant> | N |

If a prior audit exists, show the previous count alongside, with an
arrow:

| Rule | Previous | Current | Δ |
|---|---|---|---|
| <rule> | 3 | 7 | ↑ 4 |

A rising number is itself a finding worth calling out in the summary.

---

## Step 6 — Delta against prior audit

If a prior audit exists, produce three lists:

- ✅ **Resolved since last audit** — findings that are no longer
  present.
- ⚠️ **Still present** — findings carried over. For each, note
  whether it was previously triaged as `defer` or `accept` (those are
  not failures; they're just carried), or whether it was `fix-soon`
  or `fix-now` and didn't get done (those are failures).
- 🆕 **Newly introduced** — findings that did not exist in the
  previous audit.

The "newly introduced" list is the most important section of the
entire report. Anything new should be heavily scrutinised because the
milestone introduced it deliberately or accidentally.

---

## Output format

Write the full report to `<root>/<latest-tag>-<timestamp>.md`,
where:

- `<root>` resolves in this order: `.playbook-audits/` if it
  exists, else `docs/audits/` if that exists (legacy convention),
  else create `.playbook-audits/` and append `.playbook-audits/`
  to `.gitignore` (creating `.gitignore` if absent — these are
  working artefacts, not tracked history).
- `<timestamp>` is current UTC time in basic ISO 8601 format
  `YYYYMMDDTHHMMSS` — generate with `date -u +%Y%m%dT%H%M%S`
  (e.g. `20260519T143022`).

Always write a new file; do not overwrite prior runs (even for the
same tag) — the directory is an ordered history. Structure:

```
# Audit — <tag>

Date: <today>
Stack variant: <nextjs | python | …>
Audit window: <previous-tag>..<latest-tag>
Files changed in window: <count>
Convention sources read: <list of files>

## Summary

<2-3 sentence verdict — overall health, biggest concern, biggest win
since last audit>

## Convention drift counter

<table from Step 5 / variant>

## Convention compliance

<grouped by rule, ⚠️ ISSUE / 💡 CANDIDATE entries>

## Milestone diff findings

<grouped by Step 3 category from variant>

## Full-sweep regression findings

<grouped by Step 4 category from variant — actionable findings
listed in full, pattern observations aggregated with top 3 worst>

## Extraction

<grouped by Step 4.5 category from variant — 💡 EXTRACT entries>

## Delta against <previous-tag> audit

<three lists from Step 6>

## Triage recommendations

<For every ⚠️ ISSUE in the report, suggest one of:
  - fix-now: ship a fix in the current sprint
  - fix-soon: schedule before next milestone
  - defer: real but not worth fixing yet
  - accept: known and not worth changing
The user will override these, but a recommendation forces the auditor
to commit to a view.>
```

Each finding entry uses this shape:

- ⚠️ ISSUE — `path/to/file:42` — Description in one sentence. **Suggested:** `fix-soon`.
- 💡 CANDIDATE — `path/to/file:42` — Description in one sentence. **Suggested:** `defer`.
- 💡 EXTRACT — `path/to/file:120-180` — Description. **Suggested:** `fix-soon`.

If a category has no findings, mark it ✅ PASS.

---

## Constraints

- Do not modify any code.
- Do not write findings to any file other than
  `<root>/<latest-tag>-<timestamp>.md`.
- If `<root>` does not exist, create it (default `.playbook-audits/`,
  see Output format).
- Every ⚠️ ISSUE must include a file path and line number.
  "Throughout the codebase" is not acceptable — pick the worst
  offender.
- Every ⚠️ ISSUE must include a triage recommendation.
- Pattern observations in Step 4 must include a count and the 3
  worst examples — do not enumerate every instance.
