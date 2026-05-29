---
description: Plan a Create React App upgrade — decide bump-in-place vs. migrate off CRA (Vite / Next.js), scan for affected patterns, survey codemods, produce a risk-ranked migration plan.
related: [stack-upgrade-fix-cra]
---

# Stack upgrade — Create React App variant

Plan an upgrade for a project scaffolded with Create React App
(`react-scripts`).

**This prompt extends [`core/stack-upgrade-audit.core.prompt.md`](./core/stack-upgrade-audit.core.prompt.md).**
Read the core first for the workflow shape (Steps 0–7, the report
format, and the Constraints). This file supplies the CRA-specific
detection, the **bump-in-place vs. migrate-off decision**,
release-note sources, breaking-change categories, codemods, and
gotchas.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Assumed stack

- A React SPA scaffolded with Create React App: `react-scripts` in
  `package.json`, `public/index.html` with `%PUBLIC_URL%`,
  `REACT_APP_`-prefixed env vars, often a `jsconfig.json` /
  `tsconfig.json` with `baseUrl` for absolute imports.
- React 16 / 17 / 18; JavaScript or TypeScript.
- Package manager: npm / pnpm / yarn (detect from lockfile).
- Possibly already partly ejected, or using `craco` /
  `react-app-rewired` to override the webpack config.

**Context that shapes the whole plan:** Create React App was
officially **deprecated by the React team in February 2025**.
`react-scripts` is unmaintained, pinned to webpack 5, and will not
gain official React 19 support. So a CRA "upgrade" is not a single
linear bump — it forks into two materially different projects, and
**Step 0.5 below is where this variant decides which fork applies.**

---

## §0.5 — Decide the upgrade shape (do this before cataloguing)

This step is load-bearing and unique to CRA. The breaking-change
catalogue, the codemods, and the effort estimate are completely
different depending on the fork. Determine — and confirm with the
user — which of these the plan targets:

**Fork A — bump in place.** Keep `react-scripts`, raise React (e.g.
16/17 → 18) and `react-scripts` (e.g. 4 → 5). Viable when:

- The project is on React < 18 and just wants React 18.
- The team accepts staying on an unmaintained build toolchain for
  now.
- React 19 is **not** required (react-scripts has no official React
  19 support — that need forces Fork B).

**Fork B — migrate off CRA.** Replace `react-scripts` with a
maintained toolchain. Required when the team wants React 19, faster
builds, or simply to leave an EOL dependency. Present the target
options with a recommendation matched to the project:

- **Vite** — *default recommendation for a client-rendered SPA.*
  Closest conceptual match to CRA (SPA, dev server, static build),
  smallest migration surface, no routing/runtime paradigm shift.
  Recommend this unless the project needs SSR/SSG/SEO.
- **Next.js** — recommend when the project needs SSR / SSG, file-
  based routing, an integrated API layer, or has SEO requirements a
  client-only SPA can't meet. Larger migration (routing model
  changes; React Router → App/Pages Router). After migrating,
  `stack-upgrade-audit-nextjs` and `post-milestone-audit-nextjs`
  apply.
- **Remix / React Router framework mode** — recommend when the
  project already leans heavily on React Router and wants SSR
  without adopting Next's conventions.
- **Parcel / other** — only if the team has a specific reason; not a
  default.

State your recommendation **and the reasoning from the actual
project** (does it have SSR needs? heavy React Router use? a
`react-snap`/prerender step? SEO-sensitive routes?). Do not default
silently — the choice drives the entire plan. If the user has
already named a target, skip the recommendation and plan for it.

The rest of this variant has a **Fork A** track and a **Fork B**
track; follow the one the user picked.

---

## §2 — Detect current version

```sh
# react-scripts, react, react-dom (manifest + resolved)
jq '.dependencies."react-scripts", .dependencies.react, .dependencies."react-dom"' package.json
npm ls react react-dom react-scripts 2>/dev/null

# CRA fingerprints
ls public/index.html src/index.{js,jsx,ts,tsx} 2>/dev/null
grep -rnE '%PUBLIC_URL%' public/ 2>/dev/null | head
grep -rnE 'REACT_APP_' src/ .env* 2>/dev/null | head

# Config-override tools (change the migration surface)
jq '.dependencies.craco, .dependencies."react-app-rewired", .devDependencies.craco, .devDependencies."react-app-rewired"' package.json
ls craco.config.js config-overrides.js 2>/dev/null

# Already ejected?
ls config/webpack.config.js scripts/build.js 2>/dev/null && echo "EJECTED — react-scripts no longer drives the build"

# Node pin (Vite 5 needs Node 18+; Next 15 needs Node 18.18+)
jq '.engines.node' package.json
cat .nvmrc 2>/dev/null
```

