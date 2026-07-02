# Audit duplicate issues — core

Shared scaffold for the duplicate-issues audit. Not invoked
directly — the platform-specific variants
(`audit-duplicate-issues.github.prompt.md`, and eventually variants
for GitLab / Linear / Jira / etc.) reference this file for the
workflow shape and reuse the generic sections.

A variant supplies the platform-specific content for:

- Authentication / capability preconditions.
- The target's address format (e.g. `OWNER/REPO`, project ID, etc.).
- Commands for verifying access and fetching the open-issues list.
- Commands for executing closures, body edits, and cross-links.

Everything else below is shared.

---

## How to ask

When a step needs the user to choose or answer — picking findings to
action, resolving an ambiguity, confirming a decision — present it as
a structured selection: the `AskUserQuestion` tool in Claude Code
(multi-select when more than one item can be chosen), or an
equivalent numbered list in a harness without that tool. Never ask as
a free-form prose question. Put the recommended option first, marked
"(Recommended)".

---

## Step 0 — Ask for the target

Before doing anything else, ask the user which repository /
project / workspace to audit. The variant specifies the exact
address format and how to phrase the question.

Do not guess and do not default to the current working directory's
git remote unless the user explicitly says "the project I'm in."
A wrong target burns context and risks acting on the wrong issues.

Optionally also ask:

- Maximum number of clusters to report (default ~15).

## Step 1 — Verify access and fetch open issues

The variant specifies the commands for verifying authenticated
access and fetching the open-issues list. The fetched data must
include, at minimum:

- Issue number / ID.
- Title.
- Labels / tags.
- Milestone / cycle / iteration.
- Body.
- Assignees.

Exclude pull requests / merge requests from the list.

If verification fails (not authenticated, project not found, no
access), surface the error and stop. Do not attempt to
authenticate from inside the prompt — that's an interactive flow
the user owns.

Report the issue count so the user knows the scope of the audit.

## Step 2 — Cluster candidates

Group issues by overlap signal. Don't rely on title alone:

- **Title similarity** — normalise titles (lowercase, strip
  punctuation, ignore prefixes like `Bug:`, `Fix:`, `[chore]`,
  emoji). Cluster titles that match after normalisation.
- **Body overlap** — same files / components / endpoints
  mentioned, same user-facing symptom, same acceptance criteria.
- **Label overlap** — multiple issues tagged with the same
  combination of feature / area labels describing the same work.
- **Cross-references** — if issue A's body mentions another issue
  by reference, treat the pair as a candidate.
- **Meta / sub-issue pattern** — one umbrella ticket vs. several
  granular ones is *not* a duplicate. Flag separately so the user
  can decide whether to keep both, restructure, or convert one
  into a task list on the other.

## Step 3 — Classify each cluster

For each candidate cluster, classify as one of:

- **Hard duplicate** — same intent, same scope. One is clearly
  redundant. Recommend closing the thinner one as a duplicate of
  the more developed one.
- **Overlapping scope** — both have legitimate content but cover
  the same work. Recommend merging the better content into one
  and closing the other.
- **Foundation + follow-up** — one issue covers setup, the other
  covers extensions / non-goals of the first. Recommend
  re-scoping the follow-up to explicitly depend on the
  foundation, and link both ways.
- **Related but distinct** — overlapping vocabulary, different
  work. Recommend cross-links only, no closures.
- **False positive** — surface-level similarity. Drop from the
  report.

## Step 4 — Report findings

Output a single table first:

| Cluster | Issues | Classification | Recommendation |
|---|---|---|---|
| PWA setup | #252, #279 | Foundation + follow-up | Re-scope #279 as follow-up to #252, link both ways |

For each cluster, follow the table with 2–4 lines giving:

- **Overlap signal** — be specific. "Both mention
  `apps/web/proxy.ts` and the redirect 401 symptom" beats
  "similar topic."
- **Recommended action** — concrete, citing issue numbers.
- **Caveats** — assignments, active milestones, comments from
  users other than the project owner.

Hard cap at ~15 clusters per pass (or the user-supplied cap). If
there are more, surface the top N by confidence and offer a
second pass.

Then **stop**. Do not act until the user picks which clusters to
action and how.

## Step 5 — Execute user-selected actions

Once the user picks, execute only what they confirmed. The
variant supplies the specific commands for:

- **Closures** — close the duplicate with a comment that links
  back to the kept issue. Never close silently — the comment is
  the navigable trail.
- **Body porting** — when the keep-issue's body lacks content
  from the close-issue that's worth preserving, port it across
  *before* closing the duplicate.
- **Cross-linking related-but-distinct issues** — append a
  `## Related` section to each issue body. Body links are more
  durable than comments and show in the issue's header reference
  list.

After each action, report the issue number actioned and the
command used so the user can audit the trail.

## Constraints

- Treat the open-issues list as authoritative for this run. Don't
  try to infer duplicates from closed issues unless the user
  asks.
- If the tracker uses a `duplicate` label / tag, check existing
  issues already tagged with it before re-flagging — they may
  have already been reviewed.
- Don't recommend closing an issue that has comments from users
  other than the project owner without flagging the social cost
  — their input gets buried in a closed thread.
- If two issues are duplicates but one is assigned or in an
  active milestone / cycle / iteration, prefer keeping that one
  even if the other has a better body. Port the body across;
  don't move the milestone or assignment.
- Don't propose more than ~15 clusters per pass. If there are
  more, surface the top 15 by confidence and offer a second pass.
- Do not close, edit, or comment on any issue without user
  confirmation. Closures are hard to reverse from the user's
  perspective (notifications fire, the issue drops out of the
  open queue) and silent edits hide the trail.
