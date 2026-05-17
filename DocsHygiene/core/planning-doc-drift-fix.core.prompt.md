# Planning-doc drift fix — core

Shared scaffold for the planning-doc drift fix. Not invoked
directly — the platform-specific variants
(`planning-doc-drift-fix.github-wiki.prompt.md`, and eventually
variants for Confluence / Notion / Obsidian / etc.) reference this
file for the workflow shape and reuse the generic sections.

Action the in-scope findings from the most recent
`planning-doc-drift-audit` report. Update the planning doc to
match the current decisions / scope / architecture, record the
*why* in three layers (commit messages, in-doc CHANGELOG, audit
report continuity). Do not push.

Doc-fix passes are deceptively easy to over-scope. The audit found
specific drifts; this prompt actions *those* and nothing else.
Don't rewrite sections, restructure pages, or "improve" prose
adjacent to a drift fix.

A variant supplies the platform-specific content for:

- Where the doc lives and how to edit it (sibling clone, API,
  etc.).
- How to commit / version the edit (git in a sibling clone vs API
  call with audit metadata).
- The push-refusal guardrail wording for that target.
- The shape of the in-doc CHANGELOG entry (markdown page, separate
  doc, structured metadata field).

Everything else below is shared.

---

## Inputs

The user supplies:

- **Categories in scope** — any combination of `decision`,
  `scope`, `architecture`, `mechanical`, `stale`. Default is
  `decision` + `scope` + `architecture` + `mechanical`
  (everything except `stale`). `stale` is opt-in plus a
  confirmation that the user wants advisory findings actioned.
- **Specific findings to skip** — optional. The user may have
  triaged the report and flagged some entries as
  not-actually-drift, or as needing human judgment first.
- **Doc pages in scope** — optional narrowing. Default is every
  page the audit flagged.

If the user hasn't specified, ask before doing anything else.
Don't guess scope.

---

## Step 1 — Locate the audit

The variant specifies the audit report path. Look for the file
first; if multiple timestamped reports exist, use the most recent
unless the user named one explicitly. If no report exists, stop
and recommend running the matching audit playbook first.

If the user has an inline report to paste (no filesystem
report available), accept it. Parse the same structure either way.

---

## Step 2 — Re-verify preconditions

Re-run the variant's precondition checks (auth, doc clone
present, doc clone clean, etc.). The audit may have been written
days ago — the world has moved. If a precondition now fails,
print the fix command and stop.

Specifically: if the doc surface has uncommitted / unsaved
changes, **refuse to run**. Do not stash, discard, or "fix
forward" — the user's WIP is sacred.

---

## Step 3 — Filter to scope

For each finding in the report, action it only if **all** of:

- It's under a section matching the in-scope categories
  (`Decision drift`, `Scope drift`, `Architecture drift`,
  `Mechanical drift`, `Stale-but-correct`).
