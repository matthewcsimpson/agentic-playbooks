---
description: Plan a Vite major upgrade (e.g. 4 → 5, 5 → 6, 6 → 7) — read release notes, scan for affected config / plugin / env patterns, survey migration tooling, produce a risk-ranked plan.
related: [stack-upgrade-fix-vite, post-milestone-audit-vite]
---

# Stack upgrade — Vite variant

Plan a Vite major version upgrade for an existing Vite project.

**This prompt extends [`core/stack-upgrade-audit.core.prompt.md`](./core/stack-upgrade-audit.core.prompt.md).**
Read the core first for the workflow shape (Steps 0–7, the report
format, and the Constraints). This file supplies the Vite-specific
detection commands, release-note sources, breaking-change
categories, migration tooling, and gotchas.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

This variant upgrades a project **already on Vite** across majors.
To migrate *onto* Vite from Create React App, use
`stack-upgrade-audit-cra` (it decides bump-in-place vs. migrate-off
and owns the CRA → Vite move).

---

## Assumed stack

- Vite (`vite.config.{ts,js,mjs}`) as the bundler / dev server.
- A framework plugin: `@vitejs/plugin-react` (Babel) or
  `@vitejs/plugin-react-swc`, or `@vitejs/plugin-vue`, or a Svelte /
  Solid / Qwik plugin. The plugin's major is coupled to Vite's.
- Often **Vitest** as the test runner — its major is coupled to the
  Vite major (Vitest 1 ↔ Vite 5, Vitest 2 ↔ Vite 5/6, Vitest 3 ↔
  Vite 6/7). A Vite bump usually forces a Vitest co-bump.
- Package manager: npm / pnpm / yarn (detect from lockfile).
- Deploy target: static host / CDN (Netlify, Vercel static, S3 +
  CloudFront, GitHub Pages), or a Node server serving the built
  `dist/`. The build output format matters for the deploy target.

---

## §2 — Detect current version

```sh
# Manifest version
jq '.devDependencies.vite, .dependencies.vite' package.json

# Resolved version
npm ls vite 2>/dev/null || pnpm ls vite 2>/dev/null || yarn why vite

# Framework plugin + test-runner majors (these co-bump)
jq '.devDependencies | to_entries
    | map(select(.key|test("vite|vitest|@vitejs"))) | from_entries' package.json

# Node version pins (Vite majors raise the Node minimum)
cat .nvmrc 2>/dev/null
jq '.engines.node' package.json
```

Vite majors raise the minimum Node version. Confirm `engines.node`,
`.nvmrc`, and the CI workflow's `node-version` all line up with what
the target Vite requires. If they disagree, that's the first
finding — the plan can't be coherent until they agree.

---

## §3 — Release notes sources

For each major in the upgrade path:

- Official migration guide: `https://vite.dev/guide/migration` (the
  current page covers the latest major; older majors are in the
  changelog / blog).
- Major-release blog posts: `https://vite.dev/blog` (e.g. "Vite 5.0
  is out!", "Vite 6.0 is out!").
- GitHub release notes:
  `gh release list --repo vitejs/vite --limit 40`
  then `gh release view <tag> --repo vitejs/vite`.
- The `CHANGELOG.md` shipped in `node_modules/vite/` — authoritative
  for behaviour notes.
- The matching framework-plugin and Vitest migration notes
  (`@vitejs/plugin-react`, `vitest`) — their breaking changes land
  in the same upgrade.

---

## §3.5 — Common breaking-change categories (Vite)

The catalogue varies by major; categories that recur:

- **Node baseline raised** — each major drops EOL Node lines (Vite 5
  → Node 18+, Vite 7 → Node 20.19+/22.12+). Removed Node = removed
  runtime support.
- **Config / option removals & renames** — legacy options dropped
  (`build.polyfillModulePreload` → `build.modulePreload`; CJS Node
  API of Vite removed in 5; `splitVendorChunkPlugin` removed in 7).
- **`import.meta.glob` signature** — the `as: 'raw'` / `as: 'url'`
  form was deprecated in favour of `query` + `import` (5).
- **Default changes** — default build target moving forward (Vite 7
  defaults to `'baseline-widely-available'`); CSS handling /
  minifier defaults; `resolve.conditions` defaults.
- **Environment API** (6+) — the new multi-environment model. Mostly
  additive for app authors, but custom plugins and SSR setups can be
  affected.
- **Sass / CSS preprocessor API** — the legacy Sass API path
  deprecation surfaces as build warnings/errors with newer `sass`.
- **Dependency co-bumps** — `@vitejs/plugin-react(-swc)` and
  `vitest` majors are pinned to the Vite major. esbuild / Rollup
  bumps ride along and can shift edge-case output.
- **Tooling / plugin API** — Rollup major bumps (Vite 5/6/7 track
  Rollup 4) can break community plugins that reach into Rollup
  internals.

For the specific upgrade target, fetch the migration guide and list
the *actual* changes — don't rely on the generic categories above.

---

## §4 — Scan patterns (Vite)

Patterns to scan for, adapted to the breaking changes in the path:

```sh
# The config itself — read every option for removed / renamed keys
cat vite.config.* 2>/dev/null

# Deprecated import.meta.glob "as" form
grep -rnE 'import\.meta\.glob\([^)]*\bas\b' --include='*.ts' --include='*.tsx' --include='*.js' src/

# CJS usage of the Vite Node API (removed in 5)
grep -rnE "require\(['\"]vite['\"]\)" .

# Removed helpers (splitVendorChunkPlugin removed in 7)
grep -rnE 'splitVendorChunkPlugin' .

# Build target / option keys that moved
grep -rnE 'polyfillModulePreload|build\.target|esbuildOptions' vite.config.* 2>/dev/null

# Env access surface (affected by define / mode changes)
grep -rnE 'import\.meta\.env\.' --include='*.ts' --include='*.tsx' src/ | head -50

# Sass / preprocessor config (legacy API deprecation)
grep -rnE 'preprocessorOptions|additionalData|sass' vite.config.* 2>/dev/null

# CI / deploy node version, so the co-bump is in scope
grep -rnE 'node-version|NODE_VERSION' .github/ 2>/dev/null
```

Specific high-attention patterns by version:

- **→ 7**: Node 20.19+/22.12+ required; default browser target is
  now `'baseline-widely-available'` (older-browser support needs an
  explicit `build.target`); `splitVendorChunkPlugin` removed.
- **→ 6**: Environment API introduced (SSR / custom-plugin impact);
  `resolve.conditions` / SSR defaults shifted; Sass legacy-API
  deprecation surfaces.
- **→ 5**: Node 18+ required; Vite's CJS Node API removed (config /
  scripts must be ESM); `import.meta.glob` `as` deprecated;
  `build.polyfillModulePreload` renamed.

