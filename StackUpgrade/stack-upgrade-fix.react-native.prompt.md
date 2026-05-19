---
description: Action findings from stack-upgrade-audit-react-native. Run RN upgrade helper or Expo upgrade, apply mechanical edits, bump deps, verify build, commit per category. Local only.
related: [stack-upgrade-audit-react-native, post-milestone-audit-react-native]
---

# Stack upgrade fix — React Native / Expo variant

Action findings from a `stack-upgrade-audit-react-native` report
against a React Native or Expo project.

**This prompt extends [`core/stack-upgrade-fix.core.prompt.md`](./core/stack-upgrade-fix.core.prompt.md).**
Read the core first.

---

## Assumed stack

- React Native (CLI / "bare workflow") **or** Expo (managed or
  bare with Expo modules).
- TypeScript or JavaScript.
- Package manager: detect from lockfile.
- Native projects under `ios/` and `android/` (bare workflow) or
  absent / generated on demand (managed Expo).
- Test runner: usually Jest.

Detect which by:

```sh
test -f app.json && jq '.expo' app.json 2>/dev/null            # Expo presence
test -f ios/Podfile && echo 'has iOS native'
test -f android/build.gradle && echo 'has Android native'
```

If `expo` is in `package.json` and `app.json` has an `expo` block,
**use the Expo upgrade path** (Step 3a). Otherwise use the **bare RN
path** (Step 3b).

---

## §2 — Re-verify the audit

```sh
# RN version
jq -r '.dependencies["react-native"] // empty' package.json

# Expo SDK version
jq -r '.dependencies["expo"] // empty' package.json

# React peer dep
jq -r '.dependencies["react"] // empty' package.json
```

If versions have moved since the audit, stop and re-run.

---

## §3a — Codemods (Expo path)

Expo's SDK-aligned upgrade is the canonical command:

```sh
# 1. Update the expo CLI
npm install -g eas-cli              # if not present
npx expo --version

# 2. Run the SDK upgrade
npx expo install expo@<target-major>

# 3. Sync all Expo-managed dependencies to the SDK's pinned versions
npx expo install --check            # report mismatches
npx expo install --fix              # apply the SDK's pinned versions
```

`expo install --fix` is the bulk of the Expo upgrade — it knows which
React, React Native, and Expo-module versions match the target SDK
and applies them atomically.

Verify and commit:

```sh
# Verify
npx tsc --noEmit
npm run lint
npx expo prebuild --clean           # regenerates ios/ android/ from config (managed workflow)
                                    # — skip if you've ejected and edit native code by hand

# Commit
git commit -m "upgrade(react-native): expo SDK <old> → <new> via expo install --fix"
```

For bare-workflow Expo (you have `ios/` and `android/` checked in):
**do not run `expo prebuild --clean`** without confirming with the
user — it overwrites native projects. Surface as TODO instead.

## §3b — Codemods (bare RN path)

React Native's official upgrade helper:

```sh
# Get a per-version diff
npx react-native upgrade <target-version>
```

This produces a patch listing every change between RN versions.
Apply by hand (or via `react-native-upgrade-helper` web tool's
patch output). The helper does **not** transform source code — it
shows what files differ in a fresh template at the target version
vs. the current.

For source-level transforms, RN's community sometimes ships
codemods per major (e.g. `react-native-codegen` migration in
0.73+). Run any the audit recommended:

```sh
npx jscodeshift -t <transform>.js <files>
```

Verify and commit per transform / per native-side edit:

```sh
# Verify (JS only — native build comes after Step 5)
npx tsc --noEmit
npm run lint

git commit -m "upgrade(react-native): apply <transform> codemod"
```

---

## §4 — Mechanical edits

Apply the audit's from→to pairs. Common categories:

**JS-side API changes:**

```js
// Example:
// import { NativeModules } from 'react-native' API surface changes per major
// Animated.timing(...).start(callback) signature stability
// FlatList / SectionList prop renames
```

