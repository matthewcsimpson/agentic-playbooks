# agentic-playbooks

A collection of prompts for agentic coding tools (Claude Code, Codex,
and similar) that have filesystem access, shell execution, and git.

Prompts are grouped into folders by purpose. Each folder has its own
README explaining what's inside and how the prompts there fit together.

## Invocation

The canonical prompts are plain markdown files under each collection
folder (e.g. `AuditTesting/test-coverage-audit.prompt.md`). A
generator emits a single `/playbook` router slash command for each
supported tool — type the slug, the router dispatches.

```
/playbook <slug> [optional scope or target]
/playbook --list              # full catalog with descriptions
/playbook --help              # short usage + slug list
```

For multi-variant families (e.g. `dependency-audit` has -dotnet /
-npm / -python / -swift / -terraform variants), pass just the family
name. The agent inspects the working directory to pick the matching
stack; if it's ambiguous, it asks before running.

### One-time setup

```bash
git clone https://github.com/matthewcsimpson/agentic-playbooks.git
cd agentic-playbooks
python3 tools/generate-adapters.py --install-global    # Claude + Codex, any project
```

That writes:

- `~/.claude/commands/playbook.md` — Claude Code router slash command.
- `~/.claude/skills/<slug>/SKILL.md` × 50 — auto-trigger by description
  match (hidden from the `/` picker via `user-invocable: false`).
- `~/.codex/prompts/playbook.md` — Codex CLI router slash command.
- `~/.codex/AGENTS.md` — Codex CLI user-level catalog (sentinel-bounded;
  any pre-existing content is preserved).

Re-run `--install-global` after `git pull` to refresh. Also re-run if
you move the clone to a different path — the global install bakes in
absolute paths to the source prompts. `--uninstall-global` removes
everything it wrote.

For Cursor and GitHub Copilot Chat (neither has a user-level install
path), use `--install-project <path>` to write a router with absolute
paths into a specific target project — see the Cursor and Copilot
sections below.

### Claude Code

After `--install-global`, from any project:

```
/playbook --list                              # see every available playbook
/playbook --help                              # short usage
/playbook test-coverage-audit
/playbook test-coverage-fix for the api routes
/playbook dependency-audit
/playbook stack-upgrade-nextjs
```

- **Discovery** — `/playbook --list` prints the full catalog with
  descriptions; `/playbook --help` (or `/playbook` with no slug) prints
  short usage + the slug list.
- **Exact slug** (`test-coverage-audit`, `dependency-audit-npm`,
  `db-migration-audit-prisma`, …) → dispatches directly.
- **Family name** (`dependency-audit`, `stack-upgrade`,
  `db-migration-audit`, `post-milestone-audit`) → Claude detects the
  stack from the working directory and runs the matching variant.
- **Usage-driven families** (`post-milestone-smoke-test`,
  `audit-duplicate-issues`, `planning-doc-drift-audit`,
  `planning-doc-drift-fix`) → can't be detected from the file tree;
  Claude asks which variant applies (smoke: api / cli / ios / web;
  duplicate-issues: github / clickup; planning-doc-drift: github-wiki).
- **Natural language** still works — say "audit my test coverage" and
  the matching skill auto-triggers by description.

Without `--install-global`, you can still use Claude Code from inside
this repo — `.claude/commands/playbook.md` is checked in.

### Codex CLI

```
/prompts:playbook test-coverage-audit
/prompts:playbook dependency-audit
```

The `/prompts:` prefix is Codex's namespace for user prompts —
mandatory, not optional. Same dispatch rules as above.

If your Codex version doesn't read `~/.codex/prompts/`, fall back to
the project-local `AGENTS.md` catalog (auto-read when Codex launches
in this directory) and ask by name: "run the `test-coverage-audit`
playbook".

### Cursor

Cursor 1.6+ reads slash commands from `.cursor/commands/<name>.md`.
Unlike Claude Code (`~/.claude/`) and Codex CLI (`~/.codex/`), Cursor
has **no stable user-level path** — the router file must live inside
each project you want to invoke `/playbook` from.