If the project is **ejected** or uses **craco / react-app-rewired**,
say so prominently — the build is no longer vanilla CRA, so both
forks carry extra config-translation work that a stock CRA project
doesn't.

---

## §3 — Release notes sources

**React (both forks):**

- React 18 upgrade guide: `https://react.dev/blog/2022/03/08/react-18-upgrade-guide`.
- React 19 upgrade guide: `https://react.dev/blog/2024/04/25/react-19-upgrade-guide`.
- `react-codemod` repo: `https://github.com/reactjs/react-codemod`.

**Fork A — react-scripts:**

- CRA changelog: `https://github.com/facebook/create-react-app/releases`
  (note the repo is archived/deprecated — 5.0.1 is effectively the
  last meaningful release).
- The webpack 5 migration notes (react-scripts 4 → 5 moved to
  webpack 5 and dropped automatic Node core polyfills).

**Fork B — target toolchain:**

- Vite: `https://vitejs.dev/guide/` and community "CRA → Vite"
  migration guides; env handling `https://vitejs.dev/guide/env-and-mode`.
- Next.js: the official "Migrating from Create React App" guide
  `https://nextjs.org/docs/app/building-your-application/upgrading/from-create-react-app`.

---

## §3.5 — Common breaking-change categories

### Fork A — bump in place

- **React 17 → 18** — `ReactDOM.render` → `ReactDOM.createRoot`
  (and `hydrate` → `hydrateRoot`); automatic batching changes timing
  assumptions; `StrictMode` double-invokes effects in dev; new JSX
  transform; `useEffect` cleanup timing; some `@types/react` 18
  type tightenings.
- **react-scripts 4 → 5 (webpack 5)** — **automatic Node core-module
  polyfills removed**. Code (or a dependency) that imported
  `crypto` / `stream` / `buffer` / `path` / `process` for the
  browser now fails to build; needs explicit `fallback` config
  (via craco) or removal. This is the most common Fork-A breakage.
- **Tooling** — Sass/PostCSS version bumps, ESLint config changes,
  source-map handling.

### Fork B — migrate off CRA

The breaking changes are the *migration steps*, not version deltas:

- **`index.html`** — moves from `public/` to project root (Vite); or
  is replaced by the framework's document model (Next).
- **Env vars** — `REACT_APP_FOO` → `VITE_FOO` and
  `process.env.REACT_APP_FOO` → `import.meta.env.VITE_FOO` (Vite); or
  `NEXT_PUBLIC_FOO` (Next). `%PUBLIC_URL%` → `/` or `import.meta.env.BASE_URL`.
- **Entry point** — `src/index.js` import graph and `<div id="root">`
  wiring move; Vite needs `<script type="module" src="/src/main.jsx">`.
- **Asset / SVG imports** — CRA's `import { ReactComponent as Icon }`
  needs `vite-plugin-svgr` under Vite; `import logo from './logo.svg'`
  semantics differ.
- **Absolute imports** — `jsconfig.json`/`tsconfig.json` `baseUrl`
  needs a matching `resolve.alias` (Vite) or `paths` mapping.
