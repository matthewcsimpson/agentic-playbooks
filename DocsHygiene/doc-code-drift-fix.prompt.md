---
description: Action findings from doc-code-drift-audit. Update docs to match the code, verify links and snippets, commit per drift type. Local commits only.
related: [doc-code-drift-audit]
---

# Doc-code drift fix

Action the in-scope findings from the most recent `doc-code-drift-audit`
report. Update docs to match the current code, commit locally per
category. Do not push or open a PR.

Doc-fix passes are deceptively easy to over-scope. The audit found
specific drifts; this prompt actions *those* and nothing else. Don't
rewrite paragraphs, restructure sections, or "improve" prose adjacent
to a drift fix.

---

## How to ask

When a step needs the user to choose or answer — picking findings to
action, resolving an ambiguity, confirming a decision — present it as
a structured selection: the `AskUserQuestion` tool in Claude Code
(multi-select when more than one item can be chosen), or an
equivalent numbered list in a harness without that tool. Never ask as
a free-form prose question. Put the recommended option first, marked
"(Recommended)".

---

## Inputs

The user supplies:

- **Categories in scope** — any combination of `hard`, `soft`,
  `stale`. Default is `hard` only — the audit's "Hard drifts" bucket
  is where the doc is provably wrong (path missing, function
  renamed, env var no longer read). Action `soft` only when the user
  explicitly opts in (signature drift, new required arg — the doc
  isn't wrong, just misleading). `stale` is opt-in plus a
  confirmation that the replacement practice is itself stable.
- **Specific findings to skip** — optional. The user may have
  triaged the report and flagged some entries as not-actually-drift
  (e.g. a deliberately archival doc that documents historical
  behaviour).
- **Doc files in scope** — optional narrowing. Default is every doc
  the audit flagged.

If the user hasn't specified, ask before doing anything else. Don't
guess scope.

---

## Step 1 — Locate the audit

The audit writes to `<root>/audits/doc-code-drift-<timestamp>.md`.
Resolve `<root>` in this order: `.playbook-audits/` if it exists,
else `docs/` if `docs/audits/` exists (legacy convention). Look
for files matching `<root>/audits/doc-code-drift-*.md` and pick
the most recent
(`ls -1 <root>/audits/doc-code-drift-*.md 2>/dev/null | sort | tail -1`
— the `YYYYMMDDTHHMMSS` suffix sorts lexicographically). If
neither root exists or no report is found, ask the user whether
they have an inline report to paste, or whether they need to run
the audit.

If the user named a specific report file, use that one instead of the
most recent.

If neither a file nor an inline report is available, stop and
recommend running `/playbook doc-code-drift-audit` first.

---

## Step 2 — Filter to scope

For each finding in the report, action it only if **all** of:

- It's under a section matching the in-scope categories (`Hard drifts`,
  `Soft drifts`, `Stale-but-correct`).
- It's not in the user-supplied skip list.
- A pre-edit re-check still confirms the drift. The audit may have
  been written days ago — the code may have moved, the doc may have
  been hand-fixed, or both.

The re-check shape per finding type:

- **Path drift** — does the file still not exist at the documented
  path? If someone fixed it manually, skip.
- **Renamed symbol** — grep the documented name; if still absent,
  the drift is real.
- **Renamed env var** — grep both the documented and current names
  across the whole repo (not just source — config, CI, deploy).
- **Drifted signature** — read the implementation; compare against
  the doc's example.
- **Stale command** — verify the doc's command against
  `package.json` scripts / `pyproject.toml` / `Makefile` /
  `Cargo.toml`.
- **Dead link** — for repo-relative links, check the path; for HTTP
  links, leave the user to verify externally and skip if not
  re-verifiable cheaply.

---

## Step 3 — Action findings, category by category

Findings group naturally by **drift type** (commands, paths, symbols,
env vars, snippets, links). Each type produces **one commit**.

For each type:

1. For each finding in this type:
   a. Edit the doc to match the current code. The audit's "Proposed
      fix" is a default, not a decision — adapt the wording to match
      the doc's existing voice. Don't introduce new prose; replace
      the wrong string with the right one.
   b. Re-verify by re-running the audit-style check against the
      edited doc:
      - Path: file now exists at the referenced path.
      - Command: the script / target named in the doc is present in
        the manifest.
      - Symbol: grep finds the name in source.
      - Env var: grep finds the var being read in code.
      - Signature: the doc example matches the current signature.
   c. If the verify fails (e.g. the proposed fix in the audit was
      itself stale), record under "Skipped — audit fix no longer
      applies" and move on.
   d. If verify passes: `git add` the doc edit. **Do not commit yet.**
2. When every finding in this type has been processed, commit the
   staged changes as one type-level commit. Conventional commit
   message describing what was reconciled ("docs: fix install command
   references", "docs: update renamed env var docs",
   "docs: update API signature in README examples").
3. If every finding in the type was skipped, nothing is staged —
   move to the next type without committing.

---

## Step 4 — Snippet drift (special handling)

Drifted code snippets in docs need extra care:

- A snippet that no longer compiles against the current API is the
  highest-value drift to fix — wrong examples mislead more than
  missing examples.
- Update the snippet to use the current API, matching the
  surrounding doc's style (variable names, formatting, level of
  detail).
- If the snippet was demonstrating a *capability* that no longer
  exists (the feature was removed), delete the snippet and the
  paragraph that introduced it. Don't leave orphaned prose
  referencing a code block that's gone.
- If the snippet is in an inline doc comment (JSDoc, docstring,
  rustdoc), the edit may be inside a source file rather than a doc
  file — group those into their own commit ("docs: refresh
  docstrings in `lib/auth/`") rather than mixing with markdown
  doc edits.

---

## Step 5 — Run the project's doc-related checks

When all in-scope findings are actioned, run whatever the project
has wired up for docs:

- Link checker (if configured — `lychee`, `markdown-link-check`).
- Markdown lint (`markdownlint`, `vale`).
- Doc build (Docusaurus, MkDocs, Sphinx) — a passing build is the
  gate.
- Any project-defined `docs:check` script.

If nothing is wired up, that's the report — note it.

---

## Step 6 — Report

Output a short summary:

- **Findings actioned** — count per drift type, with file paths.
- **Findings skipped within scope** — with reason per finding
  ("audit fix no longer applies", "user opted to keep", "external
  link, deferred to user").
- **Doc files modified** — list.
- **Final check result** — pass / fail with the failing command, or
  "no doc-check tooling configured."
- **Suggested PR title and body summary** — draft for a human to
  paste, not to open.

---

## Constraints

- Do not push to the remote.
- Do not open a PR.
- Do not action `soft` or `stale` findings unless the user explicitly
  opted in.
- Do not rewrite prose adjacent to a drift fix. Replace the wrong
  string, leave everything else alone. Scope creep turns a low-risk
  doc fix into a review burden.
- Do not "improve" example code beyond restoring it to a working
  state. If the audit said "example uses old signature", update the
  signature — don't refactor the example into something the audit
  didn't recommend.
- Do not change documented behaviour to match buggy code. If the doc
  says X and the code does Y, and Y looks like a regression, stop and
  flag for human review — the right fix may be to the code, not the
  doc.
- Do not delete CHANGELOG entries even if they describe behaviour
  that no longer exists. Historical entries are historical by design.
- If a doc fix would require changing the doc's structure (adding a
  new section, splitting a file, renaming a heading referenced by
  links), stop and flag — structural edits belong in a separate,
  deliberate doc pass.
