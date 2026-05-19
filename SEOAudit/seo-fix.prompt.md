---
description: Action findings from seo-audit. Edits metadata, robots, sitemap, canonical, JSON-LD, alt, lang per category, verifies build, commits per category. Local commits only.
related: [seo-audit]
---

# SEO fix

Action findings from a `seo-audit` report against a web app. Edits
metadata declarations, robots / sitemap config, canonical URLs,
structured data, alt attributes, and the other findings the audit
surfaced. Verifies the build between categories and commits per
category so a regression can be reverted without losing the others.

This prompt is conservative by default. It actions one category at a
time and commits per category. It does **not** push and does **not**
open a PR.

## Context

SEO fixes are usually mechanical (add a meta tag, declare a
canonical, fill an `alt`) but a handful are judgment-heavy (writing
plausible alt text from inferred image content, choosing a canonical
hostname when two are in use, picking between consolidating
duplicates and 301-redirecting them). The default behaviour is:
mechanical fixes auto-apply; judgment fixes leave a `TODO` and
surface in the report.

---

## Inputs

The user supplies:

- **Categories in scope** — any combination of:
  - `crawlability` — fix `robots.txt`, wire up sitemap, fix
    accidental `Disallow: /`, fix `X-Robots-Tag: noindex` leakage.
  - `metadata` — add missing `<title>`, `<meta description>`,
    `<html lang>`, viewport, charset.
  - `canonical` — add missing `rel="canonical"`, fix wrong-host
    canonicals, fix canonicals pointing to redirects.
  - `social` — add or repair Open Graph and Twitter card tags,
    fix OG image URLs.
  - `structured-data` — add JSON-LD blocks for high-value page
    types (Article, Product, Organization, BreadcrumbList,
    FAQPage), repair property mismatches.
  - `headings` — fix missing or duplicate `<h1>`, repair
    heading-level skips.
  - `images` — add missing `alt` attributes (with TODO stubs for
    judgment cases), add `width` / `height`, swap raw `<img>` for
    the framework Image component on flagged hot paths.
  - `urls` — fix tracking params in canonicals / sitemap, fix
    trailing-slash inconsistency in redirects config.
  - `i18n` — fix `hreflang` bidirectionality, add `x-default`,
    align `<html lang>` with the route locale.
  - `performance-static` — add `async` / `defer` to render-blocking
    scripts, swap unhosted Google Fonts for the framework's font
    handler, replace whole-library imports with named or scoped
    imports.
  - `noindex-leakage` — remove `noindex` accidentally applied to
    production routes; add `noindex` to routes that should be
    hidden (search results pages, internal tools).

  Default scope is `crawlability` + `metadata` + `canonical` +
  `noindex-leakage`. The other categories require explicit opt-in
  (structured data, images, and performance carry larger
  blast radius and want a deliberate decision).

- **Alt-text policy** — for the `images` category:
  - `alt:todo` (default) — for images without obvious alt text from
    surrounding code (filename, caption, context), write
    `alt="TODO: describe <filename>"` and surface the count.
  - `alt:infer` — attempt to derive alt text from filename,
    surrounding text, and component props. Higher risk of bad text;
    only choose when the user has confirmed they want it.

- **Excluded paths** — optional, comma-separated list of route
  segments or file globs to skip even within an in-scope category.
  Use for routes the user wants to handle by hand (the marketing
  team's landing page templates, a complex i18n redirect graph,
  etc.).

- **Included paths** — optional, mutually exclusive with excluded.
  Narrows action to just those paths within the in-scope categories.

If the user hasn't specified, ask before doing anything else. Don't
guess scope. The audit is the survey; the fix should be deliberate.

---

## Step 1 — Locate the audit

The audit writes to `<root>/seo-<timestamp>.md`. Resolve `<root>`
in this order: `.playbook-audits/` if it exists, else
`docs/audits/` if that exists (legacy convention). Look for files
matching `<root>/seo-*.md` and pick the most recent
(`ls -1 <root>/seo-*.md 2>/dev/null | sort | tail -1` — the
`YYYYMMDDTHHMMSS` suffix sorts lexicographically). If neither root
exists or no report is found, ask the user whether they have an
inline report to paste, or whether they need to run the audit.

If the user named a specific report file, use that one instead of the
most recent.

If neither a file nor an inline report is available, stop and
recommend running `/playbook seo-audit` first.

---

## Step 1.5 — Apply the include / exclude filter

Before any action, build the final action list:

1. Start with every audit finding under the in-scope categories.
2. If `Included paths` is set, drop everything except those paths.
3. If `Excluded paths` is set, drop those paths.
4. Surface the filtered list to the user before proceeding ("After
   filtering, X findings remain in scope: ..."). If the filter
   removed everything, stop — there's nothing to do.

---

## Step 2 — Verify the audit is still valid

SEO findings can go stale if files were edited between audit and
fix. Before acting on any finding, re-check:

- The file still exists at the path the audit cited.
- The reported line still has the issue (a missing `alt` may have
  been added by hand between runs).
- The route-level metadata file (e.g. `page.tsx`, `route.ts`) is
  still the right declaration site for the framework version in
  use.

If a finding no longer applies, record under "Skipped — no longer
applies" and move on.

---

## Step 3 — Action `crawlability`

### robots.txt

If missing: create one with the safe default for the framework.

For Next.js (App Router), prefer `app/robots.ts`:

```ts
// app/robots.ts
import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: '*', allow: '/' },
    sitemap: 'https://<host>/sitemap.xml',
  };
}
```

For static / generic projects, write `public/robots.txt`:

```
User-agent: *
Allow: /

Sitemap: https://<host>/sitemap.xml
```

If a `Disallow: /` is present on what looks like a production build,
**do not silently remove it** — flag it for confirmation. The user
may have left it intentionally on a staging build that shares the
repo. Ask explicitly which environments should be indexable.

### Sitemap

If missing and the project is Next.js App Router, add
`app/sitemap.ts`:

```ts
// app/sitemap.ts
import type { MetadataRoute } from 'next';

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: 'https://<host>/', lastModified: new Date() },
    // ...add per-route entries here, ideally generated from the
    // same source the routes are.
  ];
}
```

For other frameworks: add the project's idiomatic sitemap generator
(`next-sitemap` for Next.js Pages router, `@nuxtjs/sitemap` for
Nuxt, `astro-sitemap` for Astro, a `build` step that writes
`public/sitemap.xml` for static generators). Do not hand-maintain a
sitemap if the framework offers a generator.

### Production-only headers

If the audit flagged `X-Robots-Tag: noindex` served from production,
that's typically a hosting-platform setting (Vercel preview
deployments, Netlify staging branches). The fix lives in deploy
config, not the repo — surface the finding under "Skipped —
external config" with a one-line note on where to look.

---

## Step 4 — Action `metadata`

For each route with missing metadata, add the framework's
declaration.

**Next.js note** — all Next.js `Metadata`-typed examples in this and
following steps assume `import type { Metadata } from 'next';` at
the top of the file. Add the import when introducing the typed
declaration into a file that doesn't already have it.

**Next.js (App Router)** — add or extend `export const metadata` (or
`generateMetadata` for dynamic):

```ts
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '<Page-specific title> | <Site name>',
  description: '<70-160 chars>',
};
```

**Next.js (Pages Router)** — add `<Head>` from `next/head` in the
page component.

**Nuxt 3** — `useSeoMeta({ title, description })`.

**Remix** — `export const meta = ({ ... }) => [{ title }, { name:
'description', content: '...' }]`.

**SvelteKit** — `<svelte:head><title>...</title>...</svelte:head>`.

**Astro** — frontmatter `<title>` / `<meta>` in the layout, with
`Astro.props` per-page overrides.

**Static / generic** — edit the template's `<head>` block.

For `<html lang>`, viewport, and charset: these are usually at the
root layout. Fix once.

If the audit found *duplicate* titles across distinct pages, prefer
inserting per-page `title` declarations over editing the layout —
the layout is the wrong fix site for a per-page concern.

---

## Step 5 — Action `canonical`

For each route missing a canonical or carrying a wrong canonical:

**Next.js (App Router)**:

```ts
export const metadata: Metadata = {
  alternates: { canonical: 'https://<host>/<route>' },
};
```

**Generic**: add `<link rel="canonical" href="...">` to the page
`<head>`.

Use the absolute production URL — relative canonicals work but
hosting drift (subdomain changes, multi-region) breaks them
silently. Read the project's configured base URL from env / config
rather than hard-coding.

For canonicals pointing to a redirect: fix the canonical to point to
the final destination, not the redirector.

If two hosts are in use (`www.` and bare apex, or two locales of the
same content), the canonical choice is a project decision — stop and
ask which is canonical. Don't pick silently.

---

## Step 6 — Action `social`

For each route missing OG / Twitter tags:

**Next.js (App Router)**:

```ts
export const metadata: Metadata = {
  openGraph: {
    title: '...',
    description: '...',
    url: 'https://<host>/<route>',
    siteName: '<Site>',
    images: [{ url: 'https://<host>/og.png', width: 1200, height: 630 }],
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: '...',
    description: '...',
    images: ['https://<host>/og.png'],
  },
};
```

