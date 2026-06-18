---
description: Audit a React Native / Expo codebase after a milestone tag is cut — drift, regressions, extraction signals, and convention compliance against documented rules.
related: [post-milestone-fix]
---

# Post-milestone audit — React Native / Expo variant

Audit a React Native (Expo or bare RN) codebase after a milestone
tag is cut.

**This prompt extends [`core/post-milestone-audit.core.prompt.md`](./core/post-milestone-audit.core.prompt.md).**
Read the core file first for the workflow shape, audit-window
logic, convention-source discovery, delta logic, output format,
and constraints. This file supplies the React Native specifics for
§2 examples, §3 milestone-diff focus, §4 regression sweeps, §4.5
extraction signals, and the §5 drift counter.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Assumed stack

- **Framework**: React Native (bare or Expo SDK).
- **Language**: TypeScript with `strict` mode expected.
- **Navigation**: `react-navigation` or `expo-router`.
- **State / data**: typically React Query / TanStack Query or
  Zustand / Redux Toolkit / Apollo.
- **Styles**: `StyleSheet.create` and / or a theme provider; some
  projects layer Tamagui / NativeWind / Restyle on top.
- **Testing**: Jest + React Native Testing Library; Detox or
  Maestro for E2E (not exercised by this audit).
- **Build / package**: pnpm / npm / yarn; if Expo, also `expo-cli`
  and EAS Build.

For Next.js front-end work see `.nextjs`. For client-rendered
React-web work (Vite / CRA SPA) see `.vite` — it carries the
SPA-specific env, routing, and code-splitting checks.

---

## §2 — Per-rule sweep (React Native rule categories to look for)

Beyond the convention sources listed in the core, also read:

- `app.json` / `app.config.{ts,js}` — Expo config, plugin list,
  permissions declarations.
- `metro.config.js` — Metro bundler customisation, especially
  any monorepo / workspace setup.
- `babel.config.js` — Babel preset (`babel-preset-expo` or
  `@react-native/babel-preset`); plugins like Reanimated.
- `tsconfig.json` — `strict` flags, path aliases.
- `package.json` scripts — `start`, `ios`, `android`, `build`,
  `test`, `lint`.
- `eas.json` — EAS Build profiles (development, preview,
  production).

Common rule categories the project's docs tend to enforce:

- **Language / spelling** — locale conventions everywhere
  including UI strings.
- **File / folder layout** — screens vs components vs hooks;
  navigation stacks colocated with their screens.
- **TypeScript discipline** — same as web; plus typed navigation
  params (the `RootStackParamList` pattern).
- **Platform-specific code** — `Platform.OS === 'ios'` branches
  vs `.ios.tsx` / `.android.tsx` files; consistent within the
  project.
- **Permissions** — declared in `app.json` / `Info.plist` /
  `AndroidManifest.xml`; requested at the point of use with a
  rationale; handle "denied" + "denied permanently" states.
- **Asset management** — images optimised, multiple densities
  (`@2x`, `@3x`) provided; fonts registered through Expo's
  config plugins or `react-native.config.js`.
