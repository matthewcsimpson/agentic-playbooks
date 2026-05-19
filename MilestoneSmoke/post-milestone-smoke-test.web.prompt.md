---
description: Drive a web app through a browser MCP server after a milestone tag is cut — exercise headline flows, write a pass/fail/blocked report.
---

# Post-milestone smoke test — web variant

Drive a web app through a browser MCP server after a milestone tag
is cut.

**This prompt extends [`core/post-milestone-smoke-test.core.prompt.md`](./core/post-milestone-smoke-test.core.prompt.md).**
Read the core file first for the workflow shape (Step 1 milestone
window, Step 2 bucketing, Step 3 flow planning, Step 4 execution
loop, Step 5 cross-cutting concept, Step 6 report shape, and the
Constraints). This file supplies the web-specific bits.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Scope

This variant is **web-app-only**. It assumes:

- The app is reachable through a browser (HTML / JS / network) —
  not a CLI, daemon, mobile binary, library, or background worker.
- A browser-control MCP tool is available (Playwright MCP
  recommended).
- A running dev server is reachable from the browser.

For CLI tools, libraries, mobile apps, or background workers, see
the sibling smoke variants (`.cli`, `.api`, etc.) or open an
issue for a missing one.

---

## Prerequisites

The session running this prompt must have:

- A browser-control MCP tool available (Playwright MCP, Puppeteer
  MCP, or chrome-devtools MCP — any tool offering: navigate to
  URL, fill input, click element by role / text / selector, read
  element text and attributes, capture screenshot, read console
  output, read network response codes).
- A running dev server reachable from the browser (typically
  `http://localhost:3000` or similar). If the server isn't
  running, surface that as a blocker and stop — do not attempt to
  start it from this prompt.

If the browser tool is unavailable, surface that and stop. The
smoke test is meaningful only when it actually runs.

### One-time setup — Playwright MCP (recommended)

```bash
# 1. Register the server if not already in the user-scope config.
if ! claude mcp list 2>/dev/null | grep -q "^playwright:"; then
  claude mcp add playwright npx @playwright/mcp@latest --scope user
else
  echo "playwright MCP already registered — skipping."
fi

# 2. Install Chromium (idempotent).
npx playwright install chromium

# 3. Verify. Output should list `playwright: ✓ Connected`.
claude mcp list
```

Run these in a regular terminal, not inside an active Claude Code
session. After registering, **start a fresh Claude Code session**
from the repo root before pasting this prompt — MCP servers are
loaded at session start.

Open the new session with an explicit cue so the agent routes
through the MCP tool rather than shell-driven Playwright:

> Use Playwright MCP to navigate to http://localhost:3000 and take
> a screenshot.

Once that confirms the tool is wired up, paste this prompt into
the same session.

---

## Test accounts

The project must document seeded dev accounts in a known location
(e.g. `docs/test-accounts.md`, a section in `CLAUDE.md`, or passed
into this prompt directly). The expected shape is a table of
alias / email / password rows.

When a flow needs two interacting users (friending, sharing,
comparison), use the first two. When a flow needs a brand-new
unseeded account, surface that explicitly — sign-up flows produce
write-side data the run can't easily reset, so create new accounts
only when the flow specifically tests sign-up itself.

If no test accounts are documented, surface that and stop —
guessing credentials will burn the run.

---

## §2 — What "user-facing" means (web)

A web user-facing surface is: a new page, modal, flow, button,
badge, visibility flag, settings tab, or any DOM-rendered control.
Schema migrations, build / CI changes, internal refactors are
"behind-the-scenes" per the core's §2.

---

## §3 — Step shape (web)

Steps must be concrete browser actions executable by the MCP:

- `Navigate to /<path>`
- `Fill #<selector> with "<value>"` or `Fill <role-and-name> with "<value>"`
- `Click button "<text>"` or `Click <role> "<accessible-name>"`
- `Wait for <route or selector>`
- `Confirm element <selector> has text "<expected>"`

Avoid narrative steps ("then the user fills in their name") —
every step is a specific MCP action.

---

## §4 — Execute mechanics (web)

**Reset state**: close any open tabs, clear cookies for the dev
origin if the flow needs an unauthed start. (Two consecutive
flows that both run as the same user don't need a reset between
them; only reset when the next flow's preconditions differ.)

**Walk the steps** using the browser MCP. After each step,
confirm the expected DOM state before the next.

**Observe during execution**:

- **Console** — every error and unexpected warning logged in the
  browser console. A single known-deferred warning is fine; new
  ones are findings.
- **Network** — every 4xx / 5xx, and any request whose duration
  exceeds ~1.5s without an obvious reason (cold cache, real
  upload). Capture the URL and status.

**Capture an artefact**: a screenshot at the moment of decision
(success state for pass, last-good-state for fail / blocked).
Save under `<root>/smoke-tests/screenshots/<tag>-<timestamp>/<flow-number>.png`
and link from the report.

---

## §5 — Cross-cutting checks (web)

After the per-feature flows, do one targeted run for:

- **Layout shell** — visit the top 3–5 most-used signed-in routes.
  For each: no console errors, primary chrome (header / sidebar /
  footer) renders, no obvious style breakage.
- **Anonymous viewer** — sign out. Visit the public routes
  (landing, public profile page, any catalogue / browse view).
  For each: no auth-required redirect on a route that should be
  public, no 500s.

Each is its own pass / fail row.

---

## §6 — Report observation fields (web)

In the per-flow report block, fill in:

- **Observations**:
  - Console: <empty | "1 new error: …" | etc.>
  - Network: <empty | "POST /api/foo returned 500" | etc.>
- **Artefact**: `<root>/smoke-tests/screenshots/<tag>-<timestamp>/<flow-number>.png`
