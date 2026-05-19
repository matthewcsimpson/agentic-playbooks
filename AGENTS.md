# AGENTS.md

Index of reusable prompts in the agentic-playbooks library, for
agent-aware tools (Codex CLI, OpenCode, Aider, and others that
auto-read `AGENTS.md`).

**Invocation pattern** — every supported tool exposes one router slash
command that takes a slug:

- Codex CLI: `/prompts:playbook <slug> [user scope]`
- Natural language (any agent that reads this file): "run the
  `<slug>` playbook against <target>".

For multi-variant families (e.g. `dependency-audit`), pass just the
family name and the agent will inspect the working directory to pick
the right variant.

Canonical sources live in the per-collection folders. The router
shims under `.claude/`, `.cursor/`, `.github/`, and this file are
generated from those sources by `tools/generate-adapters.py`.

## AuditTesting

- **`test-coverage-audit`** — Survey a repository's test coverage from scratch, identify the most important gaps, and present a ranked list of recommendations.
  Path: `AuditTesting/test-coverage-audit.prompt.md`
  Related: `test-coverage-fix`
- **`test-coverage-fix`** — Write missing tests for a single component, module, or feature, matching the project's existing test conventions.
  Path: `AuditTesting/test-coverage-fix.prompt.md`
  Related: `test-coverage-audit`

## DBMigrationAudit

- **`db-migration-audit-alembic`** — Pre-merge safety audit for Alembic database migrations — catches NOT NULL on populated tables, non-concurrent indexes, FK without index, rename-on-deploy hazards.
  Path: `DBMigrationAudit/db-migration-audit.alembic.prompt.md`
  Related: `db-migration-fix-alembic`
- **`db-migration-audit-ef-core`** — Pre-merge safety audit for Entity Framework Core migrations — catches NOT NULL on populated tables, non-concurrent indexes, FK without index, rename-on-deploy hazards.
  Path: `DBMigrationAudit/db-migration-audit.ef-core.prompt.md`
  Related: `db-migration-fix-ef-core`
- **`db-migration-audit-prisma`** — Pre-merge safety audit for Prisma Migrate migrations — catches NOT NULL on populated tables, non-concurrent indexes, FK without index, rename-on-deploy hazards.
  Path: `DBMigrationAudit/db-migration-audit.prisma.prompt.md`
  Related: `db-migration-fix-prisma`
- **`db-migration-audit-typeorm`** — Pre-merge safety audit for TypeORM migrations — catches NOT NULL on populated tables, non-concurrent indexes, FK without index, rename-on-deploy hazards.
  Path: `DBMigrationAudit/db-migration-audit.typeorm.prompt.md`
  Related: `db-migration-fix-typeorm`
- **`db-migration-fix-alembic`** — Action findings from db-migration-audit-alembic. Edit Alembic migrations (CONCURRENTLY, splits, NOT VALID), verify via alembic upgrade --sql, commit per migration. Local commits only.
  Path: `DBMigrationAudit/db-migration-fix.alembic.prompt.md`
  Related: `db-migration-audit-alembic`
- **`db-migration-fix-ef-core`** — Action findings from db-migration-audit-ef-core. Edit EF Core migrations (raw SQL for CONCURRENTLY, splits), verify via dotnet ef migrations script, commit per migration. Local commits only.
  Path: `DBMigrationAudit/db-migration-fix.ef-core.prompt.md`
  Related: `db-migration-audit-ef-core`
- **`db-migration-fix-prisma`** — Action findings from db-migration-audit-prisma. Edit Prisma migration SQL (CONCURRENTLY, splits, RENAME COLUMN), verify via prisma migrate diff, commit per migration. Local commits only.
  Path: `DBMigrationAudit/db-migration-fix.prisma.prompt.md`
  Related: `db-migration-audit-prisma`
- **`db-migration-fix-typeorm`** — Action findings from db-migration-audit-typeorm. Edit TypeORM migration classes (raw SQL, splits), verify via typeorm migration:show + tsc, commit per migration. Local commits only.
  Path: `DBMigrationAudit/db-migration-fix.typeorm.prompt.md`
  Related: `db-migration-audit-typeorm`

## Debugging

- **`regression-bisect`** — Given last-known-good, symptom, and reproduction steps, drive a disciplined git bisect to the breaking commit and propose a fix.
  Path: `Debugging/regression-bisect.prompt.md`

## DependencyAudit

- **`dependency-audit-dotnet`** — Audit a .NET / NuGet project for outdated versions, known vulnerabilities, unused or missing declarations, lockfile drift, and duplicate versions.
  Path: `DependencyAudit/dependency-audit.dotnet.prompt.md`
  Related: `dependency-fix-dotnet`
