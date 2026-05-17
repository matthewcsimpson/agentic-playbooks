---
description: Survey a repository's test coverage from scratch, identify the most important gaps, and present a ranked list of recommendations.
related: [test-coverage-fix]
---

# Audit test coverage

Survey a repository's test coverage from scratch, identify the most important
gaps, and present a ranked list of recommendations.

Makes no assumptions about prior surveys, curated strategy documents, or
pre-existing inventories — every run is a fresh look. Run this any time you
want an honest picture of where the test suite is thin. Pair with
`test-coverage-fix.prompt.md` to act on a finding.

## Inputs

Scope is the load-bearing input. The same repo audited "whole" vs
"just the auth module" produces very different reports.

If the user hasn't named a scope, **ask before starting**. Offer them
three options:

1. **Name a specific scope** — a directory, package, or feature area
   (e.g. `apps/api/`, `lib/auth/`, "the payment flow").
2. **Run against the whole repo** — confirm they want the wide
   scan; the resulting ranked list will be longer and harder to
   triage. Better for "is the suite generally healthy" than "what's
   the next thing to write."
3. **Infer it yourself** — pick a scope based on the project's
   structure. Default heuristic: largest non-test source directory,
   or the directory with the most recent commit activity if `git
   log` is informative. State your choice and the reasoning before
   proceeding.

Don't guess silently.

## Your job

### 1. Discover the repo's LLM instructions

Look for any of the following, in this priority order, and read every one
you find:

- `CLAUDE.md` at the repo root, and any nested `CLAUDE.md` files closer to
  the code you'll touch.
- `AGENTS.md`.
- `.github/copilot-instructions.md`.
- `.github/instructions/**/*.md`.
- `.cursor/rules/**/*` (or `.cursorrules`).
- `README.md` — skim for build/test instructions and contribution
  conventions.

State which files you found and which you're treating as primary. If the
repo has none, say so explicitly — you'll still proceed, but with weaker
convention signals and the user should know that.

### 2. Learn the code conventions

Don't trust instruction files alone — read the code too. Files often drift
from documented rules.

- Read the manifest: `package.json` / `pyproject.toml` / `Cargo.toml` /
  `go.mod` / equivalent. Note language, primary frameworks, test runner,
  available scripts.
- Read the test config: `vitest.config.*`, `jest.config.*`, `pytest.ini` /
  `pyproject.toml [tool.pytest.ini_options]`, `cargo` test setup, etc.
- Read 3–5 representative existing tests. Note: file naming, location
  pattern (colocated siblings vs. `__tests__/` vs. top-level `tests/`),
  assertion library, mocking style, setup helpers.
- Read 3–5 representative source files spanning the app's domains. Note:
  file naming, folder layout, language features used (TS strictness,
  decorators, etc.), import conventions.

Summarise in 5–10 bullets what a contributor would need to know to write a
test that fits this codebase. This is the contract the executor prompt
will follow.

### 3. Establish a baseline

Run the project's test command once (`npm test`, `pytest`, `cargo test`,
etc., inferred from §2). Report:

- Number of tests.
- Pass / fail / skip counts.
- Runtime.

**If the suite is red, stop here.** Report which tests fail and ask the
user how to proceed. You can't audit a broken baseline — the noise will
swamp signal.

### 4. Survey gaps

Enumerate testable source files. "Testable" usually means:

- Business logic modules / services / use-cases.
- Route handlers / controllers / API endpoints.
- Utilities and pure helpers.
- Components / pages / views (anything with rendering logic, for
  UI codebases).
- Auth, payment, and other security or money-handling code.

Explicitly skip:

- Type-only files (`*.types.ts`, `*.d.ts`, `*.pyi`, etc.).
- Re-export barrels (files that only re-export from other modules).
- Generated code, vendored / third-party files.
- Configuration files.
- Stories, fixtures, scripts, build helpers.

For each testable file, classify:

- ✅ **Covered** — has a sibling / companion test that exercises it
  directly.
- 🟡 **Partial** — an adjacent helper or upstream module is tested but the
  file itself isn't, OR the file has a test but obvious failure cases are
  missing.
- ❌ **Missing** — no test references it at all.

**Classify per file, not per folder.** When a folder contains a barrel
re-export (`index.ts`, `index.js`, `mod.rs`, `__init__.py`) plus other
source files, the barrel is excluded from the testable set (per the
skip list above) — *but each sibling source file is classified on its
own merits*. Example: a folder with `Foo.ts`, `Foo.test.ts`, and
`index.ts` (re-export only) has `Foo.ts` as ✅ **Covered**. Do **not**
aggregate the folder to ❌ Missing because the barrel has no companion
test — the barrel was already taken out of scope, so its untested
state is not a finding. This false-positive bites when an agent
implicitly treats `index.ts` as the folder's canonical file and
searches for `index.test.ts`; the rule is per-file, period.

Group by feature / domain (infer from directory structure — e.g.
`components/Checkout/**` → "Checkout"; `lib/auth/**` → "Auth").
Grouping is for *report layout only* — it never changes a file's
classification.

### 5. Prioritise

Rank gaps using these heuristics, from highest to lowest:

1. **Critical risk** — money handling (payments, totals, refunds), auth
   boundaries (login, session, JWT, permissions), data integrity
   (mutations that can't be rolled back), security boundaries.
2. **Core user flows** — whatever the LLM instructions or README describe
   as the app's primary purpose. Read those for signals on what matters
   most.
3. **High-leverage modules** — a tested module unblocks confidence in many
   dependents (e.g. an API client used by twenty call sites).
4. **🟡 → ✅ wins** — items where one small test would flip the marker.
   Cheap, definite progress; surface them even when not critical.
5. **Secondary features** — user-facing functionality outside the core
   flow.
6. **Display-only code** — leaf UI components, formatters, simple
   serialisers, and other code with no logic of its own. Lowest
   priority unless it sits on a critical-flow path.

Within a band, prefer files that:
- Have clear, named failure modes in the code (early returns, throws,
  validation guards) — they're easy to test exhaustively.
- Sit on the critical path you identified in §2.

### 6. Report and offer

Present the top 5–10 gaps as a ranked list. For each:

- **File** — path.
- **Why it ranks here** — one sentence tying it to a heuristic from §5.
- **Suggested test cases** — 2–4 success cases and 2–4 failure cases,
  inferred from reading the file. Phrase as behaviours
  (`"refuses to add an item when the cart is locked"`), not assertions.

Close with a recommendation: "I suggest starting with X because …" and
offer to proceed. If the user picks one, hand off to
`test-coverage-fix.prompt.md` with the chosen target.

## Scope discipline

- This is a **read-only audit.** Do not write tests, modify source, or
  create files during this prompt. The user decides what to act on.
- Do not create a "strategy document" or persist findings to disk unless
  the user explicitly asks. Audits are designed to be re-runnable from a
  clean slate; persisting them invites drift.
- Do not propose CI / tooling changes (test runners, coverage thresholds,
  CI gates) inside the ranking — those are infrastructure decisions and
  need separate agreement. You may note them at the end as observations.

## Reporting

End with a short summary:
- LLM instruction files read.
- Test framework + baseline (count + runtime).
- Total testable files, covered vs. partial vs. missing.
- The ranked top-N gap list.
- Your recommended starting point.
