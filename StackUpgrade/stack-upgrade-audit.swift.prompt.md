---
description: Plan a Swift / Xcode / iOS SDK upgrade — read release notes, scan for affected patterns, survey codemods, produce a risk-ranked migration plan.
related: [stack-upgrade-fix-swift, post-milestone-fix]
---

# Stack upgrade — Swift / Xcode variant

Plan a Swift language version, Xcode version, or iOS / macOS SDK
upgrade.

**This prompt extends [`core/stack-upgrade-audit.core.prompt.md`](./core/stack-upgrade-audit.core.prompt.md).**
Read the core first for the workflow shape (Steps 0–7, the report
format, and the Constraints). This file supplies the Swift-
specific detection commands, release-note sources, breaking-change
categories, codemod tools, and gotchas.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Assumed stack

- Swift project (iOS, macOS, watchOS, or tvOS).
- Xcode-managed build (`*.xcodeproj` / `*.xcworkspace`) or
  SwiftPM-managed (`Package.swift`).
- Dependencies: SPM, CocoaPods, or both.

Swift upgrades come in three roughly-independent axes:

1. **Swift language version** (e.g. Swift 5.10 → Swift 6.0).
2. **Xcode version** (e.g. Xcode 15 → Xcode 16).
3. **iOS / macOS / watchOS / tvOS SDK / deployment target**.

A "Swift upgrade" usually combines axes — newer Xcode ships a
newer Swift compiler and a newer SDK. State which axis (or
combination) the upgrade targets in Step 0.

---

## §2 — Detect current version

```sh
# Swift toolchain
swift --version 2>/dev/null
xcodebuild -version 2>/dev/null

# SWIFT_VERSION from project / package
grep -rE 'SWIFT_VERSION' *.xcodeproj/project.pbxproj 2>/dev/null
grep -E 'swift-tools-version' Package.swift 2>/dev/null

# Deployment targets
grep -rE 'IPHONEOS_DEPLOYMENT_TARGET|MACOSX_DEPLOYMENT_TARGET|WATCHOS_DEPLOYMENT_TARGET|TVOS_DEPLOYMENT_TARGET' \
  *.xcodeproj/project.pbxproj 2>/dev/null
grep -rE 'platform :ios|platform :osx|platform :watchos' Podfile 2>/dev/null

# SPM pinned packages
find . -name 'Package.resolved' -not -path '*/build/*' -not -path '*/DerivedData/*'

# CocoaPods version
pod --version 2>/dev/null
```

Note any divergence between deployment target and the Xcode /
SDK target. A deployment target of iOS 13 with code that uses
iOS 17 APIs without `@available` checks is a runtime crash on
older devices.

---

## §3 — Release notes sources

- **Swift language**: `https://www.swift.org/blog/`. Release notes
  per major (5.9, 5.10, 6.0).
- **Xcode**: Apple Developer Releases page; Xcode 15 / 16 / etc.
  release notes describe SDK changes.
- **iOS SDK**: per-OS release notes, e.g.
  `https://developer.apple.com/documentation/ios-ipados-release-notes`.
- **SwiftPM**: changes ship with Swift; same source as language.

The `Diagnostics` tab in newer Xcode versions surfaces upgrade-
relevant warnings; treat as a complementary input.

---

## §3.5 — Common breaking-change categories (Swift)

- **Language**: Swift 6 strict concurrency by default; warnings
  in Swift 5.10 that become errors in Swift 6 (`Sendable`,
  isolation, actor reentrancy). Pattern-match exhaustiveness
  tightening. New keywords (`consume`, `borrow`, `transferring`)
  may collide with identifier names.
- **Standard library**: collection conformance refinements, new
  protocols, removed deprecated symbols.
- **SDK** (UIKit / AppKit / SwiftUI / Foundation): iOS / macOS
  per-version: new APIs, deprecated APIs (still callable, may
  warn), removed APIs (rare but happens at SDK majors). SwiftUI
  evolves quickly — `ViewBuilder` semantics, property wrappers
  (`@Observable` in 17+), navigation API changes (`NavigationStack`
  vs `NavigationView`).
- **Defaults**: build setting defaults (active compilation
  conditions, optimisation modes, library evolution settings),
  ATS, privacy manifest requirements at certain Xcode majors.
- **Tooling**: `xcodebuild` flag deprecations, scheme format
  changes, Asset Catalog format changes, archiving behaviour,
  Swift macros (Xcode 15+).
- **Dependency**: SPM packages whose `swift-tools-version` doesn't
  match the new compiler; CocoaPods that haven't kept up with
  Xcode majors.

---