---

## §5 — Migration tool survey (Vite)

**Vite ships no official codemod runner.** The migration is driven by
the migration guide, the build's own deprecation warnings, and
TypeScript. This makes the scan in §4 and the build's warning output
the primary signal — there is no transform to lean on.

Practical tooling to drive the survey:

```sh
# The build surfaces most deprecation / removed-option warnings.
# Read-only preview: run the build on the CURRENT version and capture
# warnings — do NOT bump anything yet (the bump is the fix prompt's job).
npm run build 2>&1 | grep -iE 'deprecat|warn|removed' || true

# npm's own view of what a bump would pull (no install):
npm outdated vite @vitejs/plugin-react vitest 2>/dev/null
```

- `npm run build` (current version) — the cheapest way to surface
  deprecation warnings the project is already tripping, which the
  next major will turn into errors.
- TypeScript (`tsc --noEmit`) — catches removed exports from the Vite
  type surface once types are bumped (the fix prompt does the bump).
- Community "Vite N migration" blog checklists — useful, but treat
  the official guide as authoritative.

Because there's no codemod, downstream effort is **manual-heavy** —
size the estimate accordingly. The win is that the affected surface
(config + a handful of `import.meta` call sites) is usually small and
well-localised compared to a framework-wide upgrade.

---

## §6 — Risk patterns specific to Vite

- **Node baseline mismatch** — the most common upgrade blocker. If
  the deploy runtime (Lambda, container base image, CI) can't run the
  Node minimum the target Vite requires, the upgrade is blocked at the
  platform, not the code. Surface this in the Verdict.
- **Plugin / Vitest version lock-step** — bumping Vite without
  co-bumping `@vitejs/plugin-react(-swc)` and `vitest` produces peer-
  dep errors or subtle runtime breakage. Treat the trio as atomic.
- **Default build-target shift** (→ 7) — `'baseline-widely-available'`
  can drop output support for older browsers the project still
  targets. If the project has a documented browser-support matrix,
  this needs an explicit `build.target` — a silent-risk default
  change.
- **CJS → ESM config** (→ 5) — a `vite.config.js` using
  `require()` / `module.exports`, or `"type"` absent from
  `package.json`, breaks. Config and any Node scripts importing Vite
  must be ESM.
- **Custom Rollup plugins** — Vite tracks Rollup majors. A community
  plugin reaching into Rollup internals can break even when its Vite-
  facing API is unchanged. Inventory third-party plugins and check
  each one's Vite-N compatibility.
- **SSR / Environment API** (→ 6) — projects doing SSR or running
  custom dev-server middleware are the most exposed to the
  Environment API changes; pure static SPAs are largely insulated.

---

## Constraints (Vite-specific addenda)

- There is no codemod. Do not imply one exists or that a transform
  will sweep the changes — the plan is manual edits plus version
  co-bumps, and the effort estimate must reflect that.
- Always inventory the framework plugin and Vitest versions
  alongside Vite — a plan that bumps Vite without naming the
  co-bumps is incomplete and will fail peer-dep resolution.
- The default-build-target change (→ 7) is a silent-risk class:
  include it as an explicit finding tied to the project's browser-
  support policy even if no code "uses" it.
- Confirm `engines.node` / `.nvmrc` / CI `node-version` against the
  target's minimum in the Detected-state section — Node-baseline
  mismatch is the most common reason this upgrade can't ship.
- If the project deploys the built `dist/` to a host with a fixed
  Node runtime, verify that runtime supports the target's Node
  minimum before the plan, not after.
