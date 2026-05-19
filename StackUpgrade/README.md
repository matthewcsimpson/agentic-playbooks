# StackUpgrade

Plan a framework / runtime / language version bump, then action it.
The audit reads upstream release notes, catalogues breaking changes,
scans the repo for affected patterns, surveys available codemods,
and produces a risk-ranked migration plan. The fix companion runs
the codemods serially, applies mechanical breaking-change edits,
bumps the version pin with peer-dep co-bumps, verifies between
each step, and commits per category.

Read-only audit + narrow-scope action prompt — but the *content* of
"what changed between version N and N+1" is inherently per-stack, so
the collection ships variants keyed to the same stack tags as
[`MilestoneAudit/`](../MilestoneAudit/).

Pairs with [`post-milestone-audit-<stack>`](../MilestoneAudit/) and
[`post-milestone-fix.prompt.md`](../MilestoneAudit/post-milestone-fix.prompt.md)
at the *back* end — after the fix prompt completes the mechanical
upgrade, run `post-milestone-audit-<stack>` to catch residual drift
(documentation, conventions, runtime behaviour shifts the codemods
didn't touch). The three stages together form a complete pipeline:

```
audit → fix → post-milestone-audit / post-milestone-fix
plan    execute    drift cleanup
```

| Prompt | Scope |
|---|---|
| `stack-upgrade-audit.<stack>.prompt.md` | Read-only audit. Detects current version, catalogues breaking changes for the target, scans the repo for affected patterns, surveys codemods, produces a plan. |
| `stack-upgrade-fix.<stack>.prompt.md` | Actions the audit's plan. Default scope is `codemods` + `version-bump` (the safest mechanical pieces); `mechanical-edits` and `post-bump` are opt-in. Verifies between categories, commits per category, hands off to `post-milestone-audit-<stack>`. Does not push. |
| `core/stack-upgrade-audit.core.prompt.md` | Shared audit scaffold — Steps 0–7, report format, constraints. Not invoked directly. |
| `core/stack-upgrade-fix.core.prompt.md` | Shared fix scaffold — input scoping, locate audit, per-category action, verify-and-commit gating, hand-off. Not invoked directly. |

## Variants

| Stack | Audit | Fix |
|---|---|---|
| Next.js | `stack-upgrade-audit.nextjs.prompt.md` | `stack-upgrade-fix.nextjs.prompt.md` |
| NestJS | `stack-upgrade-audit.nestjs.prompt.md` | `stack-upgrade-fix.nestjs.prompt.md` |
| Python | `stack-upgrade-audit.python.prompt.md` | `stack-upgrade-fix.python.prompt.md` |
| .NET | `stack-upgrade-audit.dotnet.prompt.md` | `stack-upgrade-fix.dotnet.prompt.md` |
| React Native / Expo | `stack-upgrade-audit.react-native.prompt.md` | `stack-upgrade-fix.react-native.prompt.md` |
| Swift / Xcode | `stack-upgrade-audit.swift.prompt.md` | `stack-upgrade-fix.swift.prompt.md` |
| Terraform / OpenTofu | `stack-upgrade-audit.terraform.prompt.md` | `stack-upgrade-fix.terraform.prompt.md` |

## When to run this

- **Audit**: before starting the upgrade — not during, not after.
  The deliverable is a *plan* with file-level findings, a list of
  codemods to run, manual changes the codemods miss, and a risk
  assessment per breaking change.
- **Fix**: after reading the audit and deciding which categories
  are in scope. Default scope is conservative (`codemods` +
  `version-bump`); opt into `mechanical-edits` and `post-bump`
  per upgrade.

For dependency-version bumps (libraries, not framework / runtime),
use [`DependencyAudit/`](../DependencyAudit/) instead. This
collection is for the spine of the stack — the framework, the
language version, the SDK. The two collections share the trivial
mechanical step of bumping a version pin in the manifest, but they
target completely different work:

- `stack-upgrade-*` = code-change project across the whole codebase
  driven by a framework / language major.
- `dependency-audit/fix` = manifest-edit project across the whole
  graph.

## Picking a variant

Pick the variant matching the version you're upgrading:

- **Next.js 14 → 15**: `stack-upgrade-audit.nextjs` → `stack-upgrade-fix.nextjs`.
- **Python 3.11 → 3.12**: `stack-upgrade-audit.python` → `stack-upgrade-fix.python`.
- **.NET 6 → 8** (or 8 → 9): `stack-upgrade-audit.dotnet` → `stack-upgrade-fix.dotnet`.
- **NestJS 9 → 10**: `stack-upgrade-audit.nestjs` → `stack-upgrade-fix.nestjs`.
- **React Native 0.72 → 0.74** (or Expo SDK 49 → 51): `stack-upgrade-audit.react-native` → `stack-upgrade-fix.react-native`.
- **Swift 5 → 6 / Xcode 15 → 16 / iOS 17 → 18**: `stack-upgrade-audit.swift` → `stack-upgrade-fix.swift`.
- **Terraform 1.5 → 1.10 / AWS provider 4 → 5**: `stack-upgrade-audit.terraform` → `stack-upgrade-fix.terraform`.

If your stack isn't listed (Go, Rust, Ruby, Java, PHP, Salesforce,
…):

