---
description: Action findings from agent-instructions-audit: reword, add examples, codify undocumented, resolve contradictions, retire. Optional consolidate to one canonical. Commit per category. Local only.
related: [agent-instructions-audit]
---

# Agent instructions fix

Action the in-scope findings from the most recent
`agent-instructions-audit` report. Edit the project's agent / LLM
instruction files (`CLAUDE.md`, `AGENTS.md`, Cursor rules, Copilot
instructions, nested variants) to apply the audit's recommendations,
commit locally per category. Do not push or open a PR.

Instruction-file edits are higher-stakes than code edits: a sharpened
rule changes how the next contributor (human or LLM) approaches the
whole project. This prompt actions *only* what the audit flagged and
*only* what the user picked — no improvising new rules, no
restructuring sections, no tonal "polish."

---

## Inputs

The user supplies:

- **Consolidation strategy** — the most consequential decision, ask
  it first. Two options:

  - **Keep separate** (default) — each instruction file remains
    independent. The fix resolves explicit contradictions per the
    `resolve-contradiction` category but doesn't change which file
    holds which rule. Use this when different tools genuinely read
    from different files (e.g. GitHub Copilot reads
    `.github/copilot-instructions.md` and won't follow pointers,
    `.cursor/rules/` is loaded directly by Cursor).

  - **Consolidate to one canonical + pointer files** — pick one
    root-level instruction file (typically `CLAUDE.md` or
    `AGENTS.md`) as the source of truth. Move every rule from the
    other root-level files into it; leave each non-canonical file
    as a thin pointer (e.g. `AGENTS.md` becomes
    `"Rules for this project live in [\`CLAUDE.md\`](./CLAUDE.md)."`).

    **Tradeoff to surface to the user before they pick this:** thin
    pointers work for human readers and pointer-aware LLM agents
    (Claude Code, Cursor's agent mode, etc.), but **static tool
    readers** — notably GitHub Copilot reading
    `.github/copilot-instructions.md`, and some Cursor flows — won't
    follow markdown links and will effectively see an empty rule
    set. Only choose this when all the project's tools either read
    the canonical file directly or are pointer-aware. If unsure,
    keep separate.

    **Scope:** consolidation operates on tool-equivalent files
    **at the same path level**. Root-level files (`CLAUDE.md`,
    `AGENTS.md`, `.github/copilot-instructions.md` at the root)
    consolidate to one root canonical. Nested per-directory
    instruction files (e.g. `apps/web/CLAUDE.md`) are scope-
    specific and **never** consolidated across paths — they serve a
    different purpose. If consolidating, the fix also asks which
    file should be canonical.

- **Categories in scope** — any combination of `reword`,
  `add-example`, `codify-missing`, `resolve-contradiction`,
  `retire`. Default is all five of those (the doc-only categories).
  `enforce-mechanically` is **opt-in** — pass it explicitly to
  action mechanical-enforcement findings (see Step 4).
- **Specific findings to skip** — optional. The user may have
  triaged the report and flagged some entries as not-actually-needed
  (e.g. a rule that reads vague in isolation but is concrete in
  context).
- **Files in scope** — optional narrowing. Default is every file
  the audit covered.

If the user hasn't specified, ask before doing anything else. Don't
guess scope.

---

## Step 1 — Locate the audit

The audit writes to `<root>/agent-instructions-<timestamp>.md`.
Resolve `<root>` in this order: `.playbook-audits/` if it exists,
else `docs/audits/` if that exists (legacy convention). Look for
files matching `<root>/agent-instructions-*.md` and pick the most
recent
(`ls -1 <root>/agent-instructions-*.md 2>/dev/null | sort | tail -1`
— the `YYYYMMDDTHHMMSS` suffix sorts lexicographically). If
neither root exists or no report is found, ask the user whether
they have an inline report to paste, or whether they need to run
the audit.

If the user named a specific report file, use that one instead of the
most recent.

If neither a file nor an inline report is available, stop and
recommend running `/playbook agent-instructions-audit` first.

Parse the report's **Actions summary** section as the index — it
lists which rules fall under which category. The per-rule findings
section above it has the full detail (current text, proposed
change). Missing rules and cross-file contradictions live in their
own sections and are read directly (not via the Actions summary).

---

## Step 2 — Filter to scope

For each finding in the report, action it only if **all** of:

- The target file is **not auto-generated**. Apply the audit's Step 1
  detection heuristic — both conditions required:
  (1) marker appears in the file's **top region** only (YAML
  frontmatter, leading HTML comment block, or leading blockquote — not
  body prose); and
  (2) marker is one of the **strict phrases**: `@generated`,
  `<!-- generated -->`, `<!-- AUTO-GENERATED -->`,
  `<!-- DO NOT EDIT -->`, `THIS FILE IS GENERATED`,
  `THIS FILE IS AUTOGENERATED`, or YAML frontmatter `generated: true`.
  If both conditions hold, skip every finding against that file and
  record "skipped — file is auto-generated; edit the source instead."
  The audit should already have filtered these in its Step 1, but a
  defensive re-check here protects against stale audit reports and
  audits that ran before this skip-rule existed. Be deliberately
  strict — a `CLAUDE.md` whose body prose mentions generated files
  is *not* itself generated.
