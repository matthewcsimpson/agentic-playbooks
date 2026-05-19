---
description: Plan a React Native / Expo SDK upgrade — read release notes, scan for affected patterns, survey codemods, produce a risk-ranked migration plan.
related: [stack-upgrade-fix-react-native, post-milestone-fix]
---

# Stack upgrade — React Native variant

Plan a React Native (or Expo SDK) version upgrade.

**This prompt extends [`core/stack-upgrade-audit.core.prompt.md`](./core/stack-upgrade-audit.core.prompt.md).**
Read the core first for the workflow shape (Steps 0–7, the report
format, and the Constraints). This file supplies the React-Native-
specific detection commands, release-note sources, breaking-change
categories, codemod tools, and gotchas.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Assumed stack

- React Native (bare workflow) or Expo (managed or bare).
- TypeScript (likely) or JavaScript.
- Native projects: `ios/` (Xcode workspace, Podfile) and `android/`
  (Gradle build files), unless Expo managed.
- Common companions: React Navigation, Reanimated, Gesture Handler,
  React Native Screens, MMKV / AsyncStorage, Firebase / Sentry SDKs.

React Native upgrades are unusually invasive because they touch
the JS bundle, native iOS code, native Android code, and the build
toolchain. Effort estimates skew higher than other variants.

---

## §2 — Detect current version

```sh
# JS-side version
jq '.dependencies["react-native"], .devDependencies["react-native"]' package.json
jq '.dependencies.expo, .dependencies["expo"]' package.json 2>/dev/null

# Expo SDK
jq '.expo.sdkVersion' app.json 2>/dev/null
jq '.expo.sdkVersion' app.config.* 2>/dev/null

# iOS / Android targets
grep -E 'platform :ios' ios/Podfile 2>/dev/null
grep -rE 'compileSdkVersion|targetSdkVersion|minSdkVersion' android/ 2>/dev/null

# Node, Xcode, Android SDK
node -v
xcodebuild -version 2>/dev/null
sdkmanager --list_installed 2>/dev/null | head -n20
```

For Expo projects, the Expo SDK version implies a React Native
version. Always reference the React Native version as well — bare
debug builds compile against it directly.

---

## §3 — Release notes sources

For each upgrade in the path:

- **React Native bare**: official upgrade helper
  `https://react-native-community.github.io/upgrade-helper/`. This
  generates a full diff for every changed file (`package.json`,
  `ios/`, `android/`).
- **Expo**: SDK release notes
  `https://expo.dev/changelog`. Plus the per-version migration
  guide
  `https://docs.expo.dev/workflow/upgrading-expo-sdk-walkthrough/`.
- **Library compatibility** — React Native upgrades often force
  upgrades of React Navigation, Reanimated, Gesture Handler.
  Their changelogs are individually consequential.
- **Native platform SDKs** — Android `compileSdkVersion` / `min` /
  `target` and iOS deployment target sometimes shift, requiring
  Xcode / Android Studio upgrades.

---

## §3.5 — Common breaking-change categories (React Native)

- **Native build toolchain bumps** — minimum Xcode, minimum
  Gradle, minimum Android Gradle Plugin (AGP), minimum CMake.
  Often the first thing that breaks in CI.
- **New Architecture (Fabric / TurboModules)** — historically
  opt-in, becoming default in 0.74+. A version bump may force
  rebuilding native modules.
- **Removed JS APIs** — deprecated components (`Slider`,
  `CheckBox`, `WebView` moved out of core, etc.).
- **Behaviour changes** — Hermes default, Flipper / dev tooling
  changes, default new architecture behaviours.
- **Default changes** — JS engine (JSC → Hermes), bundler
  (Metro defaults), new architecture flags.
- **Native module compatibility** — every `react-native-*` package
  is potentially affected. Native modules that haven't kept up
  with new architecture become incompatible.
- **Tooling** — `react-native-cli` deprecated in favour of
  `@react-native-community/cli`; Expo's command surface evolves.

---

## §4 — Scan patterns (React Native)

