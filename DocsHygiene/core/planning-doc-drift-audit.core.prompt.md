# Planning-doc drift audit — core

Shared scaffold for the planning-doc drift audit. Not invoked
directly — the platform-specific variants
(`planning-doc-drift-audit.github-wiki.prompt.md`, and eventually
variants for Confluence / Notion / Obsidian / etc.) reference this
file for the workflow shape and reuse the generic sections.

Planning docs (project wikis, design pages, RFC pages) hold the
*original* intent: the chosen approach, scoped features, named
modules, target architecture. As coding decisions land, the doc
drifts and quietly rots into a stale snapshot. This audit surfaces
that drift by cross-referencing the planning doc against issues
and commits.

Distinct from `doc-code-drift-audit`, which targets *mechanical*
drift (commands, env vars, snippets) in repo-local docs. This pair
targets *decision/intent* drift in an external doc system.

A variant supplies the platform-specific content for:

- Authentication / capability preconditions.
- The location of the planning doc (sibling clone, API endpoint, etc.).
- Commands for fetching issues, recent commits, and doc pages.
- The exact path the audit report writes to.

Everything else below is shared.

---

## Step 0 — Ask for scope

Before doing anything else, confirm three things with the user:

1. **The project** — the variant specifies the target format
   (repo address, workspace ID, etc.). Don't default to the current
   working directory's git remote unless the user says "the
   project I'm in."
2. **The doc surface** — the entire planning doc, or a named subset
   (e.g. just the "Architecture" page family). Default: entire doc.
3. **The cutoff** — if a prior audit report exists, default to
   "everything since the prior audit's `Date:` header." Otherwise
   ask: full history, or the last 90 days?

Don't guess silently.

---

## Step 1 — Verify access and locate inputs

The variant specifies how to:

- Confirm authenticated access to the issue tracker.
- Confirm access to the planning doc (e.g. sibling clone is
  present and clean; API token works).
- List the doc pages in scope.

If any precondition fails, surface the error and stop. Do not
attempt to authenticate, clone, or pull from inside the prompt —
those are interactive flows the user owns. Print the exact one-line
command the user can run to fix the precondition, then stop.

Report a one-line summary so the user knows the scope:

```
Scanning <N> doc pages against <M closed + K open> issues and <C> commits since <cutoff>.
```

---

## Step 2 — Ingest the inputs

Pull the three input streams. The variant supplies the exact
commands; the shape required is:

- **Closed issues** — number, title, body, labels, closed-at,
  linked PRs / commits. Closed issues are where landed decisions
  live.
- **Open issues** — number, title, body, labels, assignees,
  milestone. Open issues are in-flight plans the doc may already
  contradict.
- **Recent commits** — SHA, subject, body, files changed, date.
  Used to detect architecture drift (renames, moves, splits) the
  issues alone won't reveal.
- **Doc pages** — page name, body, last-modified date.

Filter all four streams by the cutoff from Step 0. If `since` is
older than a few months and the volume is large, warn the user
before proceeding.

---

## Step 3 — Build claim ↔ reality pairs

For each doc page, extract **load-bearing claims** that can be
checked against issues / commits / code:

- **Design choices** — "we use approach X" / "library Y" / "pattern
  Z." The doc claims a choice was made.
- **Scoped features** — "the system will support A, B, C." The doc
  claims work is planned or done. Phasing claims ("Phase 1 ships
  before Phase 2") fall here — if the order changed, that's scope
  drift, not its own category.
- **Named modules / files / endpoints** — "the `Foo` service
  handles X" / "`apps/web/proxy.ts` does Y."
- **Non-goals / exclusions** — "we explicitly do not support W."

Don't extract:

- Generic prose ("we value reliability") — not fact-checkable.
- Forward-looking aspirations not tied to a planned deliverable.
- Examples that demonstrate concepts rather than the project's
  actual API (defer to `doc-code-drift-audit` for those).

For each claim, search the input streams for contradictory or
confirming evidence:

- **Issue body / title contains the named module, feature, or
  approach** — does the issue confirm the doc, propose a change,
  or already record the change?
- **Closed-issue resolution** — when an issue closed, did it land
  the doc's approach or a different one? (Check the merge commit
  message, the closing comment, the linked PR.)
