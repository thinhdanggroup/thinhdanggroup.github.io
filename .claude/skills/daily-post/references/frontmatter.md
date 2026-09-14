# Front matter contract

`script/check_frontmatter.py` enforces every rule below and runs in CI. A post that
breaks any of them fails the build, so treat this as a hard specification rather
than a style guide.

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
- **Filename** — `_posts/YYYY-MM-DD-slug.md`, no spaces. The slug becomes the URL.

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
