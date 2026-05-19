# Stack upgrade — core

Shared scaffold for the stack-upgrade prompt. Not invoked directly
— the stack-specific variants (`stack-upgrade.nextjs.prompt.md`,
`stack-upgrade.python.prompt.md`, etc.) reference this file for the
workflow shape and reuse the generic sections.

A variant supplies the stack-specific content for:

- Detecting the current version.
- Locating upstream release notes and upgrade guides.
- Categories of breaking changes between majors.
- Available codemods, lint rules, and migration tools.
- Stack-specific risk patterns.

Everything else below is shared.

---

## Context

A framework / runtime / language version bump is a special kind of
change: most of the *work* lives outside the code that explicitly
mentions the framework. Imports stay the same, types still
typecheck, the app starts — but a deprecated API still in use breaks
silently when the deprecated path is removed, a default changes,
behaviour shifts.

This prompt produces a **migration plan**, not a fix. The plan:

1. Identifies the upgrade path (current version → target, including
   any intermediate majors).
2. Reads upstream release notes / upgrade guides for every version
   in the path.
3. Catalogues breaking changes by category.
4. Scans the repo for affected patterns.
5. Surveys available codemods and lint rules.
6. Produces an ordered, risk-ranked migration plan.

The deliverable is `<root>/upgrades/<stack>-<from>-<to>-<timestamp>.md`
(see the report step below for how to resolve `<root>`).

Do not perform the upgrade. Do not change `package.json`,
`pyproject.toml`, `.csproj`, or any other manifest. Do not run
codemods that mutate files (run them in dry-run / preview mode
only). The user runs the upgrade deliberately — either by hand
using this plan as a script, or by invoking the action companion
`stack-upgrade-fix-<framework>` which consumes this report.

---

## Step 0 — Inputs

This step is load-bearing. The plan you produce changes substantially
depending on the target version and path shape — getting it wrong
means the user reads a plan for the wrong upgrade. Do not skip ahead.

**Required inputs:**

- **Current version** — detected from the manifest, but confirm.
- **Target version** — what version to upgrade to.
- **Path shape** — direct (current → target) or stepped through
  intermediate majors. Most stacks prefer major-by-major; some
  (Python language, Swift) support multi-step jumps cleanly.

If the user hasn't named the target, **ask before proceeding**.
Offer them three options:

1. **Name it directly** — e.g. `.NET 9`, `Next.js 15.0.3`,
   `Python 3.12`. You resolve any specific patch level from the
   latest stable in that line.
2. **Name a constraint and let you resolve** — e.g. "latest LTS",
   "one major ahead", "latest stable but not preview", "the version
   our deploy target supports". You read the relevant release feed
   and pick a concrete target. State your choice before producing
   the plan.
3. **Infer it yourself** — you read the current pinned version, look
   up the latest stable release for this stack, and pick a target.
   Default heuristic:
   - LTS-oriented stacks (.NET, Node) → the latest LTS.
   - Move-fast stacks (Next.js, React Native) → the latest minor of
     the latest stable major, unless that major is < 30 days old
     (early adoption risk — drop back one major).
   - Language versions (Python, Swift) → the latest stable the
     project's deploy targets support.

   State your choice and the reasoning before producing the plan.

Do not guess silently. A plan for the wrong target is worse than
asking.

If the upgrade path crosses multiple majors (e.g. .NET 6 → 8 crosses
7), also confirm whether intermediate majors are skipped or used as
stepping stones before continuing.

---

## Step 1 — Convention sourcing

Read every file the project uses to document conventions:

- `CLAUDE.md` at the repo root and any nested ones.
- `AGENTS.md`.
- `.github/copilot-instructions.md`, `.github/instructions/**/*.md`.
- `.cursor/rules/**/*` (or `.cursorrules`).
- Any `docs/upgrades.md` or `docs/<stack>-upgrade.md` from past
  upgrades — the patterns the team got bitten by last time.
- `CHANGELOG.md` — for context on what code recently shipped that
  might intersect with the upgrade.

