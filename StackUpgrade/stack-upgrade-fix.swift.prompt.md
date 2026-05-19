---
description: Action findings from stack-upgrade-audit-swift. Apply mechanical edits, bump Swift / iOS deployment target, run pod install, verify build, commit per category. Local only.
related: [stack-upgrade-audit-swift, post-milestone-audit-swift]
---

# Stack upgrade fix — Swift / Xcode variant

Action findings from a `stack-upgrade-audit-swift` report against a
Swift / Xcode project (Swift language version, Xcode toolchain, iOS
deployment target).

**This prompt extends [`core/stack-upgrade-fix.core.prompt.md`](./core/stack-upgrade-fix.core.prompt.md).**
Read the core first.

---

## Assumed stack

- Swift project — `*.xcodeproj/`, `*.xcworkspace/`, or
  `Package.swift` (SwiftPM library).
- Dependency manager: Swift Package Manager (SPM), CocoaPods
  (`Podfile`), or Carthage (legacy). Detect by presence.
- Build invocation: `xcodebuild` for apps, `swift build` for SPM
  libraries.
- Tests: XCTest, sometimes wrapped in `swift test`.

---

## §2 — Re-verify the audit

```sh
# Find every pbxproj (covers Pods/, monorepo apps under apps/<name>/<name>.xcodeproj,
# embedded frameworks — the root-level *.xcodeproj glob misses these).
find . -name 'project.pbxproj' -path '*.xcodeproj/*' -not -path '*/build/*' > /tmp/pbxprojs

# Current iOS deployment target
xargs grep -hE 'IPHONEOS_DEPLOYMENT_TARGET' < /tmp/pbxprojs 2>/dev/null | sort -u

# Swift language version
xargs grep -hE 'SWIFT_VERSION' < /tmp/pbxprojs 2>/dev/null | sort -u

# Package.swift platforms (SPM library or mixed)
find . -name 'Package.swift' -not -path '*/.build/*' \
  -exec grep -HA2 'platforms:' {} \; 2>/dev/null

# Xcode toolchain in CI
grep -E 'xcode-version|xcode_version' .github/workflows/*.yml 2>/dev/null
```

If any of those have moved since the audit, stop and re-run.

---

## §3 — Codemods

Swift's official migration tooling is **Xcode-driven**:
**Edit → Convert → To Current Swift Syntax** (in Xcode) runs
the language migrator. This is interactive and produces diffs the
developer reviews in Xcode.

The `swift-migrate` CLI exists for some Swift Concurrency
migrations (`@MainActor`, isolated globals, sendability) but
coverage is uneven and version-dependent.

**Practical fix-prompt flow:** the audit should specify either:

- **"Run Xcode migration assistant"** — surface this as a TODO in
  the fix report. The fix prompt cannot run the interactive Xcode
  assistant; the user runs it locally, accepts / reviews the diff,
  then re-runs the fix to action the remaining mechanical edits and
  the version bumps.
- **"Run `swift-migrate <transform>`"** — apply the specified
  transform via CLI, verify, commit:

```sh
swift-migrate --strict-concurrency=complete --target=<scheme>
```

If neither was specified, skip to Step 4 (mechanical edits drive the
fix).

---

## §4 — Mechanical edits

Apply the audit's documented from→to pairs. Common categories:

**Deprecated API replacements:**

```swift
// Example (use the audit's actual list):
// NSDate → Date
// UIWebView → WKWebView
// pre-async-await completion-handler patterns → async/await
```

**Strict concurrency annotations (Swift 6 prep):**

```swift
// @MainActor on UIKit/SwiftUI methods that touch UI
// Sendable conformance on data types crossing actor boundaries
```

**SwiftUI API moves between minors:**

```swift
// .navigationBarTitle(...) → .navigationTitle(...) (deprecated path)
// onChange(of:perform:) → onChange(of:initial:_:) (iOS 17+)
```

Each category commits separately:

```sh
git commit -m "upgrade(swift): replace UIWebView with WKWebView"
```