**Easiest way to try it — open this repo in Cursor.** The router is
already checked in at `.cursor/commands/playbook.md`. With no extra
setup, from the Cursor chat panel:

```
/playbook --list
/playbook test-coverage-audit
/playbook dependency-audit
```

That works because the router's relative paths
(`../../AuditTesting/...`) resolve correctly inside this repo's tree.

**Using `/playbook` from another project.** Run
`--install-project <path>` against the target — it writes a Cursor
router with absolute paths back to this repo:

```bash
python3 /path/to/agentic-playbooks/tools/generate-adapters.py \
  --install-project /path/to/target-project
```

That produces `<target>/.cursor/commands/playbook.md` (and the Copilot
equivalent — see the next section). Open that project in Cursor and
`/playbook` will resolve correctly.

Re-run `--install-project` after `git pull` in the playbooks repo, or
if you move the playbooks clone — the router carries baked-in
absolute paths. To remove it, delete
`<target>/.cursor/commands/playbook.md`.

A bare copy of the checked-in `.cursor/commands/playbook.md` into
another project will **not** work — it uses paths relative to this
repo's layout (`../../AuditTesting/...`) which won't resolve from
elsewhere. Use `--install-project` instead.

### GitHub Copilot Chat (VS Code)

VS Code Copilot Chat reads `.github/prompts/<name>.prompt.md` as a
slash command. There's no user-level install path, so — same as
Cursor — the router has to live inside each project.

**To use `/playbook` from a target project**, run
`--install-project <path>` against it (the same command also handles
Cursor in one shot):

```bash
python3 /path/to/agentic-playbooks/tools/generate-adapters.py \
  --install-project /path/to/target-project
```

That writes `<target>/.github/prompts/playbook.prompt.md` with
absolute paths back to this repo. Then in Copilot Chat:

```
/playbook test-coverage-audit
/playbook dependency-audit
```

`--install-project` deliberately does **not** touch
`.github/copilot-instructions.md` in the target project — many
projects have hand-written Copilot instructions and we won't clobber
them. If you want the natural-language catalog there too, copy this
repo's `.github/copilot-instructions.md` manually and edit the paths.

### Without filesystem access (paste into chat)

Open the prompt file, copy its contents, paste into the agent chat, add
your target / context underneath. Works for any tool, no install
required.

### Copy a prompt into a target project

If you want a specific prompt versioned alongside the project it
audits, copy the `.prompt.md` (and its `core/` sibling if it's a
variant) into that project's `prompts/` folder. The global adapters
aren't needed when the prompt travels with the target project.

## Target tools

These prompts assume an agentic CLI with file read, shell execution,
and git (branch + commit). Designed against Claude Code and Codex CLI;
anything with the same capability set should work.

**Personally verified by the maintainer:** Claude Code, Cursor (1.6+),
GitHub Copilot Chat (VS Code). The Codex CLI router is generated from
the same template and covered by the unit tests + drift check, but
hasn't been exercised end-to-end by the maintainer — if you hit a
Codex-specific quirk, please file an issue.

## A note on token usage

These playbooks are deliberately thorough — they read across a repo,
chase references, and produce structured reports. Expect them to be
**token-heavy** compared to a one-shot prompt. A full
`post-milestone-audit`, `dependency-audit`, or `stack-upgrade` run
on a non-trivial repo can consume a large fraction of a context
window and (on metered plans) a non-trivial chunk of usage.

Practical tips to keep the cost in check:

- **Scope the run.** Pass a target ("audit just `src/api/`",
  "dependency-audit for the `web/` workspace only") instead of
  letting the prompt sweep the whole repo.
- **Run audits before fixes.** Read-only audits are cheaper than the
  follow-up fix pass — review the audit first, then action only the
  findings worth fixing.
- **Prefer the smallest model that works.** Many of the read-only
  audits work well on a mid-tier model; reserve the top tier for the
  prompts that need deeper reasoning (e.g. `regression-bisect`,
  `duplicate-logic-audit`).
- **Watch the context window.** On very large repos, expect to
  `/compact` (or the equivalent) once or twice through a long audit.