- It's under a section / category matching the in-scope categories.
- It's not in the user-supplied skip list.
- A pre-edit re-check still confirms the finding. The audit may
  have been written days ago — the file may have been hand-edited
  in the meantime.

The re-check shape per category:

- **Reword** — re-read the rule's current text in the file. If it
  already matches the audit's "proposed rewording" (or close
  enough), skip and record "audit fix no longer applies."
- **Add example** — re-read the rule. If it now has an example
  (any example), skip.
- **Codify missing** — search the in-scope instruction files for
  the proposed rule's keywords. If something similar already
  exists, skip and record "rule was added since audit."
- **Resolve contradiction** — re-read both sides. If one side has
  been changed to align with the other, the contradiction is
  resolved — skip.
- **Retire** — re-read the rule. If it's already gone, skip.

---

## Step 3a — Consolidate (only if selected in Inputs)

Skip this step entirely if the user picked **Keep separate**.

If the user picked **Consolidate to one canonical + pointer files**,
this runs **before** the category-by-category action — every later
category then operates on the canonical file alone.

1. **Confirm the canonical** the user picked (or ask now if not
   specified). Hard rule: canonical must be a root-level
   instruction file the project's tools actually read. Don't
   suggest a non-standard filename like `RULES.md` as canonical
   unless the user explicitly asks for it.

2. **Move rules from non-canonical files into the canonical:**
   - If a rule in a non-canonical file is identical (modulo
     wording) to one in the canonical, drop it from the
     non-canonical file — no need to copy.
   - If a rule is unique to the non-canonical file, move it to
     the canonical file under the matching section (use the
     canonical's existing section structure; create a new
     section only if no fit exists).
   - If a rule contradicts the canonical, apply the audit's
     `resolve-contradiction` recommendation. If the audit's
     recommendation favours the non-canonical version, keep that
     version in the canonical (i.e. update the canonical to
     match) rather than silently dropping the smarter rule.
     If the audit didn't analyse this pair, stop and ask the
     user to pick.

3. **Replace each non-canonical file's body with a one-line
   pointer.** Keep the file's existing top-of-file frontmatter or
   HTML comment if present (some tools need it). Then a single
   line:

   ```
   Rules for this project live in [`<canonical>`](<relative-path>).
   ```

   Don't leave residual sections, partial rules, or "see also"
   blocks — clean pointer only. Future audits will recognise the
   pointer pattern (it doesn't match the "rule" shape the audit
   looks for) and skip the file.

4. **Commit:** one commit for the whole consolidation, since the
   set of file edits is one logical change.

   ```
   docs: consolidate agent instructions into <canonical>
   ```

   Body lists each non-canonical file reduced to a pointer plus
   the count of rules moved into the canonical.

5. **After consolidation, the `resolve-contradiction` category
   becomes a no-op** — there's a single source of truth, so any
   audit findings under that category are inherently resolved.
   Record them as "auto-resolved by consolidation" in the final
   report.

## Step 3 — Action findings, category by category

Each category produces **one commit**. Process categories in this
order so reviewers see the diff in a sensible flow:

1. `reword` — sharpens existing rules without changing intent.
2. `add-example` — adds detail to existing rules.
3. `codify-missing` — adds new rules.
4. `resolve-contradiction` — touches multiple files; reviewers
   benefit from seeing the prior categories first.
5. `retire` — removes rules; do this last so reviewers can see
   what's being removed against the now-finalised surrounding
   rules.

For each category in scope:

1. For each finding in this category:
   a. Edit the instruction file. The audit's proposed text is a
      default, not a decision — adapt to match the file's voice
      (heading style, bullet style, code-fence conventions).
      Don't introduce new prose around the edit; replace what
      the audit identified.
   b. Re-verify the edit by re-reading the rule. The change
      should be present and read coherently in context.
   c. If the verify fails (e.g. the proposed text introduced a
      conflict with a nearby rule), record under "Skipped —
      proposed fix would break adjacent context" and revert the
      edit. Move on.
   d. If verify passes, `git add` the file. **Do not commit yet.**
2. When every finding in this category has been processed, commit
   the staged changes as one category-level commit. Conventional
   commit messages:

   - `reword` → `docs: sharpen vague rules in agent instructions`
   - `add-example` → `docs: add examples to agent instruction rules`
   - `codify-missing` → `docs: codify undocumented patterns in agent instructions`
   - `resolve-contradiction` → `docs: resolve cross-file contradictions in agent instructions`
   - `retire` → `docs: retire superseded rules from agent instructions`

3. If every finding in the category was skipped, nothing is
   staged — move to the next category without committing.

### Per-category specifics

- **Reword.** Replace the rule's text. Keep the bullet / numbering
  / heading the audit referenced — other rules and the audit
  report itself may cite the rule number.

- **Add example.** Match the surrounding example style. If the
  file uses inline code (`` `color` not `colour` ``), use inline.
  If it uses fenced blocks for examples, use a fenced block. Don't
  introduce a new convention.

- **Codify missing.** Add the proposed rule under the section the
  audit identified. The audit's report uses the form
  `recommend adding under <section> in <file>` — if the
  `<section>` slot is empty, missing, or filled with a placeholder
  (`<section>`, `TBD`, `?`), **ask the user** which section before
  adding. Don't guess. New rules follow the file's existing rule
  format (single bullet, numbered line, sub-section heading).

