---
description: Read-only audit that finds places where documentation says one thing and the code does another (outdated commands, renamed env vars, drifted signatures, dead links).
related: [doc-code-drift-fix]
---

# Doc-code drift audit

Find places where the project's documentation says one thing and
the code does another. Common rot: outdated install commands, env
vars renamed, function signatures drifted, example snippets that
no longer compile, links to files that have moved or been deleted.

Read-only audit — does not fix any drift, only surfaces it.

## Inputs

Scope is load-bearing — a whole-repo doc audit and a "just `README.md`"
audit produce very different reports.

If the user hasn't named a scope, **ask before starting**. Offer them
three options:

1. **Name a specific scope** — a doc file or directory (e.g. just
   `README.md`, just `docs/api/`, just the project's LLM
   instruction files).
2. **Run against every doc in the repo** — confirm they want the
   wide scan.
3. **Infer it yourself** — start from the docs most likely to drift
   (root `README.md`, `CLAUDE.md` / `AGENTS.md`, any docs with
   embedded commands or env-var references). State your choice
   before proceeding.

Don't guess silently.

## Step 1 — Enumerate documentation

Find all docs:

- `README.md` at the root and nested in subdirectories.
- `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/**`,
  `.github/copilot-instructions.md`.
- `docs/**/*.md`.
- `CHANGELOG.md` (the *latest entry* is worth checking; older
  entries are historical and not expected to match current code).
- Inline doc comments: JSDoc / TSDoc, Python docstrings, rustdoc,
  godoc.

Skip:

- Generated docs (`docs/api/` or similar if built from code by a
  tool — they regenerate, drift isn't a stable finding).
- `node_modules/`, `vendor/`, `.venv/`, `target/`,
  `__pycache__/`.
- Test fixtures that include example docs as test data.

## Step 2 — Extract checkable claims

For each documentation file, extract claims that can be verified
against the code:

- **Install / setup commands** (`npm install`, `pip install -e .`,
  `cargo build`, `uv sync`). These go stale when the project
  changes package managers or scripts.
- **Run commands** (`npm start`, `make serve`, `python -m foo`,
  `pnpm dev`). Cross-reference with the manifest's actual scripts.
- **File paths** referenced explicitly (`see src/utils/foo.ts`).
- **Function / class / type names** referenced explicitly in
  prose.
- **Configuration keys / env vars** mentioned.
- **API endpoint paths and methods** mentioned.
- **Code snippets** (fenced code blocks claiming to be example
  usage of the project's API).
- **Architecture descriptions** that name specific modules /
  packages.

Don't extract:

- Concept-level prose ("we use a service layer pattern") — too
  fuzzy to drift-check.
- Generic snippets demonstrating *language* features rather than
  *project* APIs.
- Comparison content ("X is faster than Y") — opinion, not
  fact-checkable.

## Step 3 — Check each claim against the code

For each extracted claim:

- **Command exists** — does the project actually have this
  script / binary / make target? Cross-check with `package.json`
  scripts, `pyproject.toml` `[project.scripts]`,
  `Cargo.toml` `[[bin]]`, `Makefile` targets.
- **Path exists** — does the referenced file or directory still
  exist at that path?
- **Symbol exists** — does the function / class / type still
  exist with the documented name? Grep for the symbol.
- **Snippet compiles** (best-effort) — does the code snippet's
  API still match the source? Read the implementation and
  compare signatures.
- **Env var still read** — grep the codebase for the env var
  name.
- **Endpoint exists** — grep the route definitions for the
  documented path and method.

## Step 4 — Categorise findings

For each drift:

- **Hard drift** — the doc is provably wrong. The path doesn't
  exist, the function was renamed, the env var is no longer
  read. Safe to flag with high confidence.
- **Soft drift** — the doc looks plausible but the API has
  shifted. Signature changed, new required argument, default
  changed. The doc isn't outright wrong but using it as a guide
  would mislead.
- **Stale-but-correct** — the doc is technically right but
  describes outdated practice. Example: `npm install` works but
  the project has standardised on pnpm and the docs elsewhere
  say so. Lowest priority but worth noting.

## Step 5 — Report

Output to `docs/audits/doc-code-drift-<timestamp>.md`, where
`<timestamp>` is current UTC time in basic ISO 8601 format
`YYYYMMDDTHHMMSS` — generate with `date -u +%Y%m%dT%H%M%S` (e.g.
`20260519T143022`). Always write a new file; do not overwrite prior
runs — the directory is an ordered history. Structure:

```
# Doc-code drift audit

Date: <today>
Doc files scanned: <count>
Claims extracted: <count>
Drifts found: <count> (hard: <n>, soft: <n>, stale: <n>)

## Hard drifts (fix-now candidates)

### README.md:42 — install command

Doc says: `pnpm install`
Reality: project uses `uv sync` per `pyproject.toml`.
Proposed fix: update README install step to `uv sync`.

### docs/architecture.md:15 — moved file

Doc references `src/auth/oldFile.ts`; the file was renamed to
`src/auth/sessions.ts` (commit abc1234).
Proposed fix: update path reference.

## Soft drifts

### README.md:88 — function signature

Doc shows `createUser(name)`; actual signature is
`createUser(name, opts?: CreateUserOptions)`.
Proposed fix: update example to show the options arg.

## Stale-but-correct

- ...

## Summary

- Hard drifts: <n>
- Soft drifts: <n>
- Stale: <n>
- Top 3 worth fixing first: <list>
```

## Constraints

- Do not modify any doc or code. Surface the drift and the proposed
  fix; the user actions.
- Don't flag stylistic differences (e.g. doc says "Run `npm test`",
  code uses backticks differently) — only substantive content
  drift.
- Concept-level snippets that demonstrate *how to think* rather
  than literal API calls aren't drift even if the API changed.
  Use judgment.
- Don't flag old `CHANGELOG.md` entries as drift — those are
  historical by design. Only check the most recent entry against
  current state.
- If a project's docs are mostly fine, that's the report. Don't
  manufacture drift.
