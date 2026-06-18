---
description: Action findings from stack-upgrade-audit-vite. Apply config edits, bump vite + framework plugin + vitest + Node engines together, verify via vite build, commit per category. Local only.
related: [stack-upgrade-audit-vite, post-milestone-audit-vite]
---

# Stack upgrade fix — Vite variant

Action findings from a `stack-upgrade-audit-vite` report against a
Vite project.

**This prompt extends [`core/stack-upgrade-fix.core.prompt.md`](./core/stack-upgrade-fix.core.prompt.md).**
Read the core first for the workflow shape (input scoping, locate
audit, per-category action, verify-and-commit gating, hand-off to
`post-milestone-audit-vite`). This file supplies Vite-specific
commands and gotchas.

Vite ships **no codemod runner**, so the canonical `codemods`
category from the core does not apply here. The Vite fix categories
are `config-edits` (mechanical config/source edits the audit
documented) and `version-bump` (Vite + plugin + Vitest + Node
co-bump). `post-bump` adoption is opt-in.

---

## Assumed stack

- Vite (`vite.config.{ts,js,mjs}`).
- Framework plugin: `@vitejs/plugin-react` or
  `@vitejs/plugin-react-swc` (or the Vue / Svelte / Solid plugin).
  Its major is locked to the Vite major.