Note any project-specific rules that affect the upgrade plan:
"upgrade only during merge-freeze windows," "always upgrade staging
two weeks before prod," etc.

---

## Step 2 — Detect current version

The variant supplies the detection commands. Report:

- Current version (exact).
- Target version (exact).
- Versions in the upgrade path.
- Source of truth (which file / lockfile the version comes from).

If multiple files disagree (e.g. `engines.node` says 18,
`.nvmrc` says 20, CI workflow uses 22), surface that as the first
finding — the upgrade plan can't be coherent until they agree.

---

## Step 3 — Catalogue breaking changes

The variant supplies the source URLs and the breaking-change
categories typical for this stack.

For each version in the upgrade path, list the breaking changes
under these umbrella categories:

- **Removed APIs** — gone entirely. Code using them won't compile /
  parse / run.
- **Renamed APIs** — moved to a new name. Old name may emit a
  deprecation warning but still work, or may be removed.
- **Behaviour changes** — same API, different semantics. The
  silent-failure class — code keeps "working" but does the wrong
  thing.
- **Default changes** — same API, different default. Often easy to
  miss because callers without explicit args silently get the new
  default.
- **Dependency upgrades** — the framework upgrade forces
  upgrades to other libs (peer deps, transitive constraints).
- **Tooling changes** — build tools, CLIs, config formats.

For each breaking change, capture:

- The category.
- A one-sentence description.
- The version it lands in.
- Whether a codemod / lint rule exists for it.

This catalogue is the input to Step 4's scan.

---

## Step 4 — Scan the repo for affected patterns

For each breaking change in the catalogue, scan the repo:

- For **removed / renamed APIs**: grep for the symbol. Concrete and
  reliable.
