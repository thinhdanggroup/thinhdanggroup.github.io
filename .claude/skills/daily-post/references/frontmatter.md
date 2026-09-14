# Front matter contract

`script/check_frontmatter.py` runs in CI and enforces most rules below; a couple are
Jekyll/repo convention rather than something the script checks, and are marked as such
where they appear. Treat this as a hard specification rather than a style guide either
way — an unenforced convention here is still a rule the pipeline must follow, just one
whose violation won't be caught by CI.

## Required shape

```yaml
---
title: "Postgres Connection Pooling Under Sustained Load"
description: "pgbouncer's three pooling modes, what each one breaks, and how to pick between them."
tags:
    - PostgreSQL
    - Performance
categories:
    - databases
header:
    overlay_image: /assets/images/<slug>/banner.webp
    overlay_filter: 0.5
    teaser: /assets/images/<slug>/teaser.webp
toc: true
toc_sticky: true
---
```

`layout`, `author_profile`, `read_time`, and `related` come from `_config.yml` defaults.
Do not repeat them. The author block appears in older posts but is not required.

## Rules

- **`description`** — required, **50–200 characters**. It is the meta description
  search engines show. Write it as a sentence about what the reader gets, not a
  restatement of the title.
- **`tags`** — at least one. Reuse existing vocabulary wherever one fits; check
  `/tags/` before inventing a new tag. Common ones: `Python`, `LLM`, `System Design`,
  `Developer Tools`, `PostgreSQL`, `Kubernetes`, `Observability`, `Performance`,
  `AI Agents`, `Security`, `Testing`, `Serverless`.
- **`categories`** — exactly one, from this fixed set:
  `ai-engineering`, `databases`, `distributed-systems`, `infrastructure`, `python`,
  `software-engineering`, `web-development`. Every post in the archive carries exactly
  one category; `check_frontmatter.py` only checks set membership, but the pipeline's
  own queue schema (`script/daily_post/queue.py`) models `category` as a single string,
  so a daily post never has more than one.
- **`header.overlay_image` and `header.teaser`** — must end in `.webp` and must exist
  on disk. `script/daily_post/make_banner.py` generates both.
- **Filename** — `_posts/YYYY-MM-DD-slug.md`. Two different rules live in that one
  bullet: the **no-spaces** part is CI-enforced (`check_frontmatter.py` fails the
  build on a space in the filename); the **`YYYY-MM-DD-` date prefix** is Jekyll
  convention, not checked by that script — Jekyll uses it to derive the post's date,
  so getting it wrong silently mis-dates or hides the post instead of failing CI. Get
  both right regardless. The slug becomes the URL.

## Two traps that break the build

**Liquid inside code fences.** Jekyll renders Liquid everywhere, code fences
included. A Go template, a GitHub Actions expression, or a Jinja snippet is
evaluated and silently deleted from the published page. Any fence containing `{{`
or `{%` must be wrapped:

```
{% raw %}
```yaml
run: echo ${{ matrix.os }}
```
{% endraw %}
```

**Image references that do not resolve.** Every `/assets/images/...` path in the
body must point at a real file. The checker catches both `/assets/...` and the
relative `assets/...` spelling.

## Frozen URLs

`_config.yml` pins `permalink: /:title/`. Never reintroduce `:categories` into the
permalink — every post has a category, so that change would rewrite all live URLs
and discard their search ranking.
