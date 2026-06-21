# DocsHygiene

Audits that keep the project's documentation honest, paired with a
narrow-scope fix prompt that actions the drift findings.

| Prompt | What it does |
|---|---|
| `agent-instructions-init.prompt.md` | Generates a well-formed agent / LLM instructions file from scratch, derived from the actual codebase and recent PRs (not boilerplate). Writes a canonical `AGENTS.md` (default) and points each tool the project uses (`CLAUDE.md`, Cursor rules, Copilot instructions) at it, so there's a single source of truth. If a hand-authored file already exists, switches to merge/augment mode instead of clobbering. Leaves files for review; does not commit. |
| `agent-instructions-audit.prompt.md` | Read-only audit of the project's agent / LLM instruction files (`CLAUDE.md`, `AGENTS.md`, Cursor rules, Copilot instructions, and any nested variants). Auto-detects which files are present and audits them all. Flags vague rules, missing examples, rules the code no longer follows, conflicting rules across files, and rules that could move from doc-only to mechanical enforcement (hooks, lint, pre-commit). |
| `agent-instructions-fix.prompt.md` | Actions findings from the agent-instructions audit. Rewords vague rules, adds concrete examples, codifies undocumented patterns, resolves cross-file contradictions, retires superseded rules. Commits per category. Mechanical enforcement (adding the hook / lint rule / pre-commit check) is opt-in via flag — by default the fix touches docs only. Does not push. |
| `doc-code-drift-audit.prompt.md` | Read-only audit. Documentation versus the code: install / run commands that don't match the manifest, env vars renamed since the doc was written, function signatures that shifted, file paths that no longer exist, example snippets that no longer compile against the current API. |
| `doc-code-drift-fix.prompt.md` | Actions findings from the drift audit. Defaults to `hard` drifts only (provably wrong docs); updates docs to match current code, verifies links / snippets, commits locally per drift type. Does not push. |
| `planning-doc-drift-audit.<variant>.prompt.md` | Read-only audit of *planning* drift — decision / scope / architecture contradictions between an external planning doc (e.g. project wiki) and the issues + commits that have landed since. Distinct from `doc-code-drift-audit`, which targets mechanical drift in repo-local docs. First variant: `.github-wiki`. |
| `planning-doc-drift-fix.<variant>.prompt.md` | Actions findings from the planning-doc drift audit. Edits the external doc, commits per drift category in the doc's own version system, appends to an in-doc CHANGELOG. Local commits only — never pushes. First variant: `.github-wiki`. |

## Why this folder exists

Documentation rots silently. Linters check the code; nothing checks
whether the docs still describe it. These prompts close that gap.

The agent-instructions prompts form a lifecycle: `agent-instructions-init`
creates the file when none exists, `agent-instructions-audit` grades it as
it ages, and `agent-instructions-fix` actions the audit's findings.

Pair them with the broader principle the root README spells out:
the prompts in this repo treat documentation as a *feedback loop*,
not just static reference. Run `agent-instructions-audit` when you find
an audit catching gaps the docs *could* have prevented, then
`agent-instructions-fix` to action the rewordings, missing rules, and
contradiction resolutions. Run `doc-code-drift-audit` after a milestone
where many APIs moved, then `doc-code-drift-fix` to action the hard
drifts.

`doc-code-drift-*` and `planning-doc-drift-*` are intentionally split.
The former catches *mechanical* drift (a renamed env var, a moved
file path, a stale example) in docs that live inside the repo. The
latter catches *intent* drift (a decision reversed, a feature
descoped, an architecture renamed) in planning docs that live in
external systems — project wikis, design pages, RFC docs. Reach for
whichever matches the drift you suspect; they don't overlap.

The `planning-doc-drift` family uses a **sibling-clone convention**:
the external doc lives at `../<repo>.wiki/` next to the main repo,
matching GitHub's default `git clone <wiki-url>` output. Future
variants (Confluence, Notion, Obsidian) will inherit the same
"adjacent on disk, never `/tmp`" shape so the user can edit the
doc by hand at any point and the playbook can find it
deterministically.

## Invocation

See the [root README](../README.md#invocation) for the three
supported patterns and the assumed tool capabilities. Both prompts
need file read and shell execution; git is optional.
