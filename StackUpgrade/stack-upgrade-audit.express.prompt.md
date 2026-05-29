---
description: Plan an Express major and/or Node.js runtime upgrade — read release notes, scan for affected patterns (route syntax, removed APIs), survey middleware co-bumps, produce a risk-ranked migration plan.
related: [stack-upgrade-fix-express]
---

# Stack upgrade — Express / Node.js variant

Plan an Express major upgrade (e.g. Express 4 → 5) and/or a Node.js
runtime version bump for an Express backend.

**This prompt extends [`core/stack-upgrade-audit.core.prompt.md`](./core/stack-upgrade-audit.core.prompt.md).**
Read the core first for the workflow shape (Steps 0–7, the report
format, and the Constraints). This file supplies the Express- and
Node-specific detection commands, release-note sources,
breaking-change categories, codemod tools, and gotchas.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Assumed stack

- A Node.js HTTP service built on Express (`express` in
  `package.json`), not a higher-level framework that wraps Express
  (if `@nestjs/core` is present, use the **nestjs** variant — Nest's
  Express adapter is upgraded through the Nest family, not directly).
- JavaScript (CommonJS or ESM) or TypeScript.
- Package manager: npm / pnpm / yarn (detect from lockfile).
- Common companion middleware: `body-parser`, `cookie-parser`,
  `express-session`, `multer`, `cors`, `helmet`, `morgan`,
  `passport`, `express-validator`, `compression`.
- Deploy target: a long-running Node process (container, VM, PaaS)
  or a serverless wrapper (`serverless-http`, Lambda, Cloud Run) —
  the Node runtime upgrade affects these differently.

This variant covers **two upgrades that usually travel together**:
the Express major and the Node.js runtime. Express majors raise the
minimum Node version (Express 5 requires Node 18+), so a single plan
should address both. Confirm in Step 0 whether the user wants one,
the other, or both.

---

## §2 — Detect current version

```sh
# Express version (manifest + resolved)
jq '.dependencies.express, .devDependencies.express' package.json
npm ls express 2>/dev/null || pnpm ls express 2>/dev/null || yarn why express

# Node runtime pins — these often disagree; surface the conflict
jq '.engines.node' package.json
cat .nvmrc 2>/dev/null
grep -rnE 'node-version|FROM node' .github/workflows/ Dockerfile* 2>/dev/null
node --version    # the local toolchain, not necessarily the deploy target

# Module system (affects which Node breaking changes bite)
jq '.type' package.json
ls tsconfig.json 2>/dev/null

# Companion middleware that ship Express-major-coupled releases
jq '.dependencies' package.json | grep -iE 'body-parser|cookie-parser|express-session|multer|cors|helmet|morgan|passport|compression|connect-'
```

If `engines.node`, `.nvmrc`, the CI `node-version`, and the
Dockerfile base image disagree, surface that as the **first
finding** — the runtime upgrade can't be coherent until they agree
on a single source of truth.

---

## §3 — Release notes sources

**Express:**

- Express 5 migration guide: `https://expressjs.com/en/guide/migrating-5.html`
  (the canonical breaking-change list for 4 → 5).
- GitHub releases: `gh release list --repo expressjs/express --limit 40`
  then `gh release view <tag> --repo expressjs/express`.
- The Express 5 changelog in `node_modules/express/History.md`.
- `path-to-regexp` releases — the route-matching engine Express
  embeds; its major (0.1.x → 8.x for Express 5) is the source of the
  riskiest behaviour change: `gh release view --repo pillarjs/path-to-regexp`.

**Node.js (for each major in the runtime path):**

- Release-specific changelogs:
  `https://github.com/nodejs/node/releases/tag/v<N>.0.0`.
- The "BREAKING CHANGES" section of each major's changelog under
  `https://github.com/nodejs/node/blob/main/doc/changelogs/`.
- Deprecation list: `https://nodejs.org/api/deprecations.html` — the
  `DEP` codes that graduated to runtime removal in the target.
- Release schedule (for LTS targeting):
  `https://nodejs.org/en/about/previous-releases`.

---

## §3.5 — Common breaking-change categories

### Express 4 → 5

