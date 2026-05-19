---
description: Read-only audit of decision/scope/architecture drift between a GitHub repo's wiki (planning docs) and the issues + commits that have landed since. Surfaces contradictions, does not edit.
related: [planning-doc-drift-fix, doc-code-drift-audit, audit-duplicate-issues-github]
---

# Planning-doc drift audit — GitHub Wiki variant

Audit a GitHub repository's wiki against the project's issues and
recent commits. Surface places where the wiki's *original*
planning docs (intent, design choices, scope) have been overtaken
by decisions landed in closed issues, in-flight plans on open
issues, or refactors visible in the commit log.

**This prompt extends [`core/planning-doc-drift-audit.core.prompt.md`](./core/planning-doc-drift-audit.core.prompt.md).**
Read the core file first for the workflow shape (Step 0 ask-for-
scope, Step 3 claim ↔ reality pairing, Step 4 drift taxonomy,
Step 5 report format, plus the Constraints). This file supplies
the GitHub-specific bits: sibling-clone convention,
`gh` / `git` commands, and the exact report path.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Assumed platform

- GitHub repository with a wiki enabled.
- `gh` CLI installed and on PATH.
- `git` installed.
- User is already authenticated (`gh auth status` reports a
  logged-in account).
- Agent has shell + filesystem access.

---

## Sibling-clone convention

GitHub serves a wiki as a separate git repo at
`https://github.com/<owner>/<repo>.wiki.git`. This playbook
expects it cloned **as a sibling of the main repo**:

```
/Users/foo/Projects/bar/        ← main repo (cwd)
/Users/foo/Projects/bar.wiki/   ← wiki clone (sibling)
```

That path (`<main-repo>.wiki/` next to `<main-repo>/`) matches
GitHub's default `git clone <wiki-url>` output.

**Deriving `<repo>`.** Use the basename of the main repo's
working tree:

```
REPO=$(basename "$(git rev-parse --show-toplevel)")
```

`<repo>` in every command below is that value. If the user
cloned the main repo under a different directory name (e.g.
`git clone … my-fork`), this basename will diverge from the
GitHub repo name returned by `gh repo view --json name`.
**Detect and stop** if they differ:

```
gh repo view OWNER/REPO --json name -q .name
```

Print: "Local repo directory `<basename>` differs from GitHub
repo name `<gh-name>`. Rename the local directory or move the
wiki clone to match, then re-run." Don't try to be clever about
it — the sibling-clone path is load-bearing for every later
command, and a mismatch silently breaks the fix variant too.

Do not clone to `/tmp/`, into the main repo, or into a hidden
directory — sibling keeps the wiki obviously co-located, easy
to edit, and easy to push by hand.

If the sibling clone is missing, this playbook **stops and
prints** the exact command:

```
git clone https://github.com/<owner>/<repo>.wiki.git ../<repo>.wiki
```

Do not auto-clone from inside the prompt. Cloning into a parent
directory is the kind of side effect that should be the user's
explicit choice.

---

## §0 — Scope (GitHub specifics)

When the core's Step 0 asks for the project, the format is
`OWNER/REPO` (e.g. `acme-corp/website`). Default to the current
repo's `gh repo view` output only if the user says "the project
I'm in"; otherwise ask:

> Which repository's wiki should I audit? (`OWNER/REPO`, e.g.
> `acme-corp/website`)

The doc surface is "all wiki pages" by default. Wiki pages are
markdown files in the sibling clone — most GitHub wikis keep
every page at the root, but subdirectories are supported and
some projects use them, so enumerate recursively rather than
assuming a flat layout. If the user wants to scope to named
pages, accept a list of page names (matched against basenames).

---

## §1 — Verify access and preconditions

Run, in order, stopping on the first failure:

```
gh auth status
```

If unauthenticated, stop. Print the user-facing instruction:
"Run `gh auth login` from your terminal, then re-invoke this
playbook." Do not attempt `gh auth login` from inside the prompt.

```
gh repo view OWNER/REPO --json hasWikiEnabled,defaultBranchRef
```

If `hasWikiEnabled` is false, stop with: "This repo has no wiki
enabled — nothing to audit." If the repo is not found, stop with
the gh error.

```
test -d ../<repo>.wiki
```

If the sibling clone is missing, stop and print the `git clone`
command from above. Do not auto-clone.

```
git -C ../<repo>.wiki status --porcelain
```

If output is non-empty (uncommitted changes in the wiki clone),
stop. The audit is read-only, but the *fix* playbook will refuse
to run with a dirty clone, and surfacing it now saves the user a
round-trip. Print: "The wiki clone has uncommitted changes — commit
or stash them in `../<repo>.wiki/` before running the fix
playbook."

```
git -C ../<repo>.wiki pull --ff-only
```

Run unconditionally — it's a no-op when current, and the only
robust way to ensure the audit runs against fresh wiki state.
If the pull fails (diverged history, conflicting changes), stop
and flag for human review. Don't try to parse `%cr` / "N hours
ago" relative timestamps to gate the pull — that's a fragile
heuristic and the pull is cheap.