- **Commit subject / body / files** — was the named module
  renamed, moved, or removed? Was a different library introduced?
- **Cross-references** — does an issue say "supersedes #N" or
  "see wiki/Page" where the wiki page is now stale?

A claim with no contradictory evidence is *not* drift — even if
the doc page is old. Don't manufacture drift; old-but-correct is a
valid state.

---

## Step 4 — Categorise drift

Each contradiction is one of:

- **Decision drift** — the doc states approach X; a closed issue
  landed approach Y (or the code clearly shows Y). The doc
  records a decision that is no longer in force.
- **Scope drift** — the doc treats feature F as planned; an issue
  closed `not planned`, was descoped, or the feature was removed
  in a commit. Conversely, a feature now in production isn't in
  the doc's scope.
- **Architecture drift** — the doc names module / file / endpoint
  M; M has been renamed, moved, split, or removed in commits.
  Different from mechanical drift because the doc may need
  *rewriting around the new structure*, not just a name swap.
- **Mechanical drift** — pure rename / path-swap with no
  conceptual change. Same kind of thing `doc-code-drift-audit`
  finds, but in the external doc. Lowest-risk to fix.
- **Stale-but-correct** — page hasn't been touched in N months
  (variant defines N; default 6) but its claims still check out.
  Flag for visibility; do not propose a fix.

If a single page has multiple drifts, list each separately under
its own category — the fix playbook commits per category, so this
keeps the trail clean.

---

## Step 5 — Report

If Steps 3–4 found **zero drifts** (including zero `Stale-but-
correct` entries), don't write a half-empty skeleton report.
Write a one-line file at the variant's report path:

```
# Planning-doc drift audit — <variant label>
Date: <today>
Project: <project address>
No drift found. <N pages> scanned against <M closed + K open>
issues and <C> commits since <cutoff>.
```

Then stop. The next audit run will still find this report and
use its `Date:` header as the cutoff, so the empty result is
load-bearing for continuity.

Otherwise, the variant specifies the exact report path.
Structure:

```
# Planning-doc drift audit — <variant label>
Date: <today>
Project: <project address>
Doc pages scanned: <n>
Issues consulted: <closed: n, open: n>  (since: <cutoff>)
Commits scanned: <n>  (since: <cutoff>)
Drifts found: <total>  (decision: n, scope: n, architecture: n, mechanical: n, stale: n)

## Decision drift
### <page-name>:<line or section anchor> — <short title>
Doc says: "<quote>"
Reality: <one-line summary>
Evidence: #<issue>, <sha>, <PR>
Proposed fix: <one-line — rewrite "X" to reflect Y>

## Scope drift
### ...

## Architecture drift
### ...

## Mechanical drift
### ...

## Stale-but-correct
- <page-name> — last edited <date>, claims still check out. No action.

## Summary
- Top N worth fixing first (cite category + page): ...
- Anything that requires human judgment before the fix playbook can run: ...
```

Read-only. Does not edit the doc, the issues, or the code.

---

## Constraints

- Treat the doc as the *subject* of the audit, not the source of
  truth. The source of truth is the combination of closed-issue
  resolutions + landed commits.
- Don't infer drift from prose tone (e.g. "this used to be a
  goal" / "we're now focusing on..."). The doc may have already
  recorded the change in plain English — that's not drift.
- Don't flag a doc page as drift because the *code* uses different
  vocabulary. Doc-level naming may be deliberate abstraction.
  Drift requires a substantive contradiction, not a vocabulary gap.
- Don't action anything. Surface the drift and the proposed fix;
  the user picks what the fix playbook runs.
- Stale-but-correct findings are advisory only — don't crowd them
  into the top-N list.
- If the prior audit report exists and a finding was already
  recorded in a prior run *and* the doc hasn't moved, note that —
  it may be a known-deferred issue rather than fresh drift.
