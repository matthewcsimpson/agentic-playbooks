# DB migration fix — core

Shared scaffold for the database migration fix. Not invoked
directly — the ORM-specific variants
(`db-migration-fix.prisma.prompt.md`,
`db-migration-fix.alembic.prompt.md`, etc.) reference this file
for the workflow shape, edit catalogue, and commit discipline.

A variant supplies the ORM-specific content for:

- Migration file locations and parser.
- ORM-specific edit syntax (Prisma `--create-only` + hand-edit,
  Alembic `transaction_per_migration = False`, TypeORM raw SQL
  escape, EF Core annotations / SQL).
- ORM-specific verification commands (re-generate, dry-run).

Everything else below is shared.

---

## Context

Migration fixes are unusually risky compared to other fix passes:

- Most fix prompts in this library action a list of independent
  findings (delete this unused export, update that doc). Migration
  fixes often **rewrite the same file** in multiple ways and require
  the edits to be applied as a coherent whole.
- Migrations are write-once in production. A "fix" applied locally,
  then re-run against the database, can mismatch checksums. The
  variant tells you how the ORM tracks applied state.
- Several common fixes (split a backfill out, switch to
  `CONCURRENTLY`, add a `NOT VALID` constraint with a separate
  `VALIDATE`) require **splitting one migration into multiple**.
  That's structural, not a one-line patch.

This prompt is conservative by default. It actions ⚠️ CRITICAL
findings and asks before touching anything below that.

---

## Inputs

The user supplies:

- **Severity in scope** — any of `critical`, `high`, `moderate`,
  `candidate`. Default is `critical` only. Action `high` only when
  the user explicitly opts in.
- **Specific findings to skip** — optional. Per-finding skip list.
- **Restructure permission** — optional. If a finding's fix requires
  splitting one migration into multiple, that's structural; ask the
  user before doing it. They may prefer to do that themselves.
- **Mode** — one of:
  - `auto` (recommended default): the prompt detects applied-state
    during Step 2 verification and asks the user which mode to use,
    showing them which cited migrations are on a shared environment
    and which aren't. The user picks once; the rest of the run uses
    the chosen mode.
  - `in-place`: edit the migration file directly. The fix re-checks
    applied-state per migration and stops if any cited migration is
    on a shared environment. Use when you know the migration is
    still un-applied beyond local dev.
  - `corrective`: hand-editing the applied file would mismatch the
    ORM's stored checksum, so the fix instead generates a **new
    forward migration** that reverses or compensates for the audit's
    finding. Use when the original is already in
    `_prisma_migrations` / `__EFMigrationsHistory` /
    `alembic_version` / `migrations` on a shared db.

If the user hasn't specified scope, ask. Mode defaults to `auto`.

---

## Step 1 — Locate the audit

The audit usually goes to the PR conversation, but may be written to
`<root>/migrations/<migration-id>.md` if the project tracks them.
Resolve `<root>` in this order: `.playbook-audits/` if it exists,
else `docs/audits/` if that exists (legacy convention). Ask the
user where the audit lives. If they don't have one, stop and
recommend running the matching `/playbook db-migration-audit-<orm>`
first.

If the audit is in chat, ask the user to paste it.

---

## Step 2 — Verify each finding still applies

For each in-scope finding, re-check the migration file before
editing:

- The cited file/line is still present in the migration.
- The unsafe operation hasn't already been fixed (e.g. the author
  applied `CONCURRENTLY` between audit and fix).
- The migration's applied-state. Use the ORM-specific check from the
  variant. For each cited migration, classify as either:
  - **un-applied** — not present in the ORM's applied-migrations
    table on any shared environment; in-place edit is safe.
  - **applied** — present in `_prisma_migrations` /
    `__EFMigrationsHistory` / `alembic_version` / `migrations` on
    at least one shared environment; in-place edit will fail (or
    silently skip).

  Then route by mode:

  - **`auto` mode** — present the classification to the user
    (e.g. "2 migrations un-applied, 1 already on staging") and ask
    which mode to use for the whole run. Default suggestion: if
    *any* cited migration is applied, recommend `corrective` for
    the whole run; otherwise recommend `in-place`. Don't mix modes
    in one run.
  - **`in-place` mode** — if any cited migration is applied, stop
    and offer to switch to `corrective` mode.
  - **`corrective` mode** — if no cited migration is applied, the
    in-place edit would be cheaper; confirm with the user before
    generating new corrective migrations.

If a finding no longer applies, record under "Skipped — already
fixed" and move on.

---

## Step 3 — Apply edits, finding by finding

The shape differs by mode:

- **`in-place`** — edit the original migration file directly. The
  variant supplies the per-ORM edit idioms.
- **`corrective`** — generate a new migration file via the ORM's CLI,
  then put the reversing / compensating SQL in the new file. The
  original stays untouched. Each corrective migration commits as
  one unit (the new file + any schema-source-of-truth changes the
  ORM requires to keep snapshot/migration in sync).

### Per-finding flow (`in-place`)

Apply each finding's fix individually:

1. Make the edit. Use the audit's "**Fix:**" line as the default; if
   you see a better shape (e.g. the variant's preferred idiom),
   prefer that and note why in the report.
2. Verify the edit:
   - Re-read the edited file. The fix should be present; nothing
     else should have changed.
   - Run the ORM's "dry-run" or "validate" command (variant
     supplies). If the migration still parses and the ORM accepts
     it, the syntactic fix is clean.
   - For finding-level checks specific to the operation
     (`CONCURRENTLY` added, `NOT VALID` + `VALIDATE` split,
     backfill extracted), confirm by grep within the migration
     file.
