#!/usr/bin/env python3
"""Unit tests for the load-bearing helpers in generate-adapters.py.

Run: `python3 tools/test_generate_adapters.py` (from repo root) or
`python3 -m unittest tools.test_generate_adapters`. CI also runs these
before the drift check.

Covers the small, easy-to-break pieces — the frontmatter parser, slug
derivation, family/variant split, grouping, and the sentinel-merge logic
in `write_codex_agents`. The end-to-end generator path is exercised by
`--check` in CI.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "generate_adapters", HERE / "generate-adapters.py"
)
assert SPEC is not None and SPEC.loader is not None
gen = importlib.util.module_from_spec(SPEC)
# Register in sys.modules before exec — Python 3.14's @dataclass resolves
# `cls.__module__` against sys.modules during class creation and will fail
# otherwise. Required because the module name has a hyphen and can't be
# imported the normal way.
sys.modules["generate_adapters"] = gen
SPEC.loader.exec_module(gen)


class ParseFrontmatterTests(unittest.TestCase):
    def test_no_frontmatter_returns_empty(self) -> None:
        self.assertEqual(gen.parse_frontmatter("# heading\n\nbody\n"), {})

    def test_basic_scalar(self) -> None:
        text = "---\ndescription: hello world\n---\n\nbody"
        self.assertEqual(gen.parse_frontmatter(text), {"description": "hello world"})

    def test_inline_list(self) -> None:
        text = "---\nrelated: [a, b, c]\n---\n"
        self.assertEqual(gen.parse_frontmatter(text), {"related": ["a", "b", "c"]})

    def test_empty_inline_list(self) -> None:
        text = "---\nrelated: []\n---\n"
        self.assertEqual(gen.parse_frontmatter(text), {"related": []})

    def test_quoted_strings_are_unwrapped(self) -> None:
        text = "---\ndescription: \"quoted value\"\nname: 'single'\n---\n"
        self.assertEqual(
            gen.parse_frontmatter(text),
            {"description": "quoted value", "name": "single"},
        )

    def test_comments_and_blank_lines_ignored(self) -> None:
        text = "---\n# this is a comment\n\ndescription: ok\n---\n"
        self.assertEqual(gen.parse_frontmatter(text), {"description": "ok"})

    def test_block_scalar_rejected(self) -> None:
        text = "---\ndescription: |\n  multi-line\n---\n"
        with self.assertRaises(SystemExit):
            gen.parse_frontmatter(text)

    def test_line_without_colon_rejected(self) -> None:
        text = "---\ndescription ok\n---\n"
        with self.assertRaises(SystemExit):
            gen.parse_frontmatter(text)

    def test_real_prompt_frontmatter_parses(self) -> None:
        """Smoke-test parse_frontmatter against a real on-disk prompt
        file from one of the new families. Catches future frontmatter
        drift (e.g. accidentally introducing a block scalar or an
        unsupported construct) without needing a full --check run.
        """
        target = gen.REPO_ROOT / "DependencyAudit" / "dependency-fix.npm.prompt.md"
        self.assertTrue(target.exists(), f"missing prompt fixture: {target}")
        fm = gen.parse_frontmatter(target.read_text(encoding="utf-8"))
        self.assertIn("description", fm)
        self.assertIsInstance(fm["description"], str)
        # description is bounded by the same limit the generator enforces
        self.assertLessEqual(len(fm["description"]), gen.DESC_MAX)
        self.assertEqual(fm.get("related"), ["dependency-audit-npm"])


class SlugAndVariantTests(unittest.TestCase):
    def test_slugify_single_variant(self) -> None:
        self.assertEqual(gen.slugify("test-coverage-audit.prompt.md"), "test-coverage-audit")

    def test_slugify_dotted_variant(self) -> None:
        self.assertEqual(
            gen.slugify("dependency-hygiene.npm.prompt.md"),
            "dependency-hygiene-npm",
        )

    def test_derive_family_variant_single(self) -> None:
        self.assertEqual(
            gen.derive_family_variant("test-coverage-audit.prompt.md"),
            ("test-coverage-audit", ""),
        )

    def test_derive_family_variant_multi(self) -> None:
        self.assertEqual(
            gen.derive_family_variant("dependency-hygiene.npm.prompt.md"),
            ("dependency-hygiene", "npm"),
        )

    def test_derive_family_variant_too_many_dots(self) -> None:
        with self.assertRaises(SystemExit):
            gen.derive_family_variant("foo.bar.baz.prompt.md")


class GroupingTests(unittest.TestCase):
    def _p(self, slug: str, collection: str, family: str = "", variant: str = "") -> gen.Prompt:
        return gen.Prompt(
            slug=slug,
            collection=collection,
            rel_path=f"{collection}/{slug}.prompt.md",
            description="x",
            family=family or slug,
            variant=variant,
        )

    def test_group_by_family_sorts_variants(self) -> None:
        prompts = [
            self._p("dependency-audit-python", "DependencyAudit", family="dependency-audit", variant="python"),
            self._p("dependency-audit-npm", "DependencyAudit", family="dependency-audit", variant="npm"),
        ]
        grouped = gen.group_by_family(prompts)
        self.assertEqual(
            [p.variant for p in grouped["dependency-audit"]],
            ["npm", "python"],
        )

    def test_audit_fix_pair_are_separate_families_same_collection(self) -> None:
        """An audit family and its matching fix family share a collection
        folder but render as two separate families in the router catalog.

        Verifies the audit/fix naming convention is parsed correctly:
        `dependency-audit.npm.prompt.md` and `dependency-fix.npm.prompt.md`
        live in DependencyAudit/ together but group_by_family must keep
        them in separate buckets.
        """
        prompts = [
            self._p("dependency-audit-npm", "DependencyAudit", family="dependency-audit", variant="npm"),
            self._p("dependency-audit-python", "DependencyAudit", family="dependency-audit", variant="python"),
            self._p("dependency-fix-npm", "DependencyAudit", family="dependency-fix", variant="npm"),
            self._p("dependency-fix-python", "DependencyAudit", family="dependency-fix", variant="python"),
        ]
        grouped = gen.group_by_family(prompts)
        self.assertEqual(set(grouped.keys()), {"dependency-audit", "dependency-fix"})
        self.assertEqual(
            [p.variant for p in grouped["dependency-audit"]], ["npm", "python"]
        )
        self.assertEqual(
            [p.variant for p in grouped["dependency-fix"]], ["npm", "python"]
        )

        by_collection = gen.group_by_collection(prompts)
        self.assertEqual(set(by_collection.keys()), {"DependencyAudit"})
        self.assertEqual(len(by_collection["DependencyAudit"]), 4)

    def test_group_by_collection_sorts_slugs(self) -> None:
        prompts = [
            self._p("zeta", "Foo"),
            self._p("alpha", "Foo"),
        ]
        grouped = gen.group_by_collection(prompts)
        self.assertEqual([p.slug for p in grouped["Foo"]], ["alpha", "zeta"])


class CodexAgentsMergeTests(unittest.TestCase):
    def _prompts(self) -> list[gen.Prompt]:
        return [
            gen.Prompt(
                slug="test-coverage-audit",
                collection="AuditTesting",
                rel_path="AuditTesting/test-coverage-audit.prompt.md",
                description="Audit test coverage.",
                family="test-coverage-audit",
            ),
        ]

    def test_creates_file_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "AGENTS.md"
            gen.write_codex_agents(target, self._prompts(), Path(tmp))
            content = target.read_text()
            self.assertIn(gen.GLOBAL_MARKER_BEGIN, content)
            self.assertIn(gen.GLOBAL_MARKER_END, content)
            self.assertIn("test-coverage-audit", content)

    def test_replaces_existing_managed_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "AGENTS.md"
            target.write_text(
                "user preamble\n\n"
                f"{gen.GLOBAL_MARKER_BEGIN}\nstale\n{gen.GLOBAL_MARKER_END}\n"
                "user epilogue\n"
            )
            gen.write_codex_agents(target, self._prompts(), Path(tmp))
            content = target.read_text()
            self.assertIn("user preamble", content)
            self.assertIn("user epilogue", content)
            self.assertNotIn("stale", content)
            self.assertEqual(content.count(gen.GLOBAL_MARKER_BEGIN), 1)
            self.assertIn("test-coverage-audit", content)

    def test_appends_when_markers_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "AGENTS.md"
            target.write_text("hand-written notes\n")
            gen.write_codex_agents(target, self._prompts(), Path(tmp))
            content = target.read_text()
            self.assertTrue(content.startswith("hand-written notes"))
            self.assertIn(gen.GLOBAL_MARKER_BEGIN, content)


class InstallProjectTests(unittest.TestCase):
    def _prompts(self) -> list[gen.Prompt]:
        return [
            gen.Prompt(
                slug="test-coverage-audit",
                collection="AuditTesting",
                rel_path="AuditTesting/test-coverage-audit.prompt.md",
                description="Audit test coverage.",
                family="test-coverage-audit",
            ),
        ]

    def test_writes_cursor_and_copilot_routers_with_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                gen.install_project(self._prompts(), target)
            cursor = target / ".cursor" / "commands" / "playbook.md"
            copilot = target / ".github" / "prompts" / "playbook.prompt.md"
            self.assertTrue(cursor.exists())
            self.assertTrue(copilot.exists())
            expected_path_fragment = str(
                gen.REPO_ROOT.resolve() / "AuditTesting" / "test-coverage-audit.prompt.md"
            )
            for f in (cursor, copilot):
                content = f.read_text()
                self.assertIn(expected_path_fragment, content)
                self.assertNotIn("../", content)

    def test_skips_copilot_instructions_to_avoid_clobber(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                gen.install_project(self._prompts(), target)
            self.assertFalse((target / ".github" / "copilot-instructions.md").exists())

    def test_adds_playbook_audits_to_gitignore_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                gen.install_project(self._prompts(), target)
            gitignore = target / ".gitignore"
            self.assertTrue(gitignore.exists())
            self.assertIn(".playbook-audits/", gitignore.read_text().splitlines())

    def test_appends_playbook_audits_preserving_existing_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / ".gitignore").write_text("node_modules/\n*.log\n")
            with contextlib.redirect_stdout(io.StringIO()):
                gen.install_project(self._prompts(), target)
            lines = (target / ".gitignore").read_text().splitlines()
            self.assertIn("node_modules/", lines)
            self.assertIn("*.log", lines)
            self.assertIn(".playbook-audits/", lines)

    def test_does_not_duplicate_existing_playbook_audits_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            # Pre-existing entry without trailing slash should still count.
            (target / ".gitignore").write_text("foo\n.playbook-audits\nbar\n")
            with contextlib.redirect_stdout(io.StringIO()):
                gen.install_project(self._prompts(), target)
            text = (target / ".gitignore").read_text()
            self.assertEqual(text.count(".playbook-audits"), 1)

    def test_refuses_to_install_into_playbooks_repo_itself(self) -> None:
        with self.assertRaises(SystemExit):
            gen.install_project(self._prompts(), gen.REPO_ROOT)

    def test_errors_on_missing_target(self) -> None:
        with self.assertRaises(SystemExit):
            gen.install_project(
                self._prompts(),
                Path("/nonexistent/zxxxq/agentic-playbooks-test-target"),
            )


class GeneratedMarkerTests(unittest.TestCase):
    """The project-local generated catalogs must carry the top-of-file marker
    so the agent-instructions audit / init playbooks skip them as canonical."""

    def _prompts(self) -> list[gen.Prompt]:
        return [
            gen.Prompt(
                slug="test-coverage-audit",
                collection="AuditTesting",
                rel_path="AuditTesting/test-coverage-audit.prompt.md",
                description="Audit test coverage.",
                family="test-coverage-audit",
            ),
        ]

    def test_agents_and_copilot_start_with_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            gen.generate_project_local(out, self._prompts())
            for rel in ("AGENTS.md", ".github/copilot-instructions.md"):
                content = (out / rel).read_text()
                self.assertTrue(
                    content.startswith(gen.GENERATED_MARKER),
                    f"{rel} is missing the generated marker",
                )
                # First non-blank line is the exact strict phrase the
                # audit / init heuristics match.
                self.assertEqual(
                    content.splitlines()[0], "<!-- AUTO-GENERATED -->"
                )


if __name__ == "__main__":
    sys.exit(unittest.main(verbosity=2))