## Best with documented conventions

Most prompts here look for project-specific LLM instructions —
`CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`,
`.cursor/rules/**` — to understand the conventions they should
enforce or honour. The audit prompts use those rules as the *spine*
of the audit; the test-writing prompts read them to match local
style rather than guess.

A repo with no LLM instructions still works — the prompts fall back
to generic categories — but the project-specific spine collapses. A
short, opinionated `CLAUDE.md` is usually a higher-leverage
investment than tuning the prompts themselves.

If you find an audit catching gaps that documented rules *could*
have prevented, add the rule and re-run. Treat the prompts as a
feedback loop on your convention documentation, not just on the
code.

## Current contents

### `AuditTesting/`

A pair of prompts for working on a repo's test suite.

- `test-coverage-audit.prompt.md` — read-only survey that ranks the
  most important coverage gaps and suggests cases for each.
- `test-coverage-fix.prompt.md` — takes one target from the audit (or
  one you name directly) and writes tests for it, matching the
  project's existing conventions.

See [`AuditTesting/README.md`](AuditTesting/README.md) for the full
workflow.

### `MilestoneSmoke/`

Behavioural smoke-test prompts that run after a milestone tag is
cut. Variants target different runtime surfaces. Run this before
`MilestoneAudit/` so behavioural regressions surface before
static drift.

- `post-milestone-smoke-test.web.prompt.md` — drives the
  milestone's flows through a browser MCP. Web apps.
- `post-milestone-smoke-test.api.prompt.md` — exercises HTTP
  endpoints against a running API instance with `curl` /
  `httpie`.
- `post-milestone-smoke-test.cli.prompt.md` — invokes CLI
  commands with concrete args; observes exit code / stdout /
  stderr / side effects.
- `post-milestone-smoke-test.ios.prompt.md` — drives an iOS
  app through the iOS Simulator via Maestro or XCUITest.
- `core/post-milestone-smoke-test.core.prompt.md` — shared
  scaffold (not invoked directly).
- `post-milestone-smoke-fix.prompt.md` — actions ❌ Fail flows
  from the smoke report. Commits locally only. Stack-agnostic.

See [`MilestoneSmoke/README.md`](MilestoneSmoke/README.md).

### `MilestoneAudit/`

Static-drift audit prompts plus the follow-up fix. Pair with
`MilestoneSmoke/`. Filenames carry a stack tag (`.nextjs`,
`.nestjs`, `.python`, `.dotnet`, `.react-native`, `.swift`,
`.terraform`) when a prompt is tied to a particular stack.

- `post-milestone-audit.nextjs.prompt.md` — Next.js +
  TypeScript front-end / SSR.
- `post-milestone-audit.nestjs.prompt.md` — NestJS backend
  services.
- `post-milestone-audit.python.prompt.md` — Python (FastAPI /
  Django / Flask / CLI / library).
- `post-milestone-audit.dotnet.prompt.md` — .NET / C# (ASP.NET
  Core, EF Core, worker services).
- `post-milestone-audit.react-native.prompt.md` — React Native
  / Expo (cross-platform mobile, JS layer).
- `post-milestone-audit.swift.prompt.md` — Swift / Xcode
  (native iOS / macOS / watchOS / tvOS).
- `post-milestone-audit.terraform.prompt.md` — Terraform /
  OpenTofu infrastructure-as-code.
- `core/post-milestone-audit.core.prompt.md` — shared scaffold
  (not invoked directly).
- `post-milestone-fix.prompt.md` — actions the audit findings
  matching the labels and sections you specify. Commits locally
  only. Stack-agnostic.

See [`MilestoneAudit/README.md`](MilestoneAudit/README.md) for
the full workflow, how to pick an audit variant, and how to add
a new one.

### `StackUpgrade/`

Per-stack version-bump planners. Reads upstream release notes,
scans the repo for affected patterns, surveys available codemods,
and produces a risk-ranked migration plan. Pair with
`MilestoneAudit/`'s `post-milestone-fix.prompt.md` to action the
plan.

