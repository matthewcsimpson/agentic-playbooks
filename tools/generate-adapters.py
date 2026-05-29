#!/usr/bin/env python3
"""Generate per-tool router files from the canonical *.prompt.md library.

A single `/playbook` slash command in each supported tool dispatches by slug
to the canonical prompt file. Multi-variant collections (e.g. dependency-audit
has -dotnet/-npm/-python/-swift/-terraform variants) detect the active stack
from the working directory and pick the matching variant.

Outputs (one router per tool, plus a long-form catalog for natural-language
discovery):

  .claude/commands/playbook.md         — Claude Code slash command
  .claude/skills/<slug>/SKILL.md       — Claude Code skills (user-invocable: false,
                                          hidden from / picker but auto-trigger
                                          by description match)
  .github/prompts/playbook.prompt.md   — GitHub Copilot Chat slash command
  .github/copilot-instructions.md      — Copilot auto-context catalog
  .cursor/commands/playbook.md         — Cursor slash command (Cursor 1.6+)
  AGENTS.md                            — Codex CLI / agent-aware tools catalog

The .prompt.md files remain the only place a prompt's body lives; routers
are pointers.

Modes:
  (no flag)             regenerate project-local adapters
  --check               verify project-local adapters match source (CI)
  --install-global      install routers into ~/.claude (commands + skills)
                        and ~/.codex (prompts/playbook.md + AGENTS.md), with
                        absolute paths — works from any project.
  --uninstall-global    remove globally-installed routers + skills
  --install-project PATH
                        install Cursor + Copilot routers into the target
                        project at PATH, with absolute paths back to this
                        repo. Use this for tools that lack a user-level
                        install path (Cursor, GitHub Copilot Chat).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DESC_MAX = 200
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

# Skill files live at <root>/.claude/skills/<slug>/SKILL.md — three directory
# segments deep, so a relative link back to a prompt at <root>/<col>/<file>
# needs "../../../" to reach <root>.
SKILL_LINK_DEPTH = 3

GLOBAL_MARKER_BEGIN = "<!-- BEGIN agentic-playbooks (managed by tools/generate-adapters.py) -->"
GLOBAL_MARKER_END = "<!-- END agentic-playbooks -->"


def die(message: str) -> None:
    print(f"generate-adapters: {message}", file=sys.stderr)
    sys.exit(1)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")


# Audit prompts write their working reports to `.playbook-audits/`. The
# prompts append this to `.gitignore` on first run, but installing the
# playbooks into a project is the natural moment to do it proactively —
# so the artefacts never land in `git status` even before the first audit.
AUDIT_ARTEFACT_GITIGNORE_ENTRY = ".playbook-audits/"


def ensure_gitignore_entry(target: Path, entry: str = AUDIT_ARTEFACT_GITIGNORE_ENTRY) -> bool:
    """Ensure `entry` is present in `target/.gitignore`.

    Creates `.gitignore` if absent, appends `entry` if missing, and is a
    no-op if an equivalent entry (ignoring a trailing slash) already
    exists. Returns True if the file was created or modified.
    """
    gitignore = target / ".gitignore"
    wanted = entry.rstrip("/")
    if gitignore.exists():
        text = gitignore.read_text(encoding="utf-8")
        if any(line.strip().rstrip("/") == wanted for line in text.splitlines()):
            return False
        sep = "" if text == "" or text.endswith("\n") else "\n"
        gitignore.write_text(f"{text}{sep}{entry}\n", encoding="utf-8")
    else:
        gitignore.write_text(f"{entry}\n", encoding="utf-8")
    return True


# Detection signals for multi-variant collections. Keys are the variant tokens
# that appear after the family name in a prompt filename
# (e.g. `dependency-audit.npm.prompt.md` → variant `npm`).
VARIANT_SIGNALS: dict[str, tuple[str, list[str]]] = {
    "dotnet":       (".NET / C#",
                     ["`*.csproj`, `*.sln`, `global.json`, `Directory.Packages.props`"]),
    "npm":          ("JavaScript / TypeScript (npm / pnpm / yarn)",
                     ["`package.json` *and* no Next.js / NestJS / React-Native indicators"]),
    "python":       ("Python",
                     ["`pyproject.toml`, `requirements.txt`, `Pipfile`, `setup.py`"]),
    "swift":        ("Swift / iOS / macOS",
                     ["`Package.swift`, `*.xcodeproj/`, `*.xcworkspace/`"]),
    "terraform":    ("Terraform / OpenTofu",
                     ["`*.tf`, `*.tofu`"]),
    "nestjs":       ("NestJS backend",
                     ["`nest-cli.json` or `@nestjs/core` in `package.json`"]),
    "nextjs":       ("Next.js",
                     ["`next.config.{js,ts,mjs}` or `next` in `package.json`"]),
    "react-native": ("React Native / Expo",
                     ["`app.json` with Expo/RN config, or `react-native` / `expo` in `package.json`"]),
    "express":      ("Express / Node.js backend",
                     ["`express` in `package.json` and no higher-level framework (Nest) wrapping it"]),
    "cra":          ("Create React App (react-scripts)",
                     ["`react-scripts` in `package.json`, `public/index.html` with `%PUBLIC_URL%`, `REACT_APP_` env vars"]),
    "alembic":      ("Alembic (Python + SQLAlchemy migrations)",
                     ["`alembic.ini`, `alembic/` directory"]),
    "ef-core":      ("Entity Framework Core (.NET)",
                     ["`Microsoft.EntityFrameworkCore*` in a `*.csproj`, `Migrations/` folder under a .NET project"]),
    "prisma":       ("Prisma",
                     ["`prisma/schema.prisma`, `prisma` in `package.json`"]),
    "typeorm":      ("TypeORM",
                     ["`typeorm` in `package.json`, `ormconfig.{js,json,ts}`"]),
    "api":          ("HTTP API smoke test",
                     []),  # usage-context only — ask the user
    "cli":          ("CLI binary smoke test",
                     []),
    "ios":          ("iOS Simulator smoke test",
                     []),
    "web":          ("Web app smoke test (browser MCP)",
                     []),
    "github":       ("GitHub-hosted issue tracker",
                     []),  # usage-context only — ask the user (a repo can have .github/ for Actions but use a different tracker for tickets)
    "clickup":      ("ClickUp List or Folder",
                     []),  # usage-context only — ask the user
    "github-wiki":  ("GitHub repository wiki (planning docs)",
                     []),  # usage-context only — ask the user; expects sibling clone at ../<repo>.wiki/
}


@dataclass
class Prompt:
    slug: str            # e.g. "dependency-audit-npm" or "test-coverage-audit"
    collection: str      # folder name, e.g. "DependencyAudit"
    rel_path: str        # path relative to REPO_ROOT
    description: str
    related: list[str] = field(default_factory=list)
    family: str = ""     # e.g. "dependency-audit"; equals slug for single-variant
    variant: str = ""    # e.g. "npm"; empty string for single-variant


def parse_frontmatter(text: str) -> dict[str, object]:
    """Parse the YAML frontmatter at the head of a prompt file.

    Deliberately a small subset of YAML — not a full parser. Supported:

    - `key: value` single-line scalars (optionally wrapped in single or
      double quotes, which are stripped).
    - `key: [a, b, c]` inline lists of bare tokens.
    - `# comment` lines and blank lines (ignored).

    Unsupported constructs are rejected explicitly rather than silently
    misparsed:

    - Block scalars (`key: |` / `key: >` / continuation lines).
    - Multi-line mapping values (the next non-indented `key:` line ends
      the previous value, which our line-by-line loop wouldn't honour).

    If you need more, switch to `yaml.safe_load`; just don't let this
    parser quietly absorb constructs it doesn't understand.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    body = m.group(1)
    out: dict[str, object] = {}
    for raw in body.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            die(f"frontmatter: line without ':' is not supported: {line!r}")
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value in ("|", ">", "|-", ">-", "|+", ">+"):
            die(f"frontmatter: block scalars are not supported (key {key!r})")
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            out[key] = [item.strip() for item in inner.split(",") if item.strip()] if inner else []
        else:
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            out[key] = value
    return out


def slugify(filename: str) -> str:
    return filename.removesuffix(".prompt.md").replace(".", "-")


def derive_family_variant(filename: str) -> tuple[str, str]:
    """Split `<family>.<variant>.prompt.md` → (family, variant).

    Single-variant prompts (`<name>.prompt.md`) return (name, "").
    """
    name = filename.removesuffix(".prompt.md")
    if "." not in name:
        return (name, "")
    parts = name.split(".")
    if len(parts) != 2:
        die(f"{filename}: unexpected filename shape (expected `<family>.<variant>.prompt.md`)")
    return (parts[0], parts[1])


def discover(repo: Path) -> list[Prompt]:
    prompts: list[Prompt] = []
    for path in sorted(repo.glob("*/*.prompt.md")):
        if path.parent.name == "core":
            continue
        text = path.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if "description" not in fm:
            die(f"{path.relative_to(repo)}: missing 'description' in frontmatter")
        description = str(fm["description"]).strip()
        if len(description) > DESC_MAX:
            die(f"{path.relative_to(repo)}: description is {len(description)} chars (max {DESC_MAX})")
        related = fm.get("related", []) or []
        if not isinstance(related, list):
            die(f"{path.relative_to(repo)}: 'related' must be a list")
        family, variant = derive_family_variant(path.name)
        prompts.append(
            Prompt(
                slug=slugify(path.name),
                collection=path.parent.name,
                rel_path=str(path.relative_to(repo)),
                description=description,
                related=[str(r) for r in related],
                family=family,
                variant=variant,
            )
        )

    seen: dict[str, str] = {}
    collisions: list[tuple[str, str, str]] = []
    for p in prompts:
        if p.slug in seen:
            collisions.append((p.slug, seen[p.slug], p.rel_path))
        else:
            seen[p.slug] = p.rel_path
    if collisions:
        msg = "slug collisions:\n" + "\n".join(
            f"  {slug}: {a} <-> {b}" for slug, a, b in collisions
        )
        die(msg)

    # Validate that every variant token appears in VARIANT_SIGNALS.
    unknown = sorted({p.variant for p in prompts if p.variant and p.variant not in VARIANT_SIGNALS})
    if unknown:
        die(
            "unknown variant token(s) — add them to VARIANT_SIGNALS in generate-adapters.py: "
            + ", ".join(unknown)
        )

    return prompts


def resolve_path(p: Prompt, *, absolute_root: Path | None, depth: int) -> str:
    """Return the path to a prompt file, absolute or relative.

    `absolute_root`: when set, emit absolute paths rooted there (global install).
    `depth`: number of `../` segments to reach REPO_ROOT (project-local install).
    """
    if absolute_root is not None:
        return (absolute_root / p.rel_path).as_posix()
    return "../" * depth + p.rel_path


def group_by_family(prompts: list[Prompt]) -> dict[str, list[Prompt]]:
    """Group prompts by family name; multi-variant families have len > 1.

    For single-variant prompts, family == slug, so the group has one entry.
    """
    grouped: dict[str, list[Prompt]] = {}
    for p in prompts:
        grouped.setdefault(p.family, []).append(p)
    for items in grouped.values():
        items.sort(key=lambda x: x.variant)
    return dict(sorted(grouped.items()))


def render_router_body(prompts: list[Prompt], *, absolute_root: Path | None, depth: int) -> str:
    """Render the shared router body — used by all four tool routers.

    The body is plain markdown instructions to the agent. It works in any tool
    whose slash command file is a markdown prompt that the agent reads.
    """
    families = group_by_family(prompts)
    single: list[Prompt] = []
    multi: list[tuple[str, list[Prompt]]] = []
    for fam, items in families.items():
        if len(items) == 1 and items[0].variant == "":
            single.append(items[0])
        else:
            multi.append((fam, items))

    lines: list[str] = [
        "You are dispatching to a playbook from the agentic-playbooks library.",
        "",
        "The user invoked `/playbook` followed by a slug and an optional",
        "free-form instruction. Parse their message:",
        "",
        "1. The first whitespace-delimited token after `/playbook` is the",
        "   playbook **slug**.",
        "2. Everything after that token is the **user scope** — pass it to the",
        "   playbook as additional context / target.",
        "",
        "## Dispatch rules",
        "",
        "**(a) Help / list flags.** Handle these before any other dispatch:",
        "",
        "- If the first token is `--help` or `-h`, **or** the user invoked",
        "  `/playbook` with no arguments at all, print a short usage message",
        "  followed by a compact list of available playbook slugs grouped",
        "  into *single-variant* and *multi-variant families*. Mention the",
        "  `--list` flag for full descriptions. Do not run any playbook.",
        "- If the first token is `--list` or `-l`, print the **full catalog**",
        "  below (every slug with its one-line description, grouped by",
        "  single-variant and multi-variant families with their detection",
        "  signals). Do not run any playbook.",
        "",
        "Both flags render directly in the chat — no file is read, no work is",
        "performed.",
        "",
        "**(b) Exact slug match.** If the slug is an exact key in the catalog",
        "below (e.g. `test-coverage-audit`, `dependency-audit-npm`), open",
        "that file and follow it verbatim. Use the user scope as the target /",
        "additional context the playbook should apply to.",
        "",
        "**(c) Family match — auto-detect variant.** If the slug matches a",
        "multi-variant family (e.g. `dependency-audit`, `stack-upgrade`),",
        "inspect the working directory for the detection signals listed below.",
        "Pick the variant whose signals match the project's stack and run that",
        "variant's file. If multiple match (a polyglot repo), or none match,",
        "list the candidate variants and ask the user which to run before",
        "proceeding. Never silently pick a variant when the stack is ambiguous.",
        "",
        "**(d) Usage-driven families — ask, never auto-detect.** Some",
        "families' variants are not inferable from the file tree, so",
        "auto-detection does not apply and rule (c) is not used. If the",
        "user invokes one of these family names without a variant, present",
        "a structured choice (`AskUserQuestion` in Claude Code, or an",
        "equivalent numbered prompt in other harnesses) and dispatch to",
        "the chosen variant. Do not offer an \"auto-detect\" option — there",
        "is nothing reliable to detect against. The user can still bypass",
        "the prompt by passing the full slug.",
        "",
        "- **`post-milestone-smoke-test`** — ask which artifact they just",
        "  shipped:",
        "  - **Web app** — browser-driven flows (`post-milestone-smoke-test-web`)",
        "  - **HTTP API** — REST / GraphQL / RPC over HTTP (`post-milestone-smoke-test-api`)",
        "  - **CLI** — non-interactive binary or script (`post-milestone-smoke-test-cli`)",
        "  - **iOS app** — native iOS via the Simulator (`post-milestone-smoke-test-ios`)",
        "",
        "- **`audit-duplicate-issues`** — ask which tracker hosts the",
        "  issues. The local file tree does not reliably indicate this",
        "  (a repo can have `.github/` for Actions but use a different",
        "  tracker for tickets), and silently picking the wrong tracker",
        "  risks running closures against the wrong system:",
        "  - **GitHub** — issues hosted on github.com (`audit-duplicate-issues-github`)",
        "  - **ClickUp** — tasks in a ClickUp List or Folder (`audit-duplicate-issues-clickup`)",
        "",
        "**(e) Unknown slug.** If the slug matches nothing, list the closest",
        "catalog entries (by prefix match on the slug) and ask the user to",
        "clarify. Do not guess. Suggest `/playbook --list` to see all options.",
        "",
        "Always treat the linked `.prompt.md` body as authoritative — do not",
        "summarise, paraphrase, or skip steps unless the playbook itself says to.",
        "",
        "## Catalog — single-variant playbooks (dispatch directly)",
        "",
    ]
    for p in sorted(single, key=lambda x: x.slug):
        target = resolve_path(p, absolute_root=absolute_root, depth=depth)
        lines.append(f"- **`{p.slug}`** — {p.description}")
        lines.append(f"  File: `{target}`")
        if p.related:
            related = ", ".join(f"`{r}`" for r in p.related)
            lines.append(f"  Related: {related}")
    lines.append("")
    lines.append("## Catalog — multi-variant collections (detect stack, then dispatch)")
    lines.append("")
    for fam, items in multi:
        lines.append(f"### `{fam}`")
        lines.append("")
        lines.append("Variants:")
        lines.append("")
        for p in items:
            label, signals = VARIANT_SIGNALS.get(p.variant, (p.variant, []))
            target = resolve_path(p, absolute_root=absolute_root, depth=depth)
            slug_token = f"`{fam}-{p.variant}`" if p.variant else f"`{fam}`"
            lines.append(f"- {slug_token} — {label}")
            lines.append(f"  File: `{target}`")
            if signals:
                lines.append(f"  Detect: {'; '.join(signals)}")
            else:
                lines.append("  Detect: usage context — ask the user which variant applies.")
        if items[0].related:
            related = ", ".join(f"`{r}`" for r in items[0].related)
            lines.append("")
            lines.append(f"Related across the family: {related}")
        lines.append("")
    return "\n".join(lines)


def render_claude_router(prompts: list[Prompt], *, absolute_root: Path | None, depth: int) -> str:
    body = render_router_body(prompts, absolute_root=absolute_root, depth=depth)
    return (
        "---\n"
        "description: Run a playbook from the agentic-playbooks library by slug.\n"
        "argument-hint: <playbook-slug> [user scope or target]\n"
        "---\n\n"
        f"{body}"
    )


def render_codex_router(prompts: list[Prompt], *, absolute_root: Path) -> str:
    body = render_router_body(prompts, absolute_root=absolute_root, depth=0)
    return (
        "Run a playbook from the agentic-playbooks library by slug.\n\n"
        "Usage: `/prompts:playbook <playbook-slug> [user scope or target]`\n\n"
        f"{body}"
    )


def render_copilot_router(prompts: list[Prompt], *, absolute_root: Path | None, depth: int) -> str:
    body = render_router_body(prompts, absolute_root=absolute_root, depth=depth)
    return (
        "---\n"
        "description: Run a playbook from the agentic-playbooks library by slug.\n"
        "---\n\n"
        f"{body}"
    )


def render_cursor_router(prompts: list[Prompt], *, absolute_root: Path | None, depth: int) -> str:
    return render_router_body(prompts, absolute_root=absolute_root, depth=depth)


def emit_skill(out: Path, p: Prompt, *, absolute_root: Path | None = None) -> None:
    """Emit a Claude Code skill. `user-invocable: false` hides it from the
    slash picker but Claude can still auto-trigger it by description match.
    """
    related_line = ""
    if p.related:
        related = ", ".join(f"`/playbook {r}`" for r in p.related)
        related_line = f"\nRelated: {related}.\n"
    target = resolve_path(p, absolute_root=absolute_root, depth=SKILL_LINK_DEPTH)
    if absolute_root is None:
        link = f"[`{p.rel_path}`]({target})"
    else:
        link = f"[`{target}`]({target})"
    body = (
        f"---\n"
        f"name: {p.slug}\n"
        f"description: {p.description}\n"
        f"user-invocable: false\n"
        f"---\n\n"
        f"Follow the instructions in {link}.\n"
        f"{related_line}"
    )
    write(out / "skills" / p.slug / "SKILL.md", body)


def group_by_collection(prompts: list[Prompt]) -> dict[str, list[Prompt]]:
    grouped: dict[str, list[Prompt]] = {}
    for p in prompts:
        grouped.setdefault(p.collection, []).append(p)
    for items in grouped.values():
        items.sort(key=lambda x: x.slug)
    return dict(sorted(grouped.items()))


def render_agents_body(prompts: list[Prompt], *, absolute_root: Path | None) -> str:
    lines: list[str] = [
        "# AGENTS.md",
        "",
        "Index of reusable prompts in the agentic-playbooks library, for",
        "agent-aware tools (Codex CLI, OpenCode, Aider, and others that",
        "auto-read `AGENTS.md`).",
        "",
        "**Invocation pattern** — every supported tool exposes one router slash",
        "command that takes a slug:",
        "",
        "- Codex CLI: `/prompts:playbook <slug> [user scope]`",
        "- Natural language (any agent that reads this file): \"run the",
        "  `<slug>` playbook against <target>\".",
        "",
        "For multi-variant families (e.g. `dependency-audit`), pass just the",
        "family name and the agent will inspect the working directory to pick",
        "the right variant.",
        "",
    ]
    if absolute_root is None:
        lines += [
            "Canonical sources live in the per-collection folders. The router",
            "shims under `.claude/`, `.cursor/`, `.github/`, and this file are",
            "generated from those sources by `tools/generate-adapters.py`.",
        ]
    else:
        lines += [
            f"Canonical sources live at `{absolute_root.as_posix()}`. This file",
            "is generated by `tools/generate-adapters.py --install-global` from",
            "that location.",
        ]
    lines.append("")
    for collection, items in group_by_collection(prompts).items():
        lines.append(f"## {collection}")
        lines.append("")
        for p in items:
            target = (
                (absolute_root / p.rel_path).as_posix()
                if absolute_root is not None
                else p.rel_path
            )
            lines.append(f"- **`{p.slug}`** — {p.description}")
            lines.append(f"  Path: `{target}`")
            if p.related:
                related = ", ".join(f"`{r}`" for r in p.related)
                lines.append(f"  Related: {related}")
        lines.append("")
    return "\n".join(lines)


def emit_agents_md(out_file: Path, prompts: list[Prompt], *, absolute_root: Path | None = None) -> None:
    write(out_file, render_agents_body(prompts, absolute_root=absolute_root))


def emit_copilot_instructions(out_file: Path, prompts: list[Prompt], *, absolute_root: Path | None = None) -> None:
    lines: list[str] = [
        "# Copilot instructions",
        "",
        "This repository is a library of reusable prompts for agentic coding",
        "tools. Each prompt lives as a `*.prompt.md` file in a collection folder.",
        "",
        "**Invocation** — VS Code Copilot Chat reads `.github/prompts/playbook.prompt.md`",
        "as a slash command. Type `/playbook <slug> <scope>` to dispatch by slug.",
        "For multi-variant families, pass just the family name and the agent will",
        "detect the stack from the working directory.",
        "",
        "When the user asks for one of the playbooks listed below in natural",
        "language, read the named `.prompt.md` file and follow its instructions",
        "verbatim — do not summarize or paraphrase.",
        "",
        "Variant prompts begin with a markdown link to a shared",
        "`core/*.prompt.md` scaffold. Read the core first, then the variant,",
        "as the variant body instructs.",
        "",
        "This file is generated from the prompts' YAML frontmatter by",
        "`tools/generate-adapters.py`. Do not edit by hand.",
        "",
        "## Available prompts",
        "",
    ]
    for collection, items in group_by_collection(prompts).items():
        lines.append(f"### {collection}")
        lines.append("")
        for p in items:
            target = (
                (absolute_root / p.rel_path).as_posix()
                if absolute_root is not None
                else p.rel_path
            )
            lines.append(f"- **{p.slug}** — {p.description}")
            lines.append(f"  Read: `{target}`")
            if p.related:
                related = ", ".join(f"`{r}`" for r in p.related)
                lines.append(f"  Related: {related}")
        lines.append("")
    write(out_file, "\n".join(lines))


def clean_project_local(out: Path) -> None:
    """Remove project-local generated trees so a fresh write starts clean."""
    for sub in [
        out / ".claude" / "skills",
        out / ".claude" / "commands",
        out / ".cursor" / "commands",
        out / ".github" / "prompts",
    ]:
        if sub.exists():
            shutil.rmtree(sub)


def generate_project_local(out: Path, prompts: list[Prompt]) -> None:
    clean_project_local(out)
    # Skills (one per prompt, hidden from picker but auto-discoverable)
    for p in prompts:
        emit_skill(out / ".claude", p)

    # Router slash command for each tool
    write(out / ".claude" / "commands" / "playbook.md",
          render_claude_router(prompts, absolute_root=None, depth=2))
    write(out / ".github" / "prompts" / "playbook.prompt.md",
          render_copilot_router(prompts, absolute_root=None, depth=2))
    write(out / ".cursor" / "commands" / "playbook.md",
          render_cursor_router(prompts, absolute_root=None, depth=2))

    # Long-form catalogs for natural-language discovery
    emit_agents_md(out / "AGENTS.md", prompts)
    emit_copilot_instructions(out / ".github" / "copilot-instructions.md", prompts)


def home() -> Path:
    return Path(os.path.expanduser("~"))


def remove_legacy_global_adapters(prompts: list[Prompt]) -> int:
    """Sweep up per-prompt command/skill files from older install layouts.

    Returns the number of stale files removed. Skills are still installed
    (one per slug), so we only remove stale loose command files.
    """
    h = home()
    removed = 0
    for p in prompts:
        legacy_cmd = h / ".claude" / "commands" / f"{p.slug}.md"
        if legacy_cmd.exists():
            legacy_cmd.unlink()
            removed += 1
    return removed


def install_project(prompts: list[Prompt], target: Path) -> None:
    """Install Cursor + Copilot routers into a target project.

    Neither tool has a stable user-level install path, so the router
    file must live inside each project. We write absolute paths back to
    this repo so the agent can find the prompt files regardless of
    where the target project sits relative to the playbooks clone.

    The `.github/copilot-instructions.md` catalog is deliberately not
    written — target projects often have hand-written Copilot
    instructions and we don't want to clobber them.

    Also ensures `.playbook-audits/` is in the project's `.gitignore`,
    so the working reports the audit prompts write there stay out of
    git from install time onward.
    """
    target = target.expanduser().resolve()
    if not target.is_dir():
        die(f"target project not found or not a directory: {target}")
    absolute_root = REPO_ROOT.resolve()
    if target == absolute_root:
        die(
            "target is the playbooks repo itself — use the no-flag mode "
            "(plain `python3 tools/generate-adapters.py`) to regenerate "
            "this repo's checked-in relative-path adapters."
        )

    cursor_file = target / ".cursor" / "commands" / "playbook.md"
    write(cursor_file, render_cursor_router(prompts, absolute_root=absolute_root, depth=0))

    copilot_file = target / ".github" / "prompts" / "playbook.prompt.md"
    write(copilot_file, render_copilot_router(prompts, absolute_root=absolute_root, depth=0))

    gitignore_changed = ensure_gitignore_entry(target)
    gitignore_note = (
        f"  Gitignore:       added {AUDIT_ARTEFACT_GITIGNORE_ENTRY} to {target / '.gitignore'}\n"
        if gitignore_changed
        else f"  Gitignore:       {AUDIT_ARTEFACT_GITIGNORE_ENTRY} already ignored\n"
    )

    print(
        f"generate-adapters: installed project-local routers\n"
        f"  Cursor router:   {cursor_file}\n"
        f"  Copilot router:  {copilot_file}\n"
        f"{gitignore_note}"
        f"\n"
        f"  Source prompts:  {absolute_root}\n"
        f"\n"
        f"Invocation (from {target}):\n"
        f"  Cursor:               /playbook <slug> [scope]\n"
        f"  Copilot Chat:         /playbook <slug> [scope]\n"
        f"\n"
        f"Re-run after `git pull` in {absolute_root.name}, or if you move\n"
        f"the playbooks clone — the routers carry baked-in absolute paths."
    )


def install_global(prompts: list[Prompt]) -> None:
    h = home()
    absolute_root = REPO_ROOT.resolve()

    legacy_cleared = remove_legacy_global_adapters(prompts)

    # Claude Code: single /playbook router + one hidden skill per slug
    claude_dir = h / ".claude"
    for p in prompts:
        emit_skill(claude_dir, p, absolute_root=absolute_root)
    write(claude_dir / "commands" / "playbook.md",
          render_claude_router(prompts, absolute_root=absolute_root, depth=0))

    # Codex CLI: /prompts:playbook router + AGENTS.md catalog
    codex_dir = h / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    write(codex_dir / "prompts" / "playbook.md",
          render_codex_router(prompts, absolute_root=absolute_root))
    codex_agents = codex_dir / "AGENTS.md"
    write_codex_agents(codex_agents, prompts, absolute_root)

    legacy_note = ""
    if legacy_cleared > 0:
        legacy_note = f"  Legacy per-prompt commands removed: {legacy_cleared}\n"

    print(
        f"generate-adapters: installed globally\n"
        f"  Claude Code router:  {claude_dir}/commands/playbook.md\n"
        f"  Claude Code skills:  {len(prompts)} → {claude_dir}/skills/  (user-invocable: false)\n"
        f"  Codex CLI router:    {codex_dir}/prompts/playbook.md\n"
        f"  Codex AGENTS.md:     {codex_agents}\n"
        f"{legacy_note}"
        f"\n"
        f"  Source prompts:      {absolute_root}\n"
        f"\n"
        f"Invocation:\n"
        f"  Claude Code:  /playbook <slug> [scope]\n"
        f"  Codex CLI:    /prompts:playbook <slug> [scope]\n"
        f"\n"
        f"Cursor and Copilot have no stable user-level path — install per-project\n"
        f"by running this generator with no flags inside the target repo, or\n"
        f"copy `.cursor/commands/playbook.md` + `.github/prompts/playbook.prompt.md`\n"
        f"into the target project.\n"
        f"\n"
        f"Re-run with --install-global after `git pull` to refresh."
    )


def write_codex_agents(target: Path, prompts: list[Prompt], absolute_root: Path) -> None:
    section = (
        f"{GLOBAL_MARKER_BEGIN}\n\n"
        f"{render_agents_body(prompts, absolute_root=absolute_root)}\n"
        f"{GLOBAL_MARKER_END}\n"
    )
    if not target.exists():
        target.write_text(section, encoding="utf-8")
        return

    existing = target.read_text(encoding="utf-8")
    if GLOBAL_MARKER_BEGIN in existing and GLOBAL_MARKER_END in existing:
        pattern = re.compile(
            re.escape(GLOBAL_MARKER_BEGIN) + r".*?" + re.escape(GLOBAL_MARKER_END) + r"\n?",
            re.DOTALL,
        )
        new = pattern.sub(section, existing, count=1)
    else:
        sep = "" if existing.endswith("\n") else "\n"
        new = f"{existing}{sep}\n{section}"
    target.write_text(new, encoding="utf-8")


def uninstall_global(prompts: list[Prompt]) -> None:
    h = home()
    removed = {"skills": 0, "commands": 0, "router": 0, "codex_router": 0}

    claude_skills = h / ".claude" / "skills"
    claude_commands = h / ".claude" / "commands"

    for p in prompts:
        skill_dir = claude_skills / p.slug
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            removed["skills"] += 1
        # Legacy per-prompt command files (pre-router install)
        legacy_cmd = claude_commands / f"{p.slug}.md"
        if legacy_cmd.exists():
            legacy_cmd.unlink()
            removed["commands"] += 1

    claude_router = claude_commands / "playbook.md"
    if claude_router.exists():
        claude_router.unlink()
        removed["router"] += 1

    codex_router = h / ".codex" / "prompts" / "playbook.md"
    if codex_router.exists():
        codex_router.unlink()
        removed["codex_router"] += 1

    codex_agents = h / ".codex" / "AGENTS.md"
    codex_status = "not present"
    if codex_agents.exists():
        existing = codex_agents.read_text(encoding="utf-8")
        pattern = re.compile(
            r"\n?" + re.escape(GLOBAL_MARKER_BEGIN) + r".*?" + re.escape(GLOBAL_MARKER_END) + r"\n?",
            re.DOTALL,
        )
        new = pattern.sub("", existing, count=1)
        if new != existing:
            if new.strip():
                codex_agents.write_text(new, encoding="utf-8")
                codex_status = f"section removed (other content preserved at {codex_agents})"
            else:
                codex_agents.unlink()
                codex_status = "removed (file was empty after section removal)"
        else:
            codex_status = "no managed section found"

    print(
        f"generate-adapters: uninstalled globally\n"
        f"  Claude skills removed:     {removed['skills']}\n"
        f"  Claude router removed:     {removed['router']}\n"
        f"  Codex router removed:      {removed['codex_router']}\n"
        f"  Legacy commands removed:   {removed['commands']}\n"
        f"  Codex AGENTS.md:           {codex_status}"
    )


def run_check(prompts: list[Prompt]) -> int:
    with tempfile.TemporaryDirectory(prefix="adapters-check-") as tmp:
        tmp_path = Path(tmp)
        generate_project_local(tmp_path, prompts)
        diffs: list[str] = []
        for rel in [
            ".claude/skills",
            ".claude/commands",
            ".cursor/commands",
            ".github/prompts",
            "AGENTS.md",
            ".github/copilot-instructions.md",
        ]:
            res = subprocess.run(
                ["diff", "-ruN", str(REPO_ROOT / rel), str(tmp_path / rel)],
                capture_output=True,
                text=True,
            )
            diffs.append(res.stdout)
        all_diff = "".join(diffs)
        if all_diff.strip():
            print("generate-adapters: drift detected. Run without --check to regenerate.", file=sys.stderr)
            print(all_diff)
            return 1
        print(f"generate-adapters: OK ({len(prompts)} prompts, no drift)")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--check",
        action="store_true",
        help="Verify project-local adapters match source; non-zero exit on drift.",
    )
    group.add_argument(
        "--install-global",
        action="store_true",
        help="Install routers into ~/.claude and ~/.codex with absolute paths.",
    )
    group.add_argument(
        "--uninstall-global",
        action="store_true",
        help="Remove globally-installed routers and skills.",
    )
    group.add_argument(
        "--install-project",
        metavar="PATH",
        help=(
            "Install Cursor + Copilot routers (with absolute paths back to "
            "this repo) into the target project at PATH. Use for tools "
            "without a user-level install path."
        ),
    )
    args = parser.parse_args()

    prompts = discover(REPO_ROOT)

    if args.check:
        return run_check(prompts)

    if args.install_global:
        install_global(prompts)
        return 0

    if args.uninstall_global:
        uninstall_global(prompts)
        return 0

    if args.install_project:
        install_project(prompts, Path(args.install_project))
        return 0

    generate_project_local(REPO_ROOT, prompts)
    print(
        f"generate-adapters: wrote routers + {len(prompts)} skills "
        f"(.claude/, .cursor/, .github/, AGENTS.md)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