- It's not in the user-supplied skip list.
- A pre-edit re-check still confirms the drift. The audit's
  evidence (issue #, commit sha) is the anchor — re-read the
  issue's current state and the commit; if the situation has
  changed (issue reopened, commit reverted, doc edited by hand),
  skip and record the reason.

---

## Step 4 — Action findings, category by category

Findings group by **drift category**. Each category produces
**one commit / one versioned edit** in the doc system.

For each category in scope:

1. For each finding in this category:
   a. Edit the doc page. The audit's "Proposed fix" is a default,
      not a decision — adapt the wording to match the page's
      existing voice. Replace the contradictory claim with the
      current truth; don't add new sections or restructure.
   b. **Architecture drift** often requires more than a string
      swap (e.g. a renamed module appears throughout a page).
      Read the whole page once, edit every affected reference,
      keep the surrounding narrative intact.
   c. **Decision drift** — when reversing a decision, leave a
      short trailing note where appropriate ("Previously this
      page described approach X; superseded by #<issue> on
      <date>.") *only if* the page is a living spec the team
      relies on for orientation. Throwaway pages don't need a
      breadcrumb.
   d. **Scope drift** — when removing scope that was descoped,
      delete cleanly. Don't leave "[deleted]" stubs. The
      CHANGELOG entry (Step 5) is the historical trail.
   e. **Stale-but-correct** — skip unless the user explicitly
      opted in. If opted in, the action is usually a timestamp
      refresh or a "last reviewed" note, not a content edit.
   f. Re-verify by re-reading the edited page; the contradictory
      claim should be gone and the page should still read
      coherently.
   g. If verify fails (e.g. the proposed fix in the audit was
      itself stale), record under "Skipped — audit fix no
      longer applies" and move on.
2. When every finding in this category has been processed,
   commit / version the edits as one category-level change. The
   variant specifies the commit format. Subject convention:

   ```
   docs: reconcile <category> drift
   ```

   Body convention: one bullet per finding, citing the page
   edited and the driving evidence (`#issue`, short SHA, PR):

   ```
   - <page-name>: <one-line summary> (drives: #123, abc1234)
   - <page-name>: <one-line summary> (drives: #456)
   ```

3. If every finding in the category was skipped, nothing is
   staged — move to the next category without committing.

---

## Step 5 — Update the in-doc CHANGELOG

The variant specifies the format and location of the in-doc
CHANGELOG (e.g. a `CHANGELOG.md` page in the wiki). Append a new
entry for this run:

```
## <YYYY-MM-DD> — planning-doc-drift fix run

- <page-name>: <summary> (drives: #123)
- <page-name>: <summary> (drives: #456)
```

Commit the CHANGELOG update as a final, separate commit:

```
docs: log planning-doc-drift fix run <YYYY-MM-DD>
```

Three persistence layers, each serves a different reader:

- **The audit report** in the main repo's `docs/audits/` is the
  bookkeeping for the *next* audit run (diff against prior).
- **The commit history** in the doc system is the reviewable
  trail per category.
- **The in-doc CHANGELOG** is what a *doc reader* sees — they
  notice the page changed and can see why.

If the CHANGELOG doesn't exist yet, create it. Don't gate the
fix run on its absence.

---

## Step 6 — Refuse to push, report

When all in-scope categories have been actioned:

- **Stop.** Do not push, do not open a PR, do not call the doc
  system's "publish" / "sync" API. The variant specifies the
  exact one-line command the user can run to push when they're
  ready.
- Print a short summary:
  - **Findings actioned** — count per category, with page paths.
  - **Findings skipped within scope** — with reason per finding.
  - **Doc pages modified** — list.
  - **Commits / versions created** — list with subjects.
  - **Manual next step** — the exact push command, with the
    correct working directory.

---

## Constraints

- Do not push, sync, or publish. The variant's specific wording
  applies on top of this rule.
- Do not edit the main repo working tree. All writes target the
  external doc surface (sibling clone, API, etc.). If a finding
  would require editing repo-local code or docs, stop and flag —
  that's a different playbook's job (`doc-code-drift-fix` for
  repo-local docs).
- Do not action `stale` findings unless the user explicitly opted
  in. They're advisory.
- Do not rewrite prose adjacent to a drift fix. Replace the
  contradictory claim; leave everything else alone.
- Do not delete CHANGELOG-style historical entries even if they
  describe behaviour that no longer exists. The CHANGELOG is
  historical by design.
- Do not change documented decisions to match buggy or partial
  code. If the doc says approach X is in force, and the code
  half-implements approach Y as if mid-migration, stop and flag
  for human review — the drift may be incomplete code, not stale
  doc.
- Refuse to run if the doc surface has uncommitted / unsaved
  changes. Never stash or discard the user's WIP.
- If a fix would require restructuring (splitting a page,
  renaming a page that other pages link to, adding a new
  top-level section), stop and flag — structural edits belong
  in a separate, deliberate doc pass.