- `stack-upgrade.nextjs.prompt.md` — Next.js version bumps.
- `stack-upgrade.nestjs.prompt.md` — NestJS major upgrades.
- `stack-upgrade.python.prompt.md` — Python language version
  (3.x → 3.y).
- `stack-upgrade.dotnet.prompt.md` — .NET TFM (6 → 8, 8 → 9, …).
- `stack-upgrade.react-native.prompt.md` — React Native / Expo
  SDK bumps.
- `stack-upgrade.swift.prompt.md` — Swift / Xcode / iOS SDK.
- `stack-upgrade.terraform.prompt.md` — Terraform / OpenTofu CLI
  + major provider bumps.
- `core/stack-upgrade.core.prompt.md` — shared scaffold (not
  invoked directly).

See [`StackUpgrade/README.md`](StackUpgrade/README.md).

### `PRWorkflow/`

Pre-merge checks for a pull request branch.

- `pre-pr-checklist.prompt.md` — runs the project's check suite,
  scans the diff for things reviewers can't easily catch (leftover
  debug, focus markers, secrets, unjustified suppressions, missing
  tests), and drafts a PR body. Does not push or open the PR.

See [`PRWorkflow/README.md`](PRWorkflow/README.md).

### `DBMigrationAudit/`

Pre-merge safety audit for database migration files, paired with
fix variants that action the audit findings. Catches
unsafe-under-production-load operations: NOT NULL on a populated
table, non-concurrent index on a hot table, FK without an index,
renames that break a rolling deploy.

Audits:

- `db-migration-audit.prisma.prompt.md` — Prisma migrations.
- `db-migration-audit.typeorm.prompt.md` — TypeORM migrations.
- `db-migration-audit.alembic.prompt.md` — Alembic migrations.
- `db-migration-audit.ef-core.prompt.md` — EF Core migrations.

Fixes (`db-migration-fix-<orm>`) action audit findings in the same
migration files — add `CONCURRENTLY`, split schema+backfill+NOT-NULL
into three migrations, replace `DROP+ADD` rename with `RENAME COLUMN`,
etc. Verify via the ORM's dry-run / script command, commit per
migration, local only.

- `db-migration-fix.prisma.prompt.md`
- `db-migration-fix.typeorm.prompt.md`
- `db-migration-fix.alembic.prompt.md`
- `db-migration-fix.ef-core.prompt.md`

Shared cores (`core/db-migration-audit.core.prompt.md`,
`core/db-migration-fix.core.prompt.md`) hold the unsafe-operation
catalogue, severity model, edit catalogue, and commit discipline.
Not invoked directly.

See [`DBMigrationAudit/README.md`](DBMigrationAudit/README.md).

### `IssueWorkflow/`

Issue-tracker maintenance. Filenames carry a platform tag
(`.github`, `.clickup`) — variants for other trackers (GitLab,
Linear, Jira) would sit alongside.

- `audit-duplicate-issues.github.prompt.md` — GitHub variant.
  Surveys open issues for duplicates, clusters them, classifies,
  and recommends an action per cluster. Asks for the target
  `OWNER/REPO` at the start of the run. Stops for confirmation
  before any closure or edit.
- `audit-duplicate-issues.clickup.prompt.md` — ClickUp variant.
  Audits a List or Folder via the REST API. Asks scope (List or
  Folder) and identifier (name or ID) at the start. Requires
  `CLICKUP_API_TOKEN`. Stops for confirmation before any closure
  or edit.
- `core/audit-duplicate-issues.core.prompt.md` — shared scaffold
  (not invoked directly).

See [`IssueWorkflow/README.md`](IssueWorkflow/README.md).

### `Refactoring/`

Read-only audits that surface refactor opportunities, paired with
narrow-scope fix prompts that action the findings.

- `dead-code-audit.prompt.md` — finds exports / components / env
  vars / branches that aren't used. Classifies Hard / Likely /
  Conditionally dead. Pairs with the project's static tool when
  one is configured.
- `dead-code-fix.prompt.md` — actions the in-scope findings from
  the dead-code audit. Defaults to `Hard dead` only; verifies the
  build after each deletion. Commits locally; does not push.
