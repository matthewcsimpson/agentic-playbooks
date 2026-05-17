You are dispatching to a playbook from the agentic-playbooks library.

The user invoked `/playbook` followed by a slug and an optional
free-form instruction. Parse their message:

1. The first whitespace-delimited token after `/playbook` is the
   playbook **slug**.
2. Everything after that token is the **user scope** — pass it to the
   playbook as additional context / target.

## Dispatch rules

**(a) Help / list flags.** Handle these before any other dispatch:

- If the first token is `--help` or `-h`, **or** the user invoked
  `/playbook` with no arguments at all, print a short usage message
  followed by a compact list of available playbook slugs grouped
  into *single-variant* and *multi-variant families*. Mention the
  `--list` flag for full descriptions. Do not run any playbook.
- If the first token is `--list` or `-l`, print the **full catalog**
  below (every slug with its one-line description, grouped by
  single-variant and multi-variant families with their detection
  signals). Do not run any playbook.

Both flags render directly in the chat — no file is read, no work is
performed.

**(b) Exact slug match.** If the slug is an exact key in the catalog
below (e.g. `test-coverage-audit`, `dependency-audit-npm`), open
that file and follow it verbatim. Use the user scope as the target /
additional context the playbook should apply to.

**(c) Family match — auto-detect variant.** If the slug matches a
multi-variant family (e.g. `dependency-audit`, `stack-upgrade`),
inspect the working directory for the detection signals listed below.
Pick the variant whose signals match the project's stack and run that
variant's file. If multiple match (a polyglot repo), or none match,
list the candidate variants and ask the user which to run before
proceeding. Never silently pick a variant when the stack is ambiguous.

**(d) Usage-driven families — ask, never auto-detect.** Some
families' variants are not inferable from the file tree, so
auto-detection does not apply and rule (c) is not used. If the
user invokes one of these family names without a variant, present
a structured choice (`AskUserQuestion` in Claude Code, or an
equivalent numbered prompt in other harnesses) and dispatch to
the chosen variant. Do not offer an "auto-detect" option — there
is nothing reliable to detect against. The user can still bypass
the prompt by passing the full slug.

- **`post-milestone-smoke-test`** — ask which artifact they just
  shipped:
  - **Web app** — browser-driven flows (`post-milestone-smoke-test-web`)
  - **HTTP API** — REST / GraphQL / RPC over HTTP (`post-milestone-smoke-test-api`)
  - **CLI** — non-interactive binary or script (`post-milestone-smoke-test-cli`)
  - **iOS app** — native iOS via the Simulator (`post-milestone-smoke-test-ios`)

- **`audit-duplicate-issues`** — ask which tracker hosts the
  issues. The local file tree does not reliably indicate this
  (a repo can have `.github/` for Actions but use a different
  tracker for tickets), and silently picking the wrong tracker
  risks running closures against the wrong system:
  - **GitHub** — issues hosted on github.com (`audit-duplicate-issues-github`)
  - **ClickUp** — tasks in a ClickUp List or Folder (`audit-duplicate-issues-clickup`)

**(e) Unknown slug.** If the slug matches nothing, list the closest
catalog entries (by prefix match on the slug) and ask the user to
clarify. Do not guess. Suggest `/playbook --list` to see all options.

Always treat the linked `.prompt.md` body as authoritative — do not
summarise, paraphrase, or skip steps unless the playbook itself says to.

## Catalog — single-variant playbooks (dispatch directly)

- **`agent-instructions-audit`** — Audit the project's agent / LLM instruction files for vague rules, missing examples, drifted compliance, and mechanical-enforcement opportunities.
  File: `../../DocsHygiene/agent-instructions-audit.prompt.md`
  Related: `agent-instructions-fix`
- **`agent-instructions-fix`** — Action findings from agent-instructions-audit. Reword vague rules, add examples, codify undocumented patterns, resolve contradictions, retire superseded rules. Commit per category. Local commits only.
  File: `../../DocsHygiene/agent-instructions-fix.prompt.md`
  Related: `agent-instructions-audit`
- **`dead-code-audit`** — Find code that isn't used — exports never imported, components never rendered, branches never reached, env vars never read, permanently-on/off flags. Read-only.
  File: `../../Refactoring/dead-code-audit.prompt.md`
  Related: `dead-code-fix`, `duplicate-logic-audit`
- **`dead-code-fix`** — Action the in-scope findings from the most recent dead-code-audit report. Deletes dead code, verifies the build, commits locally per category. Does not push or open a PR.
  File: `../../Refactoring/dead-code-fix.prompt.md`
  Related: `dead-code-audit`
