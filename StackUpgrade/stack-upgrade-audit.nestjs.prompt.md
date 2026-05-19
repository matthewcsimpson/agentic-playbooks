---
description: Plan a NestJS major version upgrade — read release notes, scan for affected patterns, survey codemods, produce a risk-ranked migration plan.
related: [stack-upgrade-fix-nestjs, post-milestone-fix]
---

# Stack upgrade — NestJS variant

Plan a NestJS major version upgrade.

**This prompt extends [`core/stack-upgrade-audit.core.prompt.md`](./core/stack-upgrade-audit.core.prompt.md).**
Read the core first for the workflow shape (Steps 0–7, the report
format, and the Constraints). This file supplies the NestJS-
specific detection commands, release-note sources, breaking-change
categories, codemod tools, and gotchas.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Assumed stack

- NestJS (`@nestjs/core`, `@nestjs/common`).
- TypeScript.
- HTTP adapter: Express (default) or Fastify.
- Common companion packages: `@nestjs/typeorm`, `@nestjs/microservices`,
  `@nestjs/graphql`, `@nestjs/swagger`, `@nestjs/jwt`, etc.

NestJS majors bump in lockstep across the `@nestjs/*` packages.
Mixed major versions are a common source of confusion — surface
any mismatch in the inventory.

---

## §2 — Detect current version

```sh
# All @nestjs/* versions in manifest
jq '.dependencies, .devDependencies' package.json \
  | grep -E '"@nestjs/' | sort -u

# Resolved versions
npm ls --json --depth=0 2>/dev/null \
  | jq '.dependencies | to_entries[] | select(.key | startswith("@nestjs/")) | {name: .key, version: .value.version}'

# HTTP adapter
grep -rnE 'FastifyAdapter|ExpressAdapter' --include='*.ts' . | head -n5

# Node version pin
jq '.engines.node' package.json
cat .nvmrc 2>/dev/null
```

If `@nestjs/core` is on major N but `@nestjs/typeorm` is on N-1,
flag immediately — the upgrade isn't truly across the project.

---

## §3 — Release notes sources

For each major in the upgrade path:

- GitHub release notes:
  `gh release list --repo nestjs/nest --limit 40`
  then `gh release view <tag> --repo nestjs/nest`.
- Migration guide: `https://docs.nestjs.com/migration-guide`
  (covers the latest major; older majors documented in versioned
  docs).
- Per-package release notes for the `@nestjs/*` ecosystem (e.g.
  `@nestjs/typeorm`, `@nestjs/graphql`) — these are versioned
  independently and often have breaking changes timed with the
  core bump.

---

## §3.5 — Common breaking-change categories (NestJS)

- **Removed APIs** — deprecated decorators / methods removed
  between majors (e.g. `@Render()` shape changes, lifecycle hook
  changes).
- **Renamed APIs** — module / decorator imports relocated as the
  `@nestjs/*` ecosystem reorganises (e.g. utility exports moving
  between `@nestjs/common` and `@nestjs/core`).
- **Behaviour changes** — exception filter execution order,
  pipe / guard / interceptor scope rules, lifecycle hook timing,
  dependency-resolution algorithm changes.
- **Default changes** — global validation pipe defaults, CORS
  defaults, body-parser limits, log-level defaults.
- **Dependency upgrades** — TypeScript minimum, RxJS major,
  reflect-metadata, Express / Fastify majors, class-validator /
  class-transformer majors.
- **Tooling changes** — `@nestjs/cli` config (`nest-cli.json`),
  Swagger / OpenAPI generation, build output for monorepos.

---

## §4 — Scan patterns (NestJS)

```sh
# Decorator usage (helps target a per-decorator scan once breaking changes are known)
grep -rnhE '@(Module|Controller|Injectable|Get|Post|Put|Delete|Patch|Param|Query|Body|Headers|UseGuards|UseInterceptors|UsePipes|UseFilters)\(' \
  --include='*.ts' . | sed -E 's/.*(@[A-Za-z]+).*/\1/' | sort | uniq -c | sort -rn

# Global validation pipe configuration
grep -rnE 'new ValidationPipe|app\.useGlobalPipes' --include='*.ts' .

# Custom exception filters
grep -rnE '@Catch\(|ExceptionFilter' --include='*.ts' .

# Lifecycle hooks
grep -rnE 'OnModuleInit|OnApplicationBootstrap|OnModuleDestroy|OnApplicationShutdown' --include='*.ts' .

# RxJS usage (major changes ripple through Nest)
grep -rnE "from\s+['\"](rxjs|rxjs/operators)['\"]" --include='*.ts' . | head -n20

# Microservices transport
grep -rnE 'Transport\.(TCP|REDIS|NATS|KAFKA|MQTT|GRPC|RMQ)' --include='*.ts' .

# Swagger / OpenAPI
grep -rnE "@nestjs/swagger" --include='*.ts' . | head -n10
```

For the specific upgrade target, scan for any decorator / method
the release notes mark deprecated or removed.

---

## §5 — Codemod survey (NestJS)

NestJS does not have a first-party codemod ecosystem the way
Next.js does. The migration story is largely manual + a script
runner provided in some major bumps.

```sh
# Some majors ship a one-shot migration script
npx @nestjs/cli@latest update             # interactive update assistant (limited)
```

For mechanical work:

- **`ts-morph` scripts** — write a small TS-to-TS transform if many
  call sites need the same rename. Keep these as one-off scripts,
  not committed tools.
- **ESLint with `@typescript-eslint`** — add a custom rule to flag
  the deprecated pattern, run autofix.

Manual review is the dominant mode for NestJS upgrades. The plan
should reflect that — codemod savings will be modest.

---

## §6 — Risk patterns specific to NestJS

- **Mixed `@nestjs/*` versions** — the package family must move
  together. A `@nestjs/core@10` + `@nestjs/typeorm@9` combination
  often appears to work but exhibits subtle DI bugs.
- **RxJS major bump** — RxJS 6 → 7 → 8 introduced rename / typing
  changes that ripple through every observable in the codebase.
- **TypeScript minimum bump** — Nest 10 raised the minimum;
  projects with older `tsconfig.json` settings can break.
- **`class-validator` / `class-transformer` majors** — used
  pervasively for DTO validation; their majors carry breaking
  changes that surface as silent failed-validation behaviour
  changes.
- **Fastify adapter** — different default behaviours from Express
  for some features (request logging, body parsing, CORS).
  Upgrading Nest may bring an updated Fastify; double-check.
- **`reflect-metadata`** — required for decorators; some upgrades
  shift the import location or expected initialization. A missing
  or duplicated `reflect-metadata` import is a common upgrade
  footgun.

---

## Constraints (NestJS-specific addenda)

- The `@nestjs/*` family must upgrade together. Any plan that
  upgrades `@nestjs/core` alone is wrong by construction — call
  this out in the Verdict.
- RxJS ripple effects are a large hidden category. Allow for them
  even if the Nest release notes don't lead with RxJS.
- `class-validator` and `class-transformer` are de-facto required
  by NestJS DTO patterns. Their majors carry breaking changes in
  validation behaviour — check separately even if not in the Nest
  release notes.
- For monorepos using `nest-cli.json` projects, the upgrade plan
  must address every project — a single repo can host multiple
  Nest apps with separate `main.ts` entry points.
- Don't recommend the `nest update` CLI as a one-shot solution; it
  is incomplete for most majors. Use it as one input among many.