3. If verification fails: revert the edit (working tree, not
   committed) and record under "Skipped — fix broke ORM dry-run"
   with the failing command and a one-line diagnosis.
4. If verification passes: `git add` the migration file. **Do not
   commit yet** if more findings remain on the same file — batch
   them.

### Per-finding flow (`corrective`)

1. Generate a new migration via the ORM's CLI (the variant supplies
   the command and the snapshot-update semantics).
2. Author the reversing / compensating SQL in the new migration.
   The compensation is usually one of:
   - **Add the index `CONCURRENTLY`** that the original migration
     added with a lock. (Then write a follow-up that drops the
     original index if it's no longer needed.)
   - **Backfill in batches outside a transaction**, when the
     original migration tried to do it inline.
   - **Add `NOT VALID` constraint + separate `VALIDATE`**, when the
     original added a full-validation constraint that took locks.
   - **Restore data** with another forward migration, when the
     original dropped a column. (Only viable if the data exists in
     a backup; otherwise the original is unfixable post-apply —
     surface that.)
3. Verify the new migration with the variant's dry-run command.
4. If verification fails: delete the new migration file (it's a
   plain forward migration, no state-update needed) and record
   under "Skipped — corrective fix failed dry-run".
5. If verification passes: `git add` the new migration file plus
   any ORM-snapshot files the CLI generated alongside it.

---

## Step 4 — Structural fixes (split migrations)

Several common audit recommendations require splitting one
migration into multiple. The variant supplies the per-ORM mechanics
(`alembic revision`, `prisma migrate dev --create-only`,
`dotnet ef migrations add`, TypeORM `typeorm migration:create`).

The generic shape:

1. Confirm the user opted in to restructuring (the "Restructure
   permission" input).
2. Mark the original migration's destructive operation in a comment
   as "moved to migration X / Y / Z" — easier to review the split.
3. Generate the new migration files with the ORM's tooling.
4. Move operations into the new files in the order the audit
   recommends (typically: additive first, backfill second, cleanup
   third).
5. The original migration may end up with zero operations after the
   move — that's fine if the ORM allows empty migrations; otherwise
   delete it and renumber.
6. Run the ORM's full dry-run / validate across all three new
   migrations.
7. If any split step fails verification, revert *all* split files
   (the split is a unit). Record under "Skipped — split failed
   verification".

Structural fixes commit as one logical unit (one commit covers
"split migration X into X.1 / X.2 / X.3").

---

## Step 5 — Commit per migration

Each migration that received any edits commits separately. A single
PR may end up with multiple commits — one per migration touched.

Conventional commit messages naming the migration and the fix:

- `db: make idx_users_email concurrent (migration 20260514_1200_add_users_idx)`
- `db: split add_orders_status into schema + backfill + constraint`
- `db: add NOT VALID to orders.tenant_id NOT NULL constraint`

---

## Step 6 — Run the project's check suite

When all in-scope findings are actioned:

- ORM dry-run / validate across every migration touched.
- Project type-check / lint / test as relevant. Some projects
  generate migration types (`prisma generate`, `dotnet ef dbcontext
  optimize`, `typeorm-model-generator`); re-run those if the project
  does.
- If the project has a CI dry-run job (apply migrations to a
  scratch database), the user should run that locally before the
  PR; mention it as a manual gate.

---

## Step 7 — Report

Output a short summary:

- **Mode** — `in-place` or `corrective`.
- **Findings actioned** — count per severity, with migration file
  paths.
- **Findings skipped within scope** — with reason per finding
  ("ORM dry-run failed: <command>", "user deferred restructure",
  "no longer applies — author fixed").
- **Migrations modified (`in-place` mode)** — list, with one-line
  summary of changes.
- **New corrective migrations (`corrective` mode)** — list of new
  migration filenames + the original each compensates for.
- **Structural splits performed** — list, with the resulting
  migration filenames.
- **Final check result** — ORM dry-run / typecheck pass / fail.
- **Suggested PR title and body summary** — draft for a human to
  paste, not to open.

---

## Constraints

- Do not push to the remote.
- Do not open a PR.
- Do not apply the migration to any database, even local. The fix
  prompt edits files; running migrations is the user's call.
- Do not edit a migration that has been applied to any shared
  environment (anything tracked in the ORM's applied-migrations
  table on a non-dev database) **in `in-place` mode**. The fix in
  that case is `corrective` mode (a new forward migration), not an
  in-place edit. If the user invoked `in-place` mode and a shared-
  env apply is detected, stop and offer to re-run in `corrective`
  mode.
- Do not action ⚠️ HIGH / MODERATE / CANDIDATE findings unless the
  user explicitly opted in.
- Do not perform structural splits unless the user explicitly
  opted in — splits change the migration sequence and affect every
  developer who pulls.
- Do not "improve" the migration beyond what the audit recommended
  (rename columns to match a style guide, add new constraints).
  Scope creep here turns a low-risk corrective edit into a risk in
  its own right.
- If a fix requires changing the ORM schema source (e.g.
  `schema.prisma`, an entity class, a model definition), confirm
  with the user — that's outside the migration file and the
  audit's recommendation may not have anticipated it.
- If applying a fix would require resetting the migration history
  (rare but possible — e.g. an unsigned squash on an unmerged
  branch), stop and flag rather than doing it.