```sh
# Removed / moved core components
grep -rnE "from\s+['\"]react-native['\"]" --include='*.tsx' --include='*.ts' --include='*.jsx' --include='*.js' . \
  | grep -E '(Slider|CheckBox|WebView|AsyncStorage|NetInfo|ViewPropTypes|MaskedViewIOS|TimePickerAndroid|DatePickerAndroid|ProgressBarAndroid)'

# New Architecture readiness
grep -rE 'newArchEnabled' android/gradle.properties ios/Podfile.properties.json 2>/dev/null
grep -rE 'RCT_NEW_ARCH_ENABLED' ios/ 2>/dev/null

# Native modules likely affected
grep -E '"react-native-[^"]+"' package.json | sort -u | head -n30

# Pod and Gradle versions
grep -E 'platform :ios' ios/Podfile
grep -rE 'classpath\s+["\']com\.android\.tools\.build:gradle' android/ 2>/dev/null
grep -E 'distributionUrl' android/gradle/wrapper/gradle-wrapper.properties

# Hermes config
grep -rE 'hermesEnabled|jsEngine' android/gradle.properties ios/Podfile* app.json 2>/dev/null

# Metro config
cat metro.config.js 2>/dev/null
```

For Expo:

```sh
# Compatibility check (Expo's tool flags incompatible deps)
npx expo install --check
npx expo-doctor 2>/dev/null

# Plugins in app config
grep -E 'plugins' app.json app.config.* 2>/dev/null
```

---

## §5 — Codemod survey (React Native)

```sh
# react-native-community upgrade helper — produces a precise diff
# (web tool; no CLI dry-run, but the diff is canonical):
# https://react-native-community.github.io/upgrade-helper/?from=<from>&to=<to>

# Expo SDK upgrade command (CLI; do not run as part of the audit):
# npx expo install expo@<target>          # mutates package.json
# npx expo install --fix                   # mutates package.json
```

The upgrade-helper diff is the authoritative source for what
*template files* change (`ios/Podfile`, `android/build.gradle`,
`Info.plist`, etc.). Apply by hand against the project's
customisations.

For JS-side codemods, React Native does not have a robust codemod
ecosystem comparable to Next.js's `@next/codemod`. Most JS
migrations are manual or expressed as breaking-change ESLint
rules.

---

## §6 — Risk patterns specific to React Native

- **Native module incompatibility** — the long pole. A single
  unmaintained `react-native-*` package can block the entire
  upgrade. Audit each dep's last release date and its target
  React Native compatibility statement.
- **iOS deployment target raise** — newer React Native versions
  often raise the minimum iOS. Users on old iOS versions stop
  receiving updates.
- **Android `compileSdkVersion` / `minSdkVersion` bumps** —
  cascades into native module updates.
- **New Architecture enablement** — when becomes-default, every
  native module must support it. Apps with many custom native
  modules face the largest effort.
- **Gradle / AGP / Kotlin minimum** — Android upgrades are
  cascading; updating AGP often requires Gradle Wrapper update
  + Kotlin version update + Android Studio update.
- **Xcode minimum** — Apple ships Xcode majors annually; React
  Native upgrades often raise the Xcode minimum, which may force
  macOS minimum on developer machines.
- **Custom native code** — anything in `ios/<App>/` or
  `android/app/src/main/java/` written by the team rather than
  generated. Native API breaking changes (e.g. AndroidX
  migrations, iOS SwiftUI / UIKit interop changes) hit this code
  directly.
- **Expo's "managed → bare" decision** — if the upgrade requires
  ejecting from managed to bare, the effort jumps an order of
  magnitude. Surface explicitly.

---

## Constraints (React Native-specific addenda)

- Always include the upgrade-helper diff as part of the plan,
  even if you summarise it. The native-template changes (Podfile,
  Gradle, Info.plist) are the single biggest source of upgrade
  bugs.
- Native module compatibility is the long pole. Audit each
  `react-native-*` dep individually; one un-upgraded module can
  block the upgrade.
- For Expo projects, prefer `expo install --check` as a
  read-only audit step. Do not run `expo install --fix` from the
  audit — it mutates `package.json`.
- iOS / Android minimum target raises are findings in their own
  right — they affect the user base, not just the engineering
  cost.
- If the project has not yet enabled the New Architecture and the
  target version requires or strongly defaults to it, treat as
  ⚠️ HIGH and flag separately. The architectural change is the
  bulk of the upgrade work.
- Effort estimates for React Native upgrades skew high. A
  "small" upgrade in this stack is typically a half-week of work
  including QA.