- **`doc-code-drift-audit`** — Read-only audit that finds places where documentation says one thing and the code does another (outdated commands, renamed env vars, drifted signatures, dead links).
  File: `../../DocsHygiene/doc-code-drift-audit.prompt.md`
  Related: `doc-code-drift-fix`
- **`doc-code-drift-fix`** — Action findings from doc-code-drift-audit. Update docs to match the code, verify links and snippets, commit per drift type. Local commits only.
  File: `../../DocsHygiene/doc-code-drift-fix.prompt.md`
  Related: `doc-code-drift-audit`
- **`duplicate-logic-audit`** — Find functions, modules, or components doing the same job under different names. Cluster, identify a winner, propose consolidations. Read-only — does not action.
  File: `../../Refactoring/duplicate-logic-audit.prompt.md`
  Related: `duplicate-logic-fix`, `dead-code-audit`
- **`duplicate-logic-fix`** — Action user-selected clusters from the most recent duplicate-logic-audit report. Migrate callers to the recommended winner, delete losers, verify, commit per cluster. Local commits only.
  File: `../../Refactoring/duplicate-logic-fix.prompt.md`
  Related: `duplicate-logic-audit`
- **`observability-audit`** — Read-only audit of how a codebase logs, traces, and surfaces errors — swallowed errors, missing correlation IDs, log-level mismatches, PII in logs, dishonest health checks.
  File: `../../ObservabilityAudit/observability-audit.prompt.md`
- **`post-milestone-fix`** — Action the in-scope findings from the most recent post-milestone audit report. Commits locally; does not push or open a PR.
  File: `../../MilestoneAudit/post-milestone-fix.prompt.md`
  Related: `post-milestone-audit-dotnet`, `post-milestone-audit-nestjs`, `post-milestone-audit-nextjs`, `post-milestone-audit-python`, `post-milestone-audit-react-native`, `post-milestone-audit-swift`, `post-milestone-audit-terraform`
- **`post-milestone-smoke-fix`** — Action ❌ Fail findings from the most recent post-milestone smoke-test report. Commits locally; does not push or open a PR.
  File: `../../MilestoneSmoke/post-milestone-smoke-fix.prompt.md`
  Related: `post-milestone-smoke-test-api`, `post-milestone-smoke-test-cli`, `post-milestone-smoke-test-ios`, `post-milestone-smoke-test-web`
- **`pre-pr-checklist`** — Before opening a pull request, run the project's check suite, scan the diff for things reviewers can't easily catch (debug code, secrets, missing tests), and draft a PR body.
  File: `../../PRWorkflow/pre-pr-checklist.prompt.md`
- **`regression-bisect`** — Given last-known-good, symptom, and reproduction steps, drive a disciplined git bisect to the breaking commit and propose a fix.
  File: `../../Debugging/regression-bisect.prompt.md`
- **`test-coverage-audit`** — Survey a repository's test coverage from scratch, identify the most important gaps, and present a ranked list of recommendations.
  File: `../../AuditTesting/test-coverage-audit.prompt.md`
  Related: `test-coverage-fix`
- **`test-coverage-fix`** — Write missing tests for a single component, module, or feature, matching the project's existing test conventions.
  File: `../../AuditTesting/test-coverage-fix.prompt.md`
  Related: `test-coverage-audit`

## Catalog — multi-variant collections (detect stack, then dispatch)

### `audit-duplicate-issues`

Variants:

- `audit-duplicate-issues-clickup` — ClickUp List or Folder
  File: `../../IssueWorkflow/audit-duplicate-issues.clickup.prompt.md`
  Detect: usage context — ask the user which variant applies.
- `audit-duplicate-issues-github` — GitHub-hosted issue tracker
  File: `../../IssueWorkflow/audit-duplicate-issues.github.prompt.md`
  Detect: usage context — ask the user which variant applies.

### `db-migration-audit`

Variants:

- `db-migration-audit-alembic` — Alembic (Python + SQLAlchemy migrations)
  File: `../../DBMigrationAudit/db-migration-audit.alembic.prompt.md`
  Detect: `alembic.ini`, `alembic/` directory
- `db-migration-audit-ef-core` — Entity Framework Core (.NET)
  File: `../../DBMigrationAudit/db-migration-audit.ef-core.prompt.md`
  Detect: `Microsoft.EntityFrameworkCore*` in a `*.csproj`, `Migrations/` folder under a .NET project
