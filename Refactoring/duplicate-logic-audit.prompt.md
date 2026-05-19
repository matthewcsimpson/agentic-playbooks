---
description: Find functions, modules, or components doing the same job under different names. Cluster, identify a winner, propose consolidations. Read-only — does not action.
related: [duplicate-logic-fix, dead-code-audit]
---

# Find duplicate logic

Find functions, modules, or components that do the same job under
different names. Propose consolidations and identify which version
should win. Read-only audit — does not action any consolidations.

The LLM's value-add over static dedup tools is *semantic* similarity
(two validators with different naming conventions doing the same
job, or two helpers with the same job and slightly different return
shapes). Static tools find textual duplicates; this prompt covers
both.

## Inputs

Scope is load-bearing — a whole-repo duplicate-logic audit and a
"just the validation helpers" audit produce very different reports.

If the user hasn't named a scope, **ask before starting**. Offer them
three options:

1. **Name a specific scope** — a directory, package, feature area,
   or category (e.g. `lib/utils/`, "the route handlers", "the
   formatting helpers").
2. **Run against the whole repo** — confirm they want the wide
   scan; the resulting cluster count will be larger and harder to
   triage.
3. **Infer it yourself** — pick a scope likely to contain duplicates:
   utility / helper directories (`utils/`, `helpers/`, `lib/`),
   validation modules, or formatting/parsing code. State your
   choice before proceeding.

Don't guess silently.

## Step 1 — Establish scope

Read:

- The project manifest to identify language and framework.
- LLM instruction files (`CLAUDE.md`, `AGENTS.md`, etc.) for any
  documented patterns about where helpers / utilities live (which
  package, which folder, what "shared" means here).
- Workspace structure: which directories are sources, which are
  generated, which are vendored, which are tests.

Skip vendored / generated / build output. List what you're treating
as in-scope.

## Step 2 — Enumerate candidates

Group source files by purpose, based on the project's structure.
Typical groups:

- Utility / helper modules.
- Route / controller / handler files.
- View / component files.
- Service / repository / use-case files.
- Validation / parsing / formatting modules.

For each group, list every exported function / class / component
with a one-line description of what it does. Read the function
bodies, not just the signatures — semantically identical work
often has different signatures.

## Step 3 — Cluster by behaviour

Within each group, cluster items that appear to do the same job. A
cluster is two or more items that, given the same inputs, would
produce the same outputs (or trigger the same side effects). Reach
across files freely — the most useful duplicates often live in
different directories.

For each cluster of 2+:

- List the members (file path + symbol name).
- Describe what they all do (one sentence).
- Identify the differences (parameter names, return shapes, edge
  case handling, presence of logging, hidden side effects).

## Step 4 — Recommend a winner per cluster

For each cluster, recommend which member to keep and propose
consolidations:

- **Keep** — the version with the broadest API, the best test
  coverage, the cleanest implementation, or the placement that
  matches the project's documented monorepo / layering rules.
- **Drop / migrate** — the others. One-line note on the migration
  (rename + import update, generalise parameters, etc.).
- **Risk** — anything subtle that could break in the migration:
  callers depending on a specific edge case, hidden side effects,
  transitively re-exported symbols, public API surface.

## Step 5 — Report

Output to `<root>/duplicate-logic-<timestamp>.md`, where:

- `<root>` resolves in this order: `.playbook-audits/` if it
  exists, else `docs/audits/` if that exists (legacy convention),
  else create `.playbook-audits/` and append `.playbook-audits/`
  to `.gitignore` (creating `.gitignore` if absent — these are
  working artefacts, not tracked history).
- `<timestamp>` is current UTC time in basic ISO 8601 format
  `YYYYMMDDTHHMMSS` — generate with `date -u +%Y%m%dT%H%M%S`
  (e.g. `20260519T143022`).

Always write a new file; do not overwrite prior runs — the
directory is an ordered history. Structure:

```
# Duplicate logic audit

Date: <today>
Scope: <whole repo | directory>
Files scanned: <count>
Clusters found: <count>

## Cluster 1 — <one-line description>

Members:
- `path/to/a.ts:foo` — <one-line distinguishing detail>
- `path/to/b.ts:bar` — <one-line distinguishing detail>
- `path/to/c.ts:baz` — <one-line distinguishing detail>

Recommended winner: `path/to/a.ts:foo`
Why: <one-sentence reason>
Migration: <one-line plan>
Risk: <one-line callout, or "low">

## Cluster 2 — ...
```

End with a summary:

- Total clusters.
- Total members that would be removed if all consolidations were
  applied (ballpark LOC removal).
- The top 3 clusters worth prioritising and why.

## Constraints

- Do not action any consolidations — this prompt is purely
  detection. Use a follow-up prompt or a manual pass to act on
  individual clusters.
- Do not flag near-duplicates that exist by design (paired
  encode / decode, getter / setter, request / response pairs,
  test fixtures intentionally similar to production data). Use
  judgment.
- A cluster of 2 is worth listing only when the consolidation is
  clearly worth doing. Small differences that justify both
  versions belong in a "considered but kept" appendix, not the
  main list.
- Pattern observations apply: if one rule produces many small
  clusters (e.g. dozens of "`X.from()` vs `new X()`"
  near-equivalences), report the count and the 3 worst examples
  rather than enumerating every instance.
