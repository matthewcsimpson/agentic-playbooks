---
description: Plan a Python language version upgrade (e.g. 3.10 → 3.12) — read release notes, scan for affected patterns, survey codemods, produce a risk-ranked migration plan.
related: [stack-upgrade-fix-python]
---

# Stack upgrade — Python variant

Plan a Python language version upgrade (e.g. 3.10 → 3.12).

**This prompt extends [`core/stack-upgrade-audit.core.prompt.md`](./core/stack-upgrade-audit.core.prompt.md).**
Read the core first for the workflow shape (Steps 0–7, the report
format, and the Constraints). This file supplies the Python-
specific detection commands, release-note sources, breaking-change
categories, codemod tools, and gotchas.

If pasting into a chat without filesystem access, paste the core
first, then this variant.

---

## Assumed stack

- Python 3.x (this variant covers 3.x → 3.y; 2 → 3 is a separate
  conversation).
- Package / project manager: pip, uv, Poetry, pdm, or pipenv.
- Optional layer: pyenv / asdf / Docker Python image / serverless
  runtime (Lambda, Cloud Functions).

Python upgrades are usually safer than framework upgrades — the
language is conservative about breaking changes. The risk lives
in dropped modules (`distutils` in 3.12), behavioural shifts
(asyncio rules tightening), and especially in *dependencies*
that lag the language release.

---

## §2 — Detect current version

```sh
# Project-declared version
grep -E '^requires-python|^python\s*=' pyproject.toml 2>/dev/null
cat .python-version 2>/dev/null
grep -E 'python_version' setup.cfg 2>/dev/null

# Runtime in use
python -V
which python

# Docker / runtime image
grep -rE '^FROM python:' Dockerfile* 2>/dev/null

# Serverless runtime declarations
grep -rE 'Runtime:\s*python|python[0-9]+\.[0-9]+' serverless.yml template.yaml 2>/dev/null
grep -rE 'runtime\s*=\s*"python' --include='*.tf' .

# CI version
grep -rE 'python-version' .github/workflows/*.yml 2>/dev/null
```

If `requires-python`, `.python-version`, Dockerfile, and CI disagree,
the upgrade isn't coherent until they line up. Surface the mismatch
first.

---

## §3 — Release notes sources

For each minor in the upgrade path (Python upgrades are typically
minor-by-minor: 3.10 → 3.11 → 3.12):

- "What's New": `https://docs.python.org/3/whatsnew/<x.y>.html`.
- Deprecation schedule:
  `https://docs.python.org/3/library/index.html` (each module's
  `Deprecated since version` markers).
- PEPs landing in that release — listed in the What's New.

Also check the runtime support window for the project's deploy
target before committing to a target:

- AWS Lambda Python runtimes:
  `https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html`.
- GCP Cloud Functions runtimes.
- Heroku stacks.

If the project's deploy target doesn't support the target version,
the plan is moot. Surface in the Verdict.

---

## §3.5 — Common breaking-change categories (Python)

- **Removed APIs / modules** — `distutils` removed in 3.12;
  `imp` removed in 3.12; `asynchat` / `asyncore` removed in 3.12.
  Future releases will continue trimming stdlib.
- **Behaviour changes** — asyncio strictness (e.g. `asyncio.run`
  defaults, deprecation of get_event_loop in some contexts),
  hashing algorithm changes, decimal context defaults.
- **Default changes** — `enum.StrEnum` formatting (3.11),
  `__class_getitem__` behaviour for builtin generics, `int` →
  `str` conversion limits (3.11 security fix).
- **Performance characteristics** — 3.11 made a step-change in
  perf; code that *depended on* specific perf shapes (custom
  caches, etc.) may behave differently.
- **Syntax** — `match` (3.10), `except*` (3.11), `type` statement
  (3.12). Mostly additive — you don't *have* to adopt them.
- **Dependency upgrades** — the long pole. Many libraries lag the
  Python language by 6–12 months. Check every direct dep in
  `pyproject.toml` for compatibility with the target.
- **C extensions** — wheels for the target Python may not exist
  yet for some packages, causing install failures or fall-back
  to slow source builds.

---

## §4 — Scan patterns (Python)