- `db-migration-audit-prisma` — Prisma
  File: `../../DBMigrationAudit/db-migration-audit.prisma.prompt.md`
  Detect: `prisma/schema.prisma`, `prisma` in `package.json`
- `db-migration-audit-typeorm` — TypeORM
  File: `../../DBMigrationAudit/db-migration-audit.typeorm.prompt.md`
  Detect: `typeorm` in `package.json`, `ormconfig.{js,json,ts}`

Related across the family: `db-migration-fix-alembic`

### `db-migration-fix`

Variants:

- `db-migration-fix-alembic` — Alembic (Python + SQLAlchemy migrations)
  File: `../../DBMigrationAudit/db-migration-fix.alembic.prompt.md`
  Detect: `alembic.ini`, `alembic/` directory
- `db-migration-fix-ef-core` — Entity Framework Core (.NET)
  File: `../../DBMigrationAudit/db-migration-fix.ef-core.prompt.md`
  Detect: `Microsoft.EntityFrameworkCore*` in a `*.csproj`, `Migrations/` folder under a .NET project
- `db-migration-fix-prisma` — Prisma
  File: `../../DBMigrationAudit/db-migration-fix.prisma.prompt.md`
  Detect: `prisma/schema.prisma`, `prisma` in `package.json`
- `db-migration-fix-typeorm` — TypeORM
  File: `../../DBMigrationAudit/db-migration-fix.typeorm.prompt.md`
  Detect: `typeorm` in `package.json`, `ormconfig.{js,json,ts}`

Related across the family: `db-migration-audit-alembic`

### `dependency-audit`

Variants:

- `dependency-audit-dotnet` — .NET / C#
  File: `../../DependencyAudit/dependency-audit.dotnet.prompt.md`
  Detect: `*.csproj`, `*.sln`, `global.json`, `Directory.Packages.props`
- `dependency-audit-npm` — JavaScript / TypeScript (npm / pnpm / yarn)
  File: `../../DependencyAudit/dependency-audit.npm.prompt.md`
  Detect: `package.json` *and* no Next.js / NestJS / React-Native indicators
- `dependency-audit-python` — Python
  File: `../../DependencyAudit/dependency-audit.python.prompt.md`
  Detect: `pyproject.toml`, `requirements.txt`, `Pipfile`, `setup.py`
- `dependency-audit-swift` — Swift / iOS / macOS
  File: `../../DependencyAudit/dependency-audit.swift.prompt.md`
  Detect: `Package.swift`, `*.xcodeproj/`, `*.xcworkspace/`
- `dependency-audit-terraform` — Terraform / OpenTofu
  File: `../../DependencyAudit/dependency-audit.terraform.prompt.md`
  Detect: `*.tf`, `*.tofu`

Related across the family: `dependency-fix-dotnet`

### `dependency-fix`

Variants:

- `dependency-fix-dotnet` — .NET / C#
  File: `../../DependencyAudit/dependency-fix.dotnet.prompt.md`
  Detect: `*.csproj`, `*.sln`, `global.json`, `Directory.Packages.props`
- `dependency-fix-npm` — JavaScript / TypeScript (npm / pnpm / yarn)
  File: `../../DependencyAudit/dependency-fix.npm.prompt.md`
  Detect: `package.json` *and* no Next.js / NestJS / React-Native indicators
- `dependency-fix-python` — Python
  File: `../../DependencyAudit/dependency-fix.python.prompt.md`
  Detect: `pyproject.toml`, `requirements.txt`, `Pipfile`, `setup.py`
- `dependency-fix-swift` — Swift / iOS / macOS
  File: `../../DependencyAudit/dependency-fix.swift.prompt.md`
  Detect: `Package.swift`, `*.xcodeproj/`, `*.xcworkspace/`
- `dependency-fix-terraform` — Terraform / OpenTofu
  File: `../../DependencyAudit/dependency-fix.terraform.prompt.md`
  Detect: `*.tf`, `*.tofu`

Related across the family: `dependency-audit-dotnet`

### `planning-doc-drift-audit`

Variants:

- `planning-doc-drift-audit-github-wiki` — GitHub repository wiki (planning docs)
  File: `../../DocsHygiene/planning-doc-drift-audit.github-wiki.prompt.md`
  Detect: usage context — ask the user which variant applies.

Related across the family: `planning-doc-drift-fix`, `doc-code-drift-audit`, `audit-duplicate-issues-github`

### `planning-doc-drift-fix`

Variants:

