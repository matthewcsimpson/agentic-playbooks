# DBMigrationAudit

Pre-merge safety audit for database migration files, paired with fix
variants that action the audit findings. Catches the
unsafe-under-production-load operations that look fine in isolation
but break a live system: NOT NULL on a populated table, a non-
concurrent index on a hot table, an FK without an index, a rename
that breaks a rolling deploy.

Run the audit on a PR branch before merge, after the migration has
been written but before it's been applied anywhere beyond a local
dev database. Run the matching fix to action the findings — split
migrations, add `CONCURRENTLY`, replace `DROP+ADD` with `RENAME
COLUMN`, etc.

Variants carry an ORM tag (`.prisma`, `.typeorm`, `.alembic`,
`.ef-core`) because migration file shapes differ entirely across
ORMs — but the **unsafe operations themselves are universal**. The
cores capture the operation catalogue, edit catalogue, and severity
model; each variant supplies the parser, ORM idioms, and engine-
specific commands.

| Audit | Fix | Migration shape |
|---|---|---|
| `db-migration-audit.prisma.prompt.md` | `db-migration-fix.prisma.prompt.md` | SQL-ish migration files in `prisma/migrations/`, declarative `schema.prisma` deltas |
| `db-migration-audit.typeorm.prompt.md` | `db-migration-fix.typeorm.prompt.md` | TypeScript classes implementing `MigrationInterface` (`up()` / `down()`) |
| `db-migration-audit.alembic.prompt.md` | `db-migration-fix.alembic.prompt.md` | Python files in `alembic/versions/`, `op.*` operations, `upgrade()` / `downgrade()` |
| `db-migration-audit.ef-core.prompt.md` | `db-migration-fix.ef-core.prompt.md` | C# classes extending `Migration`, `MigrationBuilder` API, `Up()` / `Down()` |
| `core/db-migration-audit.core.prompt.md` | `core/db-migration-fix.core.prompt.md` | Shared scaffolds — operation catalogue, severity model, edit catalogue, commit discipline. Not invoked directly. |

The fix prompts deliberately default to a **narrow** scope:

- `db-migration-fix-*` defaults to ⚠️ CRITICAL findings only. Action
  HIGH / MODERATE / CANDIDATE only when the user explicitly opts in.
- Structural fixes (splitting one migration into multiple) are opt-in
  per cluster — splits change the migration sequence and affect every
  developer who pulls.
- Each migration edited gets its own commit; no bulk-rewrite.

All fix prompts commit locally only — they don't push or apply the
migration to any database. The intended flow is: run the audit, read
the report, decide which findings are worth acting on, invoke the fix
with that scope.

## Picking a variant

Pick the variant matching the project's ORM. The unsafe-operation
list is identical; the variant adapts the file paths, parsing
strategy, and per-ORM idioms (Prisma's `@@map` rename behaviour,
TypeORM's `synchronize: true` footgun, Alembic's autogenerate
limits, EF Core's annotations-driven schema).

If your ORM isn't listed (Knex, Sequelize, Liquibase, Flyway, Django,
ActiveRecord, raw SQL files, …):

1. Copy the closest variant pair (audit + fix).
2. Rename to `db-migration-audit.<orm>.prompt.md` and
   `db-migration-fix.<orm>.prompt.md`.
3. Replace the file-path conventions, parsing strategy, and ORM-
   specific notes. Keep the operation and edit catalogues in the
   cores.
4. Leave the `core/` references intact.
5. Update this README's variant table and open a PR.

## What the audit catches

The audit ranks findings by *blast radius under production load*,
not by syntactic concern. A NOT NULL on an empty table is fine; on a
populated table it's an outage. The audit is context-aware in that
sense.

- ⚠️ **Locks the table** — operations that block writes (or reads)
  for the duration of the migration. Disaster on a hot table.
- ⚠️ **Breaks rolling deploys** — schema state that the previous
  application version cannot tolerate. The window between "old
  pods serving" and "new pods serving" becomes an error window.
- ⚠️ **Backfills inside a migration transaction** — long-running
  UPDATEs that hold locks far longer than expected.
- ⚠️ **No downgrade path** — destructive operations with no `down`
  / `downgrade` implementation, or where the down is silently
  lossy.
- ⚠️ **Missing index on FK** — adds an FK constraint without an
  index on the referencing column. Reads slow; deletes on the
  parent table take exclusive locks.
- ⚠️ **Constraint added without a precheck** — UNIQUE, CHECK, FK
  added against existing data without verifying conformance first.
- 💡 **Migration that should have been two migrations** — schema
  + backfill in one go; the safe shape is split into separate
  steps.

## What the fix actions

The fix's edit catalogue mirrors the audit's findings:

- **Add `CONCURRENTLY`** — Postgres / MySQL non-blocking index
  creation. Each ORM has its own escape hatch (raw SQL +
  `suppressTransaction`, `--create-only` + hand-edit, etc.).
- **Split schema + backfill + NOT NULL** — generate three new
  migrations using the ORM's CLI, then move operations across them
  in the right order.
- **`NOT VALID` + `VALIDATE CONSTRAINT`** — Postgres-specific
  pattern for adding constraints on populated tables without locking.
- **Replace `DROP+ADD` column rename with `RENAME COLUMN`** —
  preserves data; uses the ORM's native rename API where available.
- **Add missing index before FK** — atomic per-migration; on hot
  tables, splits the index into a concurrent-mode migration first.

## Required tool capabilities

- File read across the repo.
- Shell execution for the ORM's CLI (verification: `prisma migrate
  diff`, `dotnet ef migrations script`, `alembic upgrade --sql`,
  `typeorm migration:show`).
- No database connection needed — the audit and fix are both static.
  Applying the migration is the user's call.

Designed for Claude Code and Codex CLI; anything with the same
capability set should work.

## Output discipline

The audit's report goes to the PR / commit conversation or to
`<root>/migrations/<migration-id>.md` (default `<root>` is
`.playbook-audits/`; `docs/audits/` is honored as legacy). It does
not write to disk by default — migration audits are point-in-time
artefacts and don't benefit from a tracked history.

The fix produces local commits, one per migration touched.

## Invocation

See the [root README](../README.md#invocation) for the three
supported patterns. For paste-mode, paste the core file first, then
the variant — the variant references the core for the catalogue.