- `duplicate-logic-audit.prompt.md` — finds functions / modules /
  components doing the same job under different names; clusters
  and recommends a winner per cluster.
- `duplicate-logic-fix.prompt.md` — actions user-selected clusters
  from the duplicate-logic-audit report. Defaults to `risk:low` and asks
  which to action; verifies the build between each cluster.
  Commits locally; does not push.

See [`Refactoring/README.md`](Refactoring/README.md).

### `DependencyAudit/`

A bundled dependency audit — outdated versions, known
vulnerabilities, unused / missing declarations, lockfile drift, and
duplicate versions — in one prioritised report. Paired with fix
variants that action the audit per category (vuln fixes, patch /
minor / major bumps, removals, lockfile re-resolution). Variants are
ecosystem-specific because the commands and manifest shapes differ.

Audits:

- `dependency-audit.npm.prompt.md` — npm / pnpm / yarn.
- `dependency-audit.python.prompt.md` — pip / uv / Poetry / pdm.
- `dependency-audit.dotnet.prompt.md` — NuGet.
- `dependency-audit.swift.prompt.md` — SPM + CocoaPods.
- `dependency-audit.terraform.prompt.md` — provider / module
  versions.

Fixes (`dependency-fix-<ecosystem>`) default to `vulnerable` +
`outdated-patch` + lockfile-drift; majors are opt-in and isolated
per commit. Verify build + tests between each category, local
commits only.

- `dependency-fix.npm.prompt.md`
- `dependency-fix.python.prompt.md`
- `dependency-fix.dotnet.prompt.md`
- `dependency-fix.swift.prompt.md`
- `dependency-fix.terraform.prompt.md`

Shared cores (`core/dependency-audit.core.prompt.md`,
`core/dependency-fix.core.prompt.md`) hold the audit framework, edit
catalogue, and constraints. Not invoked directly.

See [`DependencyAudit/README.md`](DependencyAudit/README.md).

### `ObservabilityAudit/`

Read-only audit of how the codebase logs, traces, and surfaces
errors at runtime, paired with a narrow-scope fix prompt that
actions the findings. Stack-agnostic — the questions (swallowed
errors, missing correlation IDs, log-level mismatches, PII in
logs, dishonest health checks) are universal.

- `observability-audit.prompt.md` — single stack-agnostic audit.
- `observability-fix.prompt.md` — actions audit findings. Default
  scope is `sensitive-data` + `log-levels` (mechanical, low blast
  radius); `error-handling`, `correlation`, `tracing`, `metrics`,
  and `health-checks` are opt-in because they change runtime
  behaviour. Sensitive-data fixes always commit ahead of other
  categories. Commits per category. Does not push.

See [`ObservabilityAudit/README.md`](ObservabilityAudit/README.md).

### `SEOAudit/`

Read-only SEO audit for a web app, paired with a narrow-scope fix
prompt that actions the findings. Crawlability, on-page metadata,
structured data, semantic HTML, images, URL structure, i18n,
static performance heuristics. Stack-agnostic — the audit detects
the framework (Next.js, Nuxt, Remix, SvelteKit, Astro, static
generators, CSR-only SPA) and adapts its declaration sites.

- `seo-audit.prompt.md` — single stack-agnostic audit.
- `seo-fix.prompt.md` — actions audit findings. Default scope is
  `crawlability` + `metadata` + `canonical` + `noindex-leakage`;
  structured data, images, and performance categories are opt-in.
  Commits per category. Does not push.

Static-only. Core Web Vitals, rich-result eligibility, and
crawler-visible HTML in CSR apps need a runtime probe — pair with
`MilestoneSmoke/post-milestone-smoke-test.web.prompt.md` or a manual
Lighthouse / Search Console pass.

See [`SEOAudit/README.md`](SEOAudit/README.md).

### `DocsHygiene/`

Audits that keep documentation honest.

- `agent-instructions-audit.prompt.md` — auto-detects every agent /
  LLM instruction file in the repo (CLAUDE.md, AGENTS.md, Cursor
  rules, Copilot instructions, nested variants) and audits them all
  for vague rules, missing examples, drifted compliance, cross-file
  contradictions, and mechanical-enforcement opportunities.
