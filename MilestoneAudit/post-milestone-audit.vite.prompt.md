---
description: Audit a Vite + React (client-rendered SPA) + TypeScript codebase after a milestone tag is cut — drift, regressions, extraction signals, and convention compliance.
related: [post-milestone-fix]
---

# Post-milestone audit — Vite / React SPA variant

Audit a Vite-bundled, client-rendered React single-page app
(TypeScript) after a milestone tag is cut.

**This prompt extends [`core/post-milestone-audit.core.prompt.md`](./core/post-milestone-audit.core.prompt.md).**
Read the core file first for the workflow shape, audit-window logic,
convention-source discovery, delta logic, output format, and
constraints. This file supplies the Vite / React-SPA specifics for §2
examples, §3 milestone-diff focus, §4 regression sweeps, §4.5
extraction signals, and the §5 drift counter.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

This is the variant for **client-rendered** React: a Vite dev server
and `vite build` producing static assets, no server components, no
server-side rendering. For Next.js (App Router / RSC / server
actions) use `.nextjs`. For React Native / Expo use `.react-native`.
A Create React App project mid-migration to Vite, or just migrated,
audits cleanly here once `react-scripts` is gone.

---

## Assumed stack

- **Build tool**: Vite (`vite.config.{ts,js,mjs}`), `index.html` at
  the project root with `<script type="module" src="/src/main.tsx">`.
- **Language**: TypeScript (`.ts` / `.tsx`).
- **Framework**: React, rendered entirely on the client (`createRoot`
  in `src/main.tsx`). No server components, no SSR.
- **Routing**: client-side — `react-router` / `react-router-dom`,
  TanStack Router, or Wouter. No file-system routing.
- **Data**: TanStack Query / SWR / RTK Query, or hand-rolled `fetch`
  in effects. API base URL comes from an env var.
- **Styling**: CSS Modules (`*.module.{css,scss}`), Tailwind,
  vanilla-extract, or a CSS-in-JS solution — the variant's styling
  checks adapt to whichever the project uses.
- **Testing**: Vitest + React Testing Library for unit/component;
  Playwright or Cypress for E2E (not exercised by this audit).
- **Package manager**: pnpm / npm / yarn (commands inferred from the
  lockfile and `package.json`).

If the project deviates from these assumptions, fall back to the
generic categories where the variant's checks don't apply.

---

## §2 — Per-rule sweep (Vite / React-SPA rule categories to look for)

Beyond the convention sources listed in the core, also read:

- `tsconfig.json` / `tsconfig.app.json` — `strict` settings, path
  aliases (these must be mirrored in `vite.config` `resolve.alias`
  and, if used, `vite-tsconfig-paths`).
- `vite.config.{ts,js,mjs}` — `resolve.alias`, `define`, `base`,
  `server.proxy`, `build.rollupOptions` (especially `manualChunks`),
  active plugins.
- `.env`, `.env.*`, and `env.d.ts` / `vite-env.d.ts` — which env vars
  are declared, and the `ImportMetaEnv` interface if typed.
- `eslint.config.*` / `.eslintrc.*` — active rule plugins (especially
  `eslint-plugin-react`, `eslint-plugin-react-hooks`,
  `eslint-plugin-react-refresh`).
- `package.json` `scripts` — to identify the dev / build / preview /
  lint / test commands.

Common rule categories the project's docs tend to enforce — sweep
each one that the project actually documents:

- **Language / spelling** — locale conventions in code, comments,
  strings, identifiers.
- **File extensions** — TypeScript only (`.ts` / `.tsx`); no stray
  `.js` / `.jsx` outside tooling config exceptions like
  `eslint.config.js` / `vite.config.js`.
- **Imports** — alias preferences (`@/...` over `../../...`); the
  alias must resolve in *both* `tsconfig` `paths` and Vite
  `resolve.alias` (a TS-only alias typechecks but fails at runtime).
- **Env access** — client env read via `import.meta.env.VITE_*` only;
  no `process.env` in client code (Vite does not define it by
  default); secrets never given a `VITE_` prefix (the prefix inlines
  the value into the shipped bundle).