- Often **Vitest** — its major is locked to the Vite major too.
- Package manager: detect from lockfile (`package-lock.json` → npm,
  `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn classic / berry).
- Deploy target: static `dist/` on a CDN, or a Node server. The Node
  baseline of the target matters for the version bump.

---

## §2 — Re-verify the audit

```sh
# Confirm the pinned vite version hasn't moved since the audit
jq -r '.devDependencies.vite // .dependencies.vite' package.json

# Confirm the plugin + test-runner positions the audit recorded
jq -r '.devDependencies | to_entries
       | map(select(.key|test("@vitejs|vitest"))) | from_entries' package.json
```

If `vite` is no longer at the version the audit recorded, stop and
re-run `stack-upgrade-audit-vite`. Acting on a stale plan is how the
silent default-change findings (build target, env handling) get
missed.

---

## §3 — Config & source edits

There is no codemod — apply the audit's documented from→to edits by
hand, grouped by category, verifying and committing per category.
Common categories:

```sh
# vite.config: renamed / removed option keys, e.g.
#   build.polyfillModulePreload  → build.modulePreload      (→ 5)
#   splitVendorChunkPlugin()     → manualChunks config       (→ 7, removed)
#
# import.meta.glob: deprecated `as` form → query + import    (→ 5)
#   import.meta.glob('./x/*', { as: 'raw' })
#     → import.meta.glob('./x/*', { query: '?raw', import: 'default' })
#
# CJS config → ESM (→ 5): module.exports → export default,
#   require() → import; ensure package.json "type":"module"
#   or the config file is named vite.config.mjs.
```

For each category the audit listed, apply across all flagged sites,
verify, and commit:

```sh
git add -A
git commit -m "upgrade(vite): migrate import.meta.glob to query+import form

Upstream: https://vite.dev/guide/migration"
```

If a finding is a **silent default change** the audit flagged
(notably the → 7 `build.target` default moving to
`'baseline-widely-available'`), and the project has a documented
browser-support matrix, set `build.target` explicitly to preserve
the old behaviour rather than accepting the new default. If the
audit's specification is ambiguous, surface it as a TODO — do not
improvise.

---

## §4 — Version bump (Vite + plugin + Vitest, atomic)

The trio is locked in lock-step — bump them in one command and one
commit. Bumping Vite without the plugin / Vitest co-bump fails
peer-dep resolution or breaks the test run.

```sh
# npm
npm install --save-dev vite@<target> @vitejs/plugin-react@<target> vitest@<target>

# pnpm
pnpm add -D vite@<target> @vitejs/plugin-react@<target> vitest@<target>

# yarn
yarn add -D vite@<target> @vitejs/plugin-react@<target> vitest@<target>
```

Use `@vitejs/plugin-react-swc` in place of `@vitejs/plugin-react` if
that's what the project uses. Include any other Vite-coupled plugins
the audit flagged (`vite-tsconfig-paths`, `vite-plugin-svgr`, etc.)
in the same bump.

If the audit flagged a Node baseline raise, edit `engines.node`,
`.nvmrc`, and the CI `node-version` in the **same commit** — the
project can't build / deploy without all of them aligned:

```sh
# package.json engines.node
jq '.engines.node = ">=20.19.0"' package.json > /tmp/pkg && mv /tmp/pkg package.json

# .nvmrc
echo '20.19' > .nvmrc
```

Commit the bump as one unit:

```sh
git commit -m "upgrade(vite): bump vite 5 → 6, @vitejs/plugin-react 4 → 5, vitest 1 → 2, node ≥ 20.19"
```

Never suppress a peer-dep `ERESOLVE` with `--legacy-peer-deps` /
`--force` — a plugin that can't resolve against the target Vite is a
blocker to surface, not to paper over.

---

## §5 — Post-bump edits (opt-in)

Edits that only make sense after the bump, and only if the user
opted into the `post-bump` scope:

- Adopting the Environment API (→ 6) in custom dev-server middleware
  or SSR setups the audit identified.
- Replacing a removed helper with its successor pattern (e.g.
  `splitVendorChunkPlugin` → an explicit `build.rollupOptions.
  manualChunks` function), if the audit recommended it rather than
  just removing the call.

These are adoption, not strict-upgrade fixes — surface as TODOs
unless explicitly opted into.

---

## §6 — Verification

```sh
# Per-category gate
npx tsc --noEmit                      # or: pnpm typecheck / yarn typecheck
npm run lint
npm run build                         # the most useful gate — surfaces
                                      # removed options, bad config, and
                                      # remaining deprecation warnings as errors

# Full suite when all categories are done
npm test                              # vitest — confirm the co-bumped runner is green
npm run preview &                     # smoke the built output locally if practical

# Inspect deprecation warnings the build still prints
npm run build 2>&1 | grep -iE 'deprecat|warn' || true
```

`vite build` is the load-bearing gate — it's where removed options
and incompatible plugins fail loudly. A green `tsc` alone does not
prove the upgrade landed.

For monorepos, scope to the affected workspace:

```sh
pnpm --filter <app> build
turbo run build --filter=<app>
```

---

## §7 — Hand off

After the full suite passes, recommend:

```
/playbook post-milestone-audit-vite
```

to catch residual drift the mechanical upgrade didn't touch.

Common residual drift after a Vite upgrade:

- `README.md` / CI still referencing an old Node version or a removed
  Vite flag.
- `vite.config` still carrying a now-default option that can be
  deleted (noise, not breakage).
- A community plugin pinned to an old major that resolved but logs
  runtime deprecation warnings.
- Browser-support regressions from the → 7 default target change if
  `build.target` wasn't set explicitly.

---

## Constraints (Vite-specific addenda)

- Never bump `vite` without co-bumping the framework plugin and
  Vitest in the same commit. The trio is atomic; a partial bump is a
  broken tree.
- Never suppress an `ERESOLVE` peer-dep error with
  `--legacy-peer-deps` / `--force`. An unresolvable plugin is a real
  blocker — surface and stop.
- Do not accept the → 7 `build.target` default silently when the
  project documents an older-browser support matrix — set
  `build.target` explicitly, per the audit.
- `vite build` must pass before a category is committed. A passing
  `tsc` is not sufficient — config / plugin removals only fail at
  build time.
- Do not edit CI / deploy config (Dockerfile, `vercel.json`,
  `netlify.toml`, CI workflows) beyond the Node-version co-bump the
  audit flagged. Broader pipeline drift is a separate PR.
