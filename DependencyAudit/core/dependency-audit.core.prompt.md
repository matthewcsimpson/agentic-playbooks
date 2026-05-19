# Dependency audit — core

Shared scaffold for the dependency audit. Not invoked directly
— the ecosystem-specific variants
(`dependency-audit.npm.prompt.md`,
`dependency-audit.python.prompt.md`, etc.) reference this file for
the workflow shape and reuse the generic sections.

A variant supplies the ecosystem-specific content for:

- Manifest and lockfile file locations.
- Outdated, audit, and listing commands.
- Unused / missing detection (static tool + grep strategy).
- Lockfile drift detection.
- Duplicate / version-conflict detection.
- Ecosystem-specific report rows and constraints.

Everything else below is shared.

---

## Context

A dependency audit answers four questions at once:

1. **What deps are out of date?** And how badly — patch / minor /
   major.
2. **What deps have known vulnerabilities?** And are they reachable in
   this project's usage?
3. **What deps are declared but not used (bloat) and what's used but
   not declared (latent breakage)?**
4. **Does the lockfile faithfully match the manifest?** Drift here
   causes "works on my machine" upgrades.

These are usually run with different tools at different times. This
audit consolidates them into a single pass with one prioritised report
— a transitive CVE on a leaf dep can outrank a major-behind core lib
instead of living in a separate terminal window.

The deliverable is `docs/audits/dependencies-<timestamp>.md` (see
Step 7). Do not modify any manifest, lockfile, or installed dep —
investigate and report only.

---

## Step 0 — Convention sourcing

Read every file the project uses to document conventions, in priority
order:

- `CLAUDE.md` at the repo root and any nested ones.
- `AGENTS.md`.
- `.github/copilot-instructions.md`, `.github/instructions/**/*.md`.
- `.cursor/rules/**/*` (or `.cursorrules`).
- Any `docs/dependencies.md`, `docs/upgrades.md`, or `CONTRIBUTING.md`
  section on adding / pinning deps.
- CI workflow files — what dep checks already run, so the audit can
  layer on top rather than duplicate.

Enumerate the rules you'll be checking (banned licences, pinning
practice, vendoring rules, allowed registries, …) before scanning.

If the repo has none of these, say so and fall back to the variant's
generic categories.

---

## Step 1 — Inventory

The variant supplies the discovery commands. Establish:

- Which manifest file(s) exist (path per workspace if a monorepo).
- Which lockfile is canonical. Multiple lockfiles for the same
  ecosystem is itself a finding — report it before continuing and
  stop until the user picks one.
- Which package manager is in use (detected from lockfile, not from
  developer convention).
- Which ecosystems share the repo (a JS + Python monorepo gets one
  audit per ecosystem, run separately).

Report the inventory at the top of the audit so the rest is
interpretable.

---

## Step 2 — Outdated

The variant supplies the command.

Categorise findings by gap:

- **Major-behind** — N major versions behind upstream. Flag with the
  count. Direct deps in this bucket are the highest-leverage
  findings.
- **Minor-behind** — minor versions behind. Lower priority unless on
  a security-sensitive dep (auth, crypto, framework core).
- **Patch-behind** — patch versions behind. Usually safe; group these
  together rather than listing individually.

For each outdated dep, capture:

- Current version.
- Latest available.
- Release date of latest (if the tool surfaces it) — a year-stale
  patch is a different shape from a week-old one.
- Direct vs transitive.

Transitive deps that are major-behind are usually downstream
consequences of an outdated direct dep — fix the direct first.

---

## Step 3 — Vulnerabilities

The variant supplies the command. For every advisory:

- Severity (low / moderate / high / critical) as the tool reports it.
- Affected dep, current version, fix version (or `no fix yet`).
- Whether the vulnerability is reachable in this project's usage.
  This is a judgment call — often "unclear", say so. A high advisory
  on a transitive that isn't reachable is genuinely lower priority
  than a moderate on a direct dep used in the request path.

Report tool-severity AND your reachability assessment as **separate
fields**. Do not downgrade a CVE because reachability is unclear; let
the user decide.

If the project pins around a CVE via overrides / resolutions / a
constraint file, list the pin — that context matters for the
remediation plan.

---

## Step 4 — Unused / missing

The variant supplies the static-analysis tool. After running it:

- **Unused** — declared in manifest, not imported anywhere. Confirm
  by greping the package name across the whole repo (not just
  source — config files, scripts, CI workflows count).
- **Missing** — imported in source but not in the manifest. Usually
  means the project relies on a transitive that hoists to top-level.
  Fragile; treat as ⚠️ ISSUE.
- **Misplaced** — test- or dev-only deps declared in the production
  scope (or vice versa). Separate finding from "unused".

Static tools miss usages behind dynamic imports, runtime
registration, plugin discovery, and codegen. Flag those as candidates
and confirm by grep rather than reporting them as hard findings.

---

## Step 5 — Lockfile drift

The variant supplies the drift-detection command (the `--frozen` /
`--ci` mode of the package manager).

Drift means: the lockfile no longer matches what the manifest would
resolve to. Causes:

- CI installs that differ from local installs.
- "Works on my machine" upgrades that aren't really upgraded.
- Migration diffs that look like noise but are real version moves.

Report any drift as ⚠️ ISSUE — the fix is straightforward (re-lock)
but the consequences if missed are large. This check is binary
pass / fail; do not soften it.

---

## Step 6 — Duplicates / version conflicts

The variant supplies the command. For each duplicate:

- Dep name and the versions present.
- Which top-level dep brings each version in (matters for fix
  planning — sometimes you can only dedupe by upgrading a sibling).

Pay extra attention to libraries that hold state at module level
(React, React DOM, state managers, ORM clients, telemetry SDKs) —
duplicates cause runtime bugs, not just bundle bloat.

---

## Step 7 — Report

Write to `docs/audits/dependencies-<timestamp>.md`, where
`<timestamp>` is current UTC time in basic ISO 8601 format
`YYYYMMDDTHHMMSS` — generate with `date -u +%Y%m%dT%H%M%S` (e.g.
`20260519T143022`). Always write a new file; do not overwrite prior
runs — the directory is an ordered history. Structure:

```
# Dependency audit — <ecosystem>

Date: <today>
Ecosystem variant: <npm | python | dotnet | swift | terraform | …>
Manifest(s): <list>
Lockfile: <path>
Convention sources read: <list>

## Summary

<2-3 sentences — overall posture, biggest concern, total counts>

## Top priorities

<Ranked list across all sections — what the user reads first.>
1. ⚠️ CRITICAL — <dep> — <one-line description and fix>
2. ⚠️ HIGH — <dep> — ...

## Vulnerabilities

| Severity | Dep | Current | Fix in | Reachable? | Direct? |
|---|---|---|---|---|---|

## Outdated

### Major-behind direct
### Minor-behind direct
### Patch-behind direct (grouped count + worst 3)
### Transitive (top 10 worst)

## Unused / missing

### Unused
### Missing
### Misplaced (e.g. dev dep in production scope)

## Lockfile drift

✅ PASS / ⚠️ ISSUE — <details>

## Duplicates

## Recommendations

<5-10 concrete actions, ranked. "Bump X from a@1 to a@2 in
apps/web/package.json to clear CVE-Y" is concrete. "Upgrade
your deps" is not.>
```

Finding markers:

- ⚠️ CRITICAL / HIGH / MODERATE / LOW for vulnerabilities (use tool
  severity directly).
- ⚠️ ISSUE for everything else that is unambiguously wrong (drift,
  missing dep).
- 💡 CANDIDATE for judgment calls (e.g. "consider dropping X — only
  used in one place").

If a category has no findings, mark it ✅ PASS.

---

## Constraints

- Do not modify any manifest or lockfile. Do not install, upgrade, or
  remove packages.
- Every finding must name a specific dep. "Several deps are
  outdated" is not acceptable — list them.
- Report tool-reported severity and reachability assessment as
  separate fields. Do not collapse them.
- If a dep is both vulnerable AND major-behind, list it once under
  Vulnerabilities — duplicate listings inflate the report.
- Lockfile drift is binary pass / fail. Don't soften it.
- Don't recommend "auto-fix" commands (`npm audit fix --force`,
  `pip-audit --fix`, etc.) — those can perform unsafe upgrades. The
  user runs upgrades deliberately.
- Don't flag re-export barrels, plugin-discovery deps, or codegen
  deps as unused without confirming by grep. Static tools miss
  these.
