---
description: Action findings from stack-upgrade-audit-nestjs. Apply mechanical breaking-change edits, bump @nestjs/* packages, verify build, commit per category. Local only.
related: [stack-upgrade-audit-nestjs, post-milestone-audit-nestjs]
---

# Stack upgrade fix — NestJS variant

Action findings from a `stack-upgrade-audit-nestjs` report against
a NestJS backend.

**This prompt extends [`core/stack-upgrade-fix.core.prompt.md`](./core/stack-upgrade-fix.core.prompt.md).**
Read the core first.

---

## Assumed stack

- NestJS — usually `@nestjs/common`, `@nestjs/core`, `@nestjs/platform-*`.
- TypeScript (NestJS is TS-first; JS Nest apps exist but are rare).
- Package manager: detect from lockfile.
- Frequently paired with: TypeORM, Mongoose, `@nestjs/microservices`,
  `@nestjs/swagger`, `@nestjs/cli`.

NestJS has a smaller official codemod story than Next.js or React.
Most upgrades are **mechanical-edit-heavy** with no codemod
coverage. The fix prompt leans on the audit's from→to pairs.

---

## §2 — Re-verify the audit

```sh
jq -r '.dependencies | to_entries[] | select(.key | startswith("@nestjs")) | "\(.key): \(.value)"' package.json
jq -r '.devDependencies | to_entries[] | select(.key | startswith("@nestjs")) | "\(.key): \(.value)"' package.json
```

If any `@nestjs/*` package has moved since the audit, stop and re-run
the audit.

---

## §3 — Codemods

There is no first-party `nest codemod`. A few community options:

- `nestjs-codemod` on npm — limited; not consistently maintained.
- `jscodeshift` with hand-rolled transforms — only if the audit
  specifically prepared one.

In practice, the audit should rely on **mechanical edits** (Step 4),
not codemods, for most NestJS upgrades. If the audit listed
codemods, run them per the core's Step 3 shape and verify after each.

If no codemods apply, skip to Step 4.

---

## §4 — Mechanical edits

Apply the audit's documented from→to pairs. Common categories across
recent Nest majors:

**Decorator / module API renames:**

```ts
// Example (illustrative — use the audit's actual list):
// import { HttpModule } from '@nestjs/common' → '@nestjs/axios' (v8)
// @nestjs/passport: passport.strategy() signature change between v9 and v10
```

**Configuration shape changes:**

```ts
// Example:
// app.useGlobalPipes(new ValidationPipe(...)) — option keys evolve per major
// CacheModule.register(...) → CacheModule.registerAsync(...) for newer interceptor lifecycle
```

**Lifecycle / DI:**

```ts
// Module imports now expecting forwardRef
// Provider scope changes (REQUEST vs TRANSIENT)
```

For each category, apply across the audit's flagged sites, verify,
commit per category:

```sh
git commit -m "upgrade(nestjs): migrate HttpModule import from @nestjs/common to @nestjs/axios"
```

If the audit's from→to is ambiguous (e.g. "rewrite to use the new
lifecycle hook"), surface as TODO and skip.

---

## §5 — Version bump

NestJS upgrades require **co-bumping the entire `@nestjs/*` family**
to the same major. Mixing majors is the most common upgrade failure
mode.

```sh
# Identify all installed @nestjs/* packages
jq -r '.dependencies, .devDependencies | to_entries[]? | select(.key | startswith("@nestjs")) | .key' package.json | sort -u

# Bump them in one go (npm)
npm install \
  @nestjs/common@<target> \
  @nestjs/core@<target> \
  @nestjs/platform-express@<target> \
  @nestjs/cli@<target> \
  @nestjs/schematics@<target> \
  @nestjs/testing@<target>
```

(Use the actual list from the `jq` output above. The audit should
have enumerated them.)

For pnpm / yarn, swap `npm install` for the equivalent (see
`dependency-fix-npm` for ecosystem syntax).

Peer deps that frequently need co-bumping:

- `reflect-metadata` — usually stable.
- `rxjs` — major version often pinned by Nest.
- `typescript` — Nest 10+ requires TS 5+.
- `class-validator` / `class-transformer` — version constraints in
  Nest majors.

The audit should have listed which peer co-bumps the target Nest
requires.

Commit:

```sh
git commit -m "upgrade(nestjs): bump @nestjs/* from <old> to <new>, rxjs <old> to <new>, typescript <old> to <new>"
```

---

## §6 — Post-bump edits

Edits that only apply after the bump:

- New decorators or providers available in the target major (often
  optional adoption — surface as TODO unless explicitly in scope).
- Test harness shape changes when `@nestjs/testing` moves.

---

## §7 — Verification

```sh
# Per-category gate
npx tsc --noEmit
npm run lint
npm run build         # nest build — exercises module resolution end-to-end

# Full suite when all categories done
npm test              # jest unit tests
npm run test:e2e      # Nest's e2e harness — catches DI / module-loading regressions
```

For monorepos:

```sh
turbo run build --filter=<service>
pnpm --filter <service> build
```

---

## §8 — Hand off

```
/playbook post-milestone-audit-nestjs
```

Residual drift common after a Nest upgrade:

- Module-level `imports` arrays still referencing renamed modules
  the audit missed.
- Custom providers with `scope: Scope.DEFAULT` where the target
  major changed default scope semantics.
- OpenAPI / Swagger config still passing options the new
  `@nestjs/swagger` doesn't accept.

---

## Constraints (NestJS-specific addenda)

- Always bump the entire `@nestjs/*` family in one commit. Mixed
  majors fail at runtime, often with confusing "cannot find module"
  or DI-resolution errors that don't point at the version skew.
- `@nestjs/cli` and `@nestjs/schematics` are dev-time but still
  pinned per major — co-bump them with the runtime packages.
- `rxjs` major bumps frequently cascade into application code
  (operator removals, pipe semantics). If the audit flagged rxjs
  call sites as affected, treat that as its own mechanical-edit
  category, not a transparent co-bump.
- TypeScript major upgrades that ride a Nest bump may surface
  type errors in **unrelated code**. Verification will catch them
  but they're not part of the Nest upgrade's intended scope —
  surface as TODOs for a separate pass.
- Microservices transport drivers (`@nestjs/microservices` + Redis
  / NATS / Kafka adapters) have their own per-major option-shape
  changes. The audit should have flagged these explicitly; the fix
  applies the audit's from→to spec without improvising transport
  config.