For OG images: if the project has a dynamic OG image generator
(Next.js `opengraph-image.tsx`, Vercel OG, Satori, etc.), prefer it
to a single static `og.png`. If not, surface the absence as a
recommendation rather than scaffolding one — generating per-route OG
images is its own project.

---

## Step 7 — Action `structured-data`

For each page type the audit flagged for missing schema, add a
JSON-LD block in the page's metadata.

**Organization** (site-wide, in the root layout):

```ts
const orgJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: '<Site>',
  url: 'https://<host>',
  logo: 'https://<host>/logo.png',
};
// Render via <script type="application/ld+json">{JSON.stringify(orgJsonLd)}</script>
// in the root layout.
```

**Article** (on blog/post pages) — `@type: 'Article'` with
`headline`, `datePublished`, `author`, `image`.

**Product** (on product pages) — `@type: 'Product'` with `name`,
`image`, `offers`.

**BreadcrumbList** — on any deep page, listing the path.

**FAQPage** — on FAQ pages, listing questions and answers.

Constraints:

- Do not declare properties the page does not visibly contain.
  Declaring `Recipe.cookTime: 'PT30M'` when no cook time is shown to
  the user violates Google's structured-data policy.
- For per-page schema, *generate* from the same source the page
  renders from. Hard-coded blocks copy-pasted across pages drift.
- If the project's framework has a `<JsonLd>` or `<Script
  type="application/ld+json">` helper component, use it.

After adding, the user must verify rich-result eligibility with the
Rich Results Test in Search Console — that's runtime and out of
scope here. Note it in the report.

---

## Step 8 — Action `headings`

For each heading finding:

- **Missing `<h1>`** — add one to the page template, using the
  page's primary title. Don't reuse the site name.
- **Multiple `<h1>` per page** — promote the most semantically
  central to `<h1>`, demote others to `<h2>`. If unclear which is
  primary, surface as a `TODO` for the content owner rather than
  guessing.
- **Heading-level skip (`h1` → `h3`)** — insert an `<h2>` or demote
  the `<h3>` to `<h2>`. Pick whichever matches the visual
  hierarchy already on the page.

These edits touch presentation. If the project has visual styles
keyed off heading levels, run the visual smoke step (Step 12) before
committing.

---

## Step 9 — Action `images`

For each missing `alt` attribute:

- **Obvious decorative image** (icons inside buttons that already
  have labels, divider images, background-style hero overlays):
  add `alt=""` explicitly.
- **Filename or surrounding context implies content** (`alt:infer`
  in scope): synthesise alt text from the filename, neighbouring
  caption, or component props. Keep it under 125 chars.
- **Unclear content** (`alt:todo` default, or `alt:infer` with no
  signal): insert `alt="TODO: describe <filename>"` and count it
  in the report. The user follows up with the content owner.

For `width` / `height`: read from the source image where possible.
If the image is dynamic (CMS-driven, remote URL), use the framework
Image component (which handles intrinsic sizing) rather than
hardcoding.

For raw `<img>` → framework Image component: only swap on the
specific files the audit flagged — usually high-traffic pages or
hero images. Sweeping the whole repo is scope creep.

For hero / LCP images flagged as lazy-loaded: set `priority` (Next.js
Image), or remove `loading="lazy"` (raw `<img>`).

---

## Step 10 — Action `urls`, `i18n`, `performance-static`, `noindex-leakage`

These categories are each small and routine; action mechanically:

- **URLs**: strip `utm_*` / `fbclid` / `gclid` from canonical
  builders and sitemap generators. Fix trailing-slash mismatches in
  redirects config to a single project-wide convention.
- **i18n**: pair up `hreflang` entries so every locale references
  every other locale, including `x-default`. Align `<html lang>`
  per route from the route's locale rather than a global.
- **Performance-static**: add `async` or `defer` to render-blocking
  scripts. Replace `<link href="fonts.googleapis.com">` with
  `next/font` (or framework equivalent). Replace
  `import _ from 'lodash'` with `import { pick } from 'lodash-es'`
  or `import pick from 'lodash/pick'`.
- **noindex-leakage**: remove `<meta name="robots" content="noindex">`
  from production routes. Make staging `noindex` env-conditional
  rather than hard-coded. Add `noindex` to internal-tool routes the
  audit flagged.

---

## Step 11 — Verification per category

After **each** category's action:

```sh
# Typecheck (if TS)
<project's typecheck command>

# Lint
<project's lint command>

# Build — the most useful gate; catches Metadata API misuse,
# missing imports, broken JSX
<project's build command>

