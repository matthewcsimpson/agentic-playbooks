---
description: Action findings from stack-upgrade-audit-express. Apply mechanical edits (route paths, removed APIs), bump express + Node engines + middleware, verify build, commit per category. Local only.
related: [stack-upgrade-audit-express]
---

# Stack upgrade fix — Express / Node.js variant

Action findings from a `stack-upgrade-audit-express` report against
an Express backend — an Express major bump (e.g. 4 → 5), a Node.js
runtime bump, or both.

**This prompt extends [`core/stack-upgrade-fix.core.prompt.md`](./core/stack-upgrade-fix.core.prompt.md).**
Read the core first for the workflow shape (input scoping, locate
audit, per-category action, verify-and-commit gating, hand-off).
This file supplies Express- and Node-specific commands and gotchas.

---

## Assumed stack

- An Express HTTP service (`express` in `package.json`). If
  `@nestjs/core` is present, stop — use the **nestjs** fix variant
  instead.
- JavaScript (CJS or ESM) or TypeScript.
- Package manager: detect from lockfile.
- Companion middleware that frequently need Express-5-compatible
  co-bumps: `passport`, `express-session`, `multer`, `cors`,
  `helmet`, `morgan`, `compression`, `connect-*` session stores.

Express has **no first-party codemod**. This upgrade is
mechanical-edit-heavy; the fix leans on the audit's from→to pairs.

---

## §2 — Re-verify the audit

```sh
# Express pin and resolved version
jq -r '.dependencies.express // .devDependencies.express' package.json
npm ls express 2>/dev/null | head -n3

# Node pins (all four should agree by the end; flag if they don't)
jq -r '.engines.node // empty' package.json
cat .nvmrc 2>/dev/null
grep -rnE 'node-version|FROM node' .github/workflows/ Dockerfile* 2>/dev/null
```

If `express` (or the Node pins) moved since the audit, stop and
re-run `stack-upgrade-audit-express`. Route-matching incidents come
from acting on a stale plan.

---

## §3 — Codemods

There is no official Express codemod. If the audit prepared a
one-off `jscodeshift` transform for a repeated mechanical rename,
run it per the core's Step 3 shape (apply mode — the audit dry-ran),
verify, and commit. Otherwise skip to Step 4; the bulk of an Express
upgrade is mechanical edits.

---

## §4 — Mechanical edits

Apply the audit's documented from→to pairs, one category at a time,
verify, commit per category. The common Express 4 → 5 categories:

**Removed / renamed method calls** (clean grep-and-replace):

```js
// app.del(...)            → app.delete(...)
// res.sendfile(path)      → res.sendFile(path)
// res.send(404)           → res.sendStatus(404)
// res.json(obj, 201)      → res.status(201).json(obj)
// res.redirect('back')    → res.redirect(req.get('Referrer') || '/')
// app.configure(...)      → remove; inline the callback
```

```sh
git commit -m "upgrade(express): rename removed 4.x method calls (app.del, res.sendfile, status-arg signatures)"
```

**Route path migration** (the `path-to-regexp` change — apply only
the audit's per-route from→to specs; do **not** improvise):

```js
// '/files/*'         → '/files/*splat'      (wildcards must be named)
// '/users/:id?'      → '/users{/:id}'        (optional segment syntax)
// '/x/:p(\\d+)'      → move the regex to a guard / validator; inline regex in the path is gone
```

If the audit's route spec is ambiguous (it said "rewrite this route"
rather than giving a concrete from→to), surface as a TODO and skip —
route rewrites are judgment calls, not mechanical edits.

```sh
git commit -m "upgrade(express): migrate route paths to path-to-regexp 8 syntax"
```

**`req.param()` removal** — only if the audit specified which source
each call meant (`req.params` / `req.body` / `req.query`). Ambiguous
ones are TODOs.

**Node removed-API edits** (if the runtime bump is in scope):

```js
// new Buffer(x)          → Buffer.from(x) / Buffer.alloc(n)
// require('punycode')    → npm i punycode.js, require('punycode.js')
// crypto.createCipher    → crypto.createCipheriv (needs an IV — judgment, likely TODO)
```

Under `risk:low`, every mechanical-edit category stops and asks
before applying. `risk:med` applies high-confidence categories
(method renames) and stops on judgment-heavy ones (route paths,
`req.param`). `risk:high` applies all the audit recommended.