- **Removed APIs** — `app.del()` → `app.delete()`; `req.param(name)`
  removed (read `req.params` / `req.body` / `req.query` directly);
  pluralised/legacy method aliases removed; `res.sendfile` →
  `res.sendFile`; `app.configure()` removed; `res.json(obj, status)`
  and `res.send(status)` two-arg / status-as-arg signatures removed
  (use `res.status(n).json(obj)`); `res.redirect('back')` removed
  (use `req.get('Referrer') || '/'`).
- **Renamed / relocated** — `body-parser` JSON / urlencoded parsing
  is built in again as `express.json()` / `express.urlencoded()`;
  standalone `body-parser` still works but the audit should note
  whichever the project uses.
- **Behaviour changes** — **route path matching** is the big one:
  `path-to-regexp` upgraded, so bare `*` wildcards, unnamed regex
  groups, and optional `:param?` segments change syntax. `*` must be
  named (`/*splat`), optional segments use `{}` (`/:file{.:ext}`),
  and stray regex characters in paths are rejected. A path string
  that silently matched in 4 can throw at mount time in 5.
- **Behaviour changes** — rejected promises returned from
  middleware / handlers are now forwarded to the error handler
  automatically (no more swallowed async rejections); `req.query` is
  a getter (no longer reassignable); `req.host` / `res.status()`
  range validation tightened.
- **Default changes** — `express.urlencoded({ extended })` no longer
  has an implicit default in some flows; pass `extended` explicitly.
- **Dependency upgrades** — Node 18+ required; several first-party
  middleware (`serve-static`, `finalhandler`, `send`) bumped majors.

### Node.js runtime (per major)

- **Removed APIs** — legacy `url.parse()` edge cases, callback-style
  APIs replaced by promises, `domain`, deprecated `crypto` /
  `Buffer()` constructors, `punycode` (now a userland install).
- **Behaviour changes** — OpenSSL major bumps (TLS / cipher
  defaults), DNS result ordering (`dns.setDefaultResultOrder`),
  global `fetch` / `WebStreams` / `structuredClone` becoming
  available (and overriding userland polyfills), V8 changes.
- **Default changes** — `--openssl-legacy-provider` needs, ESM
  resolution defaults, `NODE_OPTIONS` changes.
- **Tooling changes** — built-in test runner (`node --test`),
  `--watch`, permission model (`--permission`), corepack defaults.

For the specific targets, fetch the upgrade guides and list the
*actual* changes — the categories above are the recurring shape, not
the literal list for any one version pair.

---

## §4 — Scan patterns

```sh
# Removed / renamed Express APIs
grep -rnE '\bapp\.del\(' --include='*.js' --include='*.ts' .
grep -rnE '\breq\.param\(' --include='*.js' --include='*.ts' .
grep -rnE '\bres\.(sendfile|json|send)\s*\([^)]*,' --include='*.js' --include='*.ts' .
grep -rnE "res\.redirect\(\s*['\"]back['\"]" --include='*.js' --include='*.ts' .
grep -rnE '\bapp\.configure\(' --include='*.js' --include='*.ts' .

# Route path strings — the path-to-regexp trap. Flag wildcard / optional / regex paths.
grep -rnE "\b(app|router|route)\.(get|post|put|patch|delete|all|use)\(\s*['\"][^'\"]*[*?(){}+][^'\"]*['\"]" --include='*.js' --include='*.ts' .

# Reassignment of req.query (now a getter)
grep -rnE 'req\.query\s*=' --include='*.js' --include='*.ts' .

# body-parser usage vs built-in
grep -rnE "require\(['\"]body-parser['\"]\)|from\s+['\"]body-parser['\"]" --include='*.js' --include='*.ts' .

# Async handlers relying on the old swallow-rejection behaviour
grep -rnE 'async\s*\(req,\s*res' --include='*.js' --include='*.ts' . | head -n40

# Node API surfaces that move across runtime majors
grep -rnE "require\(['\"](punycode|domain)['\"]\)|url\.parse\(|new Buffer\(|crypto\.createCipher\(" --include='*.js' --include='*.ts' .

# Userland polyfills that the new Node global may shadow
grep -rnE "require\(['\"](node-fetch|cross-fetch|abort-controller)['\"]\)" --include='*.js' --include='*.ts' .
```

