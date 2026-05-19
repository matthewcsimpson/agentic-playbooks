# DependencyAudit

A bundled dependency audit — outdated versions, known
vulnerabilities, unused / missing declarations, lockfile drift, and
duplicate versions — in one prioritised report, paired with per-
stack fix prompts that action the audit findings.

These are usually run as separate tools at separate times (`npm
outdated`, `npm audit`, `depcheck`, etc.). The audit prompt
consolidates them into one pass with a single prioritised report, so
a transitive CVE on a leaf dep can outrank a missing major version
on a core lib instead of living in a different terminal window. The
fix actions findings per category (vuln fixes first, then bumps by
risk band, then removals, missing additions, drift, dedupe).

Variants carry an ecosystem tag (`.npm`, `.python`, `.dotnet`,
`.swift`, `.terraform`) because the commands, manifest formats, and
lockfile shapes differ entirely across package managers. The cores
are the shared scaffolds and aren't invoked directly.

| Audit | Fix | Manifest | Headline tools |
|---|---|---|---|
| `dependency-audit.npm.prompt.md` | `dependency-fix.npm.prompt.md` | `package.json` (+ npm / pnpm / yarn lockfile) | `npm outdated`, `npm audit`, `npm dedupe`, `knip` / `depcheck` |
| `dependency-audit.python.prompt.md` | `dependency-fix.python.prompt.md` | `pyproject.toml` / `requirements*.txt` | `pip list --outdated`, `pip-audit`, `deptry` |
| `dependency-audit.dotnet.prompt.md` | `dependency-fix.dotnet.prompt.md` | `*.csproj` / `Directory.Packages.props` | `dotnet list package --outdated/--vulnerable/--deprecated` |
| `dependency-audit.swift.prompt.md` | `dependency-fix.swift.prompt.md` | `Package.swift` / `Podfile` | `swift package show-dependencies`, `pod outdated` |
| `dependency-audit.terraform.prompt.md` | `dependency-fix.terraform.prompt.md` | `versions.tf` / `required_providers` | `terraform providers`, `tfsec` / `trivy` |
| `core/dependency-audit.core.prompt.md` | `core/dependency-fix.core.prompt.md` | Shared scaffolds | Not invoked directly. |

The fix prompts deliberately default to a **narrow** scope:

- `dependency-fix-*` defaults to `vulnerable` + `outdated-patch` +
  `drift` only. Action `outdated-minor`, `outdated-major`, `unused`,
  `missing`, `duplicates` only when the user explicitly opts in.
- Majors are isolated **one per commit** — easy to revert without
  losing other progress.
- An optional **excluded deps** input lets the user say "bump
  everything except `react`" without naming every dep individually.
- Build and tests run between each category — a broken category is
  reverted before the next one starts.

All fix prompts commit locally only — they don't push or open a PR.
The intended flow is: run the audit, read the report, decide which
categories are worth acting on, invoke the fix with that scope.

## Picking a variant

Pick the variant matching the project's primary package manager. In
a polyglot repo, run multiple variants (one per ecosystem) — the
report header includes the ecosystem tag, so reports don't collide.

If your ecosystem isn't listed (Go modules, Cargo, RubyGems,
Composer, …):

1. Copy the closest variant pair (audit + fix).
2. Rename to `dependency-audit.<ecosystem>.prompt.md` and
   `dependency-fix.<ecosystem>.prompt.md`.
3. Replace the commands, manifest paths, and ecosystem gotchas.
4. Leave the `core/` references intact.
5. Update this README's variant table and open a PR.

## What the audit catches

- **Outdated** — patch / minor / major-behind per direct dep, plus
  the worst transitive offenders.
- **Vulnerabilities** — tool severity (LOW / MODERATE / HIGH /
  CRITICAL) plus a reachability assessment in this codebase's usage.
- **Unused** — declared in manifest, not imported anywhere. Confirmed
  by grep across the whole repo (not just source — config files,
  scripts, CI workflows count).
- **Missing** — imported in source but not in the manifest (latent
  breakage — fragile against transitive hoisting changes).
- **Misplaced** — test- or dev-only deps in production scope, or
  vice versa.
- **Lockfile drift** — binary pass / fail.
- **Duplicates** — multiple versions of the same package in the
  tree; high-severity for state-holding libs (React, ORM clients,
  state managers).

## What the fix actions

The fix's edit catalogue mirrors the audit's findings:

- **Vulnerability remediation** — targeted bumps to the fix version;
  for transitive vulns, overrides / resolutions / constraints with
  the *reason* captured in the commit message.
- **Outdated bumps by risk band** — `risk:low` (patch + framework-
  internal minors), `risk:med` (arbitrary minors), `risk:high`
  (majors, one at a time).
- **Removals** — manifest + lockfile in one command; re-grep before
  removing for plugin-discovery / codegen references.
- **Missing additions** — pin to the version already resolved
  transitively (the version the code was likely tested against), or
  resolve `latest` to a concrete version and pin its range if no
  transitive resolution exists (`latest` is a dist-tag, not a
  semver range, so `^latest` is not a valid specifier).
- **Lockfile re-resolution** — re-lock without touching the
  manifest; surface unexpected version moves if the re-lock pulls
  changes in.
- **Dedupe** — collapse duplicate versions; for state-holding libs,
  bump the offending sibling rather than letting dedupe silently
  succeed at the wrong version.

## Required tool capabilities

- File read across the repo.
- Shell execution for the ecosystem's CLI.
- Write capability for the fix (modifies manifest, lockfile, and
  occasionally source-tree config). The audit is read-only.

Designed for Claude Code and Codex CLI; anything with the same
capability set should work.

## Output discipline

The audit writes to `<root>/dependencies-<timestamp>.md` (e.g.
`.playbook-audits/dependencies-20260519T143022.md`). `<root>`
resolves in this order: `.playbook-audits/` if it exists, else
`docs/audits/` if that exists (legacy convention), else the audit
creates `.playbook-audits/` and appends it to `.gitignore` on
first use. Each run produces a new file so the directory
accumulates an ordered history; the fix prompt picks the most
recent.

The fix produces local commits, one per category actioned.

## Invocation

See the [root README](../README.md#invocation) for the three
supported patterns. For paste-mode, paste the core file first, then
the variant — the variant references the core for the workflow
shape.