- **Routing** — where route definitions live; lazy-loaded route
  components vs eagerly imported; consistent use of the router's
  `<Link>` over bare `<a>` for internal navigation.
- **Naming** — variable / function / file / component conventions,
  single-letter variables, component prefix codes.
- **Functions** — arrow vs `function` declaration; helper
  search-before-write; prop-drilling thresholds.
- **Components** — required file grouping (`.tsx` +
  `.module.{css,scss}` + optional types/helpers), folder structure,
  prefix conventions, colocation rules.
- **Assets** — imported assets (`import logo from './logo.svg'`) vs
  `public/` static files vs `new URL('./x', import.meta.url)`;
  consistency with the project's documented asset convention.
- **Testing** — required colocated tests, Vitest vs Playwright
  placement, banned flags (`--passWithNoTests`).

---

## §3 — Milestone diff focus

For files changed in this milestone, check:

- **New components**: follow the project's structural rules (prefix,
  file grouping, colocation)? Reasonable size, or already a
  decomposition candidate?
- **New utilities / hooks**: placed correctly per the project's
  layering rules (pure helpers in a shared module, React-coupled
  logic in a `use*` hook)? Tested?
- **New env var reads**: accessed via `import.meta.env.VITE_*` (not
  `process.env`)? The var declared in `.env.example` and typed in
  `vite-env.d.ts` / `env.d.ts`? **Not** a secret given a `VITE_`
  prefix — anything `VITE_`-prefixed ships to the browser in clear.
- **New routes**: lazy-loaded with `React.lazy` + `Suspense` where
  the route is heavy, or deliberately eager? Wrapped in the
  project's error boundary?
- **New data fetching**: uses the project's data layer (TanStack
  Query / SWR / RTK Query) rather than ad-hoc `useEffect` + `fetch`
  where a convention exists? Loading and error states handled?
- **New `vite.config` changes**: new plugin justified? New
  `manualChunks` / `build` options deliberate? New `define` entries
  not leaking secrets?
- **New aliases**: added to *both* `tsconfig` `paths` and Vite
  `resolve.alias` (or covered by `vite-tsconfig-paths`)?
- **New dynamic `import()`**: used for code-splitting heavy or
  rarely-used modules, and paired with a loading state?
- **New dependencies in `package.json`**: justified, pinned
  appropriately, placed in `dependencies` vs `devDependencies`
  correctly (build-time-only tooling belongs in `devDependencies`)?
- **New TODO / FIXME comments**: list every one with file and line.
- **New `console.log` / `console.warn` / `console.error` calls**:
  list every instance (these ship to the browser console in prod
  unless stripped by config — note whether the build strips them).

---

## §4 — Full-sweep regression check

### TypeScript quality
- Non-null assertions (`!`).
- Type assertions (`as SomeType`) suppressing legitimate errors.
- Implicit `any` that should be tightened.
- `@ts-ignore` / `@ts-expect-error` without an explanatory comment.
- Missing return types on exported functions.

### React patterns
- `useEffect` hooks that could be derived state or event handlers.
- `useEffect` fetching data where the project has a data-layer
  convention (TanStack Query / SWR) that should own it.
- `useState` chains describing one coherent piece of state (usually
  a `useReducer` or custom hook in disguise).
- Prop drilling deeper than 2 levels (consider context or
  composition).
- Missing `key` props on lists; index-as-key on reorderable lists.
- Context providers re-creating their `value` object every render
  (missing `useMemo`), forcing all consumers to re-render.

### Vite / SPA patterns
- `process.env.*` reads in client code (undefined at runtime under
  Vite unless explicitly `define`d — silent `undefined`).
- Env vars read without the `VITE_` prefix expecting client exposure
  (silently `undefined`).
- Secrets or server-only values given a `VITE_` prefix (inlined into
  the public bundle — a leak).
- Path aliases present in `tsconfig` but missing from Vite
  `resolve.alias` (typechecks, breaks at runtime / build).
- Heavy modules (charts, editors, PDF, date-locale bundles) imported
  statically at the top level instead of lazy-loaded — bloats the
  initial chunk.