For **behaviour-change** findings (route matching, async rejection
forwarding, shadowed globals), mark candidates with the reasoning
rather than collapsing into a confident classification — these are
the silent-risk class.

---

## §5 — Codemod survey

Express has **no first-party codemod ecosystem**. The migration is
mechanical-edit-heavy and grep-driven. Options:

```sh
# No official runner. For repeated mechanical renames, a one-off
# jscodeshift transform is the practical tool — keep it as a throwaway
# script, not a committed dependency.
npx jscodeshift -t <local-transform>.js --dry src/
```

What is mechanical (cleanly grep-and-replace) vs. what needs
judgment:

- **Mechanical** — `app.del` → `app.delete`, `res.sendfile` →
  `res.sendFile`, `res.send(status)` → `res.sendStatus(status)`,
  `res.redirect('back')` → `res.redirect(req.get('Referrer') || '/')`.
- **Judgment (no codemod)** — route path string migration under the
  new `path-to-regexp` (each wildcard / optional / regex path is a
  per-route decision); `req.param()` removal (which of params / body
  / query did the caller mean?); async rejection-forwarding
  behaviour. Flag these ⚠️ manual-review.

For the Node runtime, there is no codemod; removed-API findings are
grep-driven mechanical replacements (e.g. `punycode` →
`npm i punycode.js`, `new Buffer()` → `Buffer.from()`).

Codemod savings on this upgrade are modest — set the manual-effort
expectation accordingly in the plan.

---

## §6 — Risk patterns specific to Express / Node

- **Route path matching (4 → 5)** — the single biggest silent-risk
  change. A path like `'/users/:id?'` or `'/files/*'` that matched
  for years can throw `Missing parameter name` at mount time, or
  match differently. Every dynamic / wildcard / optional route is a
  finding. This is the category that turns an "afternoon" upgrade
  into a "couple of days" one.
- **Async error handling** — code that previously relied on Express
  4 *not* forwarding rejected promises (and handled errors some
  other way) can now hit the error handler twice or behave
  differently. Audit `async` handlers and any custom error
  middleware.
- **Middleware co-bump lag** — `passport`, `express-session`,
  `multer`, `connect-*` stores often need an Express-5-compatible
  major. A single non-compatible middleware can block the whole
  upgrade; surface the compatibility status of each in the Verdict.
- **Shadowed globals (Node)** — a project that polyfilled `fetch`
  via `node-fetch` now gets the native `fetch`, which has different
  behaviour (no automatic proxy support, different body handling).
  Removing the polyfill is the fix, but it's a behaviour change, not
  a no-op.
- **OpenSSL / TLS defaults (Node)** — runtime bumps that cross an
  OpenSSL major can break outbound TLS to legacy endpoints or change
  cipher negotiation. Flag if the service talks to legacy systems.
- **Deploy-target runtime lag** — AWS Lambda, Cloud Run, and PaaS
  Node runtimes lag the language by months. Confirm the target Node
  major is actually available on the deploy platform before planning
  the bump — a plan for a runtime the platform can't run is moot.

---

## Constraints (Express / Node-specific addenda)

- The route-path-matching change is the most common cause of a
  failed Express 5 boot. Always enumerate every dynamic / wildcard /
  optional / regex route as explicit findings — never summarise as
  "the app uses some wildcard routes".
- If the project still uses standalone `body-parser`, note both
  options (keep it, or move to built-in `express.json()` /
  `express.urlencoded()`) but do not assume one — it's the user's
  call.
- Treat the Node runtime bump and the Express major as separable in
  the plan even when bundled: a team may want Node 20 now and
  Express 5 later (or vice-versa). Group breaking changes by which
  upgrade introduces them so the user can split the work.
- Enumerate every companion middleware and its Express-5
  compatibility status in the Verdict — middleware lag is the most
  common blocker, and it's invisible until the bump fails.
- If the service is wrapped for serverless (`serverless-http`,
  `aws-serverless-express`), check that the wrapper supports the
  target Express major — these wrappers historically lagged.
