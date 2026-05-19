# DB migration audit — core

Shared scaffold for the database migration audit. Not invoked
directly — the ORM-specific variants
(`db-migration-audit.prisma.prompt.md`,
`db-migration-audit.alembic.prompt.md`, etc.) reference this file
for the workflow shape, unsafe-operation catalogue, severity model,
and report format.

A variant supplies the ORM-specific content for:

- Migration file location and shape.
- Parsing strategy (SQL strings, declarative schema, AST).
- ORM idioms (Prisma `@@map`, TypeORM `synchronize`, Alembic
  autogenerate quirks, EF Core annotations).
- Down / downgrade requirements.

Everything else below is shared.

---

## Context

A migration that runs cleanly on a local dev database with 100 rows
is not the same as a migration that runs against a production
database with 100M rows under live traffic. The most common
incidents come from operations that *worked locally* but locked the
table or broke the prior application version under load.

This review is a static, pre-merge check. It does not run the
migration. It does not connect to a database. It reads the migration
file, classifies operations against an unsafe-operations catalogue,
and reports the highest-risk findings first.

It assumes the project deploys with **rolling updates** (some old
pods running while new pods come up). If the project does cold
deploys with downtime, several findings in this audit drop in
severity — note that in the Summary if confirmed.

---

## Step 0 — Convention sourcing

Read every file the project uses to document conventions:

- `CLAUDE.md` at the repo root and any nested ones near the
  migration directory.
- `AGENTS.md`.
- `.github/copilot-instructions.md`, `.github/instructions/**/*.md`.
- `.cursor/rules/**/*` (or `.cursorrules`).
- Any `docs/migrations.md`, `docs/database.md`, runbooks, or
  on-call docs.
- `CONTRIBUTING.md` — skim for migration policy.

Enumerate the rules you'll be checking before scanning. Common
project-specific rules:

- "Migrations must be reversible" — must have a working `down` /
  `downgrade`.
- "Migrations cannot include data backfills" — schema change and
  data move belong in separate migrations.
- "Migrations must be transactional" or "must not be
  transactional" — DDL transactionality is database-specific
  (Postgres yes for most operations; MySQL no).
- "All new columns must be nullable initially."
- "All indexes must be created concurrently."

If the repo has no migration docs, fall back to the generic
catalogue below — but note in the report that the project-specific
spine is missing.

---

## Step 1 — Inventory

The variant tells you where migration files live. List:

- All migration files in this PR (use `git diff` against the merge
  base — only review what's actually new).
- For each, the migration ID / name and the file path.
- The database engine, if discoverable from connection strings,
  config, or ORM settings (Postgres, MySQL/MariaDB, SQLite, MSSQL,
  Oracle). Several findings are engine-dependent.

State which migrations are in scope before reviewing them. Do not
review previously-merged migrations — they're already deployed.

---

## Step 2 — Classify each operation

For every operation in every migration, classify against the
unsafe-operations catalogue. The catalogue is engine-specific where
noted.

### A. Locking operations (block writes; sometimes reads)

- ⚠️ **`ALTER TABLE` adding a column with a non-null default** —
  Postgres ≥11 stores the default in metadata, fast. Postgres ≤10
  and MySQL <8.0 rewrite the table → table lock for the duration.
  Severity: depends on engine.
- ⚠️ **`ALTER TABLE … ALTER COLUMN TYPE`** — Postgres rewrites the
  table for most type changes. MySQL almost always. Even
  "compatible" type changes (`VARCHAR(50)` → `VARCHAR(100)`) can
  trigger a rewrite.
- ⚠️ **`ALTER TABLE … SET NOT NULL` on populated table** —
  Postgres takes ACCESS EXCLUSIVE while scanning to validate. On a
  large table, blocks all access for minutes.
- ⚠️ **Adding a `CHECK` constraint without `NOT VALID`** — full
  table scan under lock to validate. Use `NOT VALID` then
  `VALIDATE CONSTRAINT` separately.
- ⚠️ **Adding a `UNIQUE` constraint without a pre-existing
  unique index** — full table scan to validate. Build the index
  `CONCURRENTLY` first, then add the constraint using it.
- ⚠️ **`CREATE INDEX` without `CONCURRENTLY`** (Postgres) /
  **without `ALGORITHM=INPLACE, LOCK=NONE`** (MySQL) — blocks
  writes for the duration of the build. Almost always avoidable.
- ⚠️ **`DROP INDEX` without `CONCURRENTLY`** (Postgres) — short
  lock but exclusive; harmless on a low-write table, ⚠️ on a
  high-write one.

### B. Rolling-deploy breakers

- ⚠️ **`DROP COLUMN`** — the old application version's queries
  reference the column. Between the migration applying and the old
  pods rotating out, every query containing the column errors.
- ⚠️ **`RENAME COLUMN`** — same shape as drop, but worse: the new
  name doesn't exist for old code, the old name doesn't exist for
  new code. There is no overlap window where both work.
- ⚠️ **`RENAME TABLE`** — same as rename column at table scope.
- ⚠️ **`NOT NULL` on a column the old code still leaves NULL** —
  if the old version inserts rows without the column set, the
  migration blocks those inserts.
- ⚠️ **Adding a column the new code reads without a default** —
  in the deploy window, queries from new code may run against
  rows inserted by old code without the column. NULL handling
  matters.
- 💡 **Adding a `NOT NULL DEFAULT` and then immediately removing
  the default** — the column is correctly populated for existing
  rows but the application now bears full responsibility for
  setting it. Sometimes deliberate, often a footgun.

### C. Backfills inside migrations

- ⚠️ **`UPDATE table SET ...` covering many rows in a migration
  transaction** — holds locks for the duration of the UPDATE.
  Should be a separate, batched backfill outside the migration
  transaction, or done with a background job.
- ⚠️ **Schema change + data backfill in the same migration** —
  even if the backfill is small, it ties the schema operation's
  rollback to the data operation's rollback. The two should be
  separate migrations: schema first (additive), backfill second,
  cleanup third.

### D. Constraints added without precheck

- ⚠️ **`ADD FOREIGN KEY` without verifying the parent rows exist
  for every child row** — the migration fails partway through;
  recovery is a hand-fix in production.
- ⚠️ **`ADD UNIQUE` without verifying no duplicates** — same
  shape.
- ⚠️ **`ADD CHECK` without verifying existing rows conform** —
  same shape.

The safe pattern: a separate "verification" SELECT in the migration
that fails fast if data doesn't conform, *before* the constraint
add.

### E. FK without index

- ⚠️ **`ADD FOREIGN KEY` without a matching index on the
  referencing column** — every DELETE / UPDATE on the parent
  table now scans the child table to enforce the constraint.
  Severity scales with parent-table modification frequency.

### F. Downgrade / rollback

- ⚠️ **No `down` / `downgrade` implementation** — if the
  migration is `irreversible: false` (or equivalent), the project
  has set a policy that rollback is impossible. May be deliberate;
  flag it so the reviewer confirms.
- ⚠️ **Silently lossy `down`** — the down drops a column that the
  up added, but the up backfilled data that the down can't
  reconstruct. The migration is reversible in name only.
- ⚠️ **Asymmetric up / down** — the up does N things, the down
  reverses M < N of them. Partial rollback corrupts state.

### G. Engine-specific footguns

- 💡 **DDL inside a transaction on MySQL** — MySQL does not
  support transactional DDL in most cases. A migration that
  pretends to be atomic may not be.
- 💡 **Postgres `CONCURRENTLY` inside a transaction** — Postgres
  refuses to run `CREATE INDEX CONCURRENTLY` inside an explicit
  transaction. The migration may need `--no-transaction` mode
  depending on the ORM.
- 💡 **Case-sensitivity / collation changes** — silently changes
  query semantics for existing rows.

---

## Step 3 — Severity model

Per finding:

- ⚠️ **CRITICAL** — high-likelihood production incident. Will
  block writes on a hot table or break the rolling deploy. Do not
  merge without a redesign.
- ⚠️ **HIGH** — material risk but contextual (depends on table
  size, deploy strategy, engine version). Discuss with the
  migration author and document the call.
- ⚠️ **MODERATE** — real concern but tolerable in some
  environments. Surface it; let the reviewer decide.
- 💡 **CANDIDATE** — judgment call. Worth flagging but not blocking.

The "context" axis matters for severity. If the project tells you
the migration will run against an empty/new table (e.g. a
just-added entity not yet in production), several findings drop
from CRITICAL to MODERATE. Ask the reviewer for context if it's
unclear from the migration alone.

---

## Step 4 — Report

The audit's output goes to the PR / commit conversation or to
`<root>/migrations/<migration-id>.md`, where `<root>` resolves in
this order: `.playbook-audits/` if it exists, else `docs/audits/`
if that exists (legacy convention), else create
`.playbook-audits/` and append `.playbook-audits/` to `.gitignore`
(creating `.gitignore` if absent — these are working artefacts,
not tracked history). Structure:

```
# Migration audit — <migration id or name>

PR: <if available>
Migration file: <path>
ORM variant: <prisma | typeorm | alembic | ef-core | …>
Database engine: <postgres | mysql | sqlite | mssql | unknown>
Deploy model assumed: <rolling | cold>
Convention sources read: <list>

## Verdict

<2-3 sentences. Headline: safe to merge? Safe with changes? Block?
Biggest concern. Lowest-effort fix if applicable.>

## Findings

### ⚠️ CRITICAL

- ⚠️ CRITICAL — `path/to/migration.sql:42` —
  `CREATE INDEX idx_x ON users(email)` without `CONCURRENTLY`.
  On the `users` table, this blocks writes for the duration of
  the build (estimated minutes on a multi-million-row table).
  **Fix:** `CREATE INDEX CONCURRENTLY idx_x ON users(email)`. If
  the ORM doesn't support `CONCURRENTLY` natively, use the ORM's
  raw-SQL escape hatch with the appropriate non-transaction flag.

### ⚠️ HIGH
### ⚠️ MODERATE
### 💡 CANDIDATE

## Rollback / downgrade review

- ✅ Down exists / is symmetric.
- ⚠️ Down is silently lossy: ...
- ⚠️ No down: deliberate? Confirm with author.

## Recommended structure (if changes needed)

<If the migration needs to be split, sketch the split:>

> 1. Migration A — add nullable column `x`, deploy app code that
>    writes to `x`.
> 2. Migration B — backfill `x` for existing rows (batched, outside
>    a transaction, with progress reporting).
> 3. Migration C — set `x` NOT NULL (using `NOT VALID` + `VALIDATE
>    CONSTRAINT` for Postgres).
```

Each finding entry uses this shape:

- ⚠️ <SEVERITY> — `path/to/file:line` — One-sentence description.
  **Fix:** concrete remediation.

If a section has no findings, mark it ✅ PASS.

---

## Constraints

- Do not modify any migration file. The audit is a review; the
  user revises.
- Do not run the migration. Do not connect to any database.
- Every finding must include the file path and a specific line
  (or operation) in the migration. "The migration is unsafe" is
  not acceptable — name what.
- Severity must include context. "CRITICAL because the `users`
  table has millions of rows" is correct; "CRITICAL" alone is not.
  If the context isn't available, state the assumption you made
  ("assuming `users` is large").
- Don't recommend "use the ORM's raw SQL escape hatch" without
  explaining which flag (e.g. for Prisma, `--create-only` plus a
  hand-edit; for Alembic, `transaction_per_migration = False`).
- Engine-specific findings must name the engine. A Postgres-only
  rule reported against an unknown engine should say "if Postgres,
  …".
- If the migration is part of a multi-migration sequence in the
  same PR, evaluate the sequence as a whole — a CRITICAL in
  migration N may be mitigated by migration N+1.