# Unit tests if metadata is tested anywhere
<project's test command>
```

Infer exact commands from the project's `package.json` scripts (or
equivalent). A passing build is the gate.

**In a monorepo**, scope verification to the affected app rather
than rebuilding everything:

```sh
# Turborepo (detect: turbo.json at root)
turbo run typecheck --filter=<app>
turbo run lint --filter=<app>
turbo run build --filter=<app>

# pnpm workspaces
pnpm --filter <app> typecheck
pnpm --filter <app> lint
pnpm --filter <app> build

# npm workspaces
npm run typecheck -w <app>
npm run build -w <app>

# yarn berry workspaces
yarn workspace <app> typecheck
yarn workspace <app> build

# Nx
nx run <app>:build
nx run <app>:lint
```

If a category's edits touched multiple apps, run each app's
verification before committing — a passing build in one app does
not validate the others.

If checks fail: revert the category's edits, record under "Skipped
— broke checks" with the failing command and a one-line guess.

If checks pass: stage and commit with a per-category message. In a
monorepo, qualify the scope with the app name:

- `seo: add canonical URLs to marketing pages`
- `seo(marketing): fix accidental noindex in production layout`
- `seo(docs): add Organization JSON-LD to root layout`
- `seo: add missing alt attributes (47 fixed, 12 TODOs)`

One commit per category (per app, in a monorepo) keeps a broken
category revertible without losing the others.

---

## Step 12 — Optional: visual smoke

If the user is available and the changes touched template structure
(headings, layout-level metadata that affects rendered HTML), run a
quick visual check before committing:

- Start the project's dev server.
- Open the changed routes.
- Confirm the page still looks correct — no visual regression from
  the heading demotion, no layout shift from the new metadata.

This is a judgement check, not a hard gate. Skip if the user is
unavailable; flag the skip in the report.

---

## Step 13 — Run the full check suite

When all in-scope categories are actioned, run from a clean state:

- Typecheck.
- Lint.
- Build (scoped to the primary app if a monorepo).
- Test (unit + integration if both exist).
- If the project has an HTML / accessibility linter (`html-validate`,
  `axe`, `lighthouse-ci`), run it — the alt / heading / lang fixes
  should reduce warnings.

A passing check suite is the gate.

---

## Step 14 — Report

Output a short summary:

- **Categories actioned** — count per category, with file paths.
- **Edits applied** — list grouped by category. Example: "Added
  canonical to 14 routes under app/(marketing)/."
- **TODOs surfaced** — alt text TODOs, judgement-call canonicals,
  pending dynamic OG image setup. Count + sample.
- **Skipped within scope** — with reason per item.
- **Out-of-scope follow-ups** — Core Web Vitals measurement, rich-
  result verification, dynamic OG image generation, sweeping
  `<img>` → Image migration if the audit only flagged a few.
- **Final check result** — pass / fail with the failing command.
- **Suggested PR title and body** — draft for a human to paste, not
  to open.

---

## Constraints

- Do not push to the remote.
- Do not open a PR.
- Do not action categories outside the user's stated scope. The
  default (`crawlability` + `metadata` + `canonical` +
  `noindex-leakage`) is deliberately narrow.
- Do not generate alt text from image *content* (running OCR, image
  models, anything beyond filename + surrounding code). The fix
  prompt is a code edit pass; visual inference is a different tool
  with different review needs.
- Do not "improve" code adjacent to a fix (reformat the file,
  rename variables, reorder imports). Scope creep turns a low-risk
  SEO pass into a review burden.
- Do not pick a canonical hostname when two are plausibly in use.
  Stop and ask. A wrong canonical is harder to recover from than a
  missing one.
- Do not silently remove `Disallow: /` or production `noindex`. Both
  are sometimes intentional (staging that shares the repo, a soft-
  launch route). Confirm before removing.
- Do not scaffold dynamic OG image generation as part of a fix pass.
  It's a multi-file feature with its own design decisions; surface
  the missing-image finding and let the user pick the response.
- Do not migrate the project to a different framework / rendering
  mode (SSR adoption, prerender setup) from a fix pass. If the audit
  flagged "CSR-only SPA", that's a project decision; the fix prompt
  edits what's there.
- Do not edit CMS content. If a missing-meta finding traces to a
  CMS-driven field, surface the gap with a note that the fix lives
  in the CMS, not the repo.
- Hard-coded JSON-LD that should be data-driven is a code smell, but
  the fix prompt is allowed to commit it when no data source is
  reachable. Mark the commit message accordingly so a follow-up
  refactor is easy to find.
