---
description: Plan a .NET TFM upgrade (e.g. .NET 6 → 8, 8 → 9) — read release notes, scan for affected patterns, survey codemods, produce a risk-ranked migration plan.
related: [stack-upgrade-fix-dotnet]
---

# Stack upgrade — .NET variant

Plan a .NET TFM (Target Framework Moniker) upgrade — e.g. .NET 6 →
.NET 8, .NET 8 → .NET 9.

**This prompt extends [`core/stack-upgrade-audit.core.prompt.md`](./core/stack-upgrade-audit.core.prompt.md).**
Read the core first for the workflow shape (Steps 0–7, the report
format, and the Constraints). This file supplies the .NET-specific
detection commands, release-note sources, breaking-change
categories, codemod tools, and gotchas.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Assumed stack

- .NET (Core 6+, including .NET 6 / 7 / 8 / 9).
- C# (variant applies to F# / VB with minor adjustments).
- Project shape: ASP.NET Core (web/API), worker service, console,
  class library, Blazor, MAUI.
- Optional EF Core companion — version bumps in lockstep with .NET
  majors.

The most common upgrade path is "current LTS → next LTS"
(6 → 8, 8 → 10 once 10 ships) or "current STS → next LTS"
(7 → 8, 9 → 10).

---

## §2 — Detect current version

```sh
# TargetFramework(s) in projects
grep -rhE '<TargetFramework[s]?>' $(find . -name '*.csproj' -not -path '*/bin/*' -not -path '*/obj/*') | sort -u

# global.json SDK pin
cat global.json 2>/dev/null

# RuntimeIdentifier
grep -rhE '<RuntimeIdentifier' $(find . -name '*.csproj' -not -path '*/bin/*') | sort -u

# Installed SDKs
dotnet --list-sdks 2>/dev/null

# Project file format (modern SDK-style vs legacy)
grep -E '<Project Sdk' $(find . -name '*.csproj' -not -path '*/bin/*') | head -n3
```

Surface mixed TFMs (`net6.0` in some projects, `net8.0` in others).
Surface a stale `global.json` pin that contradicts the upgrade
target.

---

## §3 — Release notes sources

For each major in the upgrade path:

- "What's new" docs:
  `https://learn.microsoft.com/en-us/dotnet/core/whats-new/dotnet-<N>`.
- Breaking changes guide:
  `https://learn.microsoft.com/en-us/dotnet/core/compatibility/<N>`.
  Microsoft maintains an explicit breaking-changes index by area
  (ASP.NET Core, runtime, libraries, etc.).
- ASP.NET Core specific: same site under `aspnet`.
- EF Core specific: `https://learn.microsoft.com/en-us/ef/core/what-is-new`.

The .NET upgrade-assistant tool publishes its own release notes
covering what it can automate.

---

## §3.5 — Common breaking-change categories (.NET)

- **Removed APIs** — `[Obsolete(error: true)]` methods/types
  promoted from warning to error; old AdoptedEsque APIs removed.
- **Renamed APIs / Pattern changes** — `Program.cs` minimal hosting
  model (3.1 → 6), `WebApplication` builder reorganisations.
- **Behaviour changes** — JSON serialization defaults
  (`System.Text.Json` changes per major), DateTime / TimeProvider
  conventions, garbage collector defaults, threadpool defaults.
- **Default changes** — nullable reference types enabled by default
  in newer SDK templates, implicit usings, file-scoped namespaces,
  TLS defaults.
- **Dependency upgrades** — EF Core major bumps required with
  newer .NET, ASP.NET Core authentication libraries, Identity
  framework changes.
- **Tooling changes** — `dotnet test` runner defaults, project
  template changes, NuGet client behaviour, MSBuild changes,
  trimming / AOT options.

---

## §4 — Scan patterns (.NET)

