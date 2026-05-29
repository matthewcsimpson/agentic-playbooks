---
description: Action findings from stack-upgrade-audit-cra. Either bump React + react-scripts in place, or run the migration off CRA (Vite / Next.js) the audit chose. Verify build, commit per category. Local only.
related: [stack-upgrade-audit-cra, stack-upgrade-audit-nextjs, post-milestone-audit-nextjs]
---

# Stack upgrade fix — Create React App variant

Action findings from a `stack-upgrade-audit-cra` report. The audit
chose a fork; this prompt executes it:

- **Fork A — bump in place**: raise React (+ `react-scripts`) while
  staying on CRA.
- **Fork B — migrate off CRA**: replace `react-scripts` with the
  toolchain the audit recommended (Vite / Next.js / Remix).

**This prompt extends [`core/stack-upgrade-fix.core.prompt.md`](./core/stack-upgrade-fix.core.prompt.md).**
Read the core first for the workflow shape (input scoping, locate
audit, per-category action, verify-and-commit gating, hand-off).

---

## Assumed stack

- A CRA project: `react-scripts` in `package.json`,
  `public/index.html`, `REACT_APP_` env vars.
- React 16 / 17 / 18; JS or TS.
- Package manager: detect from lockfile.

**Read the audit's fork decision first.** If the audit did not
record a fork (Fork A vs. Fork B, and for B which target), stop and
re-run `stack-upgrade-audit-cra` — this fix does not pick the fork.

---

## §2 — Re-verify the audit

```sh
jq -r '.dependencies."react-scripts" // empty, .dependencies.react // empty' package.json
npm ls react react-dom react-scripts 2>/dev/null | head
```

If `react-scripts` / `react` moved since the audit, stop and re-run
the audit. For Fork B especially, a moved baseline can invalidate
the migration steps.

---

## §3 — Codemods (both forks: the React bump)

Run the React codemod the audit identified, in apply mode, then
verify and commit:

```sh
# React 19 recipe, or the React 18-era transform the audit named
npx codemod@latest react/19/migration-recipe
# or, React 18 JSX transform:
npx react-codemod new-jsx-transform src/

npx tsc --noEmit          # if TS
npm run build
git add -A && git commit -m "upgrade(cra): apply React codemod (jsx-transform / createRoot)

Upstream: https://github.com/reactjs/react-codemod"
```

Codemods don't cover automatic-batching timing changes or
`StrictMode` double-invoke effects — those stay TODOs from the
audit.

---

## §4A — Fork A: bump in place

Only run this section if the audit chose Fork A.