- `agent-instructions-fix.prompt.md` — actions findings from the
  agent-instructions audit. Rewords vague rules, adds concrete
  examples, codifies undocumented patterns, resolves cross-file
  contradictions, retires superseded rules. Commits per category.
  Mechanical enforcement (adding the hook / lint rule / pre-commit
  check) is opt-in via flag. Does not push.
- `doc-code-drift-audit.prompt.md` — finds where READMEs / docs / inline
  comments disagree with the actual code.
- `doc-code-drift-fix.prompt.md` — actions findings from the
  drift audit. Defaults to `hard` drifts only; updates docs to match
  current code, verifies links / snippets, commits locally per drift
  type. Does not push.
- `planning-doc-drift-audit.github-wiki.prompt.md` — GitHub Wiki
  variant. Read-only audit of *intent* drift: decision / scope /
  architecture contradictions between a project wiki and the issues
  + commits that have landed since. Expects the wiki sibling-cloned
  at `../<repo>.wiki/`. Distinct from `doc-code-drift-audit`, which
  catches mechanical drift in repo-local docs.
- `planning-doc-drift-fix.github-wiki.prompt.md` — GitHub Wiki
  variant. Actions findings from the planning-doc audit. Edits the
  sibling-cloned wiki, commits per drift category, appends to an
  in-wiki `CHANGELOG.md` page. Local commits only — never pushes.
- `core/planning-doc-drift-{audit,fix}.core.prompt.md` — shared
  scaffolds for the planning-doc-drift family (not invoked directly).

See [`DocsHygiene/README.md`](DocsHygiene/README.md).

### `Debugging/`

Active-loop debugging prompts (different shape from the audit
prompts elsewhere — these drive a workflow that converges on an
answer).

- `regression-bisect.prompt.md` — given last-known-good, symptom,
  and a reproduction, drives `git bisect` to the breaking commit
  and proposes a fix.

See [`Debugging/README.md`](Debugging/README.md).

## Contributing

Contributions are welcome — both new prompts and improvements to
existing ones.

### Conventions

- **File naming.** Prompt files use `<name>.prompt.md` in
  kebab-case (e.g. `test-coverage-audit.prompt.md`). Folder READMEs
  are plain `README.md`.
- **Folder organisation.** Group prompts by workflow domain (e.g.
  `AuditTesting/`, `MilestoneAudit/`), not by action verb. A new
  workflow domain gets its own folder with a `README.md` that
  explains the workflow and links any companion prompts.
- **Prompt structure.** Aim for the shape used by the existing
  prompts: a short purpose statement, inputs the user must supply,
  numbered steps, an output / report format, and a Constraints
  section that names the failure modes the prompt is defending
  against.
- **Be project-agnostic.** Don't name a specific framework,
  package manager, or repo unless the prompt is genuinely tied to
  one. Reach for the project's `CLAUDE.md` / `AGENTS.md` /
  `.cursor/rules/**` for project-specific rules at runtime instead
  of hard-coding them.

### Proposing a change

1. Open an issue describing the prompt or change you want to make.
   Quick agreement on scope up front saves rework.
2. Fork the repo or create a feature branch
   (`add-<thing>` / `improve-<thing>` / `docs-<thing>`).
3. Make the change. If you're adding a new prompt, add or update the
   folder `README.md` and the entry in the root `README.md` so it's
   discoverable.
4. **Regenerate adapters.** Every user-invocable `.prompt.md` carries
   YAML frontmatter (`description:` + optional `related:`). After
   adding or editing a prompt, run:

   ```
   python3 tools/generate-adapters.py
   ```

   Commit the regenerated `.claude/`, `.cursor/`, `.github/prompts/`,
   `.github/copilot-instructions.md`, and `AGENTS.md` alongside the
   prompt change. CI re-runs the generator with `--check` and fails on
   drift.

   If you added a new multi-variant family, add the variant token to
   `VARIANT_SIGNALS` in `tools/generate-adapters.py` with its detection
   signals — otherwise the generator fails fast on unknown variants.
