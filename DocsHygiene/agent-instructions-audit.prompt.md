---
description: Audit the project's agent / LLM instruction files for vague rules, missing examples, drifted compliance, and mechanical-enforcement opportunities.
related: [agent-instructions-fix]
---

# Audit agent instructions

Read the project's agent / LLM instruction files (CLAUDE.md, AGENTS.md,
Copilot instructions, Cursor rules, and any nested variants) and audit
them: which rules are vague, missing concrete examples, no longer
followed by the code, contradictory, or candidates for mechanical
enforcement. Output a triaged list of doc fixes the companion
`agent-instructions-fix` playbook can action.

This is the meta-prompt the other audits hint at. When an audit
catches a rule the codebase didn't follow, the real fix may be to
sharpen the rule's wording — not just the code.

## Inputs

Scope is the load-bearing input. If the user hasn't named a scope,
**ask before starting**. Offer them three options:

1. **Auto-detect (recommended)** — discover every agent instruction
   file in the repo and audit them all, with a cross-file pass for
   contradictions. The user does not need to specify which file.
2. **Name a specific file or set** — e.g. just `CLAUDE.md`, just
   `.cursor/rules/`, just the nested `CLAUDE.md` files under a
   specific package. Use this when the user wants focused attention.
3. **Pick one primary** — start with the root `CLAUDE.md` if present,
   then `AGENTS.md`, then any nested instruction files closer to
   recent code activity. State your choice before proceeding. Use
   this when the user wants a faster, narrower read.

If only one instruction file exists, skip the question and audit it.

## Step 1 — Locate instruction files

Find every file matching any of:

- `CLAUDE.md` at the root and any nested `CLAUDE.md` files.
- `AGENTS.md` at the root and any nested `AGENTS.md` files.
- `.github/copilot-instructions.md`.
- `.github/instructions/**/*.md`.
- `.cursor/rules/**/*` (or `.cursorrules`).
- Any other `*.md` file at the repo root whose name matches a known
  agent-instruction convention (e.g. `GEMINI.md`, `WINDSURF.md`).

List which files exist and which you'll be auditing. If multiple files
are present, audit **all** of them — the cross-file pass is where
contradictions surface, and that's part of the value.

If none exist, stop — there's nothing to audit. Surface that and
recommend starting from a minimal `CLAUDE.md` or `AGENTS.md` skeleton
(language, naming, testing, contribution).

## Step 2 — Enumerate rules

For each rule in each file, extract:

- The rule's text (paraphrased to one line is fine).
- Its source file and category / section heading (Language, TypeScript,
  Testing, Naming, etc.).
- Whether it has a concrete example (`color` not `colour`) or is
  abstract ("use sensible names").

Number the rules sequentially within each file so the report can
refer to them. Format: **Rule N (in `<file>`)**. Examples:
"Rule 3 (in `CLAUDE.md`)", "Rule 1 (in `AGENTS.md`)". The file is
parenthetical so the rule numbers read naturally in prose.

## Step 3 — Audit each rule

For each rule, evaluate:

1. **Clarity** — could a new contributor (or an LLM) understand
   and apply it without context? "Use idiomatic code" fails. "Use
   arrow functions over `function` declarations except for
   hoisted named exports" passes.

2. **Concreteness** — is there an example or a counter-example?
   Rules without examples are at risk; flag and propose one.

3. **Compliance** — sample 5–10 files relevant to the rule's
   scope. How often is the rule actually followed?
   - **Strong** (≥90%): the rule is enforced (mechanically or
     culturally). Worth keeping as-is.
   - **Mixed** (50–89%): the rule has drifted. Either the rule is
     unrealistic or enforcement has lapsed.
   - **Weak** (<50%): either the rule is wrong (codebase has
     superseded it) or it's been forgotten. Recommend retire,
     reword, or re-enforce.