- **Environment / secrets** — `expo-constants` / `react-native-config`
  (not `process.env.*` baked into the bundle); no secrets in the
  bundle (they're recoverable from any installed app).
- **Testing** — components tested with RN Testing Library;
  fire user events through `userEvent` rather than `fireEvent`
  where possible; screens tested with their actual
  navigation harness.
- **Accessibility** — every touchable has
  `accessibilityLabel` and `accessibilityRole`; meaningful
  text on icons; `accessible={false}` only where the parent
  composes the label.

---

## §3 — Milestone diff focus

For files changed in this milestone, check:

- **New screens**: registered in the navigation tree? Typed
  navigation params? `accessibilityLabel` on screen-level
  touchables? Screen-level analytics fired if the project tracks
  screen views?
- **New components**: `<Text>` (not bare strings or `<Text>` only
  on inner spans)? `<View>` (not `<div>`)? Platform-specific
  rendering deliberate or accidental? Memoised (`React.memo` /
  `useCallback`) if used inside a `FlatList renderItem` or
  similar hot path?
- **New lists**: `FlatList` / `SectionList` / `FlashList` for
  variable-length data, not `ScrollView` mapping over an array?
  `keyExtractor` defined? `getItemLayout` where item heights are
  known?
- **New navigation patterns**: deep links updated in the linking
  config? Back-handler / hardware-back behaviour considered on
  Android?
- **New images / fonts / assets**: dimensions specified?
  Optimised? Different resolutions present?
- **New permissions**: declared in the manifest? UX explains
  *why* before requesting? Denied / never-asked-again states
  handled?
- **New native modules** (bare RN) or **Expo modules**: required
  Expo SDK version available? Config plugin needed?
- **New env / config reads**: routed through `Constants` /
  `react-native-config`? Not `process.env.SOMETHING` literal
  (bundler-replaced; doesn't update with EAS profiles)?
- **New dependencies**: native-module deps require a rebuild
  (call out in the PR body)? Pinned to versions the EAS build
  is configured for?
- **New TODO / FIXME comments**: list every one.
- **New `console.log` / `console.warn` / `console.error`**: list
  every instance.

---

## §4 — Full-sweep regression check

### TypeScript quality
- Non-null assertions (`!`).
- Type assertions (`as SomeType`) masking errors.
- Implicit `any` (especially in navigation params).
- `@ts-ignore` without comment.

### React Native patterns
- `ScrollView` rendering more than ~10–20 items where
  `FlatList`/`FlashList` should be used (memory + perf).
- `FlatList` missing `keyExtractor` (uses index, breaks on
  reorder).
- Inline arrow functions / objects in `renderItem` (re-renders
  every row each parent render).
- Long-running computation in `render` / function body without
  `useMemo` (mobile CPUs feel this more than desktop).
- `<Text>` nested directly inside a touchable with custom
  styling — flag if the touchable's hit target doesn't match
  the text's bounding box.
- `TouchableOpacity` / `TouchableHighlight` in new code where
  `Pressable` is the modern alternative.
- `StyleSheet.create` blocks redefined in multiple components
  with the same content (extract to a shared style).
- Inline `style={{ ... }}` props doing static styling
  (allocates a new object every render) — should be
  `StyleSheet.create`.

### Navigation patterns
- Untyped `navigation.navigate('SomeRoute', { ... })` calls
  (the project should have typed navigation params).
- Hardcoded route names instead of constants.
- `useFocusEffect` used where `useEffect` would suffice (or
  vice versa).

### State / data
- `useState` chains describing one piece of state — usually a
  `useReducer` or custom hook.
- `useEffect` bodies longer than ~20 lines — typically a custom
  hook is hiding.
- Network calls outside the project's chosen query layer
  (React Query / Apollo) — flag the inconsistency.
- Cache invalidation that doesn't match the project's
  documented pattern.

### Memory / lifecycle
- Subscriptions / listeners not unsubscribed on unmount
  (`Linking.addEventListener`, `AppState.addEventListener`,
  socket subscriptions, timers).
- `setTimeout` / `setInterval` started without a cleanup.
- Refs to expensive resources (images, AV players) without
  release on unmount.

### Accessibility
- Touchables without `accessibilityLabel`.
- Icons-only buttons without accessibility text.
- Custom interactive elements without `accessibilityRole`.
- Form inputs without associated labels.

### Permissions
- Permissions requested without a pre-prompt explaining why.
- "Denied permanently" state not handled (user sent to
  settings with a clear message).
- Permissions requested at app start rather than at the moment
  of use.

### Security (regression check only)
- Secrets / API keys present in `app.json` extras or hardcoded
  in source (the bundle is readable post-install).
- Auth tokens stored in `AsyncStorage` rather than the secure
  store (`expo-secure-store` / `react-native-keychain`).
- Deep-link handling that trusts URL params (e.g.
  authentication parameters) without verification.

### Logging
- `console.log` in production paths.
- Crash analytics / error reporting (Sentry / Bugsnag / Crashlytics)
  not initialised, or initialised after the point where errors
  could occur.

### Dependency hygiene
- Circular imports.
- `devDependencies` imported in production paths.
- Native-module deps not aligned with the Expo SDK or the bare
  RN version.

---

## §4.5 — Extraction

### Screen / component decomposition

- Any screen file longer than ~300 lines.
- Any render function longer than ~80 lines.
- Any `FlatList renderItem` defined inline with non-trivial JSX
  — extract a memoised component.
- Any component with three or more `useState`s describing one
  coherent state — usually a `useReducer` or custom hook.
- Any screen with three or more `useEffect`s — typically a
  custom hook hiding.

### Logic extraction

- Any function defined inside a component body that is pure
  (no closure over state) — hoist to module scope or a
  `<screen>.helpers.ts` / shared helpers module.
- Any data-shaping logic (mapping API responses to view
  models) repeated across screens — shared helper.
- Any imperative logic inside `useEffect` that has no
  dependency on the React lifecycle — extract to a plain async
  function called from the effect.

### Style extraction

- Any `StyleSheet.create` block copy-pasted across components
  — extract to a shared theme / styles module.
- Any inline `style={{ ... }}` doing more than dynamic colour
  / dimension — extract to `StyleSheet.create`.

### Promotion candidates

- Any custom hook used by two or more screens — promote out of
  the screen folder to `hooks/`.
- Any component used by two or more screens — promote to
  `components/`.
- Any constant defined in two or more files — promote to
  `constants/` or `theme/`.

### Demotion / scope-creep candidates

- Any shared component that has accumulated screen-specific
  props — push it back into the screen that needs them.
- Any helper in `hooks/` that imports from a specific screen
  module — push back into that screen.

---

## §5 — Drift counter (React Native rule set)

| Rule | Violations |
|---|---|
| `console.log/warn/error` in production paths | N |
| Inline `style={{ ... }}` props (non-dynamic) | N |
| `ScrollView` rendering many items (should be FlatList) | N |
| `FlatList` missing `keyExtractor` | N |
| Inline `renderItem` arrow functions | N |
| `TouchableOpacity` / `TouchableHighlight` in new code | N |
| Touchables missing `accessibilityLabel` | N |
| Non-null assertions (`!`) | N |
| `as`-cast type assertions | N |
| `@ts-ignore` without comment | N |
| TODO / FIXME comments | N |
| Screens > 300 lines | N |
| Render functions > 80 lines | N |

Adapt the rows to match what the project actually documents.