- For **behaviour changes** and **default changes**: harder. Often
  needs semantic understanding ("is this code path affected by the
  new default?"). State your reasoning, mark candidates rather than
  hard findings where uncertain.
- For **dependency upgrades**: read `package.json` /
  `pyproject.toml` / `.csproj` peer deps and constraints; identify
  conflicts.
- For **tooling / config**: read the config files; flag
  deprecated keys, removed flags.

For every finding, capture:

- File path and line number.
- Which breaking change it intersects with.
- Whether a codemod handles it automatically.
- Estimated effort (trivial / small / medium / large).

Be honest about uncertainty. "This call site *may* be affected by
the new fetch caching default — depends on whether the response is
cached upstream" is a more useful finding than a confident wrong
classification.

---

## Step 5 — Codemod / migration tool survey

The variant lists the codemods / lint rules / migration assistants
available for this upgrade. For each:

- Name, source.
- What it handles (which breaking-change categories).
- What it misses.
- How to dry-run it (preview without writing).

Run the dry-run if practical. Capture:

- Number of files the codemod would change.
- Categories of changes (sample).
- Known limitations from the codemod's docs.

Codemods are usually 60–90% of an upgrade — exhaustive for some
categories, blind for others. Surface what they cover and what
they don't, so the manual-effort estimate downstream is honest.

---

## Step 6 — Risk and effort assessment

For each breaking change with findings:

- ⚠️ **CRITICAL** — many call sites, no codemod, behaviour-change
  shape (silent risk).
- ⚠️ **HIGH** — many call sites, codemod handles most, manual
  review needed for the rest.
- ⚠️ **MODERATE** — few call sites or codemod handles cleanly.
- 💡 **LOW** — handled entirely by codemod / not used in this
  project.

Effort:

- **Trivial** — < 30min, codemod-only.
- **Small** — half-day, codemod + light review.
- **Medium** — 1–2 days, manual changes required across several
  modules.
- **Large** — week+, architectural change in places (e.g.
  Next.js Pages Router → App Router).

---

## Step 7 — Migration plan

Write the plan to `<root>/upgrades/<stack>-<from>-<to>-<timestamp>.md`,
where:

- `<root>` resolves in this order: `.playbook-audits/` if it
  exists, else `docs/` if `docs/upgrades/` exists (legacy
  convention), else create `.playbook-audits/` and append
  `.playbook-audits/` to `.gitignore` (creating `.gitignore` if
  absent — these are working artefacts, not tracked history).
- `<timestamp>` is current UTC time in basic ISO 8601 format
  `YYYYMMDDTHHMMSS` — generate with `date -u +%Y%m%dT%H%M%S`
  (e.g. `20260519T143022`).

Always write a new file; do not overwrite prior runs (even for the
same stack and version pair) — the directory is an ordered
history. Create the `<root>/upgrades/` directory if absent.

Produce an ordered, executable plan. Structure:

```
# <Stack> upgrade — <from> → <to>

Date: <today>
Stack variant: <variant>
Target version: <exact>
Upgrade path: <from> → <intermediate> → <to>
Convention sources read: <list>

## Verdict

<2-3 sentences — feasibility, biggest risk, total estimated effort.>

## Detected state

- Current version: <exact>
- Source of truth: <file>
- Conflicts: <if any>

## Breaking changes (catalogue)

| Category | Change | Version | Codemod? | Findings in repo |
|---|---|---|---|---|
| Removed API | `Foo.bar()` removed | 15.0 | yes (`upgrade-foo`) | 12 sites |
| Behaviour | fetch caching default flipped | 15.0 | no | unclear, 4 candidate sites |
| ... | ... | ... | ... | ... |

## Findings by file

<Grouped by file. Each finding cites the file, line, and which
breaking change it intersects.>

## Codemod plan

<Ordered list of codemods to run, with dry-run results.>

1. `npx @next/codemod@latest upgrade` — handles X, Y, Z.
   Dry-run: would modify 23 files.
2. ...

## Manual changes

<Findings the codemods don't handle, ordered by risk.>

1. ⚠️ CRITICAL — fetch caching default. Audit 4 call sites in
   `app/api/products/route.ts:42` and three siblings to confirm
   intended caching behaviour. ...
2. ...

## Test plan

<What to run / verify after the upgrade. Minimal:>

- Unit tests: <command>.
- E2E / smoke tests: <command>.
- Build: <command>.
- Bundle size delta: <command>, expected impact.
- Performance smoke: <pages or endpoints to hand-test>.

## Rollback plan

<How to revert if the upgrade misbehaves in production.>

- Git revert the version bump in the manifest + lockfile.
- Note any DB / state changes the upgrade would have introduced
  (rare for framework bumps; common for ORM majors).

## Risk-ranked recommendation

<One paragraph: do this upgrade now / do it after X / wait. The
prompt commits to a view; the user overrides.>
```

Each finding entry uses this shape:

- ⚠️ <SEVERITY> — `path/to/file:line` — Description in one
  sentence. **Codemod:** yes / no. **Effort:** trivial / small /
  medium / large.

If a category has no findings, mark it ✅ NOT USED IN THIS PROJECT.

---

## Constraints

- Do not change any manifest, lockfile, or source file. The plan
  is a script; the user runs it.
- Do not run codemods in mutate mode. Dry-run / preview only.
  Codemod output should be reported, not committed.
- Every finding must name a file and a line. "This codebase uses
  the deprecated foo pattern" is not acceptable — list the call
  sites.
- Behaviour-change findings (silent semantic shifts) get extra
  scrutiny. State the reasoning and the uncertainty rather than
  collapsing into a confident classification.
- If the upgrade path crosses multiple majors, do not flatten the
  breaking-change catalogue across all of them — group by version
  so the user can decide whether to take intermediate stops.
- If the project's deploy environment cannot support the target
  version (e.g. AWS Lambda Python runtimes lag the language by
  months; Vercel Node defaults differ from local), flag it in the
  Verdict before the plan. The plan is moot if the target can't be
  deployed.
- The risk-ranked recommendation must commit to a view (now /
  later / wait). "It depends" is not useful as a recommendation;
  state your conditions if you want to qualify.
