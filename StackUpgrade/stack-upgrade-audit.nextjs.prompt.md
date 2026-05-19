---
description: Plan a Next.js version upgrade — read release notes, scan for affected patterns, survey codemods, produce a risk-ranked migration plan.
related: [stack-upgrade-fix-nextjs]
---

# Stack upgrade — Next.js variant

Plan a Next.js version upgrade.

**This prompt extends [`core/stack-upgrade-audit.core.prompt.md`](./core/stack-upgrade-audit.core.prompt.md).**
Read the core first for the workflow shape (Steps 0–7, the report
format, and the Constraints). This file supplies the Next.js-
specific detection commands, release-note sources, breaking-change
categories, codemod tools, and gotchas.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Assumed stack

- Next.js (App Router or Pages Router or mixed).
- TypeScript or JavaScript.
- Package manager: npm / pnpm / yarn (detect from lockfile).
- Deploy target: Vercel, self-hosted Node, edge runtime, static
  export, or container — different upgrades affect these
  differently.

---

## §2 — Detect current version

```sh
# Manifest version
jq '.dependencies.next, .devDependencies.next' package.json

# Resolved version
npm ls next 2>/dev/null || pnpm ls next 2>/dev/null || yarn why next

# Node version pin
cat .nvmrc 2>/dev/null
jq '.engines.node' package.json
```

Next.js majors are tied to minimum Node versions. Confirm `engines.node`
(and `.nvmrc`, and the CI workflow's `node-version`) all line up with
what the target Next.js requires.

---

## §3 — Release notes sources

For each major in the upgrade path:

- Official upgrade guide: `https://nextjs.org/docs/app/building-your-application/upgrading/version-<N>`
  (replace `<N>` — e.g. `version-15`).
- GitHub release notes:
  `gh release list --repo vercel/next.js --limit 40`
  then `gh release view <tag> --repo vercel/next.js`.
- The `CHANGELOG.md` shipped in `node_modules/next/` (often the
  most authoritative for behaviour notes).

---

## §3.5 — Common breaking-change categories (Next.js)

The catalogue varies by major; common categories that recur:

- **Removed APIs** — old data-fetching primitives
  (`getServerSideProps` was deprecated under App Router; legacy
  `pages/api/*` shapes; removed config flags in `next.config.*`).
- **Renamed APIs** — `headers()` / `cookies()` / `params` /
  `searchParams` becoming async in 15+ is a renamed-shape change.
- **Behaviour changes** — fetch caching defaults flipping
  (uncached by default in 15 vs cached in 13/14); revalidate
  semantics; router cache invalidation; image optimisation
  defaults.
- **Default changes** — TypeScript strict mode defaults; ESLint
  config defaults; experimental flags graduating or being removed.
- **Dependency upgrades** — React major bumps required (React 18 →
  19 for Next 15), `eslint-config-next` updates, sharp / next-image
  internals.
- **Tooling changes** — Turbopack stability, dev-server defaults,
  build-output format, middleware runtime constraints.

For the specific upgrade target, fetch the upgrade guide and list
the *actual* changes — don't rely on the generic categories above.

---

## §4 — Scan patterns (Next.js)

Patterns to scan for, adapted to the breaking changes in the path:

```sh
# Async dynamic APIs (15+)
grep -rnE '\b(params|searchParams)\s*[:.]' --include='*.ts' --include='*.tsx' app/

# Direct cookies() / headers() / draftMode() usage
grep -rnE '\b(cookies|headers|draftMode)\(\)' --include='*.ts' --include='*.tsx' .

# fetch() with caching options
grep -rnE 'fetch\([^)]+(cache|next:|revalidate)' --include='*.ts' --include='*.tsx' .

# Pages router remnants if migrating
ls -la pages/ 2>/dev/null
grep -rnE 'getServerSideProps|getStaticProps|getInitialProps' --include='*.ts' --include='*.tsx' .

# Image / Link API
grep -rnE 'from\s+["\']next/image["\']' --include='*.tsx' .
grep -rnE 'from\s+["\']next/link["\']' --include='*.tsx' .

# next.config.{js,ts,mjs} flags
cat next.config.* 2>/dev/null

# middleware
ls -la middleware.ts middleware.js 2>/dev/null
```

Specific high-attention patterns by version:

- **→ 15**: Async `params` / `searchParams` / `cookies` / `headers`
  / `draftMode`. fetch caching default flipped. React 19 required.
- **→ 14**: Server Actions stability, `useFormState` →
  `useActionState`, partial prerendering experiments.
- **→ 13**: App Router introduction, RSC defaults, font / image
  changes.

---

## §5 — Codemod survey (Next.js)

The official codemod runner:

```sh
npx @next/codemod@latest upgrade            # dry-run first via --dry
npx @next/codemod@latest <transform> .      # specific transform
```

Common transforms relevant to recent upgrades:

- `app-dir-async-params` (→ 15).
- `app-dir-runtime-config-experimental-edge` (→ 14).
- `next-async-request-api` (→ 15).
- `new-link` (→ 13).
- `next-image-to-legacy-image` and `next-image-experimental` (→ 13).

Dry-run command:

```sh
npx @next/codemod@latest <transform> --dry .
```

The codemods cover the *mechanical* renames cleanly. They don't
cover:

- fetch caching behaviour shifts — semantic, per-call analysis
  needed.
- React 18 → 19 ripple effects (ref-as-prop, useFormState rename,
  `use()` patterns).
- ESLint rule changes from `eslint-config-next` updates.
- Runtime behaviour changes in middleware / edge.

Flag these as ⚠️ manual-review.

---

## §6 — Risk patterns specific to Next.js

- **Fetch caching default flip** (14 → 15) — the single biggest
  silent-risk change in recent history. Every `fetch()` that
  *relied on* the cached-by-default behaviour now hits the
  upstream every time, blowing up latency and cost. Audit every
  call site individually.
- **App Router migration** (any major while still on Pages Router)
  — this is not a version-bump task; it's an architectural
  migration. The upgrade prompt's effort estimate should be
  **large** if the project still has a `pages/` directory and is
  jumping multiple majors.
- **Middleware runtime restrictions** — edge runtime gained / lost
  APIs between majors. Code that worked on Node may not work on
  edge.
- **Image optimisation provider** — default loaders change; CDN
  rules may need updating.
- **Build output** — standalone output, runtime config, server
  files layout. CI / deploy infrastructure may need updates.
- **React major change required** — Next 15 needs React 19.
  Library compatibility is the long pole; a Next upgrade can
  block on a single non-compatible library.

---

## Constraints (Next.js-specific addenda)

- The fetch caching default change is the most common cause of
  post-upgrade incidents. Always include it as an explicit
  finding even if the project's call sites look "obvious" — the
  silent-risk class warrants explicit scrutiny.
- Treat the `experimental.*` config keys as a separate audit pass
  — experimental flags graduate or get removed across majors, and
  the upgrade can fail loudly on a removed flag.
- If the project deploys to Vercel, mention any Vercel-specific
  defaults that change at the platform level alongside the
  Next.js bump (e.g. Edge runtime defaults).
- For App Router projects, server / client component boundaries
  may change in subtle ways across majors — flag any RSC-relevant
  behaviour changes prominently.
- React peer-dep mismatch is the most common upgrade blocker.
  Surface it in the Verdict, not buried in Findings.
