---
description: Plan a Terraform / OpenTofu CLI or major provider upgrade (e.g. AWS provider 4 → 5) — read release notes, scan for patterns, produce a risk-ranked migration plan.
related: [stack-upgrade-fix-terraform]
---

# Stack upgrade — Terraform / OpenTofu variant

Plan a Terraform (or OpenTofu) CLI version upgrade and / or a major
provider version upgrade (e.g. AWS provider 4 → 5).

**This prompt extends [`core/stack-upgrade-audit.core.prompt.md`](./core/stack-upgrade-audit.core.prompt.md).**
Read the core first for the workflow shape (Steps 0–7, the report
format, and the Constraints). This file supplies the Terraform-
specific detection commands, release-note sources, breaking-change
categories, migration tools, and gotchas.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Assumed stack

- Terraform 1.x or OpenTofu.
- One or more provider plugins (`hashicorp/aws`, `hashicorp/azurerm`,
  `hashicorp/google`, …) declared via `required_providers`.
- Backend storage holding state (S3, GCS, azurerm, Terraform Cloud,
  …).
- Optional module registry / private modules.

Two distinct upgrade shapes share this variant:

1. **CLI upgrade** — `terraform` / `opentofu` version bump
   (state-file format, `required_version` constraint, deprecation
   of CLI flags).
2. **Major provider upgrade** — e.g. AWS 4 → 5. Much higher blast
   radius: resource schemas change, attributes rename, defaults
   shift, state-migration steps may be required.

Pick a single axis per run for clarity; do both axes simultaneously
only if the user explicitly opts in.

---

## §2 — Detect current version

```sh
# CLI in use
terraform version 2>/dev/null
opentofu version 2>/dev/null

# required_version
grep -rhE 'required_version' --include='*.tf' . | sort -u

# Provider versions
grep -rhE 'source\s*=\s*"|version\s*=\s*"' --include='*.tf' . | sort -u

# Resolved provider versions per workspace
find . -name '.terraform.lock.hcl' -not -path '*/.terraform/*' \
  -exec awk '/provider/{p=$2} /version/{print p, $3}' {} +

# Backend type and config
grep -rhE -A5 'backend\s+"' --include='*.tf' . | head -n40

# State files visible
find . -name 'terraform.tfstate*' 2>/dev/null | head -n10
```

Surface any workspaces with conflicting `required_version` or
mixed provider majors. The upgrade plan should address every
workspace, not just the one the user is standing in.

---

## §3 — Release notes sources

For each version in the upgrade path:

- **Terraform CLI**: GitHub releases
  `gh release list --repo hashicorp/terraform --limit 30`,
  then `gh release view <tag> --repo hashicorp/terraform`. Plus
  the changelog `https://github.com/hashicorp/terraform/blob/main/CHANGELOG.md`.
- **OpenTofu CLI**: `gh release list --repo opentofu/opentofu`.
- **Providers**: per-provider repo, e.g.
  `gh release view <tag> --repo hashicorp/terraform-provider-aws`.
  AWS, Azure, and Google all publish detailed major-version
  upgrade guides; read them.

For each major provider upgrade, look for an "upgrade guide"
markdown page in the provider's `docs/` directory.

---

## §3.5 — Common breaking-change categories (Terraform)

CLI-axis:

- **Removed CLI flags** — older flags get retired (`-from-module`,
  `-target` semantics, the legacy `terraform env`).
- **Default-changing flags** — implicit auto-init behaviour, state
  locking defaults, parallelism.
- **State format** — newer Terraform versions can read but not
  always write older state versions. Once upgraded, downgrading
  is not always possible.
- **HCL language** — minor syntax additions; functions
  added / deprecated.
- **Required version constraint** — once `required_version`
  bumps, older clients can't operate on the workspace.

Provider-axis (the higher-blast-radius case):

- **Resource schema changes** — attribute renames, type changes,
  required-becomes-optional or vice versa. Existing state has
  the old shape; refresh / plan diffs become large.
- **Attribute relocation** — a property moves from the resource
  to a nested block, or to a different resource entirely.
- **Default changes** — a default flips, causing all existing
  resources to show a diff under `plan`.
- **Removed resources / data sources** — replaced by new ones;
  state may need import / move operations.
- **State migration tools** — `terraform state mv`,
  `terraform import`, provider-supplied migration commands.

---

## §4 — Scan patterns (Terraform)

For CLI-axis upgrades:

```sh
# required_version vs target
grep -rhE 'required_version' --include='*.tf' .

# CLI flag usage in scripts / Makefiles / CI
grep -rE 'terraform\s+\w+' .github/workflows/*.yml Makefile scripts/ 2>/dev/null

# Deprecated functions / constructs
grep -rnE 'lookup\(' --include='*.tf' .          # lookup() with 2 args deprecated for missing-key in newer versions
grep -rnE 'list\(|map\(' --include='*.tf' .      # list()/map() function deprecated for tuple/map literals
```