4. **Mechanical enforcement** — could this rule be enforced by a
   hook (Claude Code, pre-commit), an ESLint / ruff / golangci
   rule, or a CI check? If yes, note the mechanism. Mechanical
   enforcement is stronger than doc-only.

5. **Conflict** — does this rule contradict another rule in the
   same file or a different instruction file? Cross-file
   contradictions (e.g. `CLAUDE.md` says one thing, `AGENTS.md`
   says another) are especially worth surfacing. Does it
   contradict the actual code in a way that suggests it's been
   superseded?

## Step 4 — Identify gaps

Read 3–5 recent merged PRs (`gh pr list --state merged --limit 5`,
then `gh pr view <n>` on each). For each, ask: did the diff
conform to the documented rules, or did it introduce a pattern
the docs don't mention? Patterns recurring across multiple PRs
without documentation are missing rules — the project has a
convention, it just hasn't written it down.

## Step 5 — Report

Output to `docs/audits/agent-instructions.md`. Structure:

```
# Agent instructions audit

Date: <today>
Files audited: <list>
Rules enumerated: <count>

## Rule-by-rule findings

### Rule 1 (in `CLAUDE.md`) — Section: <heading> — <one-line text>

- Clarity: ✅ / ⚠️ (proposed rewording: "<text>")
- Concreteness: ✅ / ⚠️ (proposed example: "<example>")
- Compliance: Strong (10/10) / Mixed (6/10) / Weak (2/10)
- Mechanically enforceable: yes via <mechanism> / no
- Conflict: none / conflicts with Rule 3 (in `AGENTS.md`): <details>

**Suggested action**: keep / reword / add example / enforce
mechanically / retire

### Rule 2 (in `CLAUDE.md`) — ...

### Rule 1 (in `AGENTS.md`) — ...

## Missing rules (observed but undocumented)

Patterns observed in code or recent PRs that aren't documented:

- <pattern> — observed in <files / PRs> — recommend adding under
  <section> in <file> as: "<proposed rule text>"

## Cross-file contradictions

Rules in different instruction files that disagree:

- Rule N (in `<file-a>`) says X; Rule M (in `<file-b>`) says Y.
  Recommend: <resolution>.

## Mechanical enforcement opportunities

Rules currently doc-only that could be moved to lint / hooks:

- Rule N (in `<file>`) — "<text>" — propose: <hook / ESLint rule /
  pre-commit check>

## Actions summary

Index of rule findings by suggested action — the fix playbook reads
this to filter what to action per category. Every rule appears
exactly once; `keep` is a count, not a list.

- **Reword**: Rule N (in `<file>`), Rule M (in `<file>`), ...
- **Add example**: Rule N (in `<file>`), ...
- **Retire**: Rule N (in `<file>`), ...
- **Enforce mechanically**: Rule N (in `<file>`) → via <mechanism>, ...
- **Keep**: <count> rules unchanged

Missing rules (Step 4) and cross-file contradictions are listed in
their own sections above and have their own fix categories — the
fix actions those separately and doesn't need them indexed here.

## Summary

- Rules in strong shape: <n>
- Rules needing rewording / examples: <n>
- Rules drifted (compliance Mixed or Weak): <n>
- Missing rules suggested: <n>
- Cross-file contradictions: <n>
- Mechanical enforcement opportunities: <n>
```

## Constraints

- Do not modify any instruction files. Output proposed changes;
  let the user accept or reject each.
- Be specific. "Make this rule clearer" is rejected; propose the
  new wording.
- If a rule has Strong compliance, that's worth noting — not
  every rule needs a fix. Don't manufacture work.
- When suggesting mechanical enforcement, point at a concrete
  mechanism (a specific hook event, a specific ESLint rule name)
  rather than "enforce this somehow."
- Don't audit rules you can't verify from the code (e.g. "every
  PR must have a linked issue" — that's a process rule, not a
  code rule). Note them as out-of-scope for this audit.