- **`dependency-audit-npm`** — Audit a JavaScript / TypeScript project (npm, pnpm, or yarn) for outdated versions, vulnerabilities, unused or missing declarations, lockfile drift, and duplicates.
  Path: `DependencyAudit/dependency-audit.npm.prompt.md`
  Related: `dependency-fix-npm`
- **`dependency-audit-python`** — Audit a Python project (pip, uv, Poetry, or pdm) for outdated versions, vulnerabilities, unused or missing declarations, lockfile drift, and duplicates.
  Path: `DependencyAudit/dependency-audit.python.prompt.md`
  Related: `dependency-fix-python`
- **`dependency-audit-swift`** — Audit a Swift / Xcode project (Swift Package Manager and/or CocoaPods) for outdated versions, vulnerabilities, unused or missing declarations, and duplicates.
  Path: `DependencyAudit/dependency-audit.swift.prompt.md`
  Related: `dependency-fix-swift`
- **`dependency-audit-terraform`** — Audit a Terraform / OpenTofu codebase's provider, module, and backend dependencies for outdated versions, vulnerabilities, and duplicate version pins.
  Path: `DependencyAudit/dependency-audit.terraform.prompt.md`
  Related: `dependency-fix-terraform`
- **`dependency-fix-dotnet`** — Action findings from dependency-audit-dotnet. Handles Central Package Management (Directory.Packages.props), per-project vs solution bumps, multi-target frameworks. Local commits only.
  Path: `DependencyAudit/dependency-fix.dotnet.prompt.md`
  Related: `dependency-audit-dotnet`
- **`dependency-fix-npm`** — Action findings from dependency-audit-npm. Detects npm / pnpm / yarn (classic or berry), respects Corepack, uses overrides / resolutions for transitive vulns. Local commits only.
  Path: `DependencyAudit/dependency-fix.npm.prompt.md`
  Related: `dependency-audit-npm`
- **`dependency-fix-python`** — Action findings from dependency-audit-python. Detects uv / Poetry / pdm / pip-tools, regenerates requirements*.txt from .in, handles dev / test / extras groups. Local commits only.
  Path: `DependencyAudit/dependency-fix.python.prompt.md`
  Related: `dependency-audit-python`
- **`dependency-fix-swift`** — Action findings from dependency-audit-swift. Handles SPM (Package.resolved) and CocoaPods (Podfile.lock) in parallel, respects deployment-target pins. Local commits only.
  Path: `DependencyAudit/dependency-fix.swift.prompt.md`
  Related: `dependency-audit-swift`
- **`dependency-fix-terraform`** — Action findings from dependency-audit-terraform. Bumps providers / modules / backends, multi-platform re-lock (darwin / linux), gates on terraform plan showing 0 resource changes. Local commits only.
  Path: `DependencyAudit/dependency-fix.terraform.prompt.md`
  Related: `dependency-audit-terraform`

## DocsHygiene

- **`agent-instructions-audit`** — Audit the project's agent / LLM instruction files for vague rules, missing examples, drifted compliance, and mechanical-enforcement opportunities.
  Path: `DocsHygiene/agent-instructions-audit.prompt.md`
  Related: `agent-instructions-fix`
- **`agent-instructions-fix`** — Action findings from agent-instructions-audit: reword, add examples, codify undocumented, resolve contradictions, retire. Optional consolidate to one canonical. Commit per category. Local only.
  Path: `DocsHygiene/agent-instructions-fix.prompt.md`
  Related: `agent-instructions-audit`
- **`doc-code-drift-audit`** — Read-only audit that finds places where documentation says one thing and the code does another (outdated commands, renamed env vars, drifted signatures, dead links).
  Path: `DocsHygiene/doc-code-drift-audit.prompt.md`
  Related: `doc-code-drift-fix`
- **`doc-code-drift-fix`** — Action findings from doc-code-drift-audit. Update docs to match the code, verify links and snippets, commit per drift type. Local commits only.
  Path: `DocsHygiene/doc-code-drift-fix.prompt.md`
  Related: `doc-code-drift-audit`
- **`planning-doc-drift-audit-github-wiki`** — Read-only audit of decision/scope/architecture drift between a GitHub repo's wiki (planning docs) and the issues + commits that have landed since. Surfaces contradictions, does not edit.
  Path: `DocsHygiene/planning-doc-drift-audit.github-wiki.prompt.md`
  Related: `planning-doc-drift-fix`, `doc-code-drift-audit`, `audit-duplicate-issues-github`
- **`planning-doc-drift-fix-github-wiki`** — Action findings from planning-doc-drift-audit.github-wiki. Edit the sibling-cloned wiki, commit per drift category in the wiki repo, append to in-wiki CHANGELOG. Local commits only — never pushes.
  Path: `DocsHygiene/planning-doc-drift-fix.github-wiki.prompt.md`
  Related: `planning-doc-drift-audit`, `doc-code-drift-fix`

