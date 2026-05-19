---
description: Drive an iOS app through the iOS Simulator after a milestone tag is cut — execute headline user flows, observe device log and screenshots, write a pass/fail/blocked report.
---

# Post-milestone smoke test — iOS variant

Drive an iOS app through the iOS Simulator after a milestone tag
is cut. Execute the milestone's headline user flows, observe the
device log + screenshots, write a pass/fail/blocked report.

**This prompt extends [`core/post-milestone-smoke-test.core.prompt.md`](./core/post-milestone-smoke-test.core.prompt.md).**
Read the core file first for the workflow shape (Step 1 milestone
window, Step 2 bucketing, Step 3 flow planning, Step 4 execution
loop, Step 5 cross-cutting concept, Step 6 report shape, and the
Constraints). This file supplies the iOS-specific bits.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Scope

This variant is **iOS Simulator only**. It assumes:

- A built iOS app installable on the iOS Simulator (`.app`
  bundle from Xcode build output, or installed from an `.ipa`).
- A driving tool: **Maestro** (recommended — declarative YAML
  flows, single binary, no Xcode UI test target required) or
  **XCUITest** (Apple's official solution, requires a UI test
  target in the Xcode project).
- The agent has shell execution to call `xcrun simctl`,
  `xcodebuild`, and the driver.

For macOS / watchOS / tvOS apps, the shape transfers (use
`xcrun simctl` for watchOS / tvOS sims; macOS apps run on the
host directly) but the cross-cutting checks differ — consider
copying this variant and adapting.

For React Native iOS apps, use [`.web`](./post-milestone-smoke-test.web.prompt.md)
if the project ships a web build, or this variant against the
native binary if RN-on-iOS is the surface being tested. For
Android, no variant exists yet.

---

## Prerequisites

The session running this prompt must have:

- **Xcode installed** — verify with `xcodebuild -version`. If
  Xcode isn't installed, surface that and stop.
- **An available simulator** — list with `xcrun simctl list devices available`.
  Pick the simulator the project documents (e.g.
  "iPhone 15 Pro" / "iPad Air (5th gen)"); boot it with
  `xcrun simctl boot "<device name>"`.
- **A built `.app` bundle** — the project should document the
  build command (typically `xcodebuild -scheme <Scheme>
  -destination 'platform=iOS Simulator,name=<device>' build`)
  or provide a path to an existing build. If neither is
  documented, surface that and stop — don't guess.
- **The driving tool installed**:
  - **Maestro** (recommended): `maestro --version`. Install
    via `curl -Ls "https://get.maestro.mobile.dev" | bash` if
    missing — but surface the install requirement first
    rather than installing implicitly.
  - **XCUITest**: requires the UI test target in the Xcode
    project. If the project documents using XCUITest, run via
    `xcodebuild test -scheme <UITestScheme>
    -destination 'platform=iOS Simulator,name=<device>'`.

If any prerequisite is missing, surface it and stop. The smoke
test is meaningful only when it actually runs.

---

## Test fixtures and accounts

The project must document:

- **Seeded test accounts** — for flows that require sign-in,
  alias / email / password rows (same expected shape as the
  web variant).
- **Backend pointing** — staging, mock, or local. Typically
  set via a build configuration (`Debug`, `Smoke`) or a
  launch argument the simulator can pass.
- **Permission state** — whether the simulator should grant
  permissions automatically (Maestro's `permissions` block,
  or `xcrun simctl privacy <device> grant <service> <bundle-id>`)
  or test the request flow itself.
- **Initial app state** — fresh-install vs preserved storage.
  For most smoke flows, prefer fresh install per run:
  `xcrun simctl uninstall booted <bundle-id>` then
  `xcrun simctl install booted /path/to/Build/App.app`.

If test accounts / fixtures aren't documented, surface that and
stop.

---

## §2 — What "user-facing" means (iOS)

An iOS user-facing surface is: a new screen, a new control on
an existing screen, a new transition / animation that affects
flow, a new permission prompt, a new deep link target, a new
widget / shortcut / share-sheet integration, a new App Intent,
a new Lock Screen widget, a new keyboard / payment / notification
extension.

Internal refactors, schema migrations, build / CI changes,
non-visible accessibility improvements (without behaviour
change) are "behind-the-scenes" per the core's §2.

---

## §3 — Step shape (iOS)

Steps must be concrete driver instructions.

### Maestro flows

Express each step as a Maestro YAML line (the agent will
assemble these into a `.yaml` file and run `maestro test`):