- No route-level code-splitting in an app large enough to warrant it
  (a single oversized vendor chunk).
- Assets referenced by hardcoded `/src/...` paths rather than
  imported (breaks under `base` / hashing).

### Data and API
- Fetch calls with no error handling or no loading state.
- Hardcoded API URLs that should be `import.meta.env`-derived.
- Over-fetching where the API supports field selection / pagination.
- N+1 request patterns (a fetch inside a `.map` over a list).

### Styling
- Hardcoded colour values that should be CSS custom properties or
  theme tokens.
- Magic spacing / sizing numbers that should be variables / tokens.
- `!important` declarations.
- Inline `style` props (other than dynamically setting CSS custom
  properties).

### Error handling
- Empty catch blocks or catch-and-log-only.
- Missing error boundaries around route-level or lazy-loaded
  subtrees (an unhandled render error blanks the whole SPA).
- Promise rejections in event handlers swallowed without surfacing.

### Security (regression check only)
- `VITE_`-prefixed env vars holding secrets (shipped to the client).
- Tokens / API keys committed in `.env` files that are tracked by
  git (check `git ls-files | grep -i env`).
- `dangerouslySetInnerHTML` with unsanitised user content.
- User-controlled values flowing into `href` / `src` without
  scheme validation (`javascript:` URLs).

### Dependency hygiene
- Circular imports.
- `devDependencies` imported by application runtime code paths.
- Duplicate logic that suggests a missing shared utility.

---

## §4.5 — Extraction

### Component decomposition

- Any component file longer than ~250 lines, or with a render
  function longer than ~80 lines. Length isn't automatically wrong,
  but it's a signal worth surfacing.
- Any render function containing nested conditional sub-trees that
  are really separate components in disguise.
- Any component containing JSX structurally identical to JSX in
  another component, where a shared primitive would absorb both.
- Any component with three or more `useState` calls that together
  describe a single coherent piece of state.
- Any component with a `useEffect` body longer than ~20 lines, or
  three or more `useEffect`s — typically a custom hook is hiding
  inside.

### Logic extraction

- Any function defined inside a component body that is pure (no
  closure over component state) and longer than a few lines —
  should be hoisted to module scope or moved to a `.helpers.ts` /
  `.utils.ts`.
- Any data-shaping logic (mapping, filtering, grouping, sorting,
  deriving display values) appearing at the top of two or more
  components — should be a shared helper.
- Any inline JSX expression performing non-trivial computation —
  should be a `useMemo` or extracted helper.
- Any data-fetching + caching logic repeated across components —
  should be a custom hook (or a query hook if the project uses
  TanStack Query / SWR).

### Promotion candidates

- Any component used by two or more features that could move to a
  shared UI module / package.
- Any helper that is pure and could move to a shared utility module.
- Any constant defined in two or more files — should move to a
  shared constants module.

### Demotion / scope-creep candidates

- Any shared UI component that has accumulated feature-specific
  props — should move back to its feature folder.
- Any "pure" helper that has acquired an import from the router,
  the data layer, or browser globals — no longer pure; move it
  to the appropriate layer.

---

## §5 — Drift counter (Vite / React-SPA rule set)

| Rule | Violations |
|---|---|
| `function` declarations (where arrow expected) | N |
| Single-letter variables | N |
| `../` imports (where alias expected) | N |
| Aliases in `tsconfig` missing from Vite `resolve.alias` | N |
| `process.env.*` reads in client code | N |
| `VITE_`-prefixed secrets (client-exposed) | N |
| `console.log/warn/error` in production code | N |
| `!important` in styling | N |
| Non-null assertions (`!`) | N |
| `as`-cast type assertions | N |
| `@ts-ignore` / `@ts-expect-error` without comment | N |
| TODO / FIXME comments | N |
| Components missing required prefix / file grouping | N |
| Heavy modules imported statically (not lazy-loaded) | N |

Adapt the rows to match what the project actually documents — add
rows for rules the project enforces that aren't in this default
list, and drop rows for conventions it doesn't have.