- `planning-doc-drift-fix-github-wiki` — GitHub repository wiki (planning docs)
  File: `../../DocsHygiene/planning-doc-drift-fix.github-wiki.prompt.md`
  Detect: usage context — ask the user which variant applies.

Related across the family: `planning-doc-drift-audit`, `doc-code-drift-fix`

### `post-milestone-audit`

Variants:

- `post-milestone-audit-dotnet` — .NET / C#
  File: `../../MilestoneAudit/post-milestone-audit.dotnet.prompt.md`
  Detect: `*.csproj`, `*.sln`, `global.json`, `Directory.Packages.props`
- `post-milestone-audit-nestjs` — NestJS backend
  File: `../../MilestoneAudit/post-milestone-audit.nestjs.prompt.md`
  Detect: `nest-cli.json` or `@nestjs/core` in `package.json`
- `post-milestone-audit-nextjs` — Next.js
  File: `../../MilestoneAudit/post-milestone-audit.nextjs.prompt.md`
  Detect: `next.config.{js,ts,mjs}` or `next` in `package.json`
- `post-milestone-audit-python` — Python
  File: `../../MilestoneAudit/post-milestone-audit.python.prompt.md`
  Detect: `pyproject.toml`, `requirements.txt`, `Pipfile`, `setup.py`
- `post-milestone-audit-react-native` — React Native / Expo
  File: `../../MilestoneAudit/post-milestone-audit.react-native.prompt.md`
  Detect: `app.json` with Expo/RN config, or `react-native` / `expo` in `package.json`
- `post-milestone-audit-swift` — Swift / iOS / macOS
  File: `../../MilestoneAudit/post-milestone-audit.swift.prompt.md`
  Detect: `Package.swift`, `*.xcodeproj/`, `*.xcworkspace/`
- `post-milestone-audit-terraform` — Terraform / OpenTofu
  File: `../../MilestoneAudit/post-milestone-audit.terraform.prompt.md`
  Detect: `*.tf`, `*.tofu`

Related across the family: `post-milestone-fix`

### `post-milestone-smoke-test`

Variants:

- `post-milestone-smoke-test-api` — HTTP API smoke test
  File: `../../MilestoneSmoke/post-milestone-smoke-test.api.prompt.md`
  Detect: usage context — ask the user which variant applies.
- `post-milestone-smoke-test-cli` — CLI binary smoke test
  File: `../../MilestoneSmoke/post-milestone-smoke-test.cli.prompt.md`
  Detect: usage context — ask the user which variant applies.
- `post-milestone-smoke-test-ios` — iOS Simulator smoke test
  File: `../../MilestoneSmoke/post-milestone-smoke-test.ios.prompt.md`
  Detect: usage context — ask the user which variant applies.
- `post-milestone-smoke-test-web` — Web app smoke test (browser MCP)
  File: `../../MilestoneSmoke/post-milestone-smoke-test.web.prompt.md`
  Detect: usage context — ask the user which variant applies.

### `stack-upgrade`

Variants:

- `stack-upgrade-dotnet` — .NET / C#
  File: `../../StackUpgrade/stack-upgrade.dotnet.prompt.md`
  Detect: `*.csproj`, `*.sln`, `global.json`, `Directory.Packages.props`
- `stack-upgrade-nestjs` — NestJS backend
  File: `../../StackUpgrade/stack-upgrade.nestjs.prompt.md`
  Detect: `nest-cli.json` or `@nestjs/core` in `package.json`
- `stack-upgrade-nextjs` — Next.js
  File: `../../StackUpgrade/stack-upgrade.nextjs.prompt.md`
  Detect: `next.config.{js,ts,mjs}` or `next` in `package.json`
- `stack-upgrade-python` — Python
  File: `../../StackUpgrade/stack-upgrade.python.prompt.md`
  Detect: `pyproject.toml`, `requirements.txt`, `Pipfile`, `setup.py`
- `stack-upgrade-react-native` — React Native / Expo
  File: `../../StackUpgrade/stack-upgrade.react-native.prompt.md`
  Detect: `app.json` with Expo/RN config, or `react-native` / `expo` in `package.json`
- `stack-upgrade-swift` — Swift / iOS / macOS
  File: `../../StackUpgrade/stack-upgrade.swift.prompt.md`
  Detect: `Package.swift`, `*.xcodeproj/`, `*.xcworkspace/`
- `stack-upgrade-terraform` — Terraform / OpenTofu
  File: `../../StackUpgrade/stack-upgrade.terraform.prompt.md`
  Detect: `*.tf`, `*.tofu`

Related across the family: `post-milestone-fix`