**Native config / config-plugin shape (Expo):**

```js
// app.json plugins block — config-plugin major versions diverge
```

**Native code edits (bare workflow):**

The audit may have flagged native-side edits in `ios/Podfile`,
`android/build.gradle`, `MainApplication.kt`, etc. Apply per the
audit's spec **only if explicitly in scope** — native edits are
high-risk and hard to verify without a device / simulator build.

For Expo managed projects, prefer regenerating native code via
`expo prebuild` over hand-editing.

Each category commits separately:

```sh
git commit -m "upgrade(react-native): rename FlatList onEndReached signature per RN <target>"
```

---

## §5 — Version bump

**Expo:** the `expo install --fix` in Step 3a already bumped
everything; if you skipped Step 3a, do it now.

**Bare RN:**

```sh
# Bump react-native + react + react-dom (if present)
npm install react-native@<target> react@<react-target>

# Bump pods (iOS)
cd ios && pod install && cd ..
```

Android build configuration changes happen via the patches
identified in `react-native upgrade` (Step 3b) — apply them now
if not already.

Commit:

```sh
git commit -m "upgrade(react-native): bump react-native <old> → <new>, react <old> → <new>, pod install"
```

---

## §6 — Post-bump edits

Edits that only apply after the version moves:

- New core modules available in the target RN (e.g. `Pressable`
  features, new architecture types). Opt-in adoption only.
- Expo SDK new modules — opt-in.

---

## §7 — Verification

```sh
# JS-side
npx tsc --noEmit
npm run lint
npm test                              # Jest

# Metro bundler — quick sanity check
npx react-native start --reset-cache  # then ctrl-C; just confirms config is valid

# Native builds (bare workflow only)
# iOS — best run on a developer machine with Xcode set up
cd ios && xcodebuild -workspace *.xcworkspace -scheme <Scheme> -sdk iphonesimulator build && cd ..
# Android
cd android && ./gradlew assembleDebug && cd ..

# Expo prebuild (managed)
npx expo prebuild --clean             # confirms config is valid; SKIP if you've ejected
```

For monorepos:

```sh
turbo run typecheck --filter=<app>
```

---

## §8 — Hand off

```
/playbook post-milestone-audit-react-native
```

Common residual drift after an RN/Expo upgrade:

- `metro.config.js` / `babel.config.js` keys deprecated in the
  target.
- `eas.json` profile config drifted from new EAS CLI defaults.
- iOS Podfile / Android Gradle still referencing removed plugins.
- Jest config / test setup files referencing renamed `react-native`
  internals.

---

## Constraints (React Native / Expo-specific addenda)

- For managed Expo, prefer `expo install --fix` over hand-editing
  versions. The SDK pins are tested as a set — diverging from them
  is the source of most "works in dev, breaks on EAS build" issues.
- For bare workflow with native code checked in, **never** run
  `expo prebuild --clean` as part of the fix — it overwrites
  `ios/` and `android/`. Surface as TODO if the audit recommended
  it.
- React peer-dep alignment matters. RN majors pin specific React
  ranges (`0.74` → React 18.2; `0.76` → React 18.3.1; check the
  release notes for the actual target). The audit should have
  noted the required React; the fix bumps it co-atomically.
- iOS Pods need a `pod install` after a native-affecting change.
  Stale `Podfile.lock` is the source of "it builds locally but
  not on CI" failures — surface in the report.
- Hermes vs JSC engine selection moves between majors. If the
  audit flagged a change here, apply only what the audit
  specified — switching engines is its own decision.
- Do not edit `eas.json`, Fastlane config, or App Store / Play
  Store deploy config as part of the fix. Deploy pipeline drift
  is a separate PR.
- Native verification (full Xcode / Gradle builds) is the only
  reliable gate for RN upgrades. JS-side typecheck + lint catch
  some things but not Pod / Gradle resolution failures. The
  report should make this honesty clear.
