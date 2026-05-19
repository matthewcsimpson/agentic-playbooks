---
description: Read-only SEO audit for a web app — crawlability, on-page metadata, structured data, semantic HTML, images, URL structure, and i18n. Static analysis only.
related: [seo-fix]
---

# SEO audit

Read-only audit of a web app's search-engine and social-share surface.
Asks the questions a type-checker can't: *when a crawler or share-card
scraper fetches a page, does it find what it needs to rank, render a
preview, and route users correctly?*

Stack-agnostic in shape — the questions (presence of `<title>`,
canonical, sitemap, JSON-LD, alt text, lang) are universal. The
*declaration site* differs per framework: Next.js App Router uses
`generateMetadata` and file-based `robots.ts` / `sitemap.ts`; Nuxt
uses `useSeoMeta`; Remix uses route `meta` exports; SvelteKit uses
`<svelte:head>`; Astro uses frontmatter; static generators (Hugo,
Eleventy, Jekyll) bake into HTML at build time. Adapt the greps and
file-path guesses to whichever the project uses.

This audit is **static-only**. Core Web Vitals (LCP, INP, CLS), real
rendered DOM, and Lighthouse-score measurement require a runtime
probe — out of scope here. If the user wants those, point them at a
`MilestoneSmoke/post-milestone-smoke-test.web.prompt.md` run after
this audit.

## Inputs

Scope is load-bearing — a whole-app SEO audit and a "just the
marketing pages" audit produce different reports.

If the user hasn't named a scope, **ask before starting**. Offer:

1. **Name a specific scope** — a route segment, a page type, or a
   feature area (e.g. `app/(marketing)/`, `pages/blog/`, "the product
   detail pages").
2. **Run against the whole web app** — confirm they want the wide
   scan.
3. **Infer it yourself** — pick the highest-value indexable surface
   (usually marketing / blog / product pages, not authenticated app
   shells). State your choice before proceeding.

Also ask:

- Whether the site has an authenticated app shell that should be
  excluded (most apps want `/dashboard`, `/admin`, `/settings` etc.
  out of the audit — they shouldn't be indexed anyway).
- Whether a production hostname is available for optional live
  fetches of `/robots.txt` and `/sitemap.xml` (off by default —
  static analysis covers most findings; live fetches only matter when
  the user suspects deploy-time drift).

In a monorepo (Turborepo, pnpm / npm / yarn workspaces, Nx), scope
the audit per-app rather than across the whole repo — see the
monorepo detection sub-step at the start of Step 1.

Don't guess silently.

---

## Step 0 — Convention sourcing

Read every file the project uses to document conventions, in priority
order:

- `CLAUDE.md` at the repo root and any nested ones.
- `AGENTS.md`.
- `.github/copilot-instructions.md`, `.github/instructions/**/*.md`.
- `.cursor/rules/**/*` (or `.cursorrules`).
- Any `docs/seo.md`, `docs/metadata.md`, brand / content guidelines,
  or a marketing-team style guide checked into the repo.
- `README.md` — skim for SEO conventions, sitemap generation, OG
  image strategy.

Enumerate the rules you'll be checking (title-tag format, canonical
hostname, OG image dimensions, structured-data types, …) before
scanning. If the repo has none of these, fall back to the generic
categories below — but note in the report that the spine of the
audit (project-specific rules) is missing. A short, opinionated SEO
doc is usually a higher-leverage investment than tuning the audit
itself.

---

## Step 1 — Identify the stack and rendering mode

### Step 1a — Monorepo detection

Before identifying the framework, check whether the repo is a
monorepo:

```sh
ls turbo.json pnpm-workspace.yaml nx.json lerna.json 2>/dev/null
jq -r '.workspaces // empty' package.json 2>/dev/null
```

If any of those are present, enumerate the workspace apps:

```sh
# Turborepo / npm / yarn workspaces — typically under apps/ or packages/
find apps packages -maxdepth 2 -name 'package.json' 2>/dev/null

# pnpm workspaces — read the glob
cat pnpm-workspace.yaml 2>/dev/null

# Nx
jq -r '.projects // empty' nx.json 2>/dev/null
```

For each workspace app, list:

- Path (e.g. `apps/marketing`).
- Framework (run the rest of Step 1's detection per-app — a
  Turborepo can mix Next.js marketing with an Astro docs site).
- Plausible indexability — marketing sites, blogs, docs, landing
  pages are indexable; dashboards, admin panels, internal tools,
  shared libraries (`packages/ui`, `packages/utils`) are not.

**Stop and confirm the app list with the user** before scanning.
The default is "in-scope = the user-facing indexable apps you
named, plus any obvious marketing / blog / docs apps." Authenticated
shells and shared library packages are out unless the user opts
them in.

In the report, tag every finding with its app
(`apps/marketing/app/page.tsx:42`). Cross-app pattern observations
("3 of 3 apps are missing canonical tags") are valuable summary
lines.

If the repo is a single app, skip this sub-step.

### Step 1b — Framework and rendering mode

For each in-scope app (or the whole repo if not a monorepo):

- **Framework**: Next.js (App vs Pages router), Nuxt (3 vs 2), Remix,
  SvelteKit, Astro, Gatsby, Eleventy, Hugo, Jekyll, plain HTML, a
  CSR-only React / Vue / Svelte SPA.
- **Rendering mode**: SSR, SSG, ISR, CSR-only. Detect from
  framework config and per-route opt-outs (Next: `dynamic`,
  `revalidate`; Nuxt: `routeRules`; etc.).
- **Hosting platform** (if obvious from config): Vercel, Netlify,
  Cloudflare Pages, S3+CloudFront, GitHub Pages. Some platforms
  rewrite `robots.txt` / inject headers in ways the repo doesn't
  show.
- **CMS** (if any): Contentful, Sanity, Strapi, headless WordPress,
  MDX-in-repo. Affects whether metadata is authored in the repo or
  in the CMS — flag fields that *should* be CMS-driven but are
  hard-coded.

Report the stack in the audit header. The findings that follow only
make sense in context.

**Special case — CSR-only SPA**: if the app renders entirely on the
client (no SSR, no prerender, no static export), that is the headline
finding. Surface it in the Summary as ⚠️ HIGH ("crawlers and most
social scrapers will see an empty `<div id=\"root\">`"), then proceed
with the rest of the audit against whatever HTML *is* served (the
`index.html` shell still has a title, meta, link tags).

---

## Step 2 — Crawlability and indexing

### robots.txt

```sh
# Look for source files and any framework-generated equivalents
find . -name 'robots.txt' -not -path '*/node_modules/*'
find . -name 'robots.ts' -o -name 'robots.js'           # Next.js app router
find . -name 'robots.{txt,js,ts}' -path '*/public/*'
```

Check:

- ⚠️ **Missing entirely** — crawlers fall back to defaults; usually
  fine but the absence makes any future restriction harder to
  reason about.
- ⚠️ **`Disallow: /`** — blocks all crawling. Intentional on staging,
  catastrophic on production. Flag and ask the user to confirm
  context (env-conditional generation is the usual fix).
- ⚠️ **Sitemap not referenced** — `robots.txt` should end with
  `Sitemap: https://<host>/sitemap.xml`. Without it, discovery
  relies on submission to Search Console.
- 💡 **Crawl-delay or User-agent restrictions** — note them; modern
  Googlebot ignores `Crawl-delay`, and broad UA disallows often
  hide unintentional bot-blocking.

### sitemap.xml

```sh
find . -name 'sitemap*.xml' -not -path '*/node_modules/*'
find . -name 'sitemap.ts' -o -name 'sitemap.js'         # Next.js app router
find . -name 'sitemap.config.*'                          # next-sitemap, similar
```

For each sitemap found (or generator config):

- ⚠️ **Missing entirely** — no sitemap, no help for discovery of
  pages without inbound links.
- ⚠️ **Stale / hand-maintained** — last-modified dates in the
  distant past on a site that's been updated. Suggest a generator.
- ⚠️ **References URLs that 404** — if the user supplied a live
  hostname, fetch and spot-check 5-10 URLs.
- 💡 **Includes non-indexable URLs** — pages that also carry
  `noindex` or 301-redirect. Wastes crawl budget.
- 💡 **Splits not exposed** — sitemaps over 50k URLs / 50MB need a
  sitemap index; flag if the site is large enough to risk it.

### Canonical URLs

```sh
grep -rnE 'rel=["'\'']canonical["'\'']' --include='*.html' --include='*.tsx' --include='*.jsx' --include='*.vue' --include='*.svelte' --include='*.astro' .
grep -rnE '(alternates\s*[:=]\s*\{[^}]*canonical|canonical\s*:\s*)' --include='*.ts' --include='*.tsx' --include='*.js' .
```

Check:

- ⚠️ **No canonical anywhere** — leaves Google to guess; on sites
  with query-string variants, tracking params, or pagination the
  guesses are wrong.
- ⚠️ **Canonical to a different host** — staging canonicalising to
  prod, or vice versa. Often the result of a hard-coded base URL.
- ⚠️ **Canonical to a redirect or 404** — cross-reference with
  redirect config; if you have a live host, fetch and check.
- 💡 **Self-referential canonical missing on dynamic routes** —
  product / article pages often forget to set their own canonical;
  the layout-level canonical points to the wrong URL.

### noindex / nofollow

```sh
grep -rnE 'noindex|nofollow|robots["'\'']?\s*:\s*["'\''][^"'\'']*(none|noindex)' .
```

Find:

- ⚠️ **`noindex` on a page that should be indexed** — usually a
  legacy staging meta tag left in a layout file. Worst case: the
  whole site is `noindex` in production because the meta tag isn't
  env-conditional.
- 💡 **Missing `noindex` on routes that should be hidden** — search
  pages, filter combinations, paginated content past page 1,
  internal tools accidentally exposed.

### Redirects

If the project has a redirects config (`next.config.js#redirects`,
`netlify.toml`, `_redirects`, `vercel.json`, middleware), parse it:

- ⚠️ **Redirect chain (302 → 302 → 200)** — flag any path with more
  than one hop.
- ⚠️ **Redirect loop** — A → B → A.
- ⚠️ **302 where 301 was intended** — temporary redirects are
  treated as non-canonical by crawlers; old URLs keep ranking.
- 💡 **Wildcard / regex redirects that may over-match** — call out
  for review.

---

## Step 3 — On-page metadata

Per page type (home, listing, detail, article, marketing), check the
declaration of:

```sh
# Title and description (HTML-level)
grep -rnE '<title|<meta[^>]+name=["'\'']description' .

# Framework-level metadata APIs
grep -rnE 'export\s+const\s+metadata|generateMetadata|useHead|useSeoMeta|<svelte:head>|export\s+const\s+meta' .
```

For each page or layout, classify:

- ⚠️ **Missing `<title>`** — every page must have one.
- ⚠️ **Duplicate `<title>` across distinct pages** — hard to detect
  statically when titles are dynamic; check the *template* (does it
  interpolate page-specific data?). A layout-level static title
  applied to every page is a finding.
- ⚠️ **Title is the site name on every page** — `<title>Acme</title>`
  with no per-page context.
- 💡 **Title length** — over 60 chars truncates in SERPs; under 30
  chars under-uses the space. Heuristic, not a hard rule.
- ⚠️ **Missing `<meta name="description">`** — every page should
  declare one.
- 💡 **Description too long / short / duplicate** — 70–160 chars is
  the usable range.
- ⚠️ **Missing `<html lang>`** — accessibility + SEO; both Google
  and screen readers rely on it.
- ⚠️ **Missing viewport meta** — `<meta name="viewport" content="width=device-width, initial-scale=1">`.
  Mobile-friendliness ranking factor.
- ⚠️ **Missing charset** — `<meta charset="utf-8">` should be one of
  the first elements in `<head>`.

### Open Graph and Twitter cards

```sh
grep -rnE 'og:(title|description|image|type|url|site_name|locale)|twitter:(card|title|description|image|site)' .
```

For each, check:

- ⚠️ **No OG tags at all** — share links render with no preview.
- ⚠️ **`og:image` missing or 404** — if a live host is available,
  fetch a sample of OG image URLs.
- 💡 **`og:image` smaller than 1200×630** — required for large-card
  rendering on Facebook / LinkedIn. 1200×630 is the safe default.
- 💡 **Missing `twitter:card`** — falls back to `summary` (small
  preview) instead of `summary_large_image`.
- 💡 **OG URL not absolute** — share scrapers expect absolute URLs;
  relative URLs may break.

### Favicons and app icons

```sh
grep -rnE 'rel=["'\'']icon|apple-touch-icon|manifest' .
find . -name 'favicon.*' -o -name 'apple-touch-icon*' -o -name 'icon.*' -path '*/app/*'
```

- ⚠️ **No favicon** — small SEO weight; large user-trust signal.
- 💡 **No `apple-touch-icon`** — iOS home-screen bookmarks render
  ugly without it.

---

## Step 4 — Structured data (JSON-LD)

```sh
grep -rnE 'application/ld\+json|@context.*schema\.org|jsonLd|JsonLd|StructuredData' .
```

For each schema block, classify:

- 💡 **Missing schema on high-value page types** — Articles without
  `Article` / `BlogPosting`, products without `Product`, FAQ pages
  without `FAQPage`, recipes without `Recipe`. Rich-result
  eligibility is left on the table.
- ⚠️ **`Organization` schema missing site-wide** — declared once at
  the root, drives knowledge-panel data. Cheap to add.
- 💡 **`BreadcrumbList` missing on deep hierarchies** — listing →
  category → product paths without breadcrumb schema lose the
  visual breadcrumb in SERPs.
- ⚠️ **Schema references properties that aren't on the page** —
  declaring `Recipe.cookTime` when no cook time is visible to the
  user violates Google's structured-data policy and risks manual
  action. Static check: cross-reference required vs declared fields
  against schema.org type definitions.
- 💡 **Hardcoded JSON-LD in a layout that should be per-page** —
  every article carries the same `Article` block with the same
  `headline`.

Note: full rich-result eligibility (whether Google actually awards
the rich result) requires runtime testing in Search Console — out
of scope here. Surface the syntactic findings; recommend manual
verification with the Rich Results Test.

---

## Step 5 — Headings and semantic HTML

```sh
grep -rnE '<h[1-6][\s>]' .
grep -rnE '<(main|article|section|nav|header|footer|aside)[\s>]' .
```

For each page template:

- ⚠️ **No `<h1>`** — every indexable page should have one.
- ⚠️ **Multiple `<h1>` per page** — historically tolerated, still a
  signal worth keeping unambiguous on content pages.
- ⚠️ **`<h1>` is the site logo / site name on every page** — leaves
  the actual page topic unranked.
- 💡 **Heading-level skips** — h1 → h3 with no h2 between. Hurts
  both accessibility and content-structure parsing.
- 💡 **`<div>`-soup with no semantic landmarks** — no `<main>`, no
  `<article>`, no `<nav>` on a content site. Crawlers cope, but
  the signal is weaker.

---

## Step 6 — Images and media

```sh
grep -rnE '<img[^>]*' --include='*.html' --include='*.tsx' --include='*.jsx' --include='*.vue' --include='*.svelte' --include='*.astro' .

# Framework Image components — broaden to match the detected framework:
#   next/image            → <Image …>           in *.tsx / *.jsx
#   nuxt/image            → <NuxtImg …>          in *.vue
#   svelte enhanced:img   → <enhanced:img …>     in *.svelte
#   astro                 → <Image …>            in *.astro
grep -rnE '<(Image|NuxtImg|enhanced:img)[^>]*' --include='*.tsx' --include='*.jsx' --include='*.vue' --include='*.svelte' --include='*.astro' .
```

For each image element:

- ⚠️ **Missing `alt` attribute** — both accessibility and image
  SEO. Decorative images should use `alt=""` (explicit empty),
  not omit the attribute.
- 💡 **Missing `width` / `height` attributes** — drives layout
  shift (CLS), a Core Web Vitals signal.
- 💡 **Raw `<img>` instead of the framework's Image component** —
  on Next.js / Nuxt / Astro, the built-in Image component handles
  responsive `srcset`, lazy loading, and modern formats. Raw
  `<img>` skips all of that.
- 💡 **No `loading="lazy"` on below-the-fold images** — when the
  framework Image component isn't in use.
- 💡 **PNG / JPG where WebP / AVIF would do** — heuristic; surface
  as a pattern observation, not per-image.

Hero / LCP image specifically:

- ⚠️ **Hero image lazy-loaded** — `loading="lazy"` on the
  largest-contentful-paint image actively hurts LCP. Should be
  eager (or `priority` in the Next.js Image component).

---

## Step 7 — URL structure and internationalization

URL hygiene:

- 💡 **Mixed case in URLs** — `/Products/Foo` vs `/products/foo`.
  Pick one; redirect the other.
- 💡 **Trailing slash inconsistency** — `/about` and `/about/`
  serving different content (or both 200ing). Pick one.
- 💡 **Tracking params in canonical URLs** — `utm_*`, `fbclid`,
  `gclid` should not appear in canonicals or sitemap entries.

If the site is multi-locale:

```sh
grep -rnE 'hreflang|alternates.*languages|i18n.*locales' .
```

- ⚠️ **`hreflang` missing entirely** on a multi-locale site.
- ⚠️ **`hreflang` not bidirectional** — `en` points to `fr` but
  `fr` doesn't point back to `en`.
- 💡 **No `x-default`** — should point to the locale-selector or
  default-locale URL.
- 💡 **`<html lang>` doesn't match the route locale** — every
  locale's pages serve `lang="en"`.

---

## Step 8 — Performance signals (static heuristics)

Real Core Web Vitals require a runtime probe — out of scope. What
*is* visible statically:

```sh
# Render-blocking scripts in <head> without async/defer
grep -rnE '<script[^>]*src=[^>]*>' . | grep -vE 'async|defer|type="module"'

# Inline Google Fonts (unhosted)
grep -rnE 'fonts\.googleapis\.com|fonts\.gstatic\.com' .

# Whole-library imports
grep -rnE 'from\s+["'\'']lodash["'\'']|from\s+["'\'']moment["'\'']' .
```

Findings:

- ⚠️ **Render-blocking `<script>` in `<head>`** — no `async`, no
  `defer`, no `type="module"`. Blocks first paint.
- 💡 **Unhosted Google Fonts** — `<link>` to `fonts.googleapis.com`
  rather than self-hosted via `next/font` or equivalent. Adds a
  third-party round-trip to the critical path.
- 💡 **`import _ from 'lodash'`** — whole library; pay for the
  whole bundle. Prefer `lodash-es` + named imports or `lodash/pick`
  per-method imports.
- 💡 **`import moment from 'moment'`** — moment is unmaintained;
  swap for `date-fns` or `dayjs`.
- 💡 **Missing `next/font` (or equivalent)** when self-hosting
  fonts is an option in the framework.

Note explicitly in the report: this is the *static* slice. Real LCP /
INP / CLS need a runtime probe. Recommend `MilestoneSmoke/post-milestone-smoke-test.web.prompt.md`
or a Lighthouse / PageSpeed Insights pass.

---

## Step 9 — Analytics and verification tags

```sh
grep -rnE 'google-site-verification|gtag\(|gtm\.start|plausible|posthog|fathom|google-analytics' .
```

Findings:

- 💡 **No analytics installed at all** — usually intentional, worth
  surfacing.
- ⚠️ **Same analytics tag installed twice** — common after a GTM
  migration leaves the old `gtag` in place. Double-counts every
  event.
- 💡 **Search Console verification missing** — `<meta name="google-site-verification">`
  or DNS verification. Without it, the site owner can't see
  indexing problems.
- ⚠️ **Analytics in production but no consent gating** — for
  EU-targeted sites this is a compliance issue more than an SEO
  one, but worth flagging.

---

## Step 10 — Optional: live fetch checks

If the user supplied a production hostname, fetch:

```sh
curl -sI https://<host>/robots.txt
curl -s  https://<host>/robots.txt
curl -sI https://<host>/sitemap.xml
curl -sI https://<host>/                          # check the index
curl -A 'Googlebot/2.1 (+http://www.google.com/bot.html)' -s https://<host>/ | head -200
```

Check:

- ⚠️ **`robots.txt` served at production differs from repo** — a
  CDN or hosting platform is rewriting it.
- ⚠️ **`sitemap.xml` 404s in production** — file exists in repo
  but isn't being served (build config issue).
- ⚠️ **Production serves `X-Robots-Tag: noindex` header** — meta
  tag is fine but the header overrides everything. Common on
  preview deploys leaking to a public domain.
- ⚠️ **Googlebot-UA fetch returns different HTML than default UA** —
  cloaking risk; usually unintentional (a bot-detection
  middleware overshooting).

Off by default. Only run if the user has provided a hostname and
opted in.

---

## Step 11 — Report

Output to `<root>/audits/seo-<timestamp>.md`, where:

- `<root>` resolves in this order: `.playbook-audits/` if it
  exists, else `docs/` if `docs/audits/` exists (legacy
  convention), else create `.playbook-audits/` and append
  `.playbook-audits/` to `.gitignore` (creating `.gitignore` if
  absent — these are working artefacts, not tracked history).
  Create `<root>/audits/` if it doesn't exist.
- `<timestamp>` is current UTC time in basic ISO 8601 format
  `YYYYMMDDTHHMMSS` — generate with `date -u +%Y%m%dT%H%M%S`
  (e.g. `20260519T143022`).

Always write a new file; do not overwrite prior runs — the
directory is an ordered history. Structure:

```
# SEO audit

Date: <today>
Scope: <whole app | scoped path>
Stack detected: <framework + rendering mode>
Hosting (if detected): <vercel | netlify | …>
CMS (if detected): <contentful | sanity | …>
Convention sources read: <list>
Live-fetch host (if used): <host or "none">

## Summary

<2-3 sentence verdict. Biggest concern. Lowest-effort highest-impact fix.>

## Top priorities

<Ranked list across all sections — what the user reads first.>
1. ⚠️ HIGH — <finding> — <one-line description and fix>
2. ⚠️ HIGH — ...

## Crawlability and indexing

### robots.txt
### sitemap.xml
### Canonical URLs
### noindex / nofollow
### Redirects

## On-page metadata

### Title and description
### `<html lang>` / viewport / charset
### Open Graph and Twitter cards
### Favicons

## Structured data

### Missing on high-value templates
### Site-wide Organization / BreadcrumbList
### Property mismatches

## Semantic HTML

### Headings
### Landmarks

## Images

### Missing alt
### Width / height for CLS
### Raw `<img>` vs framework Image component
### Hero / LCP image handling

## URL structure and i18n

### URL hygiene
### hreflang (if multi-locale)

## Performance signals (static only)

### Render-blocking scripts
### Font loading
### Bundle red flags

## Analytics and verification

## Live-fetch findings

<Only if a hostname was supplied and live fetches ran.>

## Pattern observations

<For categories with many similar findings: count + top 3 worst
examples. Don't enumerate all 40 instances of the same issue.>

## Out of scope (needs runtime)

- Core Web Vitals measurement (LCP, INP, CLS).
- Rich-result eligibility (Search Console / Rich Results Test).
- JavaScript-rendered metadata in CSR apps — what crawlers actually
  see vs what the source declares.
- Lighthouse SEO score.

Recommend pairing this audit with `MilestoneSmoke/post-milestone-smoke-test.web.prompt.md`
or a manual Lighthouse / PageSpeed Insights / Search Console pass.

## Recommendations

<5-10 ranked actions. Concrete, with file paths. "Add `export const
metadata = { ... }` to app/(marketing)/pricing/page.tsx — currently
inheriting the layout's site-wide title" beats "Improve metadata."
The companion `seo-fix` prompt will work from these.>
```

Each finding entry uses this shape:

- ⚠️ ISSUE — `path/to/file:42` — Description in one sentence.
  **Suggested:** `fix-now` / `fix-soon` / `defer` / `accept`.
- 💡 CANDIDATE — `path/to/file:42` — Description in one sentence.
  **Suggested:** `defer`.

If a section has no findings, mark it ✅ PASS.

---

## Constraints

- Do not modify any code or config. Surface findings; the user picks
  which to fix. `seo-fix` is the action companion.
- Every ⚠️ ISSUE must include a file path and line number. "The site
  lacks structured data" is not acceptable — name the templates and
  the missing schema types.
- Distinguish *project-specific* SEO rules (sourced from CLAUDE.md,
  brand guide, etc.) from *generic* SEO rules (sourced from
  search-engine documentation). Project rules outrank generic when
  they conflict — the user wrote them deliberately.
- Do not measure Core Web Vitals. The static slice catches setup
  problems (render-blocking scripts, lazy hero images, raw `<img>`);
  actual LCP / INP / CLS values are a runtime measurement and out of
  scope.
- For CSR-only SPAs, do not pretend the source-file analysis is
  complete — the report's headline is "this is a CSR app, here's
  what crawlers actually see," not a long list of per-component
  metadata findings that no scraper will ever read.
- Pattern observations must include a count and the 3 worst
  examples. Don't enumerate every instance of the same issue.
- Findings that depend on external config (CDN-injected headers,
  Cloudflare workers, hosting-platform rewrites) should note the
  limitation — the audit only sees the repo. Live-fetch findings
  partially close that gap when the user opts in.
- Do not flag a `noindex` on a route that is plausibly intentional
  (admin areas, draft preview routes) as ⚠️ ISSUE without checking
  context. Ask if unclear.
- Do not recommend wholesale framework migrations from the audit
  ("rewrite this in Next.js to get SSR"). That's a separate
  decision; surface the SSR-absence finding and let the user pick
  the response.
