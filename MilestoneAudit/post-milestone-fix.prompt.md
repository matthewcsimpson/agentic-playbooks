---
description: Action the in-scope findings from the most recent post-milestone audit report. Commits locally; does not push or open a PR.
related: [post-milestone-audit-dotnet, post-milestone-audit-nestjs, post-milestone-audit-nextjs, post-milestone-audit-python, post-milestone-audit-react-native, post-milestone-audit-swift, post-milestone-audit-terraform]
---

# Post-milestone fix

Action the in-scope findings from the most recent audit report. Commit
locally; do not push or open a PR.

---

## Inputs

The user supplies:

- **Triage labels in scope** — typically `fix-now`. Any combination of
  the audit's triage vocabulary (`fix-now`, `fix-soon`, `defer`,
  `accept`) is allowed, but `defer` / `accept` rarely make sense
  here.
- **Sections in scope** — typically `Convention compliance` and
  `Milestone diff findings`. Names match the section headings emitted
  by `post-milestone-audit.prompt.md`.

If the user hasn't specified, ask before doing anything else. Don't
guess scope.

---

## Step 1 — Locate the audit

Read the most recent milestone audit report. Resolve `<root>` in
this order: `.playbook-audits/` if it exists, else `docs/` if
`docs/audits/` exists (legacy convention).

Files live at:

- New convention: `<root>/milestones/<tag>-<timestamp>.md` (e.g.
  `.playbook-audits/milestones/v1.6.0-20260519T143022.md`).
- Legacy convention: `<root>/audits/<tag>-<timestamp>.md` (where
  milestone reports are mixed in with other audit reports).

To find the latest report, try the new path first, then legacy:

```
ls -1 <root>/milestones/*.md 2>/dev/null | sort | tail -1
ls -1 <root>/audits/*-*.md  2>/dev/null | sort | tail -1
```

Both `<tag>` and the `YYYYMMDDTHHMMSS` suffix sort
lexicographically, so `sort | tail -1` picks the latest. If the
user named a specific tag, restrict by tag first
(`<root>/milestones/<tag>-*.md` or `<root>/audits/<tag>-*.md`).

Under the legacy layout, the `<root>/audits/` directory mixes
milestone reports with other audit reports
(`dead-code-...md`, `observability-...md`, etc.). If no tag is
named and the legacy directory contains both, ask the user to
disambiguate — picking by timestamp alone could surface the wrong
file.

If neither root nor any report can be found, surface that and
stop — there's nothing to action.

---

## Step 2 — Filter to scope

Action only findings that match **both**:

- A section listed in the in-scope sections.
- A triage recommendation matching the in-scope labels.

Skip everything else. Do not action 💡 CANDIDATE or 💡 EXTRACT entries
unless their triage explicitly says `fix-now`. Extraction work
belongs in its own focused prompts, not bundled with mechanical
fixes.

---

## Step 3 — Action each finding

For each in-scope finding:

- Make the change.
- Verify with the project's type-check and lint commands (e.g.
  `pnpm check-types && pnpm lint`, `npm run typecheck`, `pytest -q`,
  `cargo check && cargo clippy` — infer from the project manifest).
- Stage and commit with a conventional commit message that references
  the finding location (file path).

**Group commits by category, not by file** — one commit per logical
fix. If two findings are in the same category and adjacent in the
codebase, they can share a commit.

If a finding turns out to be wrong (the issue no longer exists, or the
suggested fix would break something), skip it and note the reason in
the final report. Do not silently ignore.

---

## Step 4 — Run the full check suite

When all in-scope findings are actioned, run the project's full check
suite. The standard sequence is:

- Type-check
- Lint
- Test
- Build (scoped to the primary app if the project is a monorepo)

Infer the commands from the project manifest (`package.json`,
`pyproject.toml`, `Cargo.toml`, etc.) and any documented scripts.

---

## Step 5 — Report

Output a short summary:

- **Findings actioned** — list with file path.
- **Findings skipped within scope** — list with reason (usually "the
  issue no longer exists" or "the suggested fix would break X").
- **Build / test result** — pass / fail with the failing command if
  relevant.
- **Suggested PR title and body summary** — draft for a human to
  paste, not to open.

---

## Constraints

- Do not push to the remote.
- Do not open a PR.
- Do not action findings outside the user-supplied scope, even if
  they look quick. Scope creep is the failure mode this prompt is
  defending against.
- Stop after committing locally so the changes can be reviewed.