Apply only to the audit's flagged sites. Don't sweep.

---

## §5 — Version bump

**iOS deployment target** (in `*.xcodeproj/project.pbxproj` or
`xcconfig` files):

```
IPHONEOS_DEPLOYMENT_TARGET = 17.0
```

For projects with `xcconfig` files, edit the config file rather
than the pbxproj directly. For SwiftPM:

```swift
// Package.swift
platforms: [
    .iOS(.v17),
    .macOS(.v14),
],
```

**Swift language version** (in build settings or `xcconfig`):

```
SWIFT_VERSION = 6.0
```

**CocoaPods** — if `Podfile` pins iOS:

```ruby
platform :ios, '17.0'
```

After Podfile edit:

```sh
pod install
# or
pod update    # if the audit's plan included pod updates
```

**SPM** — re-resolve:

```sh
swift package resolve            # or: xcodebuild -resolvePackageDependencies
```

Commit:

```sh
git commit -m "upgrade(swift): bump iOS deployment target 15.0 → 17.0, Swift 5.9 → 6.0"
```

---

## §6 — Post-bump edits

Edits that only make sense after the version moves:

- iOS-17-only APIs (Observation framework, new SwiftUI patterns)
  available post-bump. Opt-in adoption only.
- Swift 6 strict-concurrency errors that surface from the language
  bump. The audit should have catalogued these; apply per the
  audit's spec or surface as TODO.

---

## §7 — Verification

```sh
# SPM library
swift build
swift test

# Xcode project / workspace
xcodebuild -workspace MyApp.xcworkspace -scheme MyApp -sdk iphonesimulator clean build
xcodebuild -workspace MyApp.xcworkspace -scheme MyApp -sdk iphonesimulator test \
  -destination 'platform=iOS Simulator,name=iPhone 15'
```

The Xcode build is the only reliable gate for app projects — it
exercises the full toolchain including pods / SPM resolution.

CI considerations: the `xcodebuild` command above assumes the
appropriate Xcode is selected (`xcode-select -p`). If the audit
flagged a required toolchain bump, the local dev machine and CI
both need it; surface in the report.

---

## §8 — Hand off

```
/playbook post-milestone-audit-swift
```

Common residual drift after a Swift / Xcode bump:

- `Info.plist` keys deprecated in newer iOS (e.g.
  `UIApplicationExitsOnSuspend` semantics).
- `xcconfig` files referencing build settings the new SDK
  renamed.
- Fastlane / `xcodebuild` flags in CI referencing the old scheme
  or destination.
- Bridging headers in mixed Swift / Objective-C projects with
  modulemap drift.

---

## Constraints (Swift / Xcode-specific addenda)

- The Xcode "Convert to Current Swift Syntax" migrator is
  interactive and cannot run in a fix-prompt context. If the
  audit recommended it, surface as a TODO with the steps the
  user runs in Xcode; do not attempt to replicate it via
  command-line transforms.
- Do not edit `*.xcodeproj/project.pbxproj` directly when the
  edit can be expressed in an `xcconfig` file — pbxproj diffs
  are notoriously hard to review and prone to merge conflicts.
- `pod install` and `pod update` are different operations.
  Default to `pod install` (uses Podfile.lock as constraint); use
  `pod update` only when the audit explicitly recommended it for
  specific pods.
- Carthage projects (rare in 2025+) need their own `carthage update
  --use-xcframeworks` cycle. The audit should have flagged this;
  the fix doesn't run carthage unless the audit specified it.
- iOS deployment-target bumps drop user devices below the new
  minimum. The audit's Verdict should have flagged the user-impact
  side; the fix doesn't re-litigate that decision.
- Strict concurrency (Swift 6) findings are extensive and not
  all mechanical. The fix applies only what the audit specified
  as mechanical (e.g. adding `@MainActor` to known-UI methods);
  semantic conversions surface as TODOs.
- Do not edit `Fastfile`, App Store Connect API config, or
  provisioning profiles as part of the fix. Deploy pipeline
  drift is a separate PR.
