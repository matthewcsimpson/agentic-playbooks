# Dependency fix — core

Shared scaffold for the dependency-fix action. Not invoked directly —
the ecosystem-specific variants (`dependency-fix.npm.prompt.md`,
`dependency-fix.python.prompt.md`, etc.) reference this file for the
workflow shape and reuse the generic sections.

A variant supplies the ecosystem-specific content for:

- Upgrade commands (single dep, range, latest).
- Vulnerability remediation commands.
- Unused-dep removal commands.
- Missing-dep installation commands.
- Lockfile-drift resolution commands.
- Deduplication commands.
- Ecosystem-specific verification (build / test / typecheck).

Everything else below is shared.

---

## Context

Dependency fixes are riskier than the audit suggests. A patch bump can
break behaviour. A "remove unused" can break a plugin discovered at
runtime. A "fix vulnerability" can pull in a major upgrade with
breaking changes.

This prompt is conservative by default. It actions one category at a
time, verifies the build and tests after each, and commits per
category so a broken category can be rolled back without losing the
others.

---

## Inputs

The user supplies:

- **Categories in scope** — any combination of:
  - `vulnerable` — bump deps to fix known CVEs.
  - `outdated-patch` — patch-level bumps (`1.2.3` → `1.2.4`).
  - `outdated-minor` — minor-level bumps (`1.2.x` → `1.3.x`).
  - `outdated-major` — major-level bumps (`1.x.x` → `2.x.x`).
  - `unused` — remove deps the audit flagged as unused.
  - `missing` — add deps the audit flagged as missing (imported in
    code but not declared in the manifest).
  - `drift` — re-resolve the lockfile when it doesn't match the
    manifest.
  - `duplicates` — dedupe multiple versions of the same package.

  Default scope is `vulnerable` + `outdated-patch` + `drift`. Other
  categories require explicit opt-in.

- **Risk band for outdated bumps** — `risk:low` (default), `risk:med`,
  `risk:high`. Risk maps roughly to: low = patch + framework-internal
  minors, med = arbitrary minors, high = majors. The variant supplies
  ecosystem-specific risk hints.

- **Excluded deps** — optional comma- or space-separated list of
  package names to skip even if they fall within an in-scope
  category. Use for deps the user has a specific reason to hold
  back (`react` pinned for a coordinated upgrade,
  `@types/node` matched to a specific Node version, etc.). Pattern
  matching is exact-name only — globs and version ranges are not
  supported; list each excluded dep individually.

- **Included deps** — optional, mutually exclusive with excluded.
  Narrows action to just those deps within the in-scope categories.
  Use when the user wants a targeted pass ("just bump `lodash`",
  "only address vulns in `@apollo/*`").

If the user hasn't specified, ask before doing anything else. Don't
guess scope. The audit is the survey; the fix should be deliberate.

---

## Step 1 — Locate the audit

The audit writes to `<root>/dependencies-<timestamp>.md`. Resolve
`<root>` in this order: `.playbook-audits/` if it exists, else
`docs/audits/` if that exists (legacy convention). Look for files
matching `<root>/dependencies-*.md` and pick the most recent
(`ls -1 <root>/dependencies-*.md 2>/dev/null | sort | tail -1`
— the `YYYYMMDDTHHMMSS` suffix sorts lexicographically). If
neither root exists or no report is found, ask the user whether
they have an inline report to paste, or whether they need to run
the audit.

If the user named a specific report file, use that one instead of the
most recent.

If neither a file nor an inline report is available, stop and
recommend running the matching `/playbook dependency-audit-<ecosystem>`
first.

---

## Step 1.5 — Apply the include / exclude filter

Before any action, build the final action list:

1. Start with every audit finding under the in-scope categories.
2. If `Included deps` is set, drop everything except those deps.
3. If `Excluded deps` is set, drop those deps.
4. Surface the filtered list to the user before proceeding ("After
   filtering, X findings remain in scope: ..."). If the filter
   removed everything, stop — there's nothing to do.

Excluded deps that are vulnerable should be called out explicitly in
the report — the user excluded them deliberately, but the audit
flagged them, and the trail should record both facts.

---

## Step 2 — Verify the audit is still valid

Dependency reports go stale fast — a registry mirror can publish a new
patch the next hour. Before acting on any finding, re-check:

- The dep is still at the version the audit reported (no one bumped
  it between audit and fix).
- The advisory cited is still active (the variant supplies the
  re-check command).
- The "unused" entries still don't appear in a grep across the whole
  repo (audits can miss plugin-discovery deps; a fresh grep is cheap).

If a finding no longer applies, record under "Skipped — no longer
applies" and move on.

---

## Step 3 — Action vulnerabilities first

Vulnerable deps always action first when in scope. For each
vulnerability:

1. Determine the fix version (the variant supplies the lookup).
2. Apply the upgrade with the variant's per-ecosystem command.
3. If the fix version is a major bump (breaking change), and the user
   only opted in to `risk:low`, **defer** — do not silently skip. Add
   the dep to a **Deferred security fixes** list with: CVE id, current
   version, required major target, and a one-line note on what
   breaks. This list surfaces in the report as its own section
   (Step 10) so deferred CVEs can't be lost in noise.
4. Run the variant's verification: typecheck, lint, test.
5. If any check fails: revert the upgrade in the manifest and
   lockfile, record under "Skipped — broke checks" with the failing
   command.
6. If checks pass: stage the manifest + lockfile.

Commit all vuln fixes together: "deps: fix CVE-XXXX in `<dep>`,
CVE-YYYY in `<dep>` …". One commit per audit pass keeps the security
fix trail clean.

---

## Step 4 — Action outdated bumps, by risk band

For each in-scope risk band (`patch`, `minor`, `major`):

1. For each dep within the band:
   a. Apply the bump using the variant's command.
   b. Run the variant's verification.
   c. If any check fails: revert the bump, record under "Skipped —
      broke checks" with the failing command and a one-line guess
      ("`@types/react` 18→19 incompatible with React 18 still in
      tree").
   d. If checks pass: stage the manifest + lockfile. **Do not commit
      yet** — bumps in the same risk band batch into one commit.
2. After all bumps in the band are processed, commit as one
   per-band commit: "deps: patch-level bumps", "deps: minor bumps
   for non-framework packages", "deps: major bump for `<dep>` from
   `<old>` to `<new>`" (one major per commit is sensible).

For majors specifically: action **one at a time**, commit each. Majors
are higher-risk; isolating them per commit lets the user revert one
without losing the others.

---

## Step 5 — Action unused removals

For each "unused" dep in scope:

1. Re-grep before removal. The variant supplies the grep target list
   (config files, scripts, CI workflow files — not just source).
2. If a non-source reference exists (plugin discovery, codegen,
   docs), skip and record under "Skipped — referenced outside
   application code".
3. If truly unused: remove via the variant's uninstall command. The
   variant strips the dep from both manifest and lockfile in one
   command — don't hand-edit.
4. Run the variant's verification.
5. If checks fail (the dep was load-bearing in a way the audit
   missed): re-add it, record under "Skipped — removal broke
   build".
6. If checks pass: stage.

Commit as one per-category commit: "deps: remove unused packages".

---

## Step 6 — Action missing additions

For each "missing" dep (imported in code, not declared in manifest):

1. Determine the version to pin. Prefer the version already
   resolved transitively (use the variant's lookup) — that's the
   version the code was likely tested against. If no transitive
   resolution exists (a truly missing dep), resolve `latest` first
   (the variant supplies the lookup command), then pin to that
   resolved version using the variant's default range syntax
   (typically `^<resolved-version>`).
2. Install via the variant's command.
3. Run the variant's verification.

Commit as one per-category commit: "deps: declare implicit
dependencies (`<dep>`, `<dep>`, …)".

---

## Step 7 — Action lockfile drift

Drift is binary — the lockfile is either current or it isn't. The fix
is single-step: re-lock without changing the manifest.

1. Run the variant's lockfile re-resolve command.
2. Run the variant's verification.
3. Commit: "deps: refresh lockfile to match manifest".

If re-locking pulls in version changes that weren't in the manifest,
that's a finding in its own right — surface it; don't silently apply
the changes.

---

## Step 8 — Action duplicate dedupe

For each duplicate cluster the audit flagged:

1. Identify the top-level dep pulling in each version. The variant
   supplies the lookup command.
2. If a manifest-level upgrade of one sibling clears the duplicate,
   apply it (subject to risk-band rules).
3. If a dedupe command (`npm dedupe`, `yarn dedupe`,
   `pnpm dedupe --check`) can collapse the duplicates without a
   manifest change, run it.
4. Run the variant's verification.

Commit as one: "deps: dedupe `<package>` versions".

---

## Step 9 — Run the full check suite

When all in-scope categories are actioned, run the project's full
check suite from a clean state:

- Typecheck.
- Lint.
- Test (unit + integration if the project has both).
- Build (scoped to the primary app if a monorepo).
- The variant's full-install command (`npm ci`, `pip install -e .`,
  `dotnet restore`, etc.) — confirms the lockfile and manifest are
  internally consistent.

A passing check suite is the gate.

---

## Step 10 — Report

Output a short summary. Lead with security-sensitive items so they
can't be lost:

- **⚠️ Deferred security fixes** — vulnerabilities that required a
  major bump while the user was in `risk:low` / `risk:med`. Per
  entry: CVE id, dep, current version, required major target,
  one-line break note. **The user must follow up on these out-of-band
  before merging.** If empty, mark ✅ "No deferred CVEs".
- **⚠️ Excluded deps with active CVEs** — deps the user explicitly
  excluded that the audit still flagged as vulnerable. Per entry:
  CVE id, dep, why excluded (if the user said). If empty, mark ✅
  "No excluded CVEs".
- **Categories actioned** — count per category, with dep names.
- **Bumps applied** — list with `<dep>: <old> → <new>` format.
- **Vulnerabilities cleared** — list with CVE ids.
- **Deps removed** — list.
- **Deps added** — list.
- **Skipped within scope** — with reason per item.
- **Final check result** — pass / fail with the failing command.
- **Suggested PR title and body summary** — draft for a human to
  paste, not to open.

---

## Constraints

- Do not push to the remote.
- Do not open a PR.
- Do not action categories outside the user's stated scope. The
  default (`vulnerable` + `outdated-patch` + `drift`) is deliberately
  narrow.
- Do not perform major bumps unless the user opted in to `risk:high`.
  Major-only commits are isolated for a reason; sweeping them in with
  other categories defeats the purpose.
- Do not run "auto-fix" commands that perform unsafe upgrades
  (`npm audit fix --force`, `pip-audit --fix`, etc.). Apply specific
  upgrades the audit recommended, individually verified.
- Do not delete a dep flagged as unused without re-greping across the
  whole repo first. Static analyzers miss plugin-discovery,
  string-loaded modules, and codegen targets.
- Do not "improve" the manifest adjacent to a fix (re-sort keys,
  normalise version ranges, swap between `^` and `~`). Scope creep
  turns a low-risk dep update into a review burden.
- Do not introduce a new package manager. If the audit recommended
  switching from yarn to pnpm, that's a project-wide decision, not a
  fix-pass action.
- If the project pins a dep around a known CVE (overrides /
  resolutions / constraints), do not remove the pin unless the
  audit confirmed the upstream fix is reachable. Pins exist for
  reasons that may not be in the audit report.
- If a bump requires changes to source code (a renamed API, a
  breaking signature change), stop and flag for human review rather
  than carrying out the source edits. The fix prompt is a deps pass,
  not a refactor.