---

## §2 — Ingest the inputs (GitHub commands)

Determine the cutoff. Resolve `<root>` in this order:
`.playbook-audits/` if it exists, else `docs/audits/` if that
exists (legacy convention). Find the most recent prior audit by
listing `<root>/planning-doc-drift.github-wiki-*.md` and taking
the file whose `YYYYMMDDTHHMMSS` suffix sorts last
(`ls -1 <root>/planning-doc-drift.github-wiki-*.md 2>/dev/null | sort | tail -1`).
If one exists, parse its `Date:` header (always `YYYY-MM-DD`, see
§5) — that's the `since` value. Otherwise default to 90 days ago,
formatted as `YYYY-MM-DD`. The cutoff variable is plain ISO date —
no times, no relative strings.

Closed issues since cutoff:

```
gh issue list --repo OWNER/REPO --state closed --paginate \
  --search "closed:>=<cutoff>" \
  --json number,title,body,labels,closedAt,milestone,url,stateReason
```

Open issues (all current):

```
gh issue list --repo OWNER/REPO --state open --paginate \
  --json number,title,body,labels,milestone,assignees,url
```

`--paginate` is unconditional — it's a no-op for small repos and
the right thing for large ones. `gh issue list` already excludes
pull requests.

Recent commits on the default branch:

```
git log --since=<cutoff> --pretty=format:'%H|%ci|%s' --name-status origin/<default-branch>
```

For commits whose subject suggests rename / move / split (regex:
`rename|move|extract|split|consolidate|remove`), capture the full
file-change list — those are the architecture-drift signal.

Wiki pages:

```
find ../<repo>.wiki -name '*.md' -not -path '*/.git/*'
```

Read each one. Capture the page path relative to the wiki root
(e.g. `Architecture.md`, `design/multi-tenant.md`) and the
last-modified date
(`git -C ../<repo>.wiki log -1 --format=%ci -- <relative-path>`).

Print the one-line scope summary:

```
Scanning <N> wiki pages against <M closed + K open> issues and <C> commits since <cutoff>.
```

---

## §3–4 — Claim ↔ reality pairing and categorisation

Follow the core. GitHub-specific notes:

- **Decision drift** — closed-issue `stateReason: "completed"` plus
  a PR merge in the linked timeline is the strongest signal a
  decision landed. `stateReason: "not_planned"` plus a wiki page
  still describing the feature is scope drift, not decision drift.
- **Architecture drift** — commit subjects like
  `rename: foo → bar` or files added under a new path while the
  old path's files are deleted are the clearest signals. Read the
  commit body for the *why* — it often names the wiki page if the
  author was conscientious.
- **Mechanical drift** — a renamed file path mentioned verbatim in
  a wiki page. Strong overlap with `doc-code-drift-audit`'s remit,
  but in the wiki rather than repo-local docs.

Stale threshold (core's "N months"): **6 months** for GitHub
wikis. A page untouched for 6+ months whose claims still check
out is `Stale-but-correct`.

---

## §5 — Report path

Write to **`<root>/planning-doc-drift.github-wiki-<timestamp>.md`**
in the main repo, where:

- `<root>` resolves in this order: `.playbook-audits/` if it
  exists, else `docs/audits/` if that exists (legacy convention),
  else create `.playbook-audits/` and append `.playbook-audits/`
  to `.gitignore` (creating `.gitignore` if absent — these are
  working artefacts, not tracked history). Use the same `<root>`
  found in §2 when computing the cutoff.
- `<timestamp>` is current UTC time in basic ISO 8601 format
  `YYYYMMDDTHHMMSS` — generate with `date -u +%Y%m%dT%H%M%S`
  (e.g. `20260519T143022`).

Always write a new file; do not overwrite prior runs — the
directory is an ordered history.

If a prior report exists (see §2 for how to find it), lift its
`Date:` line into a `Prior audit:` line in the new report so the
diff is obvious.

Use the core's report shape verbatim. Variant label in the
heading: `GitHub Wiki`. The `Date:` field is `YYYY-MM-DD` (no
times, no timezones) so the next audit run can use it directly
as the `gh issue list --search "closed:>=…"` cutoff. Include
in the header:

```
Wiki clone: ../<repo>.wiki/  (HEAD: <short-sha>)
```

So the user can re-derive the exact state the audit was run
against.

---

## Constraints (GitHub specifics on top of the core)

- Do not run `gh auth login`, `git clone`, or `git pull` with
  non-fast-forward strategies from inside the prompt. Stop and
  print the command for the user to run.
- Do not write to the wiki clone. The audit is read-only on both
  the main repo and the wiki clone.
- If the wiki clone has uncommitted changes, surface it but do
  not stash or revert. The audit still runs; the fix won't.
- If the wiki is empty (no `.md` files), stop with "Wiki is empty
  — nothing to audit." The user may have enabled the wiki but
  never populated it.