```sh
# Direct stdlib usage of modules being removed in this path
grep -rnE '^(from|import)\s+(distutils|imp|asynchat|asyncore|cgi|cgitb|crypt|imghdr|sndhdr|spwd|sunau|telnetlib)\b' --include='*.py' .

# DeprecationWarning-bearing patterns
grep -rnE 'asyncio\.get_event_loop\(\)|asyncio\.coroutine|@asyncio\.coroutine' --include='*.py' .
grep -rnE 'datetime\.utcnow\(\)|datetime\.utcfromtimestamp\(\)' --include='*.py' .
grep -rnE 'collections\.(OrderedDict|MutableMapping|Mapping|Iterable|Iterator|Sequence)' --include='*.py' .

# C extensions / native deps in the manifest
grep -rE 'numpy|pandas|scipy|psycopg2|cryptography|lxml|pillow|grpcio|tensorflow|torch' pyproject.toml requirements*.txt 2>/dev/null

# Python features that change with version
grep -rnE '\bmatch\s+\w+:|except\*\s' --include='*.py' .   # newer-syntax already in use?

# Test harness / runtime locks
grep -rE 'python_requires|python_version' setup.py setup.cfg pyproject.toml 2>/dev/null
```

For C-extension deps, the upgrade plan should include
"verify wheels exist for the target on the target platform":

```sh
# Example: check what's on PyPI for a specific dep + Python tag
pip index versions <package> 2>/dev/null
```

---

## §5 — Codemod survey (Python)

```sh
# pyupgrade — applies many automatic modernisations
pipx run pyupgrade --py312-plus path/to/file.py    # per-file
find . -name '*.py' -exec pipx run pyupgrade --py312-plus --diff {} +   # dry-run via --diff

# ruff with the UP rule set — codemod-style autofixes for Python upgrades
ruff check --select UP .                              # report
ruff check --select UP --fix --diff .                 # dry-run

# 2to3-style structural changes — rope, libcst, or hand-written codemods
# for project-specific patterns
```

`pyupgrade` and ruff's `UP` rules cover most mechanical changes
(removed `__future__` imports, f-string conversion, dict / set
comprehensions, `super()` simplification, etc.). They don't
cover:

- Behaviour changes (asyncio strictness, decimal defaults).
- Removed-stdlib replacements (e.g. choosing a `distutils`
  replacement — `setuptools`, `packaging`, or `pip`'s
  `find_packages` depending on use).
- C-extension wheel availability.

Flag these as ⚠️ manual-review.

---

## §6 — Risk patterns specific to Python

- **C-extension wheel availability** — the most common upgrade
  blocker. A core dep without a wheel for the target Python falls
  back to source build, which may need a compiler / system libs
  not present on the runtime. CI install passes; production
  Docker build fails.
- **asyncio strictness** — Python has progressively tightened
  asyncio semantics. Code using `asyncio.get_event_loop()` without
  a running loop, or relying on implicit loop creation, may break
  in subtle ways.
- **datetime utc deprecations** — `datetime.utcnow()` /
  `datetime.utcfromtimestamp()` are deprecated; the replacements
  produce timezone-aware datetimes. Code that compares aware vs
  naive datetimes breaks at runtime.
- **`distutils` removal (3.12)** — used directly or transitively
  by older build tooling. `setuptools` re-vendors it but only up
  to a point.
- **`int` → `str` conversion limit** (3.11+) — security fix that
  raises ValueError for very large integers. Surfaces in code
  that handles user-supplied big integers (cryptography,
  arbitrary-precision input).
- **Deploy-runtime lag** — AWS Lambda, Cloud Functions, and
  certain managed Python platforms lag the language. Pick the
  target only after confirming the runtime exists.

---

## Constraints (Python-specific addenda)

- Wheel availability is the long pole. Surface it explicitly in
  the Verdict if any C-extension dep doesn't have a wheel for the
  target on the target platform — the rest of the plan is moot.
- Don't recommend "use the new `match` statement" or other
  additive syntax as part of the upgrade. The upgrade is about
  compatibility, not adoption of new features. Mention new syntax
  separately if at all.
- Python deprecations have long lead times (often 3+ releases).
  Code that currently raises `DeprecationWarning` is unlikely to
  break in the immediate next release, but the warning will
  become an error eventually. Flag accordingly.
- For Poetry / uv / pdm projects, `requires-python` in
  `pyproject.toml` plus the lockfile combine to constrain the
  upgrade — both need updating.
- For Docker-deployed projects, the Python base image change is
  itself a finding — `python:3.12-slim` differs from `python:3.10-slim`
  in installed system libs.