5. Open a PR against `main` with a summary and a short test plan
   (e.g. "ran against repo X, audit produced N findings, top-3
   ranked first").
6. The PR will be merged once the change is reviewed. `main` is
   protected — PRs only, no direct pushes.

### Reporting a prompt that didn't work

If a prompt produced a bad result, open an issue with: the prompt
file, the project you ran it against (or a description if private),
the actual output, and what you expected. Concrete failure cases
are the most useful contribution — they're what sharpens these
prompts over time.

## License

MIT — see [`LICENSE`](LICENSE).

## Status

Stable at [v1.4.0](https://github.com/matthewcsimpson/agentic-playbooks/releases/tag/v1.4.0).
v1.4.0 adds three playbooks and broadens two existing ones. The new
`planning-doc-drift-audit` / `planning-doc-drift-fix` pair (first
variant: `.github-wiki`) surfaces decision / scope / architecture
drift between an external planning doc and the issues + commits that
have landed since — distinct from `doc-code-drift-*`, which targets
mechanical drift in repo-local docs. The wiki variant sibling-clones
to `../<repo>.wiki/`, refuses to push, and records each run in three
layers: per-category wiki commits, an in-wiki `CHANGELOG.md` page, and
the audit report in `docs/audits/`. The new `agent-instructions-fix`
completes the audit/fix pairing for `agent-instructions-audit` (the
last DocsHygiene audit that was still audit-only); it commits per
category (reword / add-example / codify-missing / resolve-contradiction
/ retire), supports an opt-in flag for mechanical enforcement
(adding the hook / ESLint rule / pre-commit check after a verify-the-
mechanism-fires step), and offers an optional `consolidate to one
canonical + pointer files` strategy with a static-tool-reader caveat.
The companion `agent-instructions-audit` got a tightened auto-generated
file skip rule (top-region + strict phrase, eliminates a meta-recursion
false positive) and a broadened enumeration covering Cline, Aider, and
modern `.mdc` Cursor rules. `test-coverage-audit` learned that
classification is per-file even when a folder contains a barrel
re-export, fixing a `#8`-style false positive. Catalog grew from 52 to
55 playbooks.

v1.2.1 was a patch release — doc-code-drift fixes against the repo
itself (stale skill count, dead `DependencyHygiene/` link, renamed-slug
examples in the router template).

v1.2.0 aligns every audit on the `<topic>-audit` / `<topic>-fix` pair
convention, adds 12 new fix variants (doc-code-drift-fix, four
db-migration-fix variants, five dependency-fix variants), and reframes
`audit-claude-md` as `agent-instructions-audit` with auto-detect across
every agent / LLM instruction file the project uses. Catalog grew from
39 to 50 playbooks.

v1.1.0 added the `/playbook` router and per-tool adapter generator,
four collection families (DependencyAudit, StackUpgrade,
ObservabilityAudit, DBMigrationAudit), and the first dead-code-fix /
duplicate-logic-fix action prompts.

New collections and stack variants continue to be added as new
project shapes come up — see the per-folder READMEs for guidance
on adding a variant.

### Recent renames

Four prompts were renamed to align with the `<topic>-audit` /
`<topic>-fix` pair convention used by `dead-code-audit` /
`dead-code-fix`. Old slugs no longer dispatch — update any
saved invocations:

| Old slug | New slug |
|---|---|
| `audit-test-coverage` | `test-coverage-audit` |
| `add-missing-tests` | `test-coverage-fix` |
| `duplicate-logic` | `duplicate-logic-audit` |
| `duplicate-code-fix` | `duplicate-logic-fix` |
| `audit-claude-md` | `agent-instructions-audit` |
| `doc-code-drift` | `doc-code-drift-audit` (plus new `doc-code-drift-fix`) |
| `db-migration-review-*` family | `db-migration-audit-*` (plus new `db-migration-fix-*` family) |
| `dependency-hygiene-*` family | `dependency-audit-*` (plus new `dependency-fix-*` family) |