```yaml
- tapOn: "Sign in"
- inputText: "tester@example.com"
- tapOn: "Continue"
- inputText: "secret"
- tapOn: "Log in"
- assertVisible: "Welcome back"
```

Maestro selectors prefer accessibility identifiers / labels.
Use the project's accessibility identifiers where available;
fall back to text content if the project doesn't set them.

### XCUITest steps

Express each step as a Swift `XCUITest` action:

```swift
app.buttons["sign-in"].tap()
app.textFields["email"].typeText("tester@example.com")
app.buttons["continue"].tap()
app.secureTextFields["password"].typeText("secret")
app.buttons["log-in"].tap()
XCTAssertTrue(app.staticTexts["Welcome back"].waitForExistence(timeout: 5))
```

Whichever driver the project uses, **every step is an
executable action** — no narrative ("then the user logs in").

---

## §4 — Execute mechanics (iOS)

**Reset state** at the start of each flow that requires it:

```bash
xcrun simctl uninstall booted <bundle-id>
xcrun simctl install booted "<path-to>/App.app"
```

Or, for partial reset (preserve install, clear app data):

```bash
xcrun simctl get_app_container booted <bundle-id> data | xargs rm -rf
```

For flows that share state with the previous flow's setup, skip
the reset.

**Walk the steps** using the chosen driver:

- **Maestro**: write the flow YAML, run `maestro test
  --format=junit flow.yaml`. Capture the structured output.
- **XCUITest**: invoke `xcodebuild test
  -only-testing:UITests/<TestClass>/<testMethod>`. Capture
  stdout, the `.xcresult` bundle path, and any failure
  diagnostics.

**Observe during execution**:

- **Device log** — tail the device log filtered to the app's
  bundle identifier:

  ```bash
  xcrun simctl spawn booted log stream \
    --level=debug \
    --predicate "subsystem == '<bundle-id>'" \
    > flow.log &
  ```

  Watch for `error` / `fault` entries, signposts indicating
  crashes, memory warnings.
- **Crash reports** — check `~/Library/Logs/DiagnosticReports/`
  for new `.crash` / `.ips` files matching the bundle id
  during the run window.
- **Network** — if the project uses a man-in-the-middle proxy
  for smoke runs (mitmproxy, Charles), watch for unexpected
  401 / 4xx / 5xx responses. Otherwise rely on the app's own
  error UI as the observation surface.

**Capture an artefact** at the moment of decision (success
state for pass, last-good-state for fail / blocked):

```bash
xcrun simctl io booted screenshot \
  docs/smoke-tests/screenshots/<tag>-<timestamp>/<flow-number>.png
```

Save both the screenshot and the trimmed device log
(`docs/smoke-tests/<tag>-<timestamp>/<flow-number>.log`).

---

## §5 — Cross-cutting checks (iOS)

After the per-feature flows, do one targeted run for:

- **Cold launch** — uninstall and reinstall the app. Launch
  fresh. Confirm: launches within the project's documented
  cold-launch budget (typically <2s on a recent simulator),
  no crash, splash / initial screen renders.
- **Deep link handling** — if the app declares deep links in
  `Info.plist`, open one with
  `xcrun simctl openurl booted "<scheme>://<host>/<path>"`
  and confirm the app routes correctly.
- **Backgrounding** — press home (`xcrun simctl ui booted home`
  or driver-equivalent), wait 5s, reopen. Confirm the app
  resumes without resetting unexpected state.
- **Permissions prompts** — for at least one permission the
  milestone touches (camera / location / notifications /
  contacts), fresh-install and trigger the prompt. Confirm the
  prompt copy is the documented permission string and
  declining / accepting leaves the app in a usable state.
- **Memory warning** — trigger
  `xcrun simctl ui booted memory-warning` while the app is
  foregrounded. Confirm no crash and the app continues to
  function.
- **Accessibility tree non-empty** — for the app's primary
  screen, dump the accessibility tree (Maestro:
  `maestro hierarchy`; XCUITest:
  `app.debugDescription`). Confirm interactive elements have
  labels.

Each is its own pass / fail row.

---

## §6 — Report observation fields (iOS)

In the per-flow report block, fill in:

- **Observations**:
  - Device log: <"empty" | "1 new error: ..." | etc.>
  - Crash report: <"none" | "matched .ips file at …">
  - Driver result: <"pass" | "fail: assertion at step 3 — selector not found">
- **Artefact**:
  - Screenshot: `docs/smoke-tests/screenshots/<tag>-<timestamp>/<flow-number>.png`
  - Log: `docs/smoke-tests/<tag>-<timestamp>/<flow-number>.log`
