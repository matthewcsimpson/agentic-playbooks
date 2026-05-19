# MilestoneAudit

Static-drift audit and follow-up fix prompts that run after every
milestone. Pair with the sibling [`MilestoneSmoke/`](../MilestoneSmoke/)
folder, which exercises behaviour at runtime.

The audit comes in framework-flavoured variants because the
*regression categories* and *extraction signals* differ
substantially across stacks. The user-runnable variants sit at
the top of this folder; the shared scaffold lives in `core/`.

| Step | Prompt | Scope |
|---|---|---|
| 1 | `post-milestone-audit.nextjs.prompt.md` | Next.js + TypeScript |
| 1 | `post-milestone-audit.nestjs.prompt.md` | NestJS (backend TS services) |
| 1 | `post-milestone-audit.python.prompt.md` | Python (FastAPI / Django / Flask / CLI / library) |
| 1 | `post-milestone-audit.dotnet.prompt.md` | .NET / C# (ASP.NET Core, EF Core, worker services) |
| 1 | `post-milestone-audit.react-native.prompt.md` | React Native / Expo |
| 1 | `post-milestone-audit.swift.prompt.md` | Swift / Xcode (iOS / macOS / watchOS / tvOS) |
| 1 | `post-milestone-audit.terraform.prompt.md` | Terraform / OpenTofu (infrastructure-as-code) |
| — | `core/post-milestone-audit.core.prompt.md` | Shared scaffold. Not invoked directly. |
| 2 | `post-milestone-fix.prompt.md` | Stack-agnostic — reads the audit report and actions findings matching the triage labels and sections you supply. |

## Typical workflow

1. Tag the milestone (`git tag v0.x.y && git push --tags`).
2. (Optional, before this step) Run the matching variant from
   [`MilestoneSmoke/`](../MilestoneSmoke/) to catch behavioural
   regressions first.
3. Run the **audit variant** that matches your stack — produces
   `<root>/milestones/<tag>-<timestamp>.md` (default `<root>` is
   `.playbook-audits/`).
4. Triage the audit (override the `Suggested:` labels where
   needed).
5. Run **fix** with the labels and sections you want actioned.
6. Review the local commits, push, open a PR yourself.

## Picking an audit variant

- **Next.js + TypeScript** (web front-end / SSR):
  `post-milestone-audit.nextjs.prompt.md`.
- **NestJS** (TypeScript backend):
  `post-milestone-audit.nestjs.prompt.md`.
- **Python** (FastAPI / Django / Flask / CLI / library):
  `post-milestone-audit.python.prompt.md`.
- **.NET / C#** (ASP.NET Core, EF Core, worker services):
  `post-milestone-audit.dotnet.prompt.md`.
- **React Native / Expo** (cross-platform mobile, JS layer):
  `post-milestone-audit.react-native.prompt.md`.
- **Swift / Xcode** (native iOS / macOS / watchOS / tvOS):
  `post-milestone-audit.swift.prompt.md`.
- **Terraform / OpenTofu** (infrastructure-as-code):
  `post-milestone-audit.terraform.prompt.md`.
- **Other stack (Go, Rust, Ruby, Java, Salesforce, PHP /
  WordPress, …)**: copy the closest variant, adapt the
  framework-specific sections, and open a PR to add the new
  variant.

Both variants extend `core/post-milestone-audit.core.prompt.md`
that holds the parts that don't change between stacks (audit-window
logic, sourcing convention docs, delta against prior audit, output
format, constraints). The variant prompt tells the agent to read
the core file first.

**Invocation note**: if you're pasting a variant into a chat
without filesystem access to the repo, paste the core file first,
then the variant. For clone-and-reference or copy-into-project
invocation, this is transparent.

## Triage vocabulary

The audit emits a triage suggestion for every ⚠️ ISSUE; the fix
prompt filters by it:

- `fix-now` — ship in the current cycle.
- `fix-soon` — schedule before the next milestone.
- `defer` — real but not worth fixing yet.
- `accept` — known and not worth changing.

These labels are the contract between the audit and the fix
prompt. If you swap one prompt out, keep the vocabulary or update
both.

## Output discipline

The audit writes to:

- New convention: `<root>/milestones/<tag>-<timestamp>.md` (e.g.
  `.playbook-audits/milestones/v1.6.0-20260519T143022.md`).
- Legacy convention: `<root>/audits/<tag>-<timestamp>.md` (e.g.
  `docs/audits/v1.6.0-20260519T143022.md`).

`<root>` resolves in this order: `.playbook-audits/` if it
exists, else `docs/` if `docs/audits/` exists (legacy
convention), else the audit creates `.playbook-audits/` and
appends it to `.gitignore` on first use. Each run produces a new
file so re-auditing the same tag accumulates an ordered history
instead of overwriting; the fix prompt picks the most recent.
The audit uses prior reports to compute a delta, so keeping them
locally matters, but committing them invites churn — note that
the auto-gitignore only applies on the new-folder branch. If
you're on the legacy `docs/audits/` path, add it to `.gitignore`
manually.

## Required tool capabilities

- File read across the repo.
- Shell execution (git, the project's check / lint / test / build
  commands).
- Git branch and commit (fix prompt only).
- File write under `docs/` (audit prompt only).

Designed for Claude Code and Codex CLI. Anything with the same
capability set should work.

## Adapting to a project

The audit's spine is convention compliance — the variant reads
the project's `CLAUDE.md` / `AGENTS.md` / `.cursor/rules/**` and
sweeps the codebase for each documented rule. The more specific
those files are, the sharper the audit.

A reasonable adaptation pattern:

1. First run: audit catches whatever it can from the variant's
   regression categories.
2. Look at what slipped through. Add rules to `CLAUDE.md`.
3. Second run: audit catches the new rules too.

Treat the audit as a feedback loop on the convention
documentation, not just on the code.

### Adding a new audit variant

If the existing variants don't fit your stack:

1. Copy the closest variant.
2. Rename to `post-milestone-audit.<stack>.prompt.md`.
3. Replace the **Assumed stack**, **§2** sweep examples, **§3**,
   **§4**, **§4.5**, and **§5** sections with stack-appropriate
   content.
4. Leave the reference to `core/post-milestone-audit.core.prompt.md`
   intact — the core stays shared.
5. Update this README's variant table.