---

## §5 — Version bump

Bump Express, its Express-5-coupled middleware co-bumps, and the
Node runtime pins together — they're atomic.

```sh
# Express + first-party middleware (npm; swap for pnpm/yarn equivalents)
npm install express@<target>

# Companion middleware that need an Express-5-compatible major
# (use the exact list + versions the audit identified):
npm install passport@<target> express-session@<target> multer@<target> \
  helmet@<target> cors@<target> morgan@<target> compression@<target>
```

If the bump errors with `ERESOLVE` on a middleware peer dep, do
**not** paper over it with `--legacy-peer-deps` — surface and stop.
A middleware without an Express-5-compatible release is a real
blocker, not a resolver quirk.

**Node runtime pins** — if the runtime bump is in scope, move all of
them in the same commit (the service can't deploy on a mismatch):

```sh
# package.json engines.node
jq '.engines.node = ">=20.0.0"' package.json > /tmp/pkg && mv /tmp/pkg package.json

# .nvmrc
echo '20' > .nvmrc

# CI workflow node-version and Dockerfile base image — edit per the
# audit's findings (these are the two most-often-forgotten pins).
```

```sh
git commit -m "upgrade(express): bump express 4.21 → 5.1, passport/multer/session to Express-5 majors, node ≥ 20"
```

If verification fails after the bump, this is the high-stakes case:
do not silently revert and continue. Surface the failure, list the
categories already committed, and stop (per the core's Step 5).

---

## §6 — Post-bump edits

Edits that only make sense once Express 5 / the new Node is present:

- Removing userland polyfills the new Node runtime shadows
  (`node-fetch` → native `fetch`) — behaviour-changing, so TODO
  unless the audit specified it and the user opted in.
- Adopting `express.json()` / `express.urlencoded()` in place of
  standalone `body-parser` — opt-in, not a strict-upgrade fix.

---

## §7 — Verification

```sh
# Per-category gate
npx tsc --noEmit          # if TypeScript
npm run lint
npm run build             # if there's a build step

# The most useful Express gate: boot the app. Express 5 throws at
# mount time on a bad route path — a clean boot proves the route
# table parsed.
timeout 15 node <entrypoint> & sleep 3; curl -fsS localhost:<port>/health || echo "boot/health FAILED"; kill %1 2>/dev/null

# Full suite when all categories are done
npm test
npm run test:integration  # or supertest e2e — exercises the route table end-to-end
```

A clean boot + the route-level integration tests are the real gate
for an Express major; a passing typecheck does not prove the route
strings parse.

---

## §8 — Hand off

There is no `post-milestone-audit-express` variant. After the full
suite passes, recommend the generic drift catchers plus an API
smoke:

```
/playbook doc-code-drift-audit        # README/run commands, env, node version notes
/playbook dead-code-audit             # middleware / routes orphaned by the migration
/playbook post-milestone-smoke-test-api   # drive the headline endpoints on the new stack
```

Common residual drift after an Express / Node upgrade:

- README / Dockerfile / deploy docs still naming the old Node
  version.
- Error-handling middleware double-firing now that rejected promises
  forward automatically.
- Route handlers that "work" but match different paths than before
  under the new matcher.

---

## Constraints (Express / Node-specific addenda)

- Boot the app as part of verification. Express 5 fails at mount
  time on an invalid route path — a typecheck/build pass is not
  sufficient proof the upgrade is sound.
- Never improvise route-path rewrites. Apply only the audit's
  concrete per-route from→to specs; ambiguous routes are TODOs.
- Never suppress an `ERESOLVE` peer-dep error with
  `--legacy-peer-deps` to force a middleware install. A middleware
  without an Express-5 release is a blocker to surface, not to hide.
- Move all four Node pins together (`engines.node`, `.nvmrc`, CI
  `node-version`, Dockerfile base) in one commit if the runtime bump
  is in scope. A half-moved runtime pin deploys the old version
  silently.
- Do not remove userland polyfills (`node-fetch`, `abort-controller`)
  as a "cleanup" — the native replacement has different behaviour.
  Surface as a TODO unless the audit specified the migration.
- Keep the Express major and the Node runtime bump as separate
  commits when both are in scope, so either can be reverted
  independently.