- **Tests** — Jest (CRA's bundled runner) → Vitest (Vite) is the
  common pairing; test config moves out of `react-scripts test`.
- **Routing (Next only)** — React Router → App/Pages Router is an
  architectural change, not a config edit. This is what makes
  Fork-B-to-Next a **large** effort.

---

## §4 — Scan patterns

```sh
# React 18 root API (Fork A and any migration)
grep -rnE 'ReactDOM\.render\(|ReactDOM\.hydrate\(' --include='*.js' --include='*.jsx' --include='*.ts' --include='*.tsx' src/

# Node-core imports that webpack 5 / Vite won't polyfill (Fork A react-scripts 5, and Fork B)
grep -rnE "require\(['\"](crypto|stream|buffer|path|os|process|http|https|zlib)['\"]\)|from\s+['\"](crypto|stream|buffer|path|os|process)['\"]" --include='*.js' --include='*.ts' src/

# CRA-isms that must change on migration (Fork B)
grep -rnE 'process\.env\.REACT_APP_' --include='*.js' --include='*.jsx' --include='*.ts' --include='*.tsx' src/
grep -rnE '%PUBLIC_URL%' public/ src/ 2>/dev/null
grep -rnE 'ReactComponent' --include='*.js' --include='*.jsx' --include='*.ts' --include='*.tsx' src/   # SVG-as-component imports

# React Router usage (sizes the Fork-B-to-Next routing migration)
grep -rnE "from\s+['\"]react-router(-dom)?['\"]" --include='*.tsx' --include='*.jsx' src/ | head

# Test setup tied to react-scripts test / jest
grep -rnE 'react-scripts test|jest' package.json src/setupTests.* 2>/dev/null
```

For Fork B, the count of `REACT_APP_` references and SVG-component
imports directly sizes the mechanical migration; the React Router
surface sizes the Next.js routing rewrite (if Next is the target).

---

## §5 — Codemod survey

**React codemods (both forks, for the React bump):**

```sh
# React 19 migration recipe (also pulls in earlier cleanups)
npx codemod@latest react/19/migration-recipe          # dry-run by default in preview
# Individual react-codemod transforms (React 18 era)
npx react-codemod new-jsx-transform <path>
```

These cover JSX transform, `ReactDOM.render` → `createRoot` in many
cases, and deprecated-API renames. They do **not** cover automatic
batching behaviour changes or `StrictMode` double-invoke effects —
flag those ⚠️ manual-review.

**Fork B migration: no official codemod.** The CRA → Vite and CRA →
Next migrations are guide-driven and mechanical-edit-heavy
(`index.html` move, env-var rename, config authoring). Set the
expectation that Fork B is mostly hand-applied steps with the React
codemod as the only automated piece.

Run the React codemod dry and report the file count; do not run the
migration steps (they mutate the project layout).

---

## §6 — Risk patterns specific to CRA

- **react-scripts has no React 19 support** — if the goal is React
  19, Fork A is a dead end. Say so in the Verdict; the only path is
  Fork B.
- **webpack 5 polyfill removal (Fork A, rs 4 → 5)** — a transitive
  dependency pulling in `crypto`/`stream` for the browser breaks the
  build with a cryptic "Module not found: can't resolve 'crypto'".
  Enumerate the offending imports as findings.
- **craco / react-app-rewired** — these patch CRA's webpack config.
  Fork A must port the overrides to the new react-scripts; Fork B
  must translate them into `vite.config` / `next.config`. Either way
  it's extra, project-specific work — flag it.
- **Ejected projects** — `react-scripts` no longer owns the build;
  the project is a bespoke webpack setup. Both forks are effectively
  a from-scratch build-config migration; effort is **large**.
- **Env-var leakage assumptions (Fork B)** — CRA inlines
  `REACT_APP_*` at build time; Vite (`VITE_*`) and Next
  (`NEXT_PUBLIC_*`) have different exposure rules. A var that was
  public in CRA may need an explicit prefix to stay public, or
  conversely a secret may have been getting bundled — surface either.
- **SSR paradigm shift (Fork B → Next)** — components that touch
  `window`/`document` at module scope break under SSR. This is the
  largest hidden category in a CRA → Next migration; flag it
  prominently and size it from the React Router / global-access scan.

---

## Constraints (CRA-specific addenda)

- Always resolve the Fork A vs. Fork B decision (§0.5) **before**
  cataloguing breaking changes. A catalogue for the wrong fork is
  useless. If the user wants React 19, the plan must be Fork B —
  state that rather than producing a Fork A plan that can't reach
  the goal.
- For Fork B, the recommendation between Vite / Next / Remix must be
  grounded in the actual project (SSR needs, SEO, React Router
  surface), not a generic preference. Commit to a recommendation and
  give the user the trade-off.
- Treat ejected and craco/react-app-rewired projects as a separate,
  larger effort tier — the vanilla-CRA migration steps don't cover
  the custom build config.
- Surface the CRA-deprecation fact in the Verdict regardless of
  fork — even a Fork A bump is buying time on an EOL toolchain, and
  the user should make that choice knowingly.
- For a Fork-B-to-Next plan, note that the routing migration (React
  Router → App/Pages Router) is the dominant cost and hand off to
  `stack-upgrade-audit-nextjs` conventions for the Next-side detail
  rather than duplicating them here.