## IssueWorkflow

- **`audit-duplicate-issues-clickup`** — Survey a ClickUp List or Folder for duplicate and near-duplicate tasks; cluster, classify, and recommend an action per cluster. Stops before any closure or edit.
  Path: `IssueWorkflow/audit-duplicate-issues.clickup.prompt.md`
- **`audit-duplicate-issues-github`** — Survey a GitHub repository's open issues for duplicates and near-duplicates; cluster, classify, and recommend an action per cluster. Stops before any closure or edit.
  Path: `IssueWorkflow/audit-duplicate-issues.github.prompt.md`

## MilestoneAudit

- **`post-milestone-audit-dotnet`** — Audit a .NET / C# codebase after a milestone tag is cut — drift, regressions, extraction signals, and convention compliance against documented rules.
  Path: `MilestoneAudit/post-milestone-audit.dotnet.prompt.md`
  Related: `post-milestone-fix`
- **`post-milestone-audit-nestjs`** — Audit a NestJS (TypeScript) codebase after a milestone tag is cut — drift, regressions, extraction signals, and convention compliance against documented rules.
  Path: `MilestoneAudit/post-milestone-audit.nestjs.prompt.md`
  Related: `post-milestone-fix`
- **`post-milestone-audit-nextjs`** — Audit a Next.js (App Router) + TypeScript codebase after a milestone tag is cut — drift, regressions, extraction signals, and convention compliance.
  Path: `MilestoneAudit/post-milestone-audit.nextjs.prompt.md`
  Related: `post-milestone-fix`
- **`post-milestone-audit-python`** — Audit a Python codebase after a milestone tag is cut — drift, regressions, extraction signals, and convention compliance against documented rules.
  Path: `MilestoneAudit/post-milestone-audit.python.prompt.md`
  Related: `post-milestone-fix`
- **`post-milestone-audit-react-native`** — Audit a React Native / Expo codebase after a milestone tag is cut — drift, regressions, extraction signals, and convention compliance against documented rules.
  Path: `MilestoneAudit/post-milestone-audit.react-native.prompt.md`
  Related: `post-milestone-fix`
- **`post-milestone-audit-swift`** — Audit a Swift / Xcode codebase after a milestone tag is cut — drift, regressions, extraction signals, and convention compliance against documented rules.
  Path: `MilestoneAudit/post-milestone-audit.swift.prompt.md`
  Related: `post-milestone-fix`
- **`post-milestone-audit-terraform`** — Audit a Terraform infrastructure-as-code repo after a milestone tag is cut — drift, regressions, extraction signals, and convention compliance.
  Path: `MilestoneAudit/post-milestone-audit.terraform.prompt.md`
  Related: `post-milestone-fix`
- **`post-milestone-fix`** — Action the in-scope findings from the most recent post-milestone audit report. Commits locally; does not push or open a PR.
  Path: `MilestoneAudit/post-milestone-fix.prompt.md`
  Related: `post-milestone-audit-dotnet`, `post-milestone-audit-nestjs`, `post-milestone-audit-nextjs`, `post-milestone-audit-python`, `post-milestone-audit-react-native`, `post-milestone-audit-swift`, `post-milestone-audit-terraform`

## MilestoneSmoke

- **`post-milestone-smoke-fix`** — Action ❌ Fail findings from the most recent post-milestone smoke-test report. Commits locally; does not push or open a PR.
  Path: `MilestoneSmoke/post-milestone-smoke-fix.prompt.md`
  Related: `post-milestone-smoke-test-api`, `post-milestone-smoke-test-cli`, `post-milestone-smoke-test-ios`, `post-milestone-smoke-test-web`
- **`post-milestone-smoke-test-api`** — Drive a running HTTP API after a milestone tag is cut — hit headline endpoints with concrete requests, assert response shape and auth behaviour, write a pass/fail/blocked report.
  Path: `MilestoneSmoke/post-milestone-smoke-test.api.prompt.md`
- **`post-milestone-smoke-test-cli`** — Drive a CLI binary after a milestone tag is cut — invoke headline commands, observe exit code / stdout / stderr / side effects, write a pass/fail/blocked report.
  Path: `MilestoneSmoke/post-milestone-smoke-test.cli.prompt.md`
- **`post-milestone-smoke-test-ios`** — Drive an iOS app through the iOS Simulator after a milestone tag is cut — execute headline user flows, observe device log and screenshots, write a pass/fail/blocked report.
  Path: `MilestoneSmoke/post-milestone-smoke-test.ios.prompt.md`
- **`post-milestone-smoke-test-web`** — Drive a web app through a browser MCP server after a milestone tag is cut — exercise headline flows, write a pass/fail/blocked report.
  Path: `MilestoneSmoke/post-milestone-smoke-test.web.prompt.md`

## ObservabilityAudit