## §4 — Scan patterns (Swift)

```sh
# Strict-concurrency warnings (preview Swift 6 mode on Swift 5.x)
# Read project settings:
grep -E 'SWIFT_STRICT_CONCURRENCY' *.xcodeproj/project.pbxproj 2>/dev/null

# Sendable conformance — explicit @Sendable / Sendable extensions
grep -rnE '@Sendable|: Sendable|@MainActor|@globalActor' --include='*.swift' .

# Actor / @MainActor usage
grep -rnE '\bactor\b|@MainActor' --include='*.swift' . | wc -l

# Availability annotations — code paths gated by version
grep -rnE '@available\(' --include='*.swift' . | head -n30

# Deprecated SDK calls (target-version dependent)
# Manual list per upgrade — read release notes and grep accordingly.

# Property wrappers commonly affected
grep -rnE '@(State|Binding|ObservedObject|StateObject|Environment|Observable|Published)' --include='*.swift' . | wc -l

# Navigation API
grep -rnE 'NavigationView|NavigationStack|NavigationLink' --include='*.swift' . | wc -l

# UIKit / SwiftUI interop
grep -rnE 'UIViewRepresentable|UIViewControllerRepresentable|NSViewRepresentable' --include='*.swift' . | wc -l

# Async / await adoption
grep -rnE '\basync\b|\bawait\b|Task\s*\{' --include='*.swift' . | wc -l

# Privacy manifest
ls -la PrivacyInfo.xcprivacy 2>/dev/null
```

---

## §5 — Codemod survey (Swift)

Swift's codemod story is thin compared to JS / Python:

- **Xcode "Convert to Current Swift Syntax"** — under
  `Edit → Convert → To Current Swift Syntax`. Handles mechanical
  language-version renames. Run on a fresh branch; review the
  diff carefully.
- **`swift-format`** — formatting, not migration. Not a codemod
  in the upgrade sense.
- **`swiftlint`** with deprecation rules — surfaces some
  upgrade-relevant warnings.
- **Custom `swift-syntax`-based scripts** — for project-specific
  patterns. Heavyweight.

Most Swift upgrades are manual. The plan should set expectations
accordingly.

---

## §6 — Risk patterns specific to Swift

- **Strict concurrency adoption (Swift 6)** — the largest
  upgrade-time category for any codebase that uses Swift's
  concurrency. Warnings in 5.10 become errors in 6. Audit:
  - Captures of non-Sendable types across actor boundaries.
  - Singletons / shared statics that aren't `@MainActor` or
    `Sendable`.
  - Completion handlers crossing boundaries with non-Sendable
    payloads.
- **SwiftUI navigation rewrite** — `NavigationView` → `NavigationStack`
  / `NavigationSplitView`. Different API semantics; not a 1:1
  rename. Effort scales with the navigation surface.
- **`@Observable` macro** — Swift 5.9+ / iOS 17+ introduces
  `@Observable` to replace `ObservableObject`. The two coexist;
  migration is incremental but the model differs (no `@Published`).
- **iOS deployment-target raise** — affects user base, not just
  code. Surface explicitly.
- **Privacy Manifest requirements** — Apple has progressively
  required `PrivacyInfo.xcprivacy` and tracking-domains
  declarations. An Xcode upgrade may turn previously-warnings
  into store-submission rejections.
- **Asset Catalog format changes** — silent breakage of asset
  loading at runtime when the format shifts.
- **Macros (Xcode 15+)** — Swift macros require the toolchain to
  build their plugins; CI environments may need updates.
- **CocoaPods + new Xcode** — CocoaPods sometimes lags new Xcode
  majors; check the supported version before committing.

---

## Constraints (Swift-specific addenda)

- Strict concurrency adoption (when crossing Swift 6) is the
  single largest category and should be its own section in the
  plan, with effort estimated per actor / module rather than
  bundled.
- Deployment-target raises are findings even though they aren't
  bugs — they change which users can install the app. Always
  call out explicitly.
- Don't recommend "use the new SwiftUI API" as part of the
  upgrade unless the old API is deprecated to error. Upgrade =
  compatibility; adoption is a separate decision.
- For SPM-only projects (no Xcode workspace), some build setting
  patterns above don't apply — check `Package.swift` instead.
- Privacy Manifest is a store-submission gate at recent Xcode
  majors. If missing in the project, surface as ⚠️ HIGH in the
  Verdict — the upgrade can land but the next App Store
  submission can fail.
- Don't recommend running Xcode's "Convert to Current Swift
  Syntax" without a clean branch and a careful diff review — it's
  helpful for mechanical changes but historically also touches
  unrelated lines.
