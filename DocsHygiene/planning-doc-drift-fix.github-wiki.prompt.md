---
description: Action findings from planning-doc-drift-audit.github-wiki. Edit the sibling-cloned wiki, commit per drift category in the wiki repo, append to in-wiki CHANGELOG. Local commits only — never pushes.
related: [planning-doc-drift-audit, doc-code-drift-fix]
---

# Planning-doc drift fix — GitHub Wiki variant

Action the in-scope findings from the most recent
`planning-doc-drift-audit.github-wiki` report. Edit the wiki pages
in the sibling-cloned wiki repo, commit per drift category, append
to an in-wiki `CHANGELOG.md` page. Do not push.

**This prompt extends [`core/planning-doc-drift-fix.core.prompt.md`](./core/planning-doc-drift-fix.core.prompt.md).**
Read the core file first for the workflow shape (Inputs,
Step 1 audit discovery, Step 3 scope filter, Step 4 commit per
category, Step 5 CHANGELOG, Step 6 refuse-to-push, plus the
Constraints). This file supplies the GitHub-specific bits: the
sibling-clone convention, `git` commands for the wiki repo, the
in-wiki `CHANGELOG.md` page format, and the push command the
user runs by hand.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Assumed platform

- GitHub repository with a wiki enabled.
- `git` installed.
- Wiki repo cloned as a sibling of the main repo at
  `../<repo>.wiki/` (see "Sibling-clone convention" in the audit
  variant for the rationale).
- Agent has shell + filesystem access.

`gh` is not required for this playbook — all writes are to the
local wiki clone, and the push is left to the user.

---

## §1 — Locate the audit (GitHub specifics)

Look for **`docs/audits/planning-doc-drift.github-wiki.md`** in
the main repo. If multiple timestamped reports exist, use the
most recent unless the user names one.

If no report exists, stop and recommend:

> Run `/playbook planning-doc-drift-audit github-wiki` first.

---

## §2 — Re-verify preconditions

Repeat the audit variant's precondition checks, in order:

```
test -d ../<repo>.wiki
git -C ../<repo>.wiki status --porcelain
git -C ../<repo>.wiki fetch && git -C ../<repo>.wiki log -1 --format=%cr
```

If the sibling clone is missing, print the clone command and
stop. If it's dirty, **refuse to run** — print:

> The wiki clone has uncommitted changes. Commit or stash them in
> `../<repo>.wiki/` before re-running, then re-invoke this
> playbook.

Do not stash, discard, or amend. The user's WIP is sacred (see
core Constraints).

Optionally `git -C ../<repo>.wiki pull --ff-only` if the local
copy is more than an hour behind. If the pull fails, stop and
flag.

---

## §4 — Edit and commit per category (GitHub specifics)

Edits happen on files inside `../<repo>.wiki/`. Wiki page names
are the markdown filenames at the wiki root, e.g.
`../<repo>.wiki/Home.md`, `../<repo>.wiki/Architecture.md`.
GitHub wikis don't support subdirectories.

For each in-scope category with at least one actionable finding:

1. Edit the affected pages in the wiki clone (not the main repo).
2. `git -C ../<repo>.wiki add <files>`.
3. Commit with the core's category subject and bullet body:

   ```
   git -C ../<repo>.wiki commit -m "docs: reconcile decision drift" \
     -m "- Architecture.md: switched proxy story to BFF approach (drives: #142, abc1234)" \
     -m "- Home.md: removed cancelled multi-tenant feature (drives: #198)"
   ```

   One commit per category. The matching trailing bullets cite the
   driving evidence (issue numbers, short SHAs, PR numbers) so a
   future reader can trace each line back to its source.

Skip categories with zero actionable findings — no empty commits.

---

## §5 — In-wiki CHANGELOG (GitHub specifics)

The in-wiki CHANGELOG is a dedicated page at
**`../<repo>.wiki/CHANGELOG.md`**. GitHub renders it as a normal
wiki page; readers see it linked from the wiki sidebar.

Format:

```markdown
# Planning-doc drift fix log

A running log of edits made by the `planning-doc-drift-fix`
playbook. Each entry lists the pages changed and the driving
issue / commit so a reader can trace why the wiki shifted.

## 2026-05-17 — planning-doc-drift fix run

- Architecture.md: switched proxy story to BFF approach
  (drives: #142, abc1234)
- Home.md: removed cancelled multi-tenant feature (drives: #198)
- Roadmap.md: marked Phase 2 as shipped (drives: #210, def5678)

## 2026-02-04 — planning-doc-drift fix run

- ...
```

If the page doesn't exist yet, create it with the header above
plus the first run's entry. Append new entries at the top (newest
first) so the most recent run is immediately visible.

Commit the CHANGELOG update as a final, separate commit:

```
git -C ../<repo>.wiki add CHANGELOG.md
git -C ../<repo>.wiki commit -m "docs: log planning-doc-drift fix run 2026-05-17"
```

---

## §6 — Refuse to push, report (GitHub specifics)

Do not run `git -C ../<repo>.wiki push`. Print the exact command
the user runs by hand:

```
cd ../<repo>.wiki && git push
```

(Or, if the user prefers staying in the main repo's directory:
`git -C ../<repo>.wiki push`.)

The final summary:

```
Planning-doc drift fix — GitHub Wiki

Wiki clone:           ../<repo>.wiki/
Categories actioned:  <decision: n, scope: n, architecture: n, mechanical: n>
Pages modified:       <n>  (Architecture.md, Home.md, Roadmap.md)
Commits created:      <n+1>  (one per category, plus CHANGELOG)
  - docs: reconcile decision drift
  - docs: reconcile scope drift
  - docs: log planning-doc-drift fix run 2026-05-17
Findings skipped:     <n>  (see below for reasons)

To publish:           cd ../<repo>.wiki && git push
```

---

## Constraints (GitHub specifics on top of the core)

- **Local commits only.** Do not `git push` from inside the
  prompt. The wiki *is* a remote-published surface, but the
  user-runs-push discipline is the house style and keeps the
  human in the loop on what becomes visible.
- **All writes go to `../<repo>.wiki/`.** Never edit a file in
  the main repo working tree. If a finding would require editing
  repo-local docs (e.g. an architecture diagram referenced from
  the wiki lives in the repo's `docs/`), stop and flag — that's
  `doc-code-drift-fix`'s job, not this one's.
- **Refuse if the wiki clone is dirty.** Do not stash, do not
  discard, do not `git checkout` over the user's changes.
- **Don't rename or delete wiki pages.** Wiki page renames break
  inbound links from other pages and from external sources
  (issues, PRs, external docs). If a finding implies a rename or
  delete, stop and flag — structural edits belong in a separate,
  deliberate pass.
- **Don't create new wiki pages** unless the CHANGELOG.md is
  genuinely absent. New planning pages are a deliberate
  authoring decision, not a drift fix.
- **Don't `gh wiki`-anything.** There's no `gh wiki` subcommand;
  the wiki is just git. Stay in the sibling clone.
