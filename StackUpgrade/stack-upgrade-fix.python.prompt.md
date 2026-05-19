---
description: Action findings from stack-upgrade-audit-python. Run pyupgrade per target, apply mechanical edits, bump python version pin and deploy-target, verify, commit per category. Local only.
related: [stack-upgrade-audit-python, post-milestone-audit-python]
---

# Stack upgrade fix — Python variant

Action findings from a `stack-upgrade-audit-python` report against a
Python codebase (e.g. 3.10 → 3.12).

**This prompt extends [`core/stack-upgrade-fix.core.prompt.md`](./core/stack-upgrade-fix.core.prompt.md).**
Read the core first.

---

## Assumed stack

- Python language version (3.x → 3.y).
- Package manager: detect from manifest — `pyproject.toml` (uv,
  Poetry, pdm, or PEP 621), `requirements.txt` + `requirements.in`
  (pip-tools), `Pipfile` (pipenv), `setup.py` (legacy).
- Common framework workloads: FastAPI, Django, Flask, library /
  CLI / data-pipeline.
- Test runner: `pytest` (most common), `unittest`, `nose2`.

---

## §2 — Re-verify the audit

```sh
# Current pinned Python version — sources vary by project
cat .python-version 2>/dev/null
jq -r '.["tool.poetry.dependencies"]["python"] // empty' pyproject.toml 2>/dev/null
grep -E '^python' pyproject.toml 2>/dev/null
grep -E 'python_requires' setup.py 2>/dev/null
grep -E 'python-version' .github/workflows/*.yml 2>/dev/null
```

If the project's pinned Python has moved since the audit, stop and
re-run.

---

## §3 — Codemods

The primary codemod is **`pyupgrade`** — modernizes syntax for a
target Python version:

```sh
# Install
pipx install pyupgrade           # or: uv tool install pyupgrade

# Apply (target version flag matches the audit's plan)
pyupgrade --py312-plus <file_or_dir>
```

Common transformations:

- `dict()` → `{}`, `list()` → `[]` for empty constructors.
- `"%s" % x` → f-strings (where unambiguous).
- `Union[X, Y]` → `X | Y` (PEP 604, 3.10+).
- `Optional[X]` → `X | None` (3.10+).
- `typing.List` → `list` (PEP 585, 3.9+).
- `f"{x!r}"` deferral patterns.

Run pyupgrade per-package or across the repo, **verify, commit per
target-version flag**:

```sh
# Apply
pyupgrade --py312-plus $(find src/ -name '*.py')

# Verify
ruff check .                     # or: flake8 / pylint per project's lint config
mypy .                           # if mypy is configured
pytest                           # full unit suite

# Commit
git commit -m "upgrade(python): pyupgrade --py312-plus across src/"
```

Other targeted codemods the audit may recommend:

- **`autoflake`** — remove unused imports / variables surfaced by
  the cleanup.
- **`isort`** / **`ruff --fix`** — re-sort imports after pyupgrade.
- **`2to3`** — only for projects still on 2.x (rare; the audit
  should have flagged this as a separate, larger migration).
- **`pyrefly`** / **`com2ann`** — type-annotation transforms; opt-in.

For Django specifically: **`django-upgrade`**:

```sh
pipx install django-upgrade
django-upgrade --target-version <X.Y> $(find . -name '*.py' -not -path '*/migrations/*')
```

Verify and commit per codemod.

---

## §4 — Mechanical edits

Apply the audit's documented from→to pairs. Common categories:

**stdlib removals / deprecations:**

```python
# Example (use the audit's actual list):
# imp module removed in 3.12  →  use importlib
# distutils removed in 3.12  →  use setuptools / packaging
# asyncio.coroutine decorator removed  →  use async def
# collections.Callable etc. moved to collections.abc (3.10+)
```

**Library API drift surfaced by the version bump:**

```python
# pydantic 1 → 2 patterns if the audit flagged them
# SQLAlchemy 1.x → 2.0 style if the audit flagged them
```

Each category goes commit-per-category:

```sh
git commit -m "upgrade(python): replace imp module with importlib"
```

Ambiguous from→to specs → TODO.

---

## §5 — Version bump

Bump every pin the audit flagged:

**`.python-version`** (pyenv / asdf):

```sh
echo '3.12' > .python-version
```

**`pyproject.toml`** (Poetry):

```toml
[tool.poetry.dependencies]
python = "^3.12"
```

**`pyproject.toml`** (PEP 621):

```toml
[project]
requires-python = ">=3.12"
```

**`setup.py`** (legacy):

```python
python_requires=">=3.12"
```

**`tox.ini`** / **`.github/workflows/*.yml`** — bump matrix entries
if flagged.

Re-resolve the lockfile (one-shot — the variant doesn't run partial
updates):

```sh
# uv
uv lock --upgrade

# Poetry — detect major from `poetry --version` first; semantics differ.
# Poetry 2.x (2025+): `poetry lock` is no-update by default.
poetry lock                      # 2.x: no-update default; 1.x: re-resolves
# Poetry 1.x: pin behaviour explicitly
poetry lock --no-update          # 1.x: keep versions stable (deprecated in 2.x)
poetry update                    # both majors: full re-resolution

# pdm
pdm lock

# pip-tools
pip-compile requirements.in --upgrade-package <pkg>     # if specific pins
pip-compile requirements.in                              # general re-resolve
```

If a target library doesn't yet support the target Python (often
the case in the first weeks after a 3.x release), stop and surface.
Do **not** pin around it with a yanked version.

Commit:

```sh
git commit -m "upgrade(python): bump python 3.10 → 3.12, regenerate lockfile"
```

---

## §6 — Post-bump edits

Edits that only make sense after the bump:

- New stdlib modules / syntax features available in the target
  version (PEP 695 type parameters in 3.12, etc.). Usually opt-in
  adoption, not strict-upgrade fixes — surface as TODO unless the
  audit specified them.

---

## §7 — Verification

```sh
# Lint
ruff check .
# or: flake8 / pylint per project config

# Type check
mypy .
# or: pyright

# Test
pytest -x                        # stop on first failure for faster signal during the fix loop
pytest                           # full pass before declaring done

# Build (libraries / packages)
python -m build                  # if the project publishes
```

For monorepos / multi-package projects:

```sh
uv run --package <pkg> pytest
poetry run pytest                # per-pyproject in workspace projects
nx run <package>:test            # if Nx wraps Python (uncommon)
```

---

## §8 — Hand off

```
/playbook post-milestone-audit-python
```

Common residual drift after a Python bump:

- Deploy-target Python version (Lambda runtime, Docker base image,
  Heroku runtime.txt) still on the old version — the audit should
  have flagged this in the Verdict; the fix surfaces it without
  editing the deploy config.
- `tox.ini` envlist still listing the dropped version as a matrix
  entry.
- Documentation referencing `python3.X` in install commands or
  CI examples.

---

## Constraints (Python-specific addenda)

- pyupgrade is opinionated about f-string conversions. Review the
  diff from each pyupgrade run before committing — it occasionally
  converts logging calls or other formatted strings in ways that
  change runtime behaviour (logging args lazy evaluation).
- If the project depends on a library that doesn't support the
  target Python yet, do not pin the library at a yanked version
  to force the upgrade. Stop and surface — the upgrade is blocked
  on upstream.
- Django and FastAPI have their own version compatibility matrices
  with Python. The audit should have validated the chosen Python
  works with the project's framework version; the fix doesn't
  re-verify.
- Cython / native extensions (numpy, lxml, cryptography) need
  binary wheels for the target Python. The audit flags this; the
  fix relies on the variant's `uv lock` / `poetry lock` resolving
  successfully as proof of wheel availability.
- Do not edit `Dockerfile` `python:X.Y` base image lines as part
  of the fix unless the audit explicitly flagged a deploy-config
  change. Pipeline drift is a separate PR.
- For Django projects, do not run `python manage.py migrate` as
  part of the fix. Migration runs are deploy-time, not upgrade-fix-
  time.