**Mechanical edits** (apply the audit's flagged sites):

```js
// ReactDOM.render(<App/>, document.getElementById('root'))
//   → const root = ReactDOM.createRoot(document.getElementById('root'));
//     root.render(<App/>);
```

**webpack 5 polyfill removal** — for each Node-core import the audit
flagged, either drop it (browser code shouldn't need `crypto`/
`stream`) or, if a dependency requires it, add the fallback via
`craco` (do **not** eject):

```js
// craco.config.js — only if the audit confirmed a real dependency need
module.exports = { webpack: { configure: (c) => {
  c.resolve.fallback = { ...c.resolve.fallback, crypto: false, stream: false };
  return c;
}}};
```

**Version bump:**

```sh
npm install react@18 react-dom@18 react-scripts@5
npm install --save-dev @types/react@18 @types/react-dom@18   # if TS
git commit -m "upgrade(cra): bump react 17 → 18, react-scripts 4 → 5"
```

Skip §4B entirely.

---

## §4B — Fork B: migrate off CRA

Only run this section if the audit chose Fork B. Follow the track
for the target the audit recommended. These are mechanical migration
steps, not codemods — apply them as a single coherent category
(the app won't build mid-migration), verify once at the end of the
track, then commit. Under `risk:low`, confirm the target with the
user before starting — a migration is not a reversible per-site edit.

### Track: CRA → Vite (default SPA target)

```sh
# 1. Dependencies
npm install --save-dev vite @vitejs/plugin-react vite-plugin-svgr   # svgr only if ReactComponent imports exist
npm uninstall react-scripts

# 2. Move public/index.html → ./index.html, then:
#    - drop %PUBLIC_URL% (use /),
#    - add <script type="module" src="/src/main.jsx"></script> before </body>.
# 3. Rename src/index.js → src/main.jsx (entry must be referenced by index.html).
# 4. Author vite.config.js: react() plugin, svgr() if needed,
#    resolve.alias for any jsconfig/tsconfig baseUrl, server.proxy for the CRA proxy.
# 5. Env vars: REACT_APP_FOO → VITE_FOO; process.env.REACT_APP_FOO → import.meta.env.VITE_FOO.
# 6. package.json scripts: start→"vite", build→"vite build", preview→"vite preview".
```

Tests (if the audit flagged the Jest → Vitest move and it's in
scope):

```sh
npm install --save-dev vitest @testing-library/jest-dom jsdom
# point test config at vitest; "test": "vitest"
```

### Track: CRA → Next.js (when SSR / SEO / file routing is needed)

This is a **large** migration; follow the official guide
(`https://nextjs.org/docs/.../upgrading/from-create-react-app`) and
the audit's React-Router-surface findings. Headline steps:

```sh
npm install next@<target> react@<react-target> react-dom@<react-target>
npm uninstall react-scripts
# - Add next.config.js (output: 'export' for a static SPA equivalent, if no SSR yet).
# - Move src/index.* wiring into the App/Pages Router entry.
# - REACT_APP_FOO → NEXT_PUBLIC_FOO.
# - Migrate React Router routes to the chosen router (the dominant cost).
# - Guard window/document access for SSR.
```

For the Next-specific detail (async APIs, caching, image/link),
hand off to `stack-upgrade-audit-nextjs` after the migration lands —
do not duplicate Next breaking-change handling here.

---

## §5 — Version pins (Node)

If the target toolchain needs a newer Node than the project pins
(Vite 5 → Node 18+; Next 15 → Node 18.18+), move `engines.node`,
`.nvmrc`, the CI `node-version`, and any Dockerfile base image
together, per the audit:

```sh
git commit -m "upgrade(cra): require node ≥ 18.18 for <target toolchain>"
```

---

## §6 — Verification

```sh
# Per-category gate
npx tsc --noEmit          # if TS
npm run build             # Fork A: react-scripts build. Fork B: vite build / next build.

# Boot the dev server and hit the app — the real proof a migration worked
npm start &  sleep 5;  curl -fsS localhost:<port>/ >/dev/null && echo "boot OK" || echo "boot FAILED";  kill %1 2>/dev/null

# Full suite
npm test                  # CRA: react-scripts test. Vite: vitest. Next: its test setup.
```

For Fork B, a clean `build` plus a dev-server boot that serves the
root route is the gate — a typecheck pass does not prove the
`index.html` / entry / env wiring is correct.

---

## §7 — Hand off

- **Fork B → Next.js**: run `/playbook post-milestone-audit-nextjs`
  to catch Next-specific drift, then `/playbook stack-upgrade-audit-nextjs`
  if a further Next version bump is wanted.
- **Fork A or Fork B → Vite**: there's no CRA/Vite post-milestone
  variant. Run the generic catchers:

```
/playbook doc-code-drift-audit             # README scripts, env var names, node version
/playbook dead-code-audit                  # code orphaned by the migration
/playbook post-milestone-smoke-test-web    # drive the app's headline flows on the new build
```

Common residual drift after a CRA upgrade:

- README / CI still calling `react-scripts` scripts after a Fork B
  migration.
- Stray `REACT_APP_` / `%PUBLIC_URL%` references the rename missed.
- `window`/`document` module-scope access that only breaks under
  Next SSR.

---

## Constraints (CRA-specific addenda)

- Do not pick the fork. The audit chose Fork A vs. Fork B (and the
  Fork B target); this fix executes that choice. If the fork is
  missing from the audit, stop and re-run the audit.
- Never run a Fork B migration as a series of independently
  committed micro-edits — the app does not build mid-migration.
  Apply the target track as one coherent change, verify, then commit
  (the per-category gate applies between *tracks/categories*, not
  within a migration).
- Do not eject `react-scripts` to fix a Fork A webpack-5 polyfill
  issue. Use `craco` fallbacks, or remove the offending browser-side
  Node-core import. Ejecting is a one-way door outside this fix's
  scope.
- Never suppress an `ERESOLVE` React peer-dep error with
  `--legacy-peer-deps`. React 19 ecosystem lag is real; a library
  that can't resolve is a blocker to surface, not to force.
- Preserve env-var exposure semantics on a Fork B rename: confirm
  each `REACT_APP_` var should remain client-exposed under the new
  prefix (`VITE_` / `NEXT_PUBLIC_`) — do not blanket-rename a value
  that was being inlined by accident and is actually a secret.
- For Fork B → Next.js, do not hand-implement Next breaking-change
  handling here. Land the migration, then hand off to the nextjs
  variant.