```sh
# Obsolete API usage (compile warnings are the leading indicator)
dotnet build /warnaserror:CS0612,CS0618,CS0619 2>&1 | head -n100

# Minimal hosting model (Program.cs shape)
find . -name 'Program.cs' -not -path '*/bin/*' -not -path '*/obj/*' -exec head -n20 {} \;
find . -name 'Startup.cs' -not -path '*/bin/*' -not -path '*/obj/*'   # legacy hosting still present?

# System.Text.Json usage and configured options
grep -rnE 'JsonSerializer|JsonSerializerOptions|\[JsonPropertyName' --include='*.cs' . | wc -l

# DateTime patterns affected by TimeProvider / nullable changes
grep -rnE 'DateTime\.(Now|UtcNow|Today)' --include='*.cs' . | wc -l

# Nullable reference types configuration
grep -rhE '<Nullable>' $(find . -name '*.csproj' -not -path '*/bin/*') | sort -u

# EF Core version
grep -rhE 'Microsoft\.EntityFrameworkCore' $(find . -name '*.csproj' -not -path '*/bin/*')

# Authentication / Identity surface
grep -rnE 'AddJwtBearer|AddCookie|AddAuthentication|AddAuthorization|UseAuthentication|UseAuthorization' --include='*.cs' .
```

The .NET breaking-changes site is structured by area; for each
area listed under the target's breaking-changes index, run a
targeted grep.

---

## §5 — Codemod survey (.NET)

```sh
# .NET Upgrade Assistant
dotnet tool install -g upgrade-assistant
upgrade-assistant analyze <path>                # read-only analysis report
upgrade-assistant upgrade <path>                # interactive, do not run yet — use analyze for the plan
```

The upgrade-assistant tool:

- Reads the project.
- Recommends a target framework.
- Applies many mechanical changes (project file SDK-style
  conversion, minimal hosting model, etc.).
- Surfaces things it can't handle.

For Roslyn-driven analyzers and code fixers:

```sh
# Roslyn analyzer packages can be added to surface targeted upgrade
# issues. Common ones:
#   Microsoft.CodeAnalysis.NetAnalyzers (built-in from .NET 5)
#   Meziantou.Analyzer
#   StyleCop.Analyzers
dotnet build /property:RunCodeAnalysis=true     # surfaces analyzer warnings
```

Manual review covers:

- Behaviour-change findings (JSON, DateTime, TLS).
- Custom middleware / filter logic affected by ASP.NET Core
  pipeline changes.
- EF Core query shape changes between majors.
- Authentication / Authorization API changes.

---

## §6 — Risk patterns specific to .NET

- **EF Core lockstep upgrade** — EF Core majors follow .NET
  majors. The upgrade is rarely standalone; EF Core 6 → 8 carries
  query translation changes that surface as runtime behaviour
  shifts.
- **`System.Text.Json` defaults** — each major has tweaked
  serialization defaults (camelCase, default values, polymorphic
  serialization). Silent on the wire — bug reports come from API
  consumers.
- **Nullable reference types graduation** — projects upgrading
  from older majors with `<Nullable>disable</Nullable>` and
  enabling it in the upgrade get a large warning storm.
- **Minimal hosting model** — `Program.cs` + `Startup.cs` →
  `Program.cs` minimal. Optional in 6 / 7, increasingly the only
  shape in templates by 8+.
- **TLS / cipher defaults** — security-driven removals can break
  integrations with older partner systems.
- **GC / threadpool defaults** — server vs workstation GC, tiered
  compilation defaults; rarely a bug but worth a perf smoke test.
- **Runtime hosting environment** — Azure App Service, AKS,
  Lambda (via `Amazon.Lambda.AspNetCoreServer`), the .NET runtime
  image in your Dockerfile — confirm each supports the target
  before committing.

---

## Constraints (.NET-specific addenda)

- EF Core major must move with .NET major. Surface any plan that
  upgrades .NET without EF Core (or vice versa) as ⚠️ HIGH.
- If `global.json` pins an SDK, the upgrade plan must update it.
  Otherwise `dotnet build` picks the pinned SDK regardless of
  installed SDKs.
- Don't recommend running `upgrade-assistant upgrade` against the
  branch without committing the current state first — the tool
  mutates files aggressively and a partial run is hard to
  inspect.
- The `Microsoft.AspNetCore.App` shared framework is implicit on
  ASP.NET projects; its version is tied to the TFM. Don't suggest
  adding it as a PackageReference.
- For projects using `Directory.Packages.props` (Central Package
  Management), TFM changes that affect resolution may surface as
  version conflicts even if no PackageReference changed — flag
  the CPM check separately.
