# SEOAudit

A read-only SEO audit for a web app, paired with a narrow-scope fix
prompt that actions the findings. Asks the questions a type-checker
can't: *when a crawler or share-card scraper fetches a page, does it
find what it needs to rank, render a preview, and route users
correctly?*

Stack-agnostic in shape — the questions (presence of `<title>`,
canonical, sitemap, JSON-LD, alt text, lang) are universal. The
declaration site differs per framework: Next.js App Router uses
`generateMetadata` and file-based `robots.ts` / `sitemap.ts`; Nuxt
uses `useSeoMeta`; Remix uses route `meta` exports; SvelteKit uses
`<svelte:head>`; Astro uses frontmatter; static generators (Hugo,
Eleventy, Jekyll) bake into HTML at build time. The audit detects the
framework at Step 1 and adapts.

| Prompt | Scope |
|---|---|
| `seo-audit.prompt.md` | Read-only audit. Crawlability, on-page metadata, structured data, semantic HTML, images, URL structure, i18n, static performance heuristics, analytics tags. One audit, one report. |
| `seo-fix.prompt.md` | Actions findings from the audit. Edits metadata declarations, robots / sitemap config, canonicals, JSON-LD, alt attributes, heading structure. Verifies the build per category and commits per category. Does not push. |

## What the audit looks for

- **Crawlability** — `robots.txt`, sitemap presence and freshness,
  canonical URLs, accidental `noindex`, redirect chains and loops.
- **On-page metadata** — `<title>`, `<meta description>`, `<html lang>`,
  viewport, charset; Open Graph and Twitter cards; favicons.
- **Structured data** — JSON-LD presence on high-value page types
  (Article, Product, Organization, BreadcrumbList, FAQPage), property
  alignment with what's visible on the page.
- **Semantic HTML** — `<h1>` presence and uniqueness, heading-level
  skips, use of `<main>` / `<article>` / `<nav>` / `<header>` /
  `<footer>` landmarks.
- **Images** — `alt` attributes, `width` / `height` for CLS, raw
  `<img>` vs the framework's Image component, hero / LCP image
  loading priority.
- **URL structure** — case consistency, trailing-slash consistency,
  tracking params in canonicals or sitemap entries.
- **Internationalization** — `hreflang` bidirectionality, `x-default`,
  `<html lang>` per route.
- **Performance signals (static only)** — render-blocking scripts,
  unhosted Google Fonts, whole-library imports (`lodash`, `moment`).
- **Analytics and verification** — duplicate analytics installs,
  Search Console verification, consent gating.
- **Optional live fetch** — when the user supplies a production
  hostname, verify `/robots.txt` / `/sitemap.xml` served at the edge
  match the repo, no `X-Robots-Tag: noindex` leaking from preview
  deploys, no UA-conditional content drift.

## What the audit does *not* cover

This audit is **static-only**. Three slices need a runtime probe and
are out of scope:

- **Core Web Vitals** — LCP, INP, CLS measured in a real browser.
- **Rich-result eligibility** — whether Google actually grants the
  rich result for a JSON-LD block. Verified in Search Console's Rich
  Results Test.
- **Crawler-visible HTML in a CSR app** — what Googlebot sees after
  JS execution, when the source HTML is an empty `<div id="root">`.

For those, pair this audit with a runtime check —
[`MilestoneSmoke/post-milestone-smoke-test.web.prompt.md`](../MilestoneSmoke/post-milestone-smoke-test.web.prompt.md)
drives a real browser, or run Lighthouse / PageSpeed Insights / Search
Console manually.

## Monorepo support

Both prompts detect Turborepo (`turbo.json`), pnpm / npm / yarn
workspaces, and Nx (`nx.json`) at the start of the run. In a
monorepo:

- The audit enumerates apps, asks which are user-facing / indexable
  (defaults: marketing, blog, docs apps in; dashboards, admin
  panels, shared library packages out), and tags every finding with
  the app it came from.
- The fix prompt's verification step uses workspace-scoped commands
  (`turbo run build --filter=<app>`, `pnpm --filter <app> build`,
  etc.) so a single edit doesn't rebuild every app in the graph.
- Commits are app-qualified (`seo(marketing): ...`) when the edit
  is scoped to one app.

Apps in a Turborepo can mix frameworks — the audit detects each
app's stack independently rather than assuming the whole repo runs
one framework.

## Required tool capabilities

- File read across the repo.
- Shell execution for grep / static analysis.
- Optional outbound HTTP (`curl`) when the user opts into the
  live-fetch step against a production hostname.
- Git for the fix prompt's per-category commits — no runtime / no
  deploy access needed.

Designed for Claude Code and Codex CLI; anything with the same
capability set should work.

## Output discipline

The audit writes to `<root>/seo-<timestamp>.md` (e.g.
`.playbook-audits/seo-20260519T143022.md`). `<root>` resolves in
this order: `.playbook-audits/` if it exists, else `docs/audits/`
if that exists (legacy convention), else the audit creates
`.playbook-audits/` and appends it to `.gitignore` on first use.
Each run produces a new file so the directory accumulates an
ordered history; the fix prompt picks the most recent.

The fix prompt reads that file, actions per category with a verify-
and-commit gate between categories, and writes its own summary to the
conversation (not to a file). Commits are local; the prompt does not
push or open a PR.

## When to reach for variants

The current single-file pair handles every framework by detecting the
stack at Step 1 and adapting the greps / declaration sites. If
framework-specific findings start outweighing the generic ones —
typically when a project's metadata is heavily declarative in a way
that's hard to grep generically (Next.js `opengraph-image.tsx`,
dynamic Nuxt `definePageMeta`, complex Astro content collections) —
extract a `core/seo-audit.core.prompt.md` and add
`seo-audit.<framework>.prompt.md` variants alongside, following the
shape of `DependencyAudit/` or `DBMigrationAudit/`. The current
prompt's section structure already maps cleanly onto a core /
variant split.

## Invocation

See the [root README](../README.md#invocation) for the three
supported patterns. No core / variant split yet — both prompts are
single files.
