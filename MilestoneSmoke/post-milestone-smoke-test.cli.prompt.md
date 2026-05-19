---
description: Drive a CLI binary after a milestone tag is cut — invoke headline commands, observe exit code / stdout / stderr / side effects, write a pass/fail/blocked report.
---

# Post-milestone smoke test — CLI variant

Drive a CLI binary after a milestone tag is cut. Invoke the
milestone's headline commands with concrete arguments, observe
exit code / stdout / stderr / side effects, write a
pass/fail/blocked report.

**This prompt extends [`core/post-milestone-smoke-test.core.prompt.md`](./core/post-milestone-smoke-test.core.prompt.md).**
Read the core file first for the workflow shape (Step 1 milestone
window, Step 2 bucketing, Step 3 flow planning, Step 4 execution
loop, Step 5 cross-cutting concept, Step 6 report shape, and the
Constraints). This file supplies the CLI-specific bits.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Scope

This variant is **non-interactive CLI only**. It assumes:

- The project ships a binary (or script) you invoke with
  arguments and which exits when done.
- The CLI is non-interactive: no TUI, no REPL, no scripted
  keystroke input. (For TUIs / REPLs / daemons, no variant
  exists yet.)
- The CLI is buildable / installable from the repo.

For browser flows see `.web`. For HTTP APIs see `.api`.

---

## Prerequisites

The session running this prompt must have:

- A built or installed version of the CLI, reachable on PATH
  or via a known relative path (e.g. `./bin/mycli`, `target/release/mycli`,
  `dist/mycli.js`). If the binary isn't available, surface
  that as a blocker and stop — do not attempt to build it as
  part of this prompt unless the project documents the
  expected build step.
- Test fixtures the CLI needs to operate on — typically a
  `test-fixtures/` or `examples/` directory in the repo. The
  smoke run copies fixtures to a sandbox before invocation so
  the originals aren't modified.
- Any environment / config files the CLI reads (`~/.<cli>rc`,
  project-local config files). The project should document
  what test values to use.

If the binary isn't available, surface that and stop.

---

## Test fixtures

The project must document sample data the CLI can operate on.
The expected shape is one of:

- A directory of sample input files (e.g. a sample project to
  build, sample config to parse, sample JSON to transform).
- A documented set of arguments / inputs that produce
  deterministic output for known commands.

Best practice for the smoke run:

1. Copy the fixture into a sandbox (`/tmp/smoke-<tag>/`) at the
   start of the run.
2. `cd` into the sandbox before invoking the CLI.
3. Tear down the sandbox at the end (or leave it for
   inspection if the flow failed).

If no fixtures are documented, surface that and stop. Inventing
test inputs produces unreliable runs.

---

## §2 — What "user-facing" means (CLI)

A CLI user-facing surface is: a new command or subcommand, a
new flag / argument, a new output format, a new exit code, a
new prompt or interactive sub-step (within a "non-interactive
flow" — e.g. `--yes` is the documented bypass), a new
side-effect (file created, registry updated).

Schema migrations of internal data files, internal refactors,
test additions, dependency upgrades are "behind-the-scenes"
per the core's §2.

---

## §3 — Step shape (CLI)

Steps must be concrete shell invocations. Each step lists:

- **Working directory** (relative to the sandbox or absolute).
- **Environment overrides** (`FOO=bar` prefix, if any).
- **The command and its arguments**, exactly as run.
- **Expected exit code** (typically `0` for success steps).
- **Expected stdout pattern** (a substring, a regex, or "any
  output non-empty" / "empty").
- **Expected stderr pattern** (typically empty or
  warnings-only).
- **Side-effects** to verify after the command exits (files
  created, directories modified, registries updated).

Avoid narrative ("then build the project"). Every step is a
specific shell invocation:

```
cwd: /tmp/smoke-v0.5.0/sample-project
$ ./bin/mycli build --out dist
→ exit 0
→ stdout contains "Build complete"
→ stderr empty
→ ./dist/bundle.js exists and is non-empty
```

---

## §4 — Execute mechanics (CLI)

**Reset state**: at the start of each flow, copy a fresh
fixture into a sandbox directory and `cd` there. Don't operate
on the repo's `test-fixtures/` directly — that's the
fingerprint of a flow that pollutes future runs.

**Walk the steps** by invoking the command and capturing:

1. The exit code (`$?`).
2. The full stdout (capture to a file or buffer).
3. The full stderr (capture to a separate buffer).
4. The duration (note if it exceeds an obvious threshold —
   build-style commands have project-specific expectations).
5. Any files created / modified / deleted in the working
   directory.

After each step:

- Confirm the exit code matches expected.
- Confirm stdout contains the expected substring / matches
  the expected pattern.
- Confirm stderr is empty (or contains only documented-allowed
  warnings).
- Confirm the side-effects exist (files created, etc.).

If a step fails, record what was expected vs what happened,
including the captured stdout / stderr, and stop the flow.

**Observe during execution**:

- **Exit code** — unexpected non-zero is a finding.
- **Stderr** — any output to stderr in a "success" flow is a
  finding unless documented as a warning.
- **Stdout shape** — for commands with structured output
  (JSON, CSV), confirm the structure is parseable and matches
  the schema the project documents.
- **Side-effects beyond the documented scope** — flag any
  files created / modified that the step didn't document.

**Capture an artefact**: a `.log` file containing the command,
working directory, exit code, full stdout, full stderr, and a
listing of files changed. Save under
`<root>/smoke-tests/<tag>-<timestamp>/<flow-number>.log` and link from the
report.

---

## §5 — Cross-cutting checks (CLI)

After the per-feature flows, do one targeted run for:

- **`--help` everywhere** — invoke `<binary> --help` and
  `<binary> <subcommand> --help` for every documented
  subcommand. Each should exit 0 and produce non-empty help
  text. A missing or broken help is a finding.
- **`--version`** — `<binary> --version` exits 0 and prints
  the milestone tag (or a recognisable version string the
  project documents).
- **Bogus flag error** — `<binary> --not-a-real-flag` exits
  non-zero and prints a clear, helpful error to stderr (not a
  stack trace).
- **Bogus subcommand error** — `<binary> not-a-real-command`
  exits non-zero with a clear error.
- **Empty / missing argument** — for commands that take a
  required argument, invoking without it exits non-zero with
  a usage hint, not a stack trace.
- **Run from various directories** — if the CLI has
  behaviour that depends on `$PWD` (e.g. find a config file
  by walking up), test it from a directory inside the
  configured root and from a directory outside.
- **Pipe in / pipe out** — if the CLI accepts stdin or
  produces stdout suitable for piping, confirm
  `cat input | <binary> > output` works end-to-end.

Each is its own pass / fail row.

---

## §6 — Report observation fields (CLI)

In the per-flow report block, fill in:

- **Observations**:
  - Exit codes: <list per step, e.g. "0, 0, 0">
  - Stderr: <"empty" | "1 new warning: ..." | etc.>
  - Side-effects: <"as expected" | "unexpected file created at X">
- **Artefact**: `<root>/smoke-tests/<tag>-<timestamp>/<flow-number>.log`