1. Copy the closest audit + fix variant pair.
2. Rename to `stack-upgrade-audit.<stack>.prompt.md` and
   `stack-upgrade-fix.<stack>.prompt.md`.
3. Replace the **Release notes sources**, **Breaking-change
   categories**, **Codemod survey** sections in the audit, and the
   **Codemods** + **Version bump** sections in the fix.
4. Leave the `core/` references intact.
5. Update this README's variant table and open a PR.

## Default scopes and risk discipline (fix prompt)

The fix prompt's default scope is deliberately narrow:

- `codemods` (default) — run upstream codemods, one at a time,
  verify between, commit per codemod.
- `version-bump` (default) — bump the version pin and any required
  peer-dep co-bumps the audit identified, after codemods have
  prepared the codebase.

Opt-in categories:

- `mechanical-edits` — apply documented one-to-one breaking-change
  edits the codemods didn't cover. Stops-and-asks on ambiguous
  audit findings unless `risk:high`.
- `post-bump` — edits that only make sense once the version pin
  moves. Adoption of new APIs / patterns is opt-in.

The fix prompt does **not**:

- Push to remote or open a PR.
- Sweep beyond the audit's flagged sites.
- Improvise rewrites for ambiguous findings (surfaces as TODOs).
- Run codemods on a dirty working tree.
- Bump the version before codemods have run (canonical order is
  prepare → bump → finalize).
- Edit CI / deploy config (Dockerfile, Fastlane, vercel.json,
  CI workflows) unless the audit explicitly flagged a co-bump.

## Required tool capabilities

- File read across the repo.
- Shell execution for grep, codemod runs, package-manager bumps,
  build / typecheck / lint / test.
- Git for the fix prompt's per-category commits.
- Web access useful but not required — release notes are often
  also discoverable via local docs or `--changelog` output.

Designed for Claude Code and Codex CLI; anything with the same
capability set should work.

## Output discipline

The audit writes to
`<root>/upgrades/<stack>-<from>-<to>-<timestamp>.md` (e.g.
`.playbook-audits/upgrades/nextjs-14-15-20260519T143022.md`).
`<root>` resolves in this order: `.playbook-audits/` if it
exists, else `docs/` if `docs/upgrades/` exists (legacy
convention), else the audit creates `.playbook-audits/` and
appends it to `.gitignore` on first use. Each run produces a new
file so re-auditing the same upgrade path accumulates an ordered
history; the fix prompt picks the most recent for that
`<stack>-<from>-<to>` prefix.

The fix prompt reads that file, actions per category with a
verify-and-commit gate between categories, and writes its own
summary to the conversation (not to a file). Commits are local;
the prompt does not push or open a PR.

## Invocation

See the [root README](../README.md#invocation) for the three
supported patterns. For paste-mode, paste the relevant core file
first (audit core or fix core), then the variant — the variant
references the core for the workflow shape.