For provider-axis upgrades:

```sh
# Resources by type using a specific provider
grep -rnE 'resource\s+"<provider_prefix>_' --include='*.tf' .

# Data sources by type
grep -rnE 'data\s+"<provider_prefix>_' --include='*.tf' .

# Provider configuration blocks
grep -rnE -A5 'provider\s+"<provider_prefix>"' --include='*.tf' .

# Output references — outputs that other modules / workspaces consume
grep -rnE '^output\s+"' --include='*.tf' .
```

For each known breaking change in the provider's upgrade guide,
target a specific grep. Example: AWS v5 changed many `aws_s3_bucket`
sub-blocks into separate resources — `grep -rnE 'aws_s3_bucket\s+"'`
gives the call sites, then per-buy check for the affected
attributes.

---

## §5 — Migration tool survey (Terraform)

```sh
# tfupdate — bumps the version constraints in .tf files
go install github.com/minamijoyo/tfupdate@latest
tfupdate terraform --version <target> .                 # dry: --dry-run
tfupdate provider <provider> --version <target> .

# Plan dry-run after a hypothetical upgrade — read-only:
# (point terraform binary at the target version, run plan; cf. tfenv to switch versions locally)
tfenv install <target>
tfenv use <target>
terraform plan -lock=false -refresh=false               # avoid lock; surfaces diff

# Provider upgrade tools — vary by provider
# AWS: read AWS Provider v5 Upgrade Guide; some changes require
# state mv operations
# Azure: same shape
```

Plan dry-runs against a workspace using the target Terraform /
provider versions are the most reliable signal. **Do not run
`plan` against a production backend without `-lock=false` and
not while another operator might be applying** — even read-only
operations briefly touch state.

For state-migration operations (`terraform state mv`,
`terraform state rm`, `terraform import`), list them in the plan
but do not execute. State operations against production are the
single highest-risk activity in this audit.

---

## §6 — Risk patterns specific to Terraform

- **Plan diff after provider major upgrade** — the canonical
  signal. A no-change `plan` means the upgrade is safe; a
  large `plan` after upgrade means some resources will be
  recreated / modified, with all that implies (downtime, data
  loss, replacement IDs).
- **`terraform state mv` requirements** — when a provider moves
  an attribute to a separate resource, existing state must move
  too. Doing this wrong destroys infrastructure.
- **Cross-workspace coupling** — outputs consumed by other
  workspaces; remote state data sources; bucket / DB references.
  Upgrading provider in workspace A can break workspace B that
  reads from A's outputs if the output shape changes.
- **CI / CD locked Terraform version** — the upgrade plan must
  cover the CI image used to apply. A local upgrade that diverges
  from CI surfaces as state-format errors at apply time.
- **Locking the upgrade in `required_version`** — once committed,
  older clients are locked out. Make sure the dev team is ready
  for the simultaneous bump.
- **State file backward incompatibility** — Terraform's state
  schema evolves; once written by a newer client, older clients
  may refuse to read it. Combined with shared state backends,
  this means upgrading one operator implicitly upgrades the
  team.
- **OpenTofu vs Terraform fork** — feature divergence is real
  (e.g. state encryption, `.tofu` files). An upgrade that swaps
  the binary is not just a version bump; it's a tool swap.

---

## Constraints (Terraform-specific addenda)

- Never run `terraform apply`, `terraform init -upgrade`,
  `terraform state mv`, `terraform state rm`, or
  `terraform import` from the audit. The audit produces a plan;
  the user executes it deliberately in a controlled environment.
- A `terraform plan` against a real backend should use
  `-lock=false -refresh=false` to minimise side effects, but
  even then only run if the user explicitly approves — read
  operations briefly touch state and can race with concurrent
  apply.
- Provider major upgrades must be planned per workspace. Don't
  bundle "upgrade AWS provider everywhere" into a single
  recommendation — each workspace has its own state, its own
  plan diff, and potentially its own state-mv requirements.
- Once `required_version` is bumped, the upgrade is irreversible
  from a tooling perspective without state surgery. Surface this
  as a contractual fact in the Verdict.
- For OpenTofu adoption from Terraform: it's a tool migration,
  not a version upgrade. The plan should treat it as such — file
  format compatibility, state file compatibility, feature parity,
  and CI image change all need separate sections.
- State migration operations (`mv` / `rm` / `import`) listed in
  the plan must include the exact command, the workspace it
  applies to, and the expected before/after state. "Move some
  resources" is not a plan.
