---
description: Action findings from stack-upgrade-audit-terraform. Apply provider / module bumps, run terraform 0.13upgrade where applicable, plan, commit per category. Local only.
related: [stack-upgrade-audit-terraform, post-milestone-audit-terraform]
---

# Stack upgrade fix — Terraform / OpenTofu variant

Action findings from a `stack-upgrade-audit-terraform` report
against a Terraform or OpenTofu codebase (CLI version bump, major
provider bump, or backend migration).

**This prompt extends [`core/stack-upgrade-fix.core.prompt.md`](./core/stack-upgrade-fix.core.prompt.md).**
Read the core first.

---

## Assumed stack

- Terraform (>= 0.13) or OpenTofu — pinned via `required_version`.
- Provider declarations in `terraform { required_providers { ... } }`.
- Modules — local (`./modules/...`), registry (`registry.terraform.io/...`),
  git (`github.com/.../tag=...`).
- Backend — S3, GCS, Azure, Terraform Cloud, local.
- Lockfile: `.terraform.lock.hcl` (Terraform 0.14+).

---

## §2 — Re-verify the audit

```sh
# Required Terraform / OpenTofu version
grep -hE 'required_version' *.tf **/*.tf 2>/dev/null | sort -u

# Provider versions
grep -A2 -E 'required_providers\s*\{' *.tf **/*.tf | head -50

# CLI version actually installed
terraform version
tofu version 2>/dev/null
```

If versions have moved since the audit, stop and re-run.

---

## §3 — Codemods

Terraform's codemod story is thin. The notable upgrade tool:

```sh
# Legacy — only relevant for 0.12 → 0.13 migration
terraform 0.13upgrade .
```

This wraps `provider` blocks in the modern `required_providers` form.
Apply if (and only if) the audit identified a 0.12-era pattern.

Beyond that, **`tflint`** with version-target rules can surface
deprecated syntax, but it doesn't auto-fix:

```sh
tflint --init                              # download rule plugins
tflint                                     # report; the audit pre-extracted findings
```

If the audit recommended specific provider upgrade tooling (e.g.
`aws-vault-upgrade`, custom `sed` recipes for known renames), apply
per the audit's spec.

If none of these apply, skip to Step 4.

---

## §4 — Mechanical edits

Apply the audit's documented from→to pairs. Common categories:

**Provider attribute renames** (`aws_*` resources are the canonical
example — each major AWS provider release renames a handful):

```hcl
# Example (use the audit's actual list):
# aws_s3_bucket "acl" attribute moved to aws_s3_bucket_acl resource (AWS 4.x)
# aws_lb "subnets" → "subnet_mapping" semantics
```

**Resource splits / merges:**

```hcl
# aws_s3_bucket resource ground-up rewrite in 4.x:
#   - "lifecycle_rule" → aws_s3_bucket_lifecycle_configuration
#   - "server_side_encryption_configuration" → aws_s3_bucket_server_side_encryption_configuration
#   - "versioning"  → aws_s3_bucket_versioning
#
# Each becomes its own resource; the audit should have enumerated
# the affected buckets and the destination resources.
```

**Deprecated arguments removed:**

```hcl
# aws_eks_cluster vpc_config.endpoint_private_access default flipped
# google_compute_instance metadata vs metadata_startup_script
```

Each category commits separately:

```sh
git commit -m "upgrade(terraform): split aws_s3_bucket attributes into versioning, lifecycle, encryption resources (AWS 4.x)"
```

After each category, run `terraform plan` (Step 7's gate) to confirm
the **plan output shows no resource changes** — a clean upgrade
should be a no-op at the resource level. If `plan` shows
`destroy`/`create`, stop — that's the audit missing a state-move
requirement.

For state moves (`moved` blocks or `terraform state mv`), the audit
should have specified them. Apply per the audit; do **not** improvise
state moves.

---

## §5 — Version bump

**Required Terraform / OpenTofu version:**

```hcl
terraform {
  required_version = ">= 1.6.0"
}
```

**Provider versions:**

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
  }
}
```

**Module references:**

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.5"
}
```

**Lockfile re-lock — multi-platform** (so CI on linux works after a
local-macOS upgrade):

```sh
terraform init -upgrade
terraform providers lock \
  -platform=darwin_amd64 \
  -platform=darwin_arm64 \
  -platform=linux_amd64 \
  -platform=linux_arm64
```

Commit:

```sh
git commit -m "upgrade(terraform): bump terraform >= 1.6.0, aws ~> 5.30, vpc module ~> 5.5; re-lock all platforms"
```

---

## §6 — Post-bump edits

Edits that only apply after the provider/module versions move:

- New resource types or attributes available in the target. Adopt
  only if explicitly in scope.

---

## §7 — Verification

**`terraform plan` should show no resource changes** for a clean
upgrade. That's the canonical gate.

```sh
terraform init
terraform validate
terraform fmt -check -recursive

terraform plan -detailed-exitcode      # exit 0 = no changes, 2 = changes
```

For monorepo / multi-stack:

```sh
# Loop per stack
for d in stacks/*/; do
  terraform -chdir="$d" plan -detailed-exitcode
done
```

If `plan` shows changes after the upgrade, surface them in the
report. **Do not apply** to remote state from the fix prompt.

OpenTofu users substitute `tofu` for `terraform` throughout.

---

## §8 — Hand off

```
/playbook post-milestone-audit-terraform
```

Common residual drift after a Terraform / provider bump:

- `tflint` rules outdated for the new provider version (separate
  cycle: `tflint --init` to refresh plugins).
- CI workflow `terraform_version` matrix entry still listing the
  old version as supported.
- README / runbook commands referencing removed Terraform sub-
  commands.
- `.terraform-version` (tfenv) drifted from `required_version`.

---

## Constraints (Terraform-specific addenda)

- `terraform plan` showing **no resource changes** is the gate.
  Provider major bumps that look like they'll be clean often have
  subtle ordering or attribute-default shifts that show up only at
  `plan`. Do not declare the upgrade done while `plan` is
  non-empty.
- `terraform apply` is **out of scope for the fix prompt**.
  Applying state changes is a deploy operation; the upgrade fix
  leaves a clean `plan` and stops.
- Multi-platform `providers lock` matters in any team where some
  developers are on macOS and CI is on Linux. Running
  `init -upgrade` alone produces a single-platform lockfile that
  fails on the other platforms. Always include the four-platform
  `lock` command.
- `moved` blocks vs `terraform state mv` — both work for resource
  renames; `moved` blocks are preferred (terraform 1.1+) because
  they're declarative and survive collaborator runs. The audit
  should specify which; the fix doesn't choose.
- Backend migrations (changing `backend "s3"` to `backend
  "remote"`, etc.) are out of scope for the fix prompt. They
  require `terraform init -migrate-state` which is a one-way
  operation against shared state.
- Do not edit `.github/workflows/*.yml` `terraform_version` or
  CI `setup-terraform` versions as part of the fix unless the
  audit explicitly flagged a CI co-bump. Pipeline drift is a
  separate PR.
- Provider authentication (AWS credentials, GCP service account
  paths) sometimes changes between provider majors. The audit
  should have flagged; the fix does not edit credential plumbing.
