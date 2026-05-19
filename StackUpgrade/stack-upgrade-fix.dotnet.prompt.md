---
description: Action findings from stack-upgrade-audit-dotnet. Run dotnet upgrade-assistant where applicable, apply mechanical edits, bump TFM, verify build, commit per project. Local only.
related: [stack-upgrade-audit-dotnet, post-milestone-audit-dotnet]
---

# Stack upgrade fix — .NET / C# variant

Action findings from a `stack-upgrade-audit-dotnet` report against a
.NET solution (TFM bump — e.g. `net6.0` → `net8.0` → `net9.0`).

**This prompt extends [`core/stack-upgrade-fix.core.prompt.md`](./core/stack-upgrade-fix.core.prompt.md).**
Read the core first.

---

## Assumed stack

- .NET SDK with `*.csproj` / `*.sln`.
- C# (F# / VB use the same TFM mechanics; language-specific edits
  may differ).
- Package manager: NuGet — Central Package Management (CPM) via
  `Directory.Packages.props` if present.
- Build system: MSBuild via `dotnet build`.

---

## §2 — Re-verify the audit

```sh
# Current TFM(s) — multi-target projects list multiple
grep -RhE '<TargetFramework[s]?>[^<]+' --include='*.csproj' .

# SDK version pin
cat global.json 2>/dev/null
dotnet --version
```

If TFMs have changed since the audit, stop and re-run.

---

## §3 — Codemods / upgrade-assistant

The official tool is `dotnet upgrade-assistant` (formerly `try-convert`
for older paths). Install if not present:

```sh
dotnet tool install --global upgrade-assistant
```

Run against the solution or a single project, **non-interactive
mode** for the fix prompt:

```sh
upgrade-assistant upgrade --non-interactive <Solution.sln>
# or per-project
upgrade-assistant upgrade --non-interactive path/to/Project.csproj
```

The tool handles:

- TFM bump in `.csproj`.
- Common API rename / namespace move analyzers (rolled in via
  Roslyn).
- `packages.config` → `<PackageReference>` migration (legacy
  projects).

It misses:

- Behaviour-change findings the audit flagged.
- NuGet package bumps required by the TFM move that aren't direct
  TFM consequences (e.g. `Microsoft.Extensions.*` family co-bumps
  to match the new runtime).
- ASP.NET Core middleware order changes between majors.

If the audit didn't recommend `upgrade-assistant`, skip it — older
projects sometimes fight the tool. Apply mechanical edits (Step 4)
and version bump (Step 5) directly.

Verify and commit per-project after the assistant runs:

```sh
dotnet build path/to/Project.csproj
git commit -m "upgrade(dotnet): apply upgrade-assistant to Project.csproj"
```

---

## §4 — Mechanical edits

Apply the audit's documented from→to pairs. Common categories per
.NET major:

**Namespace / API renames** (Roslyn analyzers usually flag these
during build — the audit pre-extracted them):

```csharp
// Example:
// using System.Web.Http  →  using Microsoft.AspNetCore.Mvc  (Framework → Core, edge case)
// using Microsoft.AspNetCore.Http.Internal  →  removed; use Microsoft.AspNetCore.Http
```

**ASP.NET Core startup shape:**

```csharp
// Startup.cs + Program.cs (split style) → minimal Program.cs (.NET 6+)
// app.UseEndpoints(endpoints => endpoints.MapControllers())  →  app.MapControllers()
// services.AddControllers().AddNewtonsoftJson()  →  System.Text.Json default in newer majors
```

**Nullable reference types** (project-level opt-in change):

```xml
<!-- Many .NET 8+ project templates enable <Nullable>enable</Nullable> -->
<!-- The audit should have flagged the cascade of warnings as findings;
     the fix applies the audit's specified suppressions or annotations -->
```

Apply per category, verify, commit:

```sh
git commit -m "upgrade(dotnet): replace UseEndpoints + MapControllers with top-level MapControllers"
```

If the audit's specification is ambiguous, surface as TODO.

---

## §5 — Version bump

Bump the TFM in each `.csproj`. Multi-targeting projects bump each
TFM in the `<TargetFrameworks>` element.

```xml
<!-- Before -->
<TargetFramework>net6.0</TargetFramework>

<!-- After -->
<TargetFramework>net8.0</TargetFramework>
```

Use the audit's specified target TFM. If the project uses Central
Package Management, the version bumps for `Microsoft.*` packages
that move with the TFM go in `Directory.Packages.props`:

```sh
# Bump Microsoft.Extensions.* family to match the new runtime
# (the audit should have enumerated these)
dotnet add package Microsoft.Extensions.Hosting --version <target-version>
dotnet add package Microsoft.Extensions.Configuration --version <target-version>
# ...
```

Update `global.json` if the audit flagged a required SDK bump:

```json
{
  "sdk": {
    "version": "<target-sdk>",
    "rollForward": "latestFeature"
  }
}
```

For solutions with many projects, the TFM bump goes into
`Directory.Build.props` (if present) as a single change:

```xml
<PropertyGroup>
  <TargetFramework>net8.0</TargetFramework>
</PropertyGroup>
```

Restore + build:

```sh
dotnet restore
dotnet build
```

Commit:

```sh
git commit -m "upgrade(dotnet): bump TFM net6.0 → net8.0, Microsoft.Extensions.* to <version>, SDK to <version>"
```

---

## §6 — Post-bump edits

Edits that only make sense after the TFM moves:

- New analyzers shipped with the SDK may flag previously-quiet code.
  Resolve per the audit's specification or surface as TODO.
- Required-member syntax (`required` modifier on properties) and
  primary constructors (.NET 7+) are language features available
  post-bump but not strict-upgrade edits — adoption only if the
  user opted in.

---

## §7 — Verification

```sh
# Per-category gate
dotnet build                          # exercises the whole solution

# Full suite
dotnet test
dotnet format --verify-no-changes     # formatting drift check
```

For solutions with many projects:

```sh
dotnet build path/to/Project.csproj   # scope per-project for speed
dotnet test path/to/Project.Tests.csproj
```

---

## §8 — Hand off

```
/playbook post-milestone-audit-dotnet
```

Common residual drift after a TFM bump:

- `Directory.Packages.props` drift — some packages got version-
  pinned at one place but referenced at the project level too.
- Implicit `using` directives that the new SDK enabled — IDEs may
  flag previously-needed `using` statements as redundant.
- Deployment manifest (`Dockerfile`, `runtimeconfig.template.json`)
  still referencing the old runtime image / version.

---

## Constraints (.NET-specific addenda)

- For multi-target projects, bump every TFM in the
  `<TargetFrameworks>` element atomically, not one at a time.
  Half-migrated multi-target projects fail with confusing
  conditional-compile errors.
- If the project uses Central Package Management, bumps go in
  `Directory.Packages.props` only — per-project `<PackageReference>`
  with a `Version` attribute when CPM is enabled is an error.
- Do not auto-enable `<Nullable>enable</Nullable>` as part of the
  fix unless the audit specifically flagged it. Nullable annotations
  cascade thousands of warnings on legacy code; that's its own
  initiative.
- Roslyn analyzers shipped with the new SDK may suggest sweeping
  refactors. The fix prompt does **not** action those — apply only
  what the audit specified.
- Test harness frameworks (xUnit, NUnit, MSTest) sometimes lag the
  TFM. Verify the chosen test framework supports the target runtime
  before bumping — the audit should have noted this.
- Do not edit `Dockerfile` or CI workflow `dotnet-version` as part
  of the fix unless the audit explicitly flagged a change. Pipeline
  drift is a separate PR.