- **`observability-audit`** — Read-only audit of how a codebase logs, traces, and surfaces errors — swallowed errors, missing correlation IDs, log-level mismatches, PII in logs, dishonest health checks.
  Path: `ObservabilityAudit/observability-audit.prompt.md`
  Related: `observability-fix`
- **`observability-fix`** — Action findings from observability-audit. Fix log levels, redact sensitive data, repair swallowed errors, propagate correlation IDs. Verify build, commit per category. Local only.
  Path: `ObservabilityAudit/observability-fix.prompt.md`
  Related: `observability-audit`

## PRWorkflow

- **`pre-pr-checklist`** — Before opening a pull request, run the project's check suite, scan the diff for things reviewers can't easily catch (debug code, secrets, missing tests), and draft a PR body.
  Path: `PRWorkflow/pre-pr-checklist.prompt.md`

## Refactoring

- **`dead-code-audit`** — Find code that isn't used — exports never imported, components never rendered, branches never reached, env vars never read, permanently-on/off flags. Read-only.
  Path: `Refactoring/dead-code-audit.prompt.md`
  Related: `dead-code-fix`, `duplicate-logic-audit`
- **`dead-code-fix`** — Action the in-scope findings from the most recent dead-code-audit report. Deletes dead code, verifies the build, commits locally per category. Does not push or open a PR.
  Path: `Refactoring/dead-code-fix.prompt.md`
  Related: `dead-code-audit`
- **`duplicate-logic-audit`** — Find functions, modules, or components doing the same job under different names. Cluster, identify a winner, propose consolidations. Read-only — does not action.
  Path: `Refactoring/duplicate-logic-audit.prompt.md`
  Related: `duplicate-logic-fix`, `dead-code-audit`
- **`duplicate-logic-fix`** — Action user-selected clusters from the most recent duplicate-logic-audit report. Migrate callers to the recommended winner, delete losers, verify, commit per cluster. Local commits only.
  Path: `Refactoring/duplicate-logic-fix.prompt.md`
  Related: `duplicate-logic-audit`

## SEOAudit

- **`seo-audit`** — Read-only SEO audit for a web app — crawlability, on-page metadata, structured data, semantic HTML, images, URL structure, and i18n. Static analysis only.
  Path: `SEOAudit/seo-audit.prompt.md`
  Related: `seo-fix`
- **`seo-fix`** — Action findings from seo-audit. Edits metadata, robots, sitemap, canonical, JSON-LD, alt, lang per category, verifies build, commits per category. Local commits only.
  Path: `SEOAudit/seo-fix.prompt.md`
  Related: `seo-audit`

## StackUpgrade

- **`stack-upgrade-dotnet`** — Plan a .NET TFM upgrade (e.g. .NET 6 → 8, 8 → 9) — read release notes, scan for affected patterns, survey codemods, produce a risk-ranked migration plan.
  Path: `StackUpgrade/stack-upgrade.dotnet.prompt.md`
  Related: `post-milestone-fix`
- **`stack-upgrade-nestjs`** — Plan a NestJS major version upgrade — read release notes, scan for affected patterns, survey codemods, produce a risk-ranked migration plan.
  Path: `StackUpgrade/stack-upgrade.nestjs.prompt.md`
  Related: `post-milestone-fix`
- **`stack-upgrade-nextjs`** — Plan a Next.js version upgrade — read release notes, scan for affected patterns, survey codemods, produce a risk-ranked migration plan.
  Path: `StackUpgrade/stack-upgrade.nextjs.prompt.md`
  Related: `post-milestone-fix`
- **`stack-upgrade-python`** — Plan a Python language version upgrade (e.g. 3.10 → 3.12) — read release notes, scan for affected patterns, survey codemods, produce a risk-ranked migration plan.
  Path: `StackUpgrade/stack-upgrade.python.prompt.md`
  Related: `post-milestone-fix`
- **`stack-upgrade-react-native`** — Plan a React Native / Expo SDK upgrade — read release notes, scan for affected patterns, survey codemods, produce a risk-ranked migration plan.
  Path: `StackUpgrade/stack-upgrade.react-native.prompt.md`
  Related: `post-milestone-fix`
- **`stack-upgrade-swift`** — Plan a Swift / Xcode / iOS SDK upgrade — read release notes, scan for affected patterns, survey codemods, produce a risk-ranked migration plan.
  Path: `StackUpgrade/stack-upgrade.swift.prompt.md`
  Related: `post-milestone-fix`
- **`stack-upgrade-terraform`** — Plan a Terraform / OpenTofu CLI or major provider upgrade (e.g. AWS provider 4 → 5) — read release notes, scan for patterns, produce a risk-ranked migration plan.
  Path: `StackUpgrade/stack-upgrade.terraform.prompt.md`
  Related: `post-milestone-fix`
