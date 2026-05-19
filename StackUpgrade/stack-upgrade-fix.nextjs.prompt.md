---
description: Action findings from stack-upgrade-audit-nextjs. Run @next/codemod transforms per audit plan, bump next + react peer deps, verify build, commit per codemod. Local only.
related: [stack-upgrade-audit-nextjs, post-milestone-audit-nextjs]
---

# Stack upgrade fix — Next.js variant

Action findings from a `stack-upgrade-audit-nextjs` report against a
Next.js project.

**This prompt extends [`core/stack-upgrade-fix.core.prompt.md`](./core/stack-upgrade-fix.core.prompt.md).**
Read the core first for the workflow shape (input scoping, locate
audit, per-category action, verify-and-commit gating, hand-off to
`post-milestone-audit-nextjs`). This file supplies Next.js-specific
commands and gotchas.

---

## Assumed stack

- Next.js (App Router, Pages Router, or mixed).
- TypeScript or JavaScript.
- Package manager: detect from lockfile (`package-lock.json` →
  npm, `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn classic / berry).
- React peer dep — Next 15 requires React 19, Next 14 React 18+.
- Deploy target — Vercel / self-hosted Node / edge runtime / static
  export. Some upgrades affect these differently.

---

## §2 — Re-verify the audit

```sh
# Confirm the pinned next version hasn't moved since the audit
jq -r '.dependencies.next // .devDependencies.next' package.json

# Confirm React peer dep position
jq -r '.dependencies.react // empty, .dependencies["react-dom"] // empty' package.json
```

If `next` is no longer at the version the audit recorded, stop and
re-run `stack-upgrade-audit-nextjs`. Acting on a stale plan is how
fetch-caching incidents happen.

---

## §3 — Codemods

The official Next.js codemod CLI runs transforms one at a time.
**Always apply mode here** (the audit ran `--dry`). Use the codemod
name the audit's plan specified:

```sh
npx @next/codemod@latest <transform> .
```

Common transforms by upgrade target:

| Transform | Target | Handles |
|---|---|---|
| `next-async-request-api` | → 15 | `cookies()`, `headers()`, `draftMode()`, `params`, `searchParams` becoming async |
| `app-dir-runtime-config-experimental-edge` | → 14 | `experimental.runtime` config flag moves |
| `new-link` | → 13 | `<Link>` no longer needs `<a>` child |
| `next-image-to-legacy-image` | → 13 | Opt out of the new image component temporarily |
| `next-image-experimental` | → 13 | Migrate to the new image component eagerly |
| `built-in-next-font` | → 13.2 | `@next/font` → `next/font` |

Run each one separately, verify, and commit per codemod:

```sh
# 1. Run the codemod (apply mode)
npx @next/codemod@latest next-async-request-api .

# 2. Verify
npx tsc --noEmit                       # or: pnpm typecheck / yarn typecheck
npm run lint
npm run build

# 3. Commit if green
git add -A
git commit -m "upgrade(nextjs): apply next-async-request-api codemod

Upstream: https://nextjs.org/docs/messages/sync-dynamic-apis"
```

**Codemods that need a clean tree.** `@next/codemod` writes to the
working tree; verify `git status` is clean before each run.

**Codemod limitations to surface as TODOs:**

- **Fetch caching default flip (14 → 15)** — no codemod. Every
  `fetch()` that relied on the cached-by-default behaviour needs
  per-call-site review. The audit should have listed candidate
  sites; surface them as TODOs in the fix report rather than
  applying a blanket transformation.
- **React 18 → 19 ripple effects** — `useFormState` →
  `useActionState`, `forwardRef`/`ref` prop changes, `use()`
  patterns. Some are codemod-able via React's own codemod runner
  (`npx codemod@latest react/19/...`); apply those separately and
  commit alongside the React bump.
- **ESLint config drift from `eslint-config-next` updates** —
  surface as a TODO; the fix prompt doesn't sweep lint config.

---

## §4 — Mechanical edits

Apply the audit's documented from→to pairs. Examples:

```sh
# Renamed config keys in next.config.{js,ts,mjs}
# experimental.serverComponentsExternalPackages → serverExternalPackages (→ 15)
# experimental.bundlePagesExternals → bundlePagesRouterDependencies (→ 15)

# Renamed imports
# import { useRouter } from 'next/router'  → 'next/navigation' (Pages → App)
```

For each mechanical-edit category the audit listed, apply across
all flagged sites, verify, commit per category:

```sh
git commit -m "upgrade(nextjs): rename experimental.serverComponentsExternalPackages to serverExternalPackages"
```

If the audit's specification for a category is ambiguous ("rewrite
this call to use the new pattern"), surface as a TODO. Do not
improvise.

---

## §5 — Version bump

```sh
# npm
npm install next@<target> react@<react-target> react-dom@<react-target>

# pnpm
pnpm add next@<target> react@<react-target> react-dom@<react-target>

# yarn classic
yarn add next@<target> react@<react-target> react-dom@<react-target>

# yarn berry
yarn add next@<target> react@<react-target> react-dom@<react-target>
```

The peer-dep co-bumps for React are atomic with the Next bump —
commit them together. Next 15 + React 19 is the canonical pair; Next
14 supports React 18.2+.

Also bump `eslint-config-next` to match the major:

```sh
npm install --save-dev eslint-config-next@<target>
```

If the audit flagged `engines.node` / `.nvmrc` / CI Node version
needing co-bump for the target Next.js, edit those alongside (they
go in the same commit — the codebase can't deploy without all of
them):

```sh
# package.json engines.node
jq '.engines.node = ">=18.18.0"' package.json > /tmp/pkg && mv /tmp/pkg package.json

# .nvmrc
echo '20' > .nvmrc
```

Commit:

```sh
git commit -m "upgrade(nextjs): bump next 14.2.5 → 15.0.3, react 18 → 19, node ≥ 18.18"
```

---

## §6 — Post-bump edits

Edits that only make sense after the bump. Most common:

- React 19 `use()` patterns where the codemod couldn't infer the
  refactor.
- New App Router conventions that the audit identified as available
  *if* the team wants them (e.g. `unstable_after`, parallel routes).
  These are opt-in adoption, not strict-upgrade fixes — usually
  surface as TODOs unless the user opted into them explicitly.

---

## §7 — Verification

```sh
# Per-category gate
npx tsc --noEmit
npm run lint
npm run build              # the most useful gate — catches Metadata API misuse, bad async params, missing types

# Full suite when all categories are done
npm test                   # or: pnpm test / yarn test / jest / vitest
npm run e2e                # if present

# Bundle-size sanity
ls -lh .next/static/chunks/ | head     # ad-hoc; for real numbers use a bundle analyser
```

For monorepos, scope to the affected workspace:

```sh
turbo run build --filter=<app>
pnpm --filter <app> build
```

---

## §8 — Hand off

After the full suite passes, recommend:

```
/playbook post-milestone-audit-nextjs
```

Common residual drift after a Next upgrade:

- `next.config.*` with deprecated keys the codemod missed because
  it didn't recognise a custom plugin wrapper.
- Middleware files using edge-runtime APIs that changed semantics.
- Documentation drift in `README.md` install commands.

---

## Constraints (Next.js-specific addenda)

- Never apply the `next-image-experimental` codemod without
  explicit opt-in from the user. It rewrites image usage across
  the codebase in a way that's hard to review.
- The fetch caching default flip is **not** codemod-able. Do not
  attempt a blanket transformation; every call site is a per-site
  decision (was this code relying on the implicit cache?).
- React peer-dep mismatch is the most common bump blocker. If the
  bump command errors with `ERESOLVE`, do **not** add `--legacy-
  peer-deps` to suppress it — surface and stop. The library
  ecosystem hasn't caught up to React 19, and forcing the install
  papers over a real runtime risk.
- For App Router projects, server / client component boundaries
  may shift subtly. Audit's findings here surface as TODOs unless
  the audit specified a from→to.
- If the project deploys to Vercel, mention any Vercel-specific
  defaults that change at the platform level (Edge runtime
  changes, build-output format moves) in the report — the
  platform's behaviour is part of the upgrade surface but not
  part of the fix.
- Do not edit `vercel.json` / `netlify.toml` / Dockerfile as part
  of the fix unless the audit explicitly flagged a deploy-config
  change. Pipeline drift is a separate PR.