- **Resolve contradiction.** The audit's recommendation typically
  picks a canonical version. Apply it: keep the canonical rule
  intact, edit the other file(s) to either match or refer to the
  canonical one (`"See <file>#<section>"`). Don't silently delete
  the non-canonical version — leave a one-line "moved to <file>"
  breadcrumb so future readers of that file aren't confused.
  Breadcrumbs are pointers, not rules — future audit runs should
  treat them as cross-references and not flag them as vague-rule
  drift (the audit's clarity heuristic looks for "use X" /
  "do Y" rule patterns, which breadcrumbs don't match).

- **Retire.** Delete the rule and its leading bullet / number
  cleanly. **If the file uses explicit ordered-list numbering**
  (`1.`, `2.`, `3.`), re-number the subsequent rules in the same
  section. **If the file uses bullets** (`-`, `*`), no
  renumbering is needed — the audit's `Rule N` numbering is its
  own internal index, not a numbering in the source file. If the
  retired rule was the only one under a sub-section heading,
  remove the now-empty heading. Don't leave `~~strikethrough~~`
  or `[removed]` stubs — the commit message and `git log` are
  the historical trail.

---

## Step 4 — Mechanical enforcement (opt-in)

`enforce-mechanically` findings are **off by default**. They're a
code change disguised as a doc fix — adding a hook, an ESLint rule,
a pre-commit check, or a CI gate. Each mechanism has its own
config file, conventions, and side effects, and a generic
playbook can get them wrong in ways that take longer to debug than
the rule was worth.

When the user opts in (`enforce-mechanically: yes` or equivalent):

1. For each finding, read the proposed mechanism. If it's vague
   ("enforce somehow"), skip and surface — the audit should have
   named a concrete mechanism.
2. Confirm the mechanism's config file exists or can be added
   safely (e.g. for ESLint, the project actually uses ESLint
   — check `package.json` / `eslint.config.*`). If the prerequisite
   is missing, skip and flag.
3. Add the rule to the mechanism's config. Don't refactor
   surrounding config; add the minimum needed.
4. **Verify** the mechanism actually fires: run the relevant
   command (`pnpm lint`, `pre-commit run --all-files`, etc.) and
   confirm a violating-by-design fixture (or the existing
   codebase) surfaces the expected output. If the project is too
   clean to confirm the rule fires, create a fixture file
   following these rules — in order, non-negotiable:

   a. Place the fixture **inside the project's lint scope** (e.g.
      under `src/` if `src/` is what the linter targets). Linters
      and pre-commit hooks scope by config; a fixture in `/tmp/`
      or outside the lint glob is invisible to the rule and the
      verify becomes a no-op.
   b. Use a path the project's `.gitignore` already excludes
      (e.g. `src/__lint_fixture__.ts` if `__*__` is gitignored).
      If no such path exists, add one entry to `.gitignore` in
      the working tree (`.gitignore` takes effect as soon as it's
      written — no need to commit it first; the entry shields the
      fixture from staging from the moment it's saved). The
      `.gitignore` change will fold into the mechanism's commit
      in step 6, so reviewers see "rule X enforced via Y" as one
      self-contained change rather than two unexplained commits.
   c. After running the verify command and confirming the rule
      fires, **delete the fixture file**, then run
      `git status --porcelain` — the only paths shown should be
      the mechanism's config plus (if you added one in step 4b)
      the `.gitignore` change. The fixture itself must be gone.
      Do not proceed to the commit if `git status` shows anything
      unexpected.
5. Update the doc rule to reference the mechanism:
   `"Enforced by ESLint rule \`no-restricted-imports\` — see \`.eslintrc.cjs\`."`
6. Commit per-mechanism (so reviewers can revert one without
   touching others). Include the mechanism's config, the
   instruction-file rule update from step 5, and the `.gitignore`
   entry from step 4b (if you added one) — all in the same
   commit. One commit per enforced rule:

   - `chore: enforce <short-rule-summary> via <mechanism>`

If at any point the verify step fails, **revert the config
addition and skip the finding** — a half-wired enforcement rule
is worse than a doc-only one because it hides drift.

If the user didn't opt in but the audit had mechanical-enforcement
findings, list them in the final report (Step 6) so the user knows
what's deferred.

---

## Step 5 — Run the project's doc-related checks

When all in-scope findings are actioned, run whatever the project
has wired up for instruction-file hygiene:

- Markdown lint (`markdownlint`, `vale`) on edited files.
- Project's `docs:check` / `lint:docs` script if defined.
- For mechanical-enforcement edits: the relevant lint / hook /
  pre-commit command (already verified in Step 4 per finding;
  re-run once at the end to confirm the full set passes).

If nothing is wired up, that's the report — note it.

---

## Step 6 — Report

Output a short summary:

- **Findings actioned** — count per category, with rule numbers
  and file paths.
- **Findings skipped within scope** — with reason per finding
  ("audit fix no longer applies," "user opted to keep," "proposed
  fix would break adjacent context").
- **Mechanical-enforcement findings deferred** — listed only if
  user did not opt in. Each entry: rule, proposed mechanism, the
  one-line user command to opt in next run.
- **Files modified** — list (instruction files + any config
  files touched for mechanical enforcement).
- **Commits created** — list with subjects.
- **Final check result** — pass / fail with the failing command,
  or "no doc-check tooling configured."
- **Suggested PR title and body summary** — draft for a human to
  paste, not to open.

---

## Constraints

- Do not push to the remote.
- Do not open a PR.
- Do not action `enforce-mechanically` findings unless the user
  explicitly opted in.
- Do not consolidate instruction files unless the user explicitly
  selected the **Consolidate** input. Default is **Keep separate**.
  Consolidation has a real tradeoff (static tool readers don't
  follow pointers) — silent consolidation could leave a project's
  GitHub Copilot effectively rule-less without the user noticing.
- Do not consolidate **nested** per-directory instruction files
  (e.g. `apps/web/CLAUDE.md`) into the root canonical. Nested files
  exist to scope rules to a sub-directory; flattening them loses
  that scope. Consolidation operates on tool-equivalent files
  at the same path level only.
- Do not rewrite prose adjacent to a rule edit. Replace the
  flagged content, leave everything else alone. Scope creep turns
  a focused fix into a sprawling review.
- Do not restructure sections, rename headings referenced by
  other rules / external docs, or split files. Structural edits
  belong in a separate, deliberate pass.
- Do not invent new rules. Codify only what the audit listed in
  its `Missing rules (observed but undocumented)` section, and
  only with the audit's proposed wording (with light voice
  adaptation).
- Do not retire a rule the audit marked `Strong` compliance, even
  if the user asked for it — flag and require explicit
  confirmation. Strong compliance means the team is following the
  rule; retiring it removes a working norm.
- Do not silently change the *meaning* of a rule when rewording.
  If the audit's proposed rewording shifts intent (not just
  wording), stop and flag for human review.
- Do not commit a half-wired mechanical-enforcement rule. If the
  mechanism's verify step fails (Step 4), revert and skip.
- If a fix requires resolving a contradiction in a way the audit
  didn't recommend (e.g. the audit said "pick A," but on reading
  the rules in context, B reads more current), stop and flag —
  contradiction resolutions are judgment calls that shouldn't be
  made silently.
