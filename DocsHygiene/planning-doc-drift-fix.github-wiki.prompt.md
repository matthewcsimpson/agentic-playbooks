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
- `gh` CLI installed and on PATH.
- `git` installed.
- User is already authenticated (`gh auth status` reports a
  logged-in account). The core's Step 3 re-verifies each finding
  by re-reading the issue's current state — that requires `gh`.
- Wiki repo cloned as a sibling of the main repo at
  `../<repo>.wiki/` (see "Sibling-clone convention" in the audit
  variant for the rationale and `<repo>` derivation).
- Agent has shell + filesystem access.

The push is left to the user — this playbook never runs `git push`
on the wiki clone, regardless of `gh` auth state.

---

## §1 — Locate the audit (GitHub specifics)

Resolve `<root>` in this order: `.playbook-audits/` if it exists
in the main repo, else `docs/` if `docs/audits/` exists (legacy
convention). Look for files matching
**`<root>/audits/planning-doc-drift.github-wiki-*.md`** and pick
the most recent
(`ls -1 <root>/audits/planning-doc-drift.github-wiki-*.md 2>/dev/null | sort | tail -1`
— the `YYYYMMDDTHHMMSS` suffix sorts lexicographically), unless
the user names one explicitly.

If no report exists, stop and recommend:

> Run `/playbook planning-doc-drift-audit github-wiki` first.

---

## §2 — Re-verify preconditions

Derive `<repo>` exactly as the audit variant does — basename of
`git rev-parse --show-toplevel`, with the same divergence check
against `gh repo view --json name -q .name`. If the names differ,
stop with the audit variant's wording.

Repeat the audit variant's precondition checks, in order:

```
gh auth status
test -d ../<repo>.wiki
git -C ../<repo>.wiki status --porcelain
git -C ../<repo>.wiki pull --ff-only
```

If `gh auth status` fails, stop with the audit variant's wording
(`gh auth login`-from-terminal instruction). The fix re-verifies
findings against current issue state, which needs authenticated
`gh`.

If the sibling clone is missing, print the clone command and
stop. If it's dirty, **refuse to run** — print:

> The wiki clone has uncommitted changes. Commit or stash them in
> `../<repo>.wiki/` before re-running, then re-invoke this
> playbook.

Do not stash, discard, or amend. The user's WIP is sacred (see
core Constraints).

`git pull --ff-only` runs unconditionally — it's a no-op when the
local copy is current, and it's the only way to ensure the fix
edits aren't built on stale wiki state. If the pull fails
(diverged history, conflicting changes), stop and flag for human
review.

Re-verification of individual findings uses `gh issue view <n>`
and `git show <sha>` from inside the main repo. If the issue
state has changed since the audit (reopened, retitled with new
scope) or the commit has been reverted, skip the finding and
record under "Skipped — audit fix no longer applies."

---

## §4 — Edit and commit per category (GitHub specifics)

Edits happen on files inside `../<repo>.wiki/`. Wiki page paths
are markdown files anywhere in the clone, e.g.
`../<repo>.wiki/Home.md`, `../<repo>.wiki/Architecture.md`,
`../<repo>.wiki/design/multi-tenant.md`. Most GitHub wikis are
flat, but subdirectories are supported — use the page paths the
audit report recorded verbatim.

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
plus the first run's entry. **Prepend** each subsequent run's
entry directly under the top-of-file `# Planning-doc drift fix
log` heading so the newest run is immediately visible to a
reader landing on the page.

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
