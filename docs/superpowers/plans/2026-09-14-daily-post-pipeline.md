# Daily Post Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repo-local Claude Code skill and its supporting scripts so that one command produces one researched, reviewed, quality-gated blog post per run and opens a pull request for it.

**Architecture:** The pipeline splits on one line — anything mechanically checkable is a Python or shell script with an exit code, and the model only judges what cannot be scripted (truth, voice, insight). Five stages run inside a single skill: select a topic, research it into an evidence ledger, write the post, review it through four parallel gate subagents, then generate a banner, run preflight, and open the PR. Scripts are testable and tested; the skill is prose that orchestrates them.

**Tech Stack:** Python 3.12 (standard library only, plus Pillow and PyYAML, both already installed), Bash, pytest 9.1.1, Jekyll/Ruby via the existing `make` targets, `gh` for pull requests.

**Spec:** `docs/superpowers/specs/2026-09-14-daily-post-pipeline-design.md`

## Global Constraints

- **No new heavy dependencies.** `scikit-learn` and `numpy` are installed but **broken** on this machine (`ImportError: numpy.core.multiarray failed to import`). Similarity scoring MUST be implemented with the Python standard library alone. Verified working: Pillow, PyYAML, pytest 9.1.1.
- **No image tooling beyond Pillow.** `cairosvg`, `rsvg-convert`, ImageMagick, and `cwebp` are all absent. Pillow writes WebP natively; use it.
- **`gh` is NOT installed.** Scripts must detect its absence and fail fast with exit code `40`, never halfway through a run.
- **Front matter contract** (enforced by `script/check_frontmatter.py`, which runs in CI): `description` present and 50–200 chars; at least one tag; exactly one category from `ai-engineering`, `databases`, `distributed-systems`, `infrastructure`, `python`, `software-engineering`, `web-development`; `header.overlay_image` and `header.teaser` must end in `.webp` and exist on disk; no code fence containing `{{` or `{%` outside `{% raw %}`; every `/assets/images/...` reference must resolve.
- **Post length: 1,000–1,500 words.** A deliberate lighter tier than the 2,000–3,300 word archive.
- **Permalinks are frozen** at `/:title/`. Never reintroduce `:categories` into the permalink.
- **Banner sizes:** `banner.webp` at 1600px wide, `teaser.webp` at 640px wide, both under `assets/images/<slug>/`.
- **Exit codes** (`run.sh`): `0` success, `10` gates blocked with draft PR open, `20` no viable topic, `30` already ran today, `40` precondition failure, `50` preflight red.
- **Duplicate threshold:** TF-IDF cosine `> 0.55` over title + description + headings.
- **Revision cap:** at most 2 revision rounds after a gate block.
- **Unattended:** no step may prompt a human. Ever.

---

## File Structure

| Path | Responsibility |
| --- | --- |
| `script/daily_post/similarity.py` | Pure stdlib TF-IDF + cosine. No I/O. |
| `script/daily_post/corpus.py` | Reads `_posts/*.md` into `Post` records. |
| `script/daily_post/dupe_check.py` | CLI wrapping corpus + similarity; exit code signals duplicate. |
| `script/daily_post/queue.py` | Read/claim/mark topics in `_data/topic_queue.yml`. |
| `script/daily_post/make_banner.py` | Pillow banner + teaser rendering. |
| `script/daily_post/preflight.sh` | Front matter + jekyll build + htmlproofer, as CI runs them. |
| `script/daily_post/run.sh` | Daily entry point: preconditions, idempotency, exit codes. |
| `script/daily_post/tests/` | pytest suite for all of the above. |
| `_data/topic_queue.yml` | Committed queue state. |
| `.claude/skills/daily-post/SKILL.md` | The five-stage pipeline. |
| `.claude/skills/daily-post/references/*.md` | Voice, front matter, sources, gates. |

Splitting `similarity.py` (pure math, no I/O) from `corpus.py` (filesystem) from `dupe_check.py` (CLI) is deliberate: the math is then testable with literal strings and no fixtures on disk.

---

### Task 1: Similarity scoring (pure functions)

**Files:**
- Create: `script/daily_post/__init__.py` (empty)
- Create: `script/daily_post/similarity.py`
- Test: `script/daily_post/tests/test_similarity.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `tokenize(text: str) -> list[str]`
  - `tfidf_vectors(docs: list[str]) -> tuple[list[dict[str, float]], dict[str, float]]` returning per-document vectors and the IDF map
  - `vector_for(text: str, idf: dict[str, float]) -> dict[str, float]`
  - `cosine(a: dict[str, float], b: dict[str, float]) -> float`

- [ ] **Step 1: Write the failing test**

Create `script/daily_post/tests/test_similarity.py`:

```python
import math

from script.daily_post.similarity import cosine, tfidf_vectors, tokenize, vector_for


def test_tokenize_lowercases_and_drops_punctuation():
    assert tokenize("From Kafka to NATS: Less Is More!") == [
        "from", "kafka", "to", "nats", "less", "is", "more",
    ]


def test_tokenize_drops_single_characters():
    assert "a" not in tokenize("a kafka broker")


def test_cosine_of_identical_vectors_is_one():
    v = {"kafka": 1.0, "nats": 2.0}
    assert math.isclose(cosine(v, v), 1.0, rel_tol=1e-9)


def test_cosine_of_disjoint_vectors_is_zero():
    assert cosine({"kafka": 1.0}, {"postgres": 1.0}) == 0.0


def test_cosine_of_empty_vector_is_zero_not_a_crash():
    assert cosine({}, {"kafka": 1.0}) == 0.0


def test_idf_penalises_terms_present_in_every_document():
    docs = ["kafka nats messaging", "kafka postgres indexes", "kafka python asyncio"]
    _, idf = tfidf_vectors(docs)
    assert idf["kafka"] < idf["nats"]


def test_vector_for_uses_supplied_idf():
    docs = ["kafka nats messaging", "kafka postgres indexes"]
    _, idf = tfidf_vectors(docs)
    v = vector_for("kafka messaging", idf)
    assert set(v) == {"kafka", "messaging"}
    assert v["messaging"] > v["kafka"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest script/daily_post/tests/test_similarity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'script.daily_post.similarity'`

- [ ] **Step 3: Write the implementation**

Create empty `script/daily_post/__init__.py`, and an empty `script/daily_post/tests/__init__.py`. Note `script/` itself needs `script/__init__.py` (also empty) for the `script.daily_post` import path to resolve from the repo root.

Create `script/daily_post/similarity.py`:

```python
#!/usr/bin/env python3
"""TF-IDF cosine similarity, standard library only.

scikit-learn and numpy are installed but broken on the target machine
(`ImportError: numpy.core.multiarray failed to import`), so this is hand-rolled.
The corpus is ~150 short documents, which is far too small for the dependency to
have earned its place anyway.
"""
from __future__ import annotations

import math
import re
from collections import Counter

WORD_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens of two characters or more.

    Single characters carry no topical signal and inflate the vocabulary.
    """
    return [t for t in WORD_RE.findall(text.lower()) if len(t) > 1]


def tfidf_vectors(docs: list[str]) -> tuple[list[dict[str, float]], dict[str, float]]:
    """Vectorise a corpus, returning the vectors and the IDF map that built them.

    The IDF map is returned so a later candidate can be projected into the same
    space with `vector_for` instead of re-vectorising the whole corpus.
    """
    tokenized = [tokenize(d) for d in docs]
    n = len(tokenized) or 1

    df: Counter[str] = Counter()
    for tokens in tokenized:
        df.update(set(tokens))

    # Smoothed IDF: +1 inside the log keeps a term present in every document at a
    # small positive weight rather than exactly zero, so a candidate made entirely
    # of common terms still scores above the floor.
    idf = {term: math.log((1 + n) / (1 + count)) + 1.0 for term, count in df.items()}

    return [_vector(tokens, idf) for tokens in tokenized], idf


def vector_for(text: str, idf: dict[str, float]) -> dict[str, float]:
    """Project one document into an existing IDF space. Unknown terms are dropped."""
    return _vector(tokenize(text), idf)


def _vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {
        term: (count / total) * idf[term]
        for term, count in counts.items()
        if term in idf
    }


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity of two sparse vectors. Empty vectors score 0.0."""
    if not a or not b:
        return 0.0
    shared = a.keys() & b.keys()
    if not shared:
        return 0.0
    dot = sum(a[t] * b[t] for t in shared)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest script/daily_post/tests/test_similarity.py -v`
Expected: PASS, 7 tests.

- [ ] **Step 5: Commit**

```bash
git add script/__init__.py script/daily_post/__init__.py script/daily_post/similarity.py script/daily_post/tests/__init__.py script/daily_post/tests/test_similarity.py
git commit -m "Add stdlib TF-IDF similarity for daily post topic dedupe"
```

---

### Task 2: Corpus reader

**Files:**
- Create: `script/daily_post/corpus.py`
- Test: `script/daily_post/tests/test_corpus.py`

**Interfaces:**
- Consumes: nothing. Corpus produces raw text; Task 3 is what joins it to the scoring in Task 1.
- Produces:
  - `@dataclass(frozen=True) class Post: slug: str; title: str; description: str; headings: tuple[str, ...]; path: Path`
  - `Post.text` property returning `f"{title} {description} {' '.join(headings)}"`
  - `load_posts(posts_dir: Path) -> list[Post]`

- [ ] **Step 1: Write the failing test**

Create `script/daily_post/tests/test_corpus.py`:

```python
from pathlib import Path

import pytest

from script.daily_post.corpus import Post, load_posts

POST = """---
title: "From Kafka to NATS: When Less Is More"
description: "When NATS is the better fit than Kafka."
categories:
    - distributed-systems
tags:
    - Kafka
---

Intro paragraph.

## The failure mode

Body.

### A subsection that should be ignored

More body.

## Key takeaways

Done.
"""


@pytest.fixture
def posts_dir(tmp_path: Path) -> Path:
    d = tmp_path / "_posts"
    d.mkdir()
    (d / "2025-12-04-kafka-to-nats.md").write_text(POST, encoding="utf-8")
    return d


def test_load_posts_reads_title_and_description(posts_dir: Path):
    (post,) = load_posts(posts_dir)
    assert post.title == "From Kafka to NATS: When Less Is More"
    assert post.description == "When NATS is the better fit than Kafka."


def test_load_posts_derives_slug_from_filename_without_date(posts_dir: Path):
    (post,) = load_posts(posts_dir)
    assert post.slug == "kafka-to-nats"


def test_load_posts_collects_h2_headings_only(posts_dir: Path):
    (post,) = load_posts(posts_dir)
    assert post.headings == ("The failure mode", "Key takeaways")


def test_post_text_concatenates_the_searchable_fields():
    post = Post(
        slug="s", title="T", description="D", headings=("H1", "H2"), path=Path("x")
    )
    assert post.text == "T D H1 H2"


def test_load_posts_skips_files_without_front_matter(tmp_path: Path):
    d = tmp_path / "_posts"
    d.mkdir()
    (d / "2025-01-01-broken.md").write_text("no front matter here", encoding="utf-8")
    assert load_posts(d) == []


def test_load_posts_tolerates_invalid_yaml(tmp_path: Path):
    d = tmp_path / "_posts"
    d.mkdir()
    (d / "2025-01-01-bad.md").write_text(
        '---\ntitle: "unclosed\n---\n\nbody\n', encoding="utf-8"
    )
    assert load_posts(d) == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest script/daily_post/tests/test_corpus.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'script.daily_post.corpus'`

- [ ] **Step 3: Write the implementation**

Create `script/daily_post/corpus.py`:

```python
#!/usr/bin/env python3
"""Read `_posts/*.md` into records the dedupe check can compare against.

Deliberately reads the posts themselves rather than `blog_posts.json`: that export
carries only title, tags, and date, and goes stale the moment `make generate` has
not been run since the last post.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

FM_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.S)
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
DATED_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-(.+)$")


@dataclass(frozen=True)
class Post:
    slug: str
    title: str
    description: str
    headings: tuple[str, ...]
    path: Path

    @property
    def text(self) -> str:
        """The fields worth comparing a candidate topic against."""
        return " ".join([self.title, self.description, *self.headings])


def load_posts(posts_dir: Path) -> list[Post]:
    """Every parseable post. Unparseable files are skipped, not fatal.

    A single malformed post must never take down the daily run.
    """
    posts: list[Post] = []
    for path in sorted(posts_dir.glob("*.md")):
        post = _read_post(path)
        if post is not None:
            posts.append(post)
    return posts


def _read_post(path: Path) -> Post | None:
    text = path.read_text(encoding="utf-8")
    match = FM_RE.match(text)
    if not match:
        return None
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None

    body = text[match.end():]
    name_match = DATED_NAME_RE.match(path.stem)
    slug = name_match.group(1) if name_match else path.stem

    return Post(
        slug=slug,
        title=str(fm.get("title") or ""),
        description=str(fm.get("description") or ""),
        headings=tuple(H2_RE.findall(body)),
        path=path,
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest script/daily_post/tests/test_corpus.py -v`
Expected: PASS, 6 tests.

- [ ] **Step 5: Verify it reads the real archive**

Run:
```bash
python3 -c "
from pathlib import Path
from script.daily_post.corpus import load_posts
posts = load_posts(Path('_posts'))
print(len(posts), 'posts')
print(posts[-1].title)
"
```
Expected: `146 posts` (or more) and a real title. If the count is below 146, a parsing bug is silently dropping posts — fix before continuing.

- [ ] **Step 6: Commit**

```bash
git add script/daily_post/corpus.py script/daily_post/tests/test_corpus.py
git commit -m "Add post corpus reader for daily post dedupe"
```

---

### Task 3: Duplicate check CLI (with archive calibration)

**Files:**
- Create: `script/daily_post/dupe_check.py`
- Test: `script/daily_post/tests/test_dupe_check.py`

**Interfaces:**
- Consumes: `load_posts`, `Post` (Task 2); `tfidf_vectors`, `vector_for`, `cosine` (Task 1).
- Produces:
  - `@dataclass(frozen=True) class Match: slug: str; title: str; score: float`
  - `rank(candidate: str, posts: list[Post], top: int = 5) -> list[Match]`
  - `DEFAULT_THRESHOLD: float = 0.55`
  - CLI: `python3 script/daily_post/dupe_check.py --title T [--angle A] [--posts-dir _posts] [--top 5] [--threshold 0.55] [--json]`
  - CLI exit codes: `0` below threshold (topic is viable), `1` at or above (duplicate).

- [ ] **Step 1: Write the failing test**

Create `script/daily_post/tests/test_dupe_check.py`. The calibration test is the important one — it pins the threshold against the real archive rather than against invented fixtures:

```python
import json
import subprocess
import sys
from pathlib import Path

import pytest

from script.daily_post.corpus import Post, load_posts
from script.daily_post.dupe_check import DEFAULT_THRESHOLD, Match, rank

REPO = Path(__file__).resolve().parents[3]


def make_post(slug: str, title: str, description: str = "", headings=()) -> Post:
    return Post(
        slug=slug,
        title=title,
        description=description,
        headings=tuple(headings),
        path=Path(f"_posts/{slug}.md"),
    )


def test_rank_returns_matches_sorted_by_descending_score():
    posts = [
        make_post("kafka-to-nats", "From Kafka to NATS in distributed messaging"),
        make_post("pandas-speed", "Making Pandas dataframes faster"),
    ]
    matches = rank("Migrating from Kafka to NATS", posts)
    assert [m.slug for m in matches] == ["kafka-to-nats", "pandas-speed"]
    assert matches[0].score > matches[1].score


def test_rank_honours_the_top_argument():
    posts = [make_post(f"p{i}", f"Post about topic {i}") for i in range(10)]
    assert len(rank("topic 3", posts, top=3)) == 3


def test_rank_on_an_empty_corpus_returns_nothing():
    assert rank("anything", []) == []


def test_match_is_comparable_for_assertions():
    assert Match(slug="a", title="A", score=1.0) == Match(slug="a", title="A", score=1.0)


@pytest.mark.calibration
def test_threshold_flags_a_real_near_duplicate_and_spares_a_distinct_topic():
    """Pin DEFAULT_THRESHOLD against the live archive.

    "Migrating from Kafka to NATS" must collide with the existing Kafka/NATS post.
    "Postgres connection pooling under load" shares the corpus's general vocabulary
    but is a genuinely new topic and must stay clear of the threshold.
    """
    posts = load_posts(REPO / "_posts")
    assert len(posts) >= 140, "archive did not load; fixture assumptions are stale"

    duplicate = rank("Migrating from Kafka to NATS", posts)[0]
    assert duplicate.slug == "kafka-to-nats"
    assert duplicate.score > DEFAULT_THRESHOLD

    distinct = rank("Postgres connection pooling under sustained load", posts)[0]
    assert distinct.score < DEFAULT_THRESHOLD


def test_cli_exits_zero_for_a_viable_topic(tmp_path: Path):
    posts = tmp_path / "_posts"
    posts.mkdir()
    (posts / "2025-01-01-pandas.md").write_text(
        '---\ntitle: "Pandas performance"\ndescription: "d"\n---\n\nbody\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "script/daily_post/dupe_check.py",
         "--title", "Kubernetes operator patterns", "--posts-dir", str(posts)],
        cwd=REPO, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_cli_exits_one_and_emits_json_for_a_duplicate(tmp_path: Path):
    posts = tmp_path / "_posts"
    posts.mkdir()
    (posts / "2025-01-01-pandas.md").write_text(
        '---\ntitle: "Pandas performance tuning"\n'
        'description: "Making Pandas dataframes faster"\n---\n\nbody\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "script/daily_post/dupe_check.py",
         "--title", "Pandas performance tuning",
         "--posts-dir", str(posts), "--json"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["duplicate"] is True
    assert payload["matches"][0]["slug"] == "pandas"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest script/daily_post/tests/test_dupe_check.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'script.daily_post.dupe_check'`

- [ ] **Step 3: Write the implementation**

Create `script/daily_post/dupe_check.py`:

```python
#!/usr/bin/env python3
"""Score a candidate topic against every published post.

    python3 script/daily_post/dupe_check.py --title "Kafka to NATS" --json

Exits 0 when the topic is viable, 1 when it duplicates an existing post. The
daily pipeline treats exit 1 as a hard block and moves to the next candidate.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from script.daily_post.corpus import Post, load_posts
from script.daily_post.similarity import cosine, tfidf_vectors, vector_for

DEFAULT_THRESHOLD = 0.55
REPO = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Match:
    slug: str
    title: str
    score: float


def rank(candidate: str, posts: list[Post], top: int = 5) -> list[Match]:
    """The `top` posts most similar to `candidate`, most similar first."""
    if not posts:
        return []

    vectors, idf = tfidf_vectors([p.text for p in posts])
    candidate_vector = vector_for(candidate, idf)

    matches = [
        Match(slug=post.slug, title=post.title, score=cosine(candidate_vector, vector))
        for post, vector in zip(posts, vectors)
    ]
    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:top]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--angle", default="", help="one-line description of the angle")
    parser.add_argument("--posts-dir", default=str(REPO / "_posts"))
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    posts = load_posts(Path(args.posts_dir))
    candidate = f"{args.title} {args.angle}".strip()
    matches = rank(candidate, posts, top=args.top)

    top_score = matches[0].score if matches else 0.0
    duplicate = top_score >= args.threshold

    if args.as_json:
        print(json.dumps({
            "candidate": candidate,
            "threshold": args.threshold,
            "duplicate": duplicate,
            "matches": [asdict(m) for m in matches],
        }, indent=2))
    else:
        verdict = "DUPLICATE" if duplicate else "OK"
        print(f"{verdict}  top score {top_score:.3f} (threshold {args.threshold})")
        for m in matches:
            print(f"  {m.score:.3f}  {m.slug}  — {m.title}")

    return 1 if duplicate else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest script/daily_post/tests/test_dupe_check.py -v`
Expected: PASS, 7 tests.

- [ ] **Step 5: Tune the threshold if calibration fails**

If `test_threshold_flags_a_real_near_duplicate_and_spares_a_distinct_topic` fails, do **not** weaken the assertion. Print the real numbers first:

```bash
python3 script/daily_post/dupe_check.py --title "Migrating from Kafka to NATS" --top 5
python3 script/daily_post/dupe_check.py --title "Postgres connection pooling under sustained load" --top 5
```

Pick a `DEFAULT_THRESHOLD` that sits between the two observed scores, update the constant, and record both numbers in a comment above it so the next person knows what it was calibrated against.

- [ ] **Step 6: Commit**

```bash
git add script/daily_post/dupe_check.py script/daily_post/tests/test_dupe_check.py
git commit -m "Add duplicate topic check calibrated against the archive"
```

---

### Task 4: Topic queue

**Files:**
- Create: `_data/topic_queue.yml`
- Create: `script/daily_post/queue.py`
- Test: `script/daily_post/tests/test_queue.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `@dataclass class Topic: id: str; title: str; angle: str; category: str; tags: list[str]; status: str; claimed_on: str | None; slug: str | None`
  - `VALID_STATUSES = ("queued", "claimed", "published", "rejected")`
  - `load_topics(path: Path) -> list[Topic]`
  - `next_queued(topics: list[Topic]) -> Topic | None`
  - `claim(path: Path, topic_id: str, on: str) -> Topic`
  - `mark(path: Path, topic_id: str, status: str, slug: str | None = None) -> Topic`
  - `QueueError(Exception)`

- [ ] **Step 1: Write the failing test**

Create `script/daily_post/tests/test_queue.py`:

```python
from pathlib import Path

import pytest
import yaml

from script.daily_post.queue import (
    QueueError,
    claim,
    load_topics,
    mark,
    next_queued,
)

QUEUE = """topics:
  - id: nats-jetstream-backpressure
    title: "JetStream backpressure in practice"
    angle: "What happens when consumers fall behind"
    category: distributed-systems
    tags: [NATS, Distributed Systems]
    status: published
    claimed_on: "2026-09-10"
    slug: jetstream-backpressure
  - id: pg-connection-pooling
    title: "Postgres connection pooling under load"
    angle: "pgbouncer modes and when each one bites"
    category: databases
    tags: [PostgreSQL]
    status: queued
  - id: python-free-threading
    title: "Free-threaded Python in anger"
    angle: "Measuring the GIL removal on real workloads"
    category: python
    tags: [Python]
    status: queued
"""


@pytest.fixture
def queue_path(tmp_path: Path) -> Path:
    p = tmp_path / "topic_queue.yml"
    p.write_text(QUEUE, encoding="utf-8")
    return p


def test_load_topics_reads_every_entry(queue_path: Path):
    assert len(load_topics(queue_path)) == 3


def test_load_topics_defaults_status_to_queued(tmp_path: Path):
    p = tmp_path / "q.yml"
    p.write_text(
        'topics:\n  - id: x\n    title: "T"\n    angle: "A"\n'
        "    category: python\n    tags: [Python]\n",
        encoding="utf-8",
    )
    assert load_topics(p)[0].status == "queued"


def test_load_topics_rejects_an_unknown_status(tmp_path: Path):
    p = tmp_path / "q.yml"
    p.write_text(
        'topics:\n  - id: x\n    title: "T"\n    angle: "A"\n'
        "    category: python\n    tags: [Python]\n    status: banana\n",
        encoding="utf-8",
    )
    with pytest.raises(QueueError, match="banana"):
        load_topics(p)


def test_load_topics_rejects_an_unknown_category(tmp_path: Path):
    p = tmp_path / "q.yml"
    p.write_text(
        'topics:\n  - id: x\n    title: "T"\n    angle: "A"\n'
        "    category: knitting\n    tags: [Python]\n",
        encoding="utf-8",
    )
    with pytest.raises(QueueError, match="knitting"):
        load_topics(p)


def test_load_topics_rejects_duplicate_ids(tmp_path: Path):
    p = tmp_path / "q.yml"
    entry = (
        '  - id: dup\n    title: "T"\n    angle: "A"\n'
        "    category: python\n    tags: [Python]\n"
    )
    p.write_text("topics:\n" + entry + entry, encoding="utf-8")
    with pytest.raises(QueueError, match="dup"):
        load_topics(p)


def test_load_topics_on_a_missing_file_returns_empty(tmp_path: Path):
    assert load_topics(tmp_path / "absent.yml") == []


def test_next_queued_skips_non_queued_entries(queue_path: Path):
    topic = next_queued(load_topics(queue_path))
    assert topic is not None
    assert topic.id == "pg-connection-pooling"


def test_next_queued_returns_none_when_nothing_is_queued(queue_path: Path):
    topics = load_topics(queue_path)
    for t in topics:
        t.status = "published"
    assert next_queued(topics) is None


def test_claim_persists_status_and_date(queue_path: Path):
    claim(queue_path, "pg-connection-pooling", on="2026-09-14")
    data = yaml.safe_load(queue_path.read_text(encoding="utf-8"))
    entry = next(t for t in data["topics"] if t["id"] == "pg-connection-pooling")
    assert entry["status"] == "claimed"
    assert entry["claimed_on"] == "2026-09-14"


def test_claim_preserves_the_other_entries(queue_path: Path):
    claim(queue_path, "pg-connection-pooling", on="2026-09-14")
    topics = load_topics(queue_path)
    assert [t.id for t in topics] == [
        "nats-jetstream-backpressure",
        "pg-connection-pooling",
        "python-free-threading",
    ]
    assert topics[2].status == "queued"


def test_claim_on_an_unknown_id_raises(queue_path: Path):
    with pytest.raises(QueueError, match="nope"):
        claim(queue_path, "nope", on="2026-09-14")


def test_claim_on_an_already_claimed_topic_raises(queue_path: Path):
    claim(queue_path, "pg-connection-pooling", on="2026-09-14")
    with pytest.raises(QueueError, match="not queued"):
        claim(queue_path, "pg-connection-pooling", on="2026-09-15")


def test_mark_records_the_published_slug(queue_path: Path):
    mark(queue_path, "pg-connection-pooling", "published", slug="pg-pooling")
    entry = next(t for t in load_topics(queue_path) if t.id == "pg-connection-pooling")
    assert entry.status == "published"
    assert entry.slug == "pg-pooling"


def test_mark_rejects_an_invalid_status(queue_path: Path):
    with pytest.raises(QueueError, match="banana"):
        mark(queue_path, "pg-connection-pooling", "banana")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest script/daily_post/tests/test_queue.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'script.daily_post.queue'`

- [ ] **Step 3: Write the implementation**

Create `script/daily_post/queue.py`:

```python
#!/usr/bin/env python3
"""Read and update the daily post topic queue at `_data/topic_queue.yml`.

The queue is committed state: the operator edits it by hand to steer what gets
written, and the pipeline writes back claim and publish status. Every mutation
rewrites the whole file, which is safe at this size and keeps the diff readable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

VALID_STATUSES = ("queued", "claimed", "published", "rejected")

CATEGORIES = (
    "ai-engineering",
    "databases",
    "distributed-systems",
    "infrastructure",
    "python",
    "software-engineering",
    "web-development",
)


class QueueError(Exception):
    """The queue file is malformed, or the requested transition is not legal."""


@dataclass
class Topic:
    id: str
    title: str
    angle: str
    category: str
    tags: list[str] = field(default_factory=list)
    status: str = "queued"
    claimed_on: str | None = None
    slug: str | None = None


def load_topics(path: Path) -> list[Topic]:
    """Every topic in the queue. A missing file is an empty queue, not an error."""
    if not path.is_file():
        return []

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = raw.get("topics") or []

    topics: list[Topic] = []
    seen: set[str] = set()
    for entry in entries:
        topic = Topic(
            id=str(entry["id"]),
            title=str(entry["title"]),
            angle=str(entry.get("angle") or ""),
            category=str(entry.get("category") or ""),
            tags=list(entry.get("tags") or []),
            status=str(entry.get("status") or "queued"),
            claimed_on=entry.get("claimed_on"),
            slug=entry.get("slug"),
        )
        if topic.id in seen:
            raise QueueError(f"duplicate topic id: {topic.id}")
        if topic.status not in VALID_STATUSES:
            raise QueueError(
                f"{topic.id}: unknown status {topic.status!r}; "
                f"allowed: {list(VALID_STATUSES)}"
            )
        if topic.category not in CATEGORIES:
            raise QueueError(
                f"{topic.id}: unknown category {topic.category!r}; "
                f"allowed: {list(CATEGORIES)}"
            )
        seen.add(topic.id)
        topics.append(topic)
    return topics


def next_queued(topics: list[Topic]) -> Topic | None:
    """The first topic still waiting to be written, or None if the queue is dry."""
    for topic in topics:
        if topic.status == "queued":
            return topic
    return None


def claim(path: Path, topic_id: str, on: str) -> Topic:
    """Move a queued topic to `claimed`, stamping the run date.

    Claiming is what stops a second run on the same day from picking the same
    topic, so it must happen before any research work begins.
    """
    topics = load_topics(path)
    topic = _find(topics, topic_id)
    if topic.status != "queued":
        raise QueueError(f"{topic_id}: not queued (status is {topic.status!r})")
    topic.status = "claimed"
    topic.claimed_on = on
    _write(path, topics)
    return topic


def mark(path: Path, topic_id: str, status: str, slug: str | None = None) -> Topic:
    """Set a topic's terminal status, optionally recording the published slug."""
    if status not in VALID_STATUSES:
        raise QueueError(f"unknown status {status!r}; allowed: {list(VALID_STATUSES)}")
    topics = load_topics(path)
    topic = _find(topics, topic_id)
    topic.status = status
    if slug is not None:
        topic.slug = slug
    _write(path, topics)
    return topic


def _find(topics: list[Topic], topic_id: str) -> Topic:
    for topic in topics:
        if topic.id == topic_id:
            return topic
    raise QueueError(f"no topic with id {topic_id!r}")


def _write(path: Path, topics: list[Topic]) -> None:
    payload = {"topics": [_entry(t) for t in topics]}
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )


def _entry(topic: Topic) -> dict:
    """Serialise a topic, omitting keys that are still unset to keep the file clean."""
    entry = {
        "id": topic.id,
        "title": topic.title,
        "angle": topic.angle,
        "category": topic.category,
        "tags": topic.tags,
        "status": topic.status,
    }
    if topic.claimed_on:
        entry["claimed_on"] = topic.claimed_on
    if topic.slug:
        entry["slug"] = topic.slug
    return entry
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest script/daily_post/tests/test_queue.py -v`
Expected: PASS, 14 tests.

- [ ] **Step 5: Create the real queue file**

Create `_data/topic_queue.yml` with three seed topics so the first runs have something to write. Categories must come from the fixed seven; tags should reuse existing vocabulary:

```yaml
# Topics for the daily post pipeline.
#
# The pipeline takes the first entry with `status: queued`, marks it `claimed`,
# and writes it. When the queue is dry it discovers a topic from the web instead,
# so keeping entries here is how you steer what gets written.
#
# status: queued | claimed | published | rejected
# category: one of ai-engineering, databases, distributed-systems, infrastructure,
#           python, software-engineering, web-development
topics:
  - id: pg-connection-pooling
    title: "Postgres connection pooling under sustained load"
    angle: "pgbouncer's three pooling modes, what each one breaks, and how to pick"
    category: databases
    tags: [PostgreSQL, Performance]
    status: queued

  - id: python-free-threading
    title: "Free-threaded Python on a real workload"
    angle: "Measuring what GIL removal actually buys on a CPU-bound service"
    category: python
    tags: [Python, Performance]
    status: queued

  - id: otel-span-cardinality
    title: "The span attribute that blew up your observability bill"
    angle: "Why high-cardinality attributes cost more than high span volume"
    category: infrastructure
    tags: [Observability, Performance]
    status: queued
```

- [ ] **Step 6: Verify the real queue file parses**

Run:
```bash
python3 -c "
from pathlib import Path
from script.daily_post.queue import load_topics, next_queued
topics = load_topics(Path('_data/topic_queue.yml'))
print(len(topics), 'topics;  next:', next_queued(topics).id)
"
```
Expected: `3 topics;  next: pg-connection-pooling`

- [ ] **Step 7: Commit**

```bash
git add script/daily_post/queue.py script/daily_post/tests/test_queue.py _data/topic_queue.yml
git commit -m "Add topic queue with seed topics for the daily post pipeline"
```

---

### Task 5: Banner generation

**Files:**
- Create: `script/daily_post/make_banner.py`
- Test: `script/daily_post/tests/test_make_banner.py`

**Interfaces:**
- Consumes: `CATEGORIES` from `script.daily_post.queue` (Task 4).
- Produces:
  - `CATEGORY_COLORS: dict[str, tuple[tuple[int,int,int], tuple[int,int,int]]]` — one (start, end) RGB gradient pair per category.
  - `render_banner(title: str, category: str, out_dir: Path) -> tuple[Path, Path]` returning `(banner_path, teaser_path)`.
  - `wrap_title(title: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int = 4) -> list[str]`
  - `resolve_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont`
  - CLI: `python3 script/daily_post/make_banner.py --title T --category C --slug S [--assets-dir assets/images]`

Verified on this machine: Pillow 10.4.0; Inter at `/usr/share/fonts/opentype/inter/Inter-Bold.otf`; DejaVu fallback at `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`.

- [ ] **Step 1: Write the failing test**

Create `script/daily_post/tests/test_make_banner.py`:

```python
from pathlib import Path

import pytest
from PIL import Image

from script.daily_post.make_banner import (
    CATEGORY_COLORS,
    render_banner,
    resolve_font,
    wrap_title,
)
from script.daily_post.queue import CATEGORIES


def test_every_category_has_a_gradient():
    assert set(CATEGORY_COLORS) == set(CATEGORIES)


def test_render_banner_writes_both_derivatives(tmp_path: Path):
    banner, teaser = render_banner("A Short Title", "python", tmp_path)
    assert banner.name == "banner.webp"
    assert teaser.name == "teaser.webp"
    assert banner.is_file() and teaser.is_file()


def test_banner_is_1600px_wide_webp(tmp_path: Path):
    banner, _ = render_banner("A Short Title", "python", tmp_path)
    with Image.open(banner) as im:
        assert im.width == 1600
        assert im.format == "WEBP"


def test_teaser_is_640px_wide_webp(tmp_path: Path):
    _, teaser = render_banner("A Short Title", "python", tmp_path)
    with Image.open(teaser) as im:
        assert im.width == 640
        assert im.format == "WEBP"


def test_render_banner_creates_a_missing_output_directory(tmp_path: Path):
    out = tmp_path / "assets" / "images" / "some-slug"
    banner, _ = render_banner("Title", "databases", out)
    assert banner.parent == out


def test_render_banner_rejects_an_unknown_category(tmp_path: Path):
    with pytest.raises(ValueError, match="knitting"):
        render_banner("Title", "knitting", tmp_path)


def test_different_categories_produce_different_images(tmp_path: Path):
    a, _ = render_banner("Same Title", "python", tmp_path / "a")
    b, _ = render_banner("Same Title", "databases", tmp_path / "b")
    assert a.read_bytes() != b.read_bytes()


def test_render_is_deterministic_for_the_same_input(tmp_path: Path):
    a, _ = render_banner("Same Title", "python", tmp_path / "a")
    b, _ = render_banner("Same Title", "python", tmp_path / "b")
    assert a.read_bytes() == b.read_bytes()


def test_a_very_long_title_still_renders(tmp_path: Path):
    title = "Why " + "extremely " * 20 + "long titles must not overflow the banner"
    banner, _ = render_banner(title, "infrastructure", tmp_path)
    assert banner.is_file()


def test_wrap_title_breaks_on_words_within_the_line_budget():
    font = resolve_font(80)
    lines = wrap_title("one two three four five six seven eight", font, max_width=400)
    assert len(lines) > 1
    assert all(line.strip() for line in lines)


def test_wrap_title_caps_the_line_count_and_ellipsises():
    font = resolve_font(80)
    lines = wrap_title(" ".join(["word"] * 60), font, max_width=400, max_lines=4)
    assert len(lines) == 4
    assert lines[-1].endswith("…")


def test_resolve_font_returns_a_usable_font():
    font = resolve_font(48)
    assert font.getbbox("Test") is not None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest script/daily_post/tests/test_make_banner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'script.daily_post.make_banner'`

- [ ] **Step 3: Write the implementation**

Create `script/daily_post/make_banner.py`:

```python
#!/usr/bin/env python3
"""Render a post banner from its title and category.

    python3 script/daily_post/make_banner.py --title "..." --category python --slug my-post

Writes `banner.webp` (1600px, the post hero) and `teaser.webp` (640px, the archive
card) into `assets/images/<slug>/`, matching what `script/optimize-images/to_webp.py`
produces for hand-made art.

Pillow only: cairosvg, rsvg-convert, ImageMagick and cwebp are all absent on the
target machine, and Pillow writes WebP natively.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from script.daily_post.queue import CATEGORIES

REPO = Path(__file__).resolve().parents[2]

BANNER_W, BANNER_H = 1600, 900
TEASER_W = 640
Q_BANNER, Q_TEASER = 80, 76

# Font candidates in preference order. Inter matches the site; DejaVu is the
# fallback that exists on essentially every Linux box, so a machine without Inter
# still renders rather than crashing the daily run.
FONT_CANDIDATES = (
    "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)

# One gradient per category, so a reader recognises the beat before reading the title.
CATEGORY_COLORS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "ai-engineering": ((26, 16, 56), (92, 46, 145)),
    "databases": ((10, 34, 44), (18, 92, 102)),
    "distributed-systems": ((12, 22, 48), (34, 74, 140)),
    "infrastructure": ((28, 24, 18), (120, 82, 34)),
    "python": ((14, 30, 40), (32, 96, 118)),
    "software-engineering": ((24, 20, 32), (86, 62, 116)),
    "web-development": ((34, 16, 28), (138, 48, 86)),
}

assert set(CATEGORY_COLORS) == set(CATEGORIES), "category colour map is out of sync"


def resolve_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """The first available font candidate at `size`, or Pillow's built-in default."""
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size)


def wrap_title(
    title: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    max_lines: int = 4,
) -> list[str]:
    """Greedy word wrap, truncated with an ellipsis past `max_lines`.

    A word longer than the line budget is placed on its own line rather than
    looping forever trying to fit it.
    """
    words = title.split()
    lines: list[str] = []
    current = ""

    for word in words:
        trial = f"{current} {word}".strip()
        if font.getbbox(trial)[2] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
        if len(lines) == max_lines:
            break

    if current and len(lines) < max_lines:
        lines.append(current)

    if len(lines) == max_lines:
        consumed = len(" ".join(lines).split())
        if consumed < len(words):
            lines[-1] = _ellipsise(lines[-1], font, max_width)

    return lines


def _ellipsise(line: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    text = line.rstrip() + "…"
    while font.getbbox(text)[2] > max_width and " " in text:
        text = text.rsplit(" ", 1)[0].rstrip() + "…"
    return text


def _gradient(size: tuple[int, int], start: tuple[int, int, int],
              end: tuple[int, int, int]) -> Image.Image:
    """A vertical linear gradient, drawn one row at a time."""
    width, height = size
    base = Image.new("RGB", size, start)
    draw = ImageDraw.Draw(base)
    for y in range(height):
        t = y / max(height - 1, 1)
        draw.line(
            [(0, y), (width, y)],
            fill=tuple(round(s + (e - s) * t) for s, e in zip(start, end)),
        )
    return base


def render_banner(title: str, category: str, out_dir: Path) -> tuple[Path, Path]:
    """Write banner.webp and teaser.webp into `out_dir`. Returns both paths."""
    if category not in CATEGORY_COLORS:
        raise ValueError(
            f"unknown category {category!r}; allowed: {sorted(CATEGORY_COLORS)}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    start, end = CATEGORY_COLORS[category]
    image = _gradient((BANNER_W, BANNER_H), start, end)
    draw = ImageDraw.Draw(image)

    margin = 120
    text_width = BANNER_W - 2 * margin

    title_font = resolve_font(96)
    lines = wrap_title(title, title_font, text_width)
    line_height = round(96 * 1.22)

    block_height = line_height * len(lines)
    y = (BANNER_H - block_height) // 2
    for line in lines:
        draw.text((margin, y), line, font=title_font, fill=(255, 255, 255))
        y += line_height

    # Category label under the title, tracked out and dimmed so it reads as metadata.
    label_font = resolve_font(34)
    draw.text(
        (margin, y + 28),
        category.replace("-", " ").upper(),
        font=label_font,
        fill=(255, 255, 255, 200),
    )

    banner_path = out_dir / "banner.webp"
    image.save(banner_path, "WEBP", quality=Q_BANNER, method=6)

    teaser_height = round(BANNER_H * TEASER_W / BANNER_W)
    teaser_path = out_dir / "teaser.webp"
    image.resize((TEASER_W, teaser_height), Image.LANCZOS).save(
        teaser_path, "WEBP", quality=Q_TEASER, method=6
    )

    return banner_path, teaser_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--category", required=True, choices=sorted(CATEGORY_COLORS))
    parser.add_argument("--slug", required=True)
    parser.add_argument("--assets-dir", default=str(REPO / "assets" / "images"))
    args = parser.parse_args()

    banner, teaser = render_banner(
        args.title, args.category, Path(args.assets_dir) / args.slug
    )
    print(banner.relative_to(REPO) if banner.is_relative_to(REPO) else banner)
    print(teaser.relative_to(REPO) if teaser.is_relative_to(REPO) else teaser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest script/daily_post/tests/test_make_banner.py -v`
Expected: PASS, 12 tests.

- [ ] **Step 5: Eyeball one real banner**

Automated tests confirm the file is a 1600px WebP; they cannot confirm it looks acceptable. Render one and look at it:

```bash
python3 script/daily_post/make_banner.py \
  --title "Postgres connection pooling under sustained load" \
  --category databases --slug _banner_preview \
  --assets-dir /tmp/banner-preview
```

Open `/tmp/banner-preview/_banner_preview/banner.webp`. Check: title fits with margin to spare, text is legible against the gradient, nothing is clipped. Adjust `margin`, font size, or `CATEGORY_COLORS` if not. Do not commit the preview.

- [ ] **Step 6: Commit**

```bash
git add script/daily_post/make_banner.py script/daily_post/tests/test_make_banner.py
git commit -m "Add Pillow banner generation for daily posts"
```

---

### Task 6: Preflight script

**Files:**
- Create: `script/daily_post/preflight.sh` (executable)
- Test: `script/daily_post/tests/test_preflight.py`

**Interfaces:**
- Consumes: existing `script/check_frontmatter.py`.
- Produces: `script/daily_post/preflight.sh [--fast]`, exit `0` green / `1` red. `--fast` runs only the front matter check, skipping the Jekyll build and htmlproofer.

Preflight runs exactly what CI runs, so the pipeline never pushes a branch it already knows will fail: `check_frontmatter.py`, `bundle exec jekyll build --trace`, then htmlproofer with CI's flags.

- [ ] **Step 1: Write the failing test**

Create `script/daily_post/tests/test_preflight.py`:

```python
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PREFLIGHT = REPO / "script" / "daily_post" / "preflight.sh"


def run_preflight(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(PREFLIGHT), *args], cwd=REPO, capture_output=True, text=True
    )


def test_preflight_script_exists_and_is_executable():
    assert PREFLIGHT.is_file()
    assert PREFLIGHT.stat().st_mode & 0o111, "preflight.sh must be chmod +x"


def test_fast_mode_passes_on_the_clean_repo():
    result = run_preflight("--fast")
    assert result.returncode == 0, result.stdout + result.stderr


def test_fast_mode_fails_on_a_post_that_breaks_the_contract():
    """A post with no description must make preflight red."""
    bad = REPO / "_posts" / "2099-01-01-preflight-self-test.md"
    bad.write_text(
        '---\ntitle: "Preflight self test"\ntags:\n    - Python\n'
        "categories:\n    - python\n---\n\nBody.\n",
        encoding="utf-8",
    )
    try:
        result = run_preflight("--fast")
        assert result.returncode != 0
        assert "description" in (result.stdout + result.stderr)
    finally:
        bad.unlink()


@pytest.mark.slow
def test_full_preflight_builds_the_site():
    if shutil.which("bundle") is None:
        pytest.skip("bundler not installed")
    result = run_preflight()
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest script/daily_post/tests/test_preflight.py -v`
Expected: FAIL — the script does not exist.

- [ ] **Step 3: Write the implementation**

Create `script/daily_post/preflight.sh`:

```bash
#!/usr/bin/env bash
# Run everything CI runs, locally, before the daily pipeline pushes a branch.
#
#   script/daily_post/preflight.sh          front matter + jekyll build + htmlproofer
#   script/daily_post/preflight.sh --fast   front matter only
#
# Exits 0 when green, 1 when red. A red preflight is a hard stop for the pipeline:
# pushing a branch that CI will reject just moves the failure somewhere noisier.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"

FAST=0
[[ "${1:-}" == "--fast" ]] && FAST=1

echo "==> front matter contract"
python3 script/check_frontmatter.py

if [[ "$FAST" -eq 1 ]]; then
  echo "==> preflight OK (fast mode: build and link checks skipped)"
  exit 0
fi

if ! command -v bundle >/dev/null 2>&1; then
  echo "preflight: bundler not found; run 'make install' first" >&2
  exit 1
fi

echo "==> jekyll build"
JEKYLL_ENV=production bundle exec jekyll build --trace

echo "==> internal links and images"
# External links are deliberately unchecked, matching .github/workflows/ci.yml:
# third-party sites rate-limit and go down, which would fail runs for unrelated reasons.
bundle exec htmlproofer ./_site \
  --disable-external \
  --checks Links,Images,Scripts \
  --ignore-urls "/^#/" \
  --no-enforce-https \
  --swap-urls "^/:/"

echo "==> preflight OK"
```

Then make it executable:

```bash
chmod +x script/daily_post/preflight.sh
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest script/daily_post/tests/test_preflight.py -v -m "not slow"`
Expected: PASS, 3 tests (the slow build test is deselected).

- [ ] **Step 5: Run the full preflight once**

Run: `python3 -m pytest script/daily_post/tests/test_preflight.py -v`
Expected: PASS, 4 tests. This one builds the whole site and takes minutes. If `bundle` is missing it skips rather than fails — run `make install` first if you want real coverage here.

- [ ] **Step 6: Commit**

```bash
git add script/daily_post/preflight.sh script/daily_post/tests/test_preflight.py
git commit -m "Add preflight script mirroring CI for the daily post pipeline"
```

---

### Task 7: Daily entry point (`run.sh`)

**Files:**
- Create: `script/daily_post/run.sh` (executable)
- Test: `script/daily_post/tests/test_run_sh.py`

**Interfaces:**
- Consumes: nothing from earlier tasks at runtime; it shells out to `claude`.
- Produces — **this is the contract Task 8's skill must satisfy**:
  - `run.sh` invokes `claude -p "/daily-post"` from the repo root.
  - The skill writes a single token to the file named by the `DAILY_POST_STATUS` environment variable. Tokens: `published`, `blocked`, `no-topic`, `preflight-failed`.
  - `run.sh` maps that token to its exit code: `published`→`0`, `blocked`→`10`, `no-topic`→`20`, anything else or a missing file→`50`.
  - Other exit codes come from `run.sh` itself: `30` already ran today, `40` precondition failure.
  - `DAILY_POST_REPO` overrides the repo path (used by the tests).
  - Logs to `.git/daily-post-logs/<date>.log`, which git never tracks.

- [ ] **Step 1: Write the failing test**

Create `script/daily_post/tests/test_run_sh.py`. The tests build a throwaway git repo and put stub `claude`/`gh` executables on `PATH`, so no network, no model, and no real PR:

```python
import os
import subprocess
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RUN_SH = REPO / "script" / "daily_post" / "run.sh"
TODAY = date.today().isoformat()


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "_posts").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "master"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    return repo


@pytest.fixture
def stub_bin(tmp_path: Path) -> Path:
    """A PATH directory holding fake `gh` and `claude` executables."""
    d = tmp_path / "bin"
    d.mkdir()
    write_stub(d, "gh", "exit 0")
    write_stub(d, "claude", 'echo published > "$DAILY_POST_STATUS"; exit 0')
    return d


def write_stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text(f"#!/usr/bin/env bash\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


def run(repo: Path, stub_bin: Path, **env_extra) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "PATH": f"{stub_bin}:{os.environ['PATH']}",
        "DAILY_POST_REPO": str(repo),
        "DAILY_POST_SKIP_PULL": "1",
        **env_extra,
    }
    return subprocess.run(
        [str(RUN_SH)], capture_output=True, text=True, env=env
    )


def test_run_script_exists_and_is_executable():
    assert RUN_SH.is_file()
    assert RUN_SH.stat().st_mode & 0o111, "run.sh must be chmod +x"


def test_exit_0_when_the_skill_reports_published(fake_repo: Path, stub_bin: Path):
    result = run(fake_repo, stub_bin)
    assert result.returncode == 0, result.stdout + result.stderr


def test_exit_10_when_the_skill_reports_blocked(fake_repo: Path, stub_bin: Path):
    write_stub(stub_bin, "claude", 'echo blocked > "$DAILY_POST_STATUS"; exit 0')
    assert run(fake_repo, stub_bin).returncode == 10


def test_exit_20_when_the_skill_reports_no_topic(fake_repo: Path, stub_bin: Path):
    write_stub(stub_bin, "claude", 'echo no-topic > "$DAILY_POST_STATUS"; exit 0')
    assert run(fake_repo, stub_bin).returncode == 20


def test_exit_50_when_the_skill_writes_no_status(fake_repo: Path, stub_bin: Path):
    write_stub(stub_bin, "claude", "exit 0")
    assert run(fake_repo, stub_bin).returncode == 50


def test_exit_50_when_the_skill_reports_preflight_failed(fake_repo: Path, stub_bin: Path):
    write_stub(stub_bin, "claude", 'echo preflight-failed > "$DAILY_POST_STATUS"; exit 0')
    assert run(fake_repo, stub_bin).returncode == 50


def test_exit_30_when_a_post_for_today_already_exists(fake_repo: Path, stub_bin: Path):
    (fake_repo / "_posts" / f"{TODAY}-already-written.md").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=fake_repo, check=True)
    subprocess.run(["git", "commit", "-qm", "post"], cwd=fake_repo, check=True)
    result = run(fake_repo, stub_bin)
    assert result.returncode == 30
    assert "already" in (result.stdout + result.stderr).lower()


def test_exit_30_when_a_branch_for_today_already_exists(fake_repo: Path, stub_bin: Path):
    subprocess.run(
        ["git", "branch", f"daily-post/{TODAY}-something"], cwd=fake_repo, check=True
    )
    assert run(fake_repo, stub_bin).returncode == 30


def test_exit_40_when_gh_is_missing(fake_repo: Path, stub_bin: Path):
    (stub_bin / "gh").unlink()
    result = run(fake_repo, stub_bin, PATH=f"{stub_bin}")
    assert result.returncode == 40
    assert "gh" in (result.stdout + result.stderr)


def test_exit_40_when_gh_is_not_authenticated(fake_repo: Path, stub_bin: Path):
    write_stub(stub_bin, "gh", "exit 1")
    result = run(fake_repo, stub_bin)
    assert result.returncode == 40
    assert "authenticate" in (result.stdout + result.stderr).lower()


def test_exit_40_when_the_working_tree_is_dirty(fake_repo: Path, stub_bin: Path):
    (fake_repo / "README.md").write_text("changed", encoding="utf-8")
    result = run(fake_repo, stub_bin)
    assert result.returncode == 40
    assert "clean" in (result.stdout + result.stderr).lower()


def test_the_run_is_logged(fake_repo: Path, stub_bin: Path):
    run(fake_repo, stub_bin)
    log = fake_repo / ".git" / "daily-post-logs" / f"{TODAY}.log"
    assert log.is_file()


def test_the_skill_is_invoked_with_the_daily_post_command(fake_repo: Path, stub_bin: Path):
    write_stub(
        stub_bin, "claude",
        'echo "$@" > "$DAILY_POST_REPO/args.txt"; echo published > "$DAILY_POST_STATUS"',
    )
    run(fake_repo, stub_bin)
    assert "/daily-post" in (fake_repo / "args.txt").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest script/daily_post/tests/test_run_sh.py -v`
Expected: FAIL — the script does not exist.

- [ ] **Step 3: Write the implementation**

Create `script/daily_post/run.sh`:

```bash
#!/usr/bin/env bash
# Daily entry point for the blog post pipeline. Point your scheduler at this.
#
#   script/daily_post/run.sh
#
# Exit codes:
#   0   post written, gates green, PR open
#   10  gates still blocked after two revisions; draft PR open
#   20  no viable topic after three attempts
#   30  already ran today; nothing done
#   40  precondition failed (gh missing or unauthenticated, dirty tree, stale master)
#   50  pipeline failure (preflight red, or the skill reported nothing)
#
# Environment:
#   DAILY_POST_REPO       repo path (default: two levels up from this script)
#   DAILY_POST_SKIP_PULL  set to 1 to skip the git pull (tests, offline runs)
set -uo pipefail

REPO="${DAILY_POST_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$REPO" || { echo "run.sh: cannot cd to $REPO" >&2; exit 40; }

TODAY="$(date +%F)"
LOG_DIR="$REPO/.git/daily-post-logs"
LOG="$LOG_DIR/$TODAY.log"
mkdir -p "$LOG_DIR"

log() { echo "[$(date +%T)] $*" | tee -a "$LOG"; }
die() { log "PRECONDITION FAILED: $*"; exit 40; }

# --- preconditions, checked before any expensive work -----------------------
command -v git >/dev/null 2>&1 || die "git is not installed"
command -v claude >/dev/null 2>&1 || die "claude is not installed"
command -v gh >/dev/null 2>&1 || die "gh is not installed; the PR step needs it"
gh auth status >/dev/null 2>&1 || die "gh cannot authenticate; run 'gh auth login'"

[[ -z "$(git status --porcelain)" ]] || die "working tree is not clean"

if [[ "${DAILY_POST_SKIP_PULL:-0}" != "1" ]]; then
  log "pulling master"
  git pull --ff-only --quiet origin master >>"$LOG" 2>&1 \
    || die "could not fast-forward master"
fi

# --- idempotency ------------------------------------------------------------
# A double-fire, or a manual run on top of a scheduled one, must not write a
# second post for the same day.
if compgen -G "_posts/$TODAY-*.md" >/dev/null; then
  log "a post for $TODAY already exists; nothing to do"
  exit 30
fi

if git branch --list "daily-post/$TODAY-*" | grep -q .; then
  log "a daily-post branch for $TODAY already exists; nothing to do"
  exit 30
fi

# --- run the pipeline -------------------------------------------------------
STATUS_FILE="$(mktemp)"
trap 'rm -f "$STATUS_FILE"' EXIT
export DAILY_POST_STATUS="$STATUS_FILE"

log "invoking the daily-post skill"
claude -p "/daily-post" >>"$LOG" 2>&1
CLAUDE_RC=$?
log "claude exited $CLAUDE_RC"

STATUS="$(tr -d '[:space:]' <"$STATUS_FILE" 2>/dev/null)"
log "pipeline status: ${STATUS:-<none>}"

case "$STATUS" in
  published) log "PR opened; review and merge"; exit 0 ;;
  blocked)   log "gates blocked; draft PR opened with the gate report"; exit 10 ;;
  no-topic)  log "no viable topic; stock _data/topic_queue.yml"; exit 20 ;;
  preflight-failed)
             log "preflight was red; see $LOG"; exit 50 ;;
  *)         log "pipeline reported no status (claude rc=$CLAUDE_RC); see $LOG"; exit 50 ;;
esac
```

Then make it executable:

```bash
chmod +x script/daily_post/run.sh
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest script/daily_post/tests/test_run_sh.py -v`
Expected: PASS, 13 tests.

- [ ] **Step 5: Commit**

```bash
git add script/daily_post/run.sh script/daily_post/tests/test_run_sh.py
git commit -m "Add daily post entry point with preconditions and exit codes"
```

---

### Task 8: Skill reference files

**Files:**
- Create: `.claude/skills/daily-post/references/frontmatter.md`
- Create: `.claude/skills/daily-post/references/voice.md`
- Create: `.claude/skills/daily-post/references/sources.md`
- Create: `.claude/skills/daily-post/references/gates.md`
- Test: `script/daily_post/tests/test_skill_structure.py`

**Interfaces:**
- Consumes: `CATEGORIES` from `script.daily_post.queue` (Task 4) — the test cross-checks that the reference files list exactly those seven categories, so the prose cannot drift from the code.
- Produces: four reference files that `SKILL.md` (Task 9) links to by exact filename.

- [ ] **Step 1: Write the failing test**

Create `script/daily_post/tests/test_skill_structure.py`:

```python
from pathlib import Path

import pytest

from script.daily_post.queue import CATEGORIES

REPO = Path(__file__).resolve().parents[3]
SKILL_DIR = REPO / ".claude" / "skills" / "daily-post"
REFS = SKILL_DIR / "references"

REFERENCE_FILES = ("frontmatter.md", "voice.md", "sources.md", "gates.md")


@pytest.mark.parametrize("name", REFERENCE_FILES)
def test_reference_file_exists_and_is_not_a_stub(name: str):
    path = REFS / name
    assert path.is_file(), f"missing reference file: {name}"
    assert len(path.read_text(encoding="utf-8")) > 500, f"{name} looks like a stub"


def test_frontmatter_reference_lists_every_category():
    text = (REFS / "frontmatter.md").read_text(encoding="utf-8")
    for category in CATEGORIES:
        assert category in text, f"frontmatter.md does not mention {category}"


def test_frontmatter_reference_states_the_description_bounds():
    text = (REFS / "frontmatter.md").read_text(encoding="utf-8")
    assert "50" in text and "200" in text


def test_gates_reference_names_all_four_gates():
    text = (REFS / "gates.md").read_text(encoding="utf-8").lower()
    for gate in ("fact", "duplicate", "code", "voice"):
        assert gate in text, f"gates.md does not define the {gate} gate"


def test_gates_reference_states_the_revision_cap():
    text = (REFS / "gates.md").read_text(encoding="utf-8")
    assert "two" in text.lower() or "2" in text


@pytest.mark.parametrize("name", REFERENCE_FILES)
def test_reference_files_contain_no_placeholders(name: str):
    text = (REFS / name).read_text(encoding="utf-8")
    for marker in ("TODO", "TBD", "FIXME", "XXX"):
        assert marker not in text, f"{name} still contains {marker}"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest script/daily_post/tests/test_skill_structure.py -v`
Expected: FAIL — `missing reference file: frontmatter.md`

- [ ] **Step 3: Write `references/frontmatter.md`**

````markdown
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
  `software-engineering`, `web-development`.
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
````

- [ ] **Step 4: Write `references/voice.md`**

```markdown
# Voice

Rules derived from the existing archive. The voice gate in `gates.md` checks a draft
against this file, so it must describe what the blog actually sounds like — not a
generic style guide.

## Shape of a daily post

1,000–1,500 words. One idea, one worked example, one takeaway. Deliberately lighter
than the 2,000–3,300 word flagship posts, without being thinner in substance.

- **Cold open on a concrete failure or situation**, not a definition. The archive
  opens posts with lines like "At 02:13, your control plane sneezes." Never open with
  "In today's fast-paced world" or "X is a powerful tool that..."
- **H2 sections** carrying real claims as headings, not labels. "The failure mode:
  when retry becomes attack" beats "Background".
- **A worked example with runnable code**, commented, in the language the topic
  actually uses. Snippets are short and adapted for a reader to lift.
- **Tradeoffs stated plainly**, including when the thing being described is the wrong
  choice.
- **"Key takeaways"** as the closing H2, and **"Further reading"** with real links
  where sources were used.

## Register

Direct and technical, second person ("your control plane", "you end up copy-pasting"),
with occasional dry humor that never displaces the explanation. Bold for the term
being defined. Em dashes for asides. Short paragraphs — two to four sentences.

Write as an engineer who has run this in production, showing the reader what broke
and why. Not a vendor, not a tutorial mill.

## Hard blocks

The voice gate blocks the draft on any of these:

- **Filler openings** — "In today's fast-paced world", "In the ever-evolving landscape
  of", "Let's dive in", "Buckle up".
- **Hedging that carries no information** — "it's important to note that", "it's worth
  mentioning", "generally speaking", "in many cases" used to avoid committing.
- **Listicle padding** — a numbered list whose items are one sentence each and could
  be a paragraph; sections that exist to hit a count.
- **Restating the heading as the first sentence** of the section.
- **Conclusions that summarise without concluding** — a final section that repeats the
  post rather than saying what the reader should do.
- **Unearned superlatives** — "revolutionary", "game-changing", "seamless",
  "cutting-edge", "robust" used as filler.
- **The triad tic** — reflexively grouping everything into three adjectives or three
  clauses.
- **Vague attribution** — "studies show", "experts agree", "it is widely known"
  without a link.

## Two things that are not slop

Dry humor and strong opinions are in-voice. A gate that strips them produces exactly
the bland, hedged prose the gate exists to prevent. Block on the patterns listed
above, not on personality.
```

- [ ] **Step 5: Write `references/sources.md`**

````markdown
# Research sources

Used in Stage 2, and in Stage 1 when the topic queue is dry. Prefer primary sources:
specifications, release notes, source code, benchmarks, and papers over secondary
commentary. A blog post summarising a release is not a source — the release notes are.

## Per beat

| Category | Where to look |
| --- | --- |
| `distributed-systems` | Jepsen analyses, etcd/NATS/Kafka release notes, papers from OSDI/SOSP/NSDI, AWS Builders' Library |
| `ai-engineering` | arXiv cs.CL and cs.LG, model and framework release notes, inference-engine benchmarks, MCP and agent-protocol specs |
| `python` | CPython release notes and PEPs, `python/cpython` issues, major library changelogs (asyncio, Pydantic, Polars, uv) |
| `databases` | Postgres release notes and mailing lists, ClickHouse/DuckDB/SQLite changelogs, storage-engine papers |
| `infrastructure` | Kubernetes and CNCF project release notes, OpenTelemetry specs, eBPF and kernel documentation |
| `web-development` | Browser release notes, WHATWG/W3C specs, framework RFCs, HTTP/QUIC RFCs |
| `software-engineering` | Postmortems, language and tooling RFCs, engineering blogs from teams that run the system at scale |

## Discovery when the queue is dry

Scan, in this order, and stop as soon as a candidate survives the duplicate check:

1. Hacker News front page and `news.ycombinator.com/best`, last 48 hours.
2. GitHub releases for projects already covered in the archive — a major version is
   usually worth a post.
3. arXiv listings in cs.DC, cs.SE, cs.CL from the last week.
4. Engineering blogs from teams operating at scale.

A candidate is viable when it is **specific** (a mechanism, not a category), **fresh**
(the reader could not have read this a year ago), and **checkable** (primary sources
exist). Reject anything that would end up as a survey of things that already exist.

## The evidence ledger

Stage 2 produces `research.md` in the scratch directory. Every claim the post will make
appears there as:

```markdown
- **Claim:** JetStream acknowledges a publish before the replica set has fsynced.
  **Source:** https://docs.nats.io/nats-concepts/jetstream/streams
  **Quote:** "..."
```

This file is never published. It exists so the fact gate has something to check
against. **The rule that makes the gate possible: no claim may appear in the post
unless it appears in the ledger.** Write from the ledger, not from recall.
````

- [ ] **Step 6: Write `references/gates.md`**

````markdown
# Quality gates

Four gates run as parallel subagents after the draft is written. **All four are hard
blockers.** Each returns a verdict; any `block` sends the findings back to the writer.

**At most two revision rounds.** The cap is deliberate: a draft rewritten repeatedly
against a voice gate converges on blandness, which is the failure mode the gate exists
to prevent. After the second failed round, stop and open a draft PR.

## Verdict schema

Each gate subagent returns exactly this JSON and nothing else:

```json
{
  "gate": "fact | duplicate | code | voice",
  "verdict": "pass | block",
  "findings": [
    {"location": "line 42 or a quoted phrase", "problem": "what is wrong", "fix": "what to do"}
  ]
}
```

An empty `findings` array with `"verdict": "block"` is itself a failure — a blocking
gate must say what to fix.

## Gate 1 — Fact trace

Read the draft and `research.md` side by side. For every non-obvious claim in the
draft — a number, a behaviour, a version, an API, a guarantee — find the ledger line
supporting it.

**Block on:** any such claim with no ledger line; any claim whose ledger quote does not
actually support it; any citation link that does not resolve.

Common knowledge in the field needs no ledger line. A specific number always does.

## Gate 2 — Duplicate

Stage 1 already compared titles. This gate compares *arguments*. Read the three
nearest posts `dupe_check.py` reported and answer: does this draft make a point one of
them already made?

**Block on:** the draft's central argument substantially restating an existing post.
A new post on a covered topic is fine when it makes a genuinely different point — say
so explicitly in the verdict.

## Gate 3 — Code

Extract every code block. Syntax-check each one in its declared language. Run the
snippets that are runnable without network or credentials, in the scratch directory.

**Block on:** a block that does not parse; a runnable snippet that errors; code
calling an API that does not exist in the version the post names; a shell command that
would destroy data if pasted.

Pseudocode is allowed when labelled as such. Unlabelled pseudocode presented as real
code is a block.

## Gate 4 — Voice

Check the draft against `references/voice.md`.

**Block on:** any pattern in that file's "Hard blocks" section; a post outside
1,000–1,500 words; a missing worked example; a closing section that summarises without
concluding.

Do not block on dry humor or strong opinions — those are in-voice, and stripping them
produces exactly the prose this gate exists to prevent.

## After two failed rounds

Open a **draft** PR labeled `needs-work` whose body carries every gate's full verdict.
Write `blocked` to the status file. The work is preserved and the reason is legible;
nothing is silently discarded.
````

- [ ] **Step 7: Run the test to verify it passes**

Run: `python3 -m pytest script/daily_post/tests/test_skill_structure.py -v`
Expected: PASS, 12 tests.

- [ ] **Step 8: Commit**

```bash
git add .claude/skills/daily-post/references script/daily_post/tests/test_skill_structure.py
git commit -m "Add daily post skill reference files for front matter, voice, sources and gates"
```

---

### Task 9: The skill itself

**Files:**
- Create: `.claude/skills/daily-post/SKILL.md`
- Modify: `script/daily_post/tests/test_skill_structure.py` (append the SKILL.md tests)

**Interfaces:**
- Consumes: all four reference files (Task 8); `dupe_check.py` (Task 3); `queue.py` (Task 4); `make_banner.py` (Task 5); `preflight.sh` (Task 6); the status-file contract from `run.sh` (Task 7).
- Produces: the `/daily-post` skill. It writes one of `published`, `blocked`, `no-topic`, `preflight-failed` to `$DAILY_POST_STATUS`.

- [ ] **Step 1: Write the failing test**

Append to `script/daily_post/tests/test_skill_structure.py`:

```python
SKILL_MD = SKILL_DIR / "SKILL.md"

STATUS_TOKENS = ("published", "blocked", "no-topic", "preflight-failed")


def test_skill_md_exists():
    assert SKILL_MD.is_file()


def test_skill_md_has_name_and_description_front_matter():
    import yaml

    text = SKILL_MD.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    fm = yaml.safe_load(text.split("---\n")[1])
    assert fm["name"] == "daily-post"
    assert len(fm["description"]) > 40


def test_skill_md_links_every_reference_file():
    text = SKILL_MD.read_text(encoding="utf-8")
    for name in REFERENCE_FILES:
        assert f"references/{name}" in text, f"SKILL.md never references {name}"


def test_skill_md_names_every_script_it_drives():
    text = SKILL_MD.read_text(encoding="utf-8")
    for script in ("dupe_check.py", "make_banner.py", "preflight.sh", "queue.py"):
        assert script in text, f"SKILL.md never invokes {script}"


@pytest.mark.parametrize("token", STATUS_TOKENS)
def test_skill_md_documents_every_status_token(token: str):
    assert token in SKILL_MD.read_text(encoding="utf-8")


def test_skill_md_writes_to_the_status_file_variable():
    assert "DAILY_POST_STATUS" in SKILL_MD.read_text(encoding="utf-8")


def test_skill_md_forbids_interactive_prompts():
    """The pipeline runs unattended; a question is a hang, not a pause."""
    text = SKILL_MD.read_text(encoding="utf-8").lower()
    assert "never ask" in text or "no questions" in text


def test_skill_md_states_the_revision_cap():
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "two revision" in text.lower() or "2 revision" in text.lower()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest script/daily_post/tests/test_skill_structure.py -v`
Expected: FAIL on the new tests — `SKILL.md` does not exist.

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/daily-post/SKILL.md`:

````markdown
---
name: daily-post
description: Research, write, review and open a PR for one blog post. Use when running the daily post pipeline, when asked to write today's post, or when invoked as /daily-post by script/daily_post/run.sh.
---

# Daily Post

Produce one researched, reviewed blog post and open a pull request for it.

**This runs unattended. Never ask the operator a question** — every decision resolves
from `_data/topic_queue.yml` or from the gate rules. A question is a hang, not a pause.

Write the run's outcome to the file named by `$DAILY_POST_STATUS` as a single token:
`published`, `blocked`, `no-topic`, or `preflight-failed`. `run.sh` maps that token to
its exit code, so a run that writes nothing is reported as a pipeline failure.

Read these before starting:

- `references/frontmatter.md` — the contract CI enforces
- `references/voice.md` — what the blog sounds like
- `references/sources.md` — where to research, and the evidence ledger format
- `references/gates.md` — the four gates and their verdict schema

---

## Stage 1 — Select a topic

Read the queue:

```bash
python3 -c "
from pathlib import Path
from script.daily_post.queue import load_topics, next_queued
t = next_queued(load_topics(Path('_data/topic_queue.yml')))
print(t.id, '|', t.title, '|', t.angle, '|', t.category) if t else print('EMPTY')
"
```

If the queue is empty, discover a candidate using `references/sources.md`.

Check it against the archive:

```bash
python3 script/daily_post/dupe_check.py --title "<title>" --angle "<angle>" --json
```

Exit 1 means duplicate. On a duplicate, move to the next queue item or discover
another candidate. **After three rejected candidates, write `no-topic` to
`$DAILY_POST_STATUS` and stop.**

Once a candidate passes, claim it immediately — before any research — so a second run
today cannot pick the same topic:

```bash
python3 -c "
from pathlib import Path
from script.daily_post.queue import claim
claim(Path('_data/topic_queue.yml'), '<topic-id>', on='$(date +%F)')
"
```

Keep the `dupe_check` JSON. Gate 2 needs the three nearest posts it reported.

## Stage 2 — Research

Gather primary sources with WebSearch and WebFetch, following `references/sources.md`.

Write the evidence ledger to `research.md` in the scratch directory — one entry per
claim, each carrying the claim, the source URL, and a verbatim supporting quote. The
format is in `references/sources.md`.

**No claim may appear in the post unless it appears in the ledger.** Write from the
ledger, not from recall. This is what makes Gate 1 possible.

## Stage 3 — Write

Write `_posts/$(date +%F)-<slug>.md`.

- 1,000–1,500 words, following `references/voice.md`
- Front matter per `references/frontmatter.md`, with `header.overlay_image` and
  `header.teaser` pointing at `/assets/images/<slug>/banner.webp` and `teaser.webp`
- One idea, one worked example, one takeaway
- Wrap any code fence containing `{{` or `{%` in `{% raw %}` … `{% endraw %}`

## Stage 4 — Review

Dispatch all four gates from `references/gates.md` as **parallel subagents in a single
message**. Each returns the JSON verdict defined there.

If every gate passes, go to Stage 5.

If any gate blocks, hand the findings to the writer and revise. **At most two revision
rounds.** After a second failed round, skip to Stage 5 in blocked mode.

## Stage 5 — Publish

Generate the banner:

```bash
python3 script/daily_post/make_banner.py \
  --title "<title>" --category <category> --slug <slug>
```

Run preflight — exactly what CI runs:

```bash
script/daily_post/preflight.sh
```

**If preflight is red:** fix what it reports and run it again. If it is still red after
one fix, write `preflight-failed` to `$DAILY_POST_STATUS` and stop. Never push a branch
that CI will reject.

Commit and open the PR:

```bash
git checkout -b "daily-post/$(date +%F)-<slug>"
git add "_posts/$(date +%F)-<slug>.md" "assets/images/<slug>" _data/topic_queue.yml
git commit -m "<post title>"
git push -u origin "daily-post/$(date +%F)-<slug>"
```

**Gates green:**

```bash
gh pr create --title "<post title>" --body "<summary + sources used>"
```

Then mark the topic published and write the status:

```bash
python3 -c "
from pathlib import Path
from script.daily_post.queue import mark
mark(Path('_data/topic_queue.yml'), '<topic-id>', 'published', slug='<slug>')
"
echo published > "$DAILY_POST_STATUS"
```

**Gates still blocked after two revision rounds:**

```bash
gh pr create --draft --title "<post title> [needs work]" \
  --body "<every gate's full verdict>"
gh pr edit --add-label needs-work
echo blocked > "$DAILY_POST_STATUS"
```

Leave the topic `claimed` in that case — it is neither published nor rejected, and the
operator decides which it becomes.

## Failure handling

Any unrecoverable error: write the closest matching token to `$DAILY_POST_STATUS`,
explain what happened in the transcript, and stop. Never leave the status file empty —
`run.sh` reports that as exit 50, which is indistinguishable from a crash.
````

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest script/daily_post/tests/test_skill_structure.py -v`
Expected: PASS, 23 tests.

- [ ] **Step 5: Verify the skill is discoverable**

Run: `ls .claude/skills/daily-post/` and confirm `SKILL.md` plus `references/` with four files. In a fresh Claude Code session in this repo, `/daily-post` should appear in the skill list. If it does not, check the front matter parses as YAML.

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/daily-post/SKILL.md script/daily_post/tests/test_skill_structure.py
git commit -m "Add the daily-post skill orchestrating the five pipeline stages"
```

---

### Task 10: Wiring, documentation, and a full dry run

**Files:**
- Modify: `Makefile` (append daily post targets)
- Modify: `README.md` (add a "Daily post pipeline" section after "Distribution")
- Modify: `_config.yml:172-200` (add `docs` to `exclude`)
- Create: `script/daily_post/README.md`
- Test: `script/daily_post/tests/test_wiring.py`

**Interfaces:**
- Consumes: everything from Tasks 1–9.
- Produces: `make daily-post`, `make daily-post-test`, `make daily-post-preflight`.

`docs/` is currently copied into `_site` by Jekyll because it is not excluded. The spec
and this plan are markdown without front matter, so they are copied verbatim — harmless
but pointless. Exclude them.

- [ ] **Step 1: Write the failing test**

Create `script/daily_post/tests/test_wiring.py`:

```python
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]


def test_makefile_exposes_the_daily_post_targets():
    text = (REPO / "Makefile").read_text(encoding="utf-8")
    for target in ("daily-post:", "daily-post-test:", "daily-post-preflight:"):
        assert target in text, f"Makefile is missing the {target} target"


def test_readme_documents_the_pipeline():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    assert "Daily post pipeline" in text
    assert "script/daily_post/run.sh" in text
    assert "_data/topic_queue.yml" in text


def test_readme_documents_every_exit_code():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    for code in ("0", "10", "20", "30", "40", "50"):
        assert f"`{code}`" in text, f"README does not document exit code {code}"


def test_docs_are_excluded_from_the_jekyll_build():
    config = yaml.safe_load((REPO / "_config.yml").read_text(encoding="utf-8"))
    assert "docs" in config["exclude"]


def test_script_readme_exists():
    assert (REPO / "script" / "daily_post" / "README.md").is_file()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest script/daily_post/tests/test_wiring.py -v`
Expected: FAIL — `Makefile is missing the daily-post: target`

- [ ] **Step 3: Append the Makefile targets**

Add to the end of `Makefile`:

```makefile
# Daily post pipeline
daily-post:
	./script/daily_post/run.sh

daily-post-test:
	python3 -m pytest script/daily_post/tests -v

daily-post-preflight:
	./script/daily_post/preflight.sh

daily-post-dupe:
	@if [ -z "$(TITLE)" ]; then \
		echo 'Usage: make daily-post-dupe TITLE="Your candidate title"'; \
		exit 1; \
	fi
	python3 script/daily_post/dupe_check.py --title "$(TITLE)"
```

- [ ] **Step 4: Exclude `docs` from the build**

In `_config.yml`, in the `exclude:` list (around line 199, next to the
`# local tooling and docs -- not site content` comment), add one line:

```yaml
  - docs
```

- [ ] **Step 5: Add the README section**

Insert into `README.md` after the `## Distribution` section:

````markdown
## Daily post pipeline

One command researches, writes, reviews, and opens a PR for a single post:

```bash
make daily-post          # the full pipeline — point your scheduler at this
make daily-post-test     # the pipeline's own test suite
make daily-post-preflight   # what CI runs, locally
make daily-post-dupe TITLE="A candidate title"   # check a topic against the archive
```

Topics come from `_data/topic_queue.yml`. The pipeline takes the first entry with
`status: queued`, marks it `claimed`, and writes it; when the queue is dry it discovers
a topic from the web instead. **Keeping that file stocked is how you steer what gets
written.**

Four quality gates — fact trace, duplicate, code, voice — run after the draft and are
all hard blockers. A draft that still fails after two revision rounds gets a **draft**
PR labeled `needs-work` carrying the gate report rather than being discarded.

The skill lives in `.claude/skills/daily-post/`; its scripts live in
`script/daily_post/`. Scheduling is deliberately not included — wire `run.sh` into
cron, launchd, or a workflow yourself.

### Exit codes

| Code | Meaning | What to do |
| --- | --- | --- |
| `0` | Gates green, PR open | Review and merge |
| `10` | Blocked after two revisions; draft PR open | Read the gate report |
| `20` | No viable topic after three attempts | Stock the queue |
| `30` | Already ran today | Nothing — expected on a double-fire |
| `40` | Precondition failed (`gh` missing, dirty tree, stale `master`) | Fix the environment |
| `50` | Preflight red or the pipeline reported nothing | Check `.git/daily-post-logs/` |

**Requires `gh`**, installed and authenticated — the PR step depends on it.
````

- [ ] **Step 6: Write `script/daily_post/README.md`**

````markdown
# Daily post pipeline scripts

Supporting scripts for the `daily-post` skill in `.claude/skills/daily-post/`.
Run them from the repo root so the `script.daily_post` import path resolves.

| File | Responsibility |
| --- | --- |
| `run.sh` | Daily entry point: preconditions, idempotency, exit codes, logging |
| `preflight.sh` | Front matter + jekyll build + htmlproofer, exactly as CI runs them |
| `similarity.py` | TF-IDF and cosine, standard library only |
| `corpus.py` | Reads `_posts/*.md` into comparable records |
| `dupe_check.py` | CLI: is this topic a duplicate? Exit 1 means yes |
| `queue.py` | Read and update `_data/topic_queue.yml` |
| `make_banner.py` | Pillow-rendered `banner.webp` and `teaser.webp` |

## Why standard library only

`scikit-learn` and `numpy` are installed on the target machine but broken
(`ImportError: numpy.core.multiarray failed to import`). The corpus is ~150 short
documents, far too small for those dependencies to earn their place, so the TF-IDF
implementation is hand-rolled in `similarity.py`.

Likewise for images: no `cairosvg`, `rsvg-convert`, ImageMagick, or `cwebp` is present.
Pillow writes WebP natively and is the only image dependency.

## Tests

```bash
make daily-post-test                                  # everything
python3 -m pytest script/daily_post/tests -m "not slow"  # skip the full site build
```

The `slow` marker covers the full Jekyll build; the `calibration` marker covers the
duplicate threshold pinned against the live archive. If the calibration test fails
after the archive grows, re-tune `DEFAULT_THRESHOLD` — do not weaken the assertion.
````

- [ ] **Step 7: Register the pytest markers**

Create `pytest.ini` at the repo root so `slow` and `calibration` do not emit warnings:

```ini
[pytest]
markers =
    slow: tests that build the whole Jekyll site
    calibration: tests pinning thresholds against the live archive
```

- [ ] **Step 8: Run the wiring test**

Run: `python3 -m pytest script/daily_post/tests/test_wiring.py -v`
Expected: PASS, 5 tests.

- [ ] **Step 9: Run the whole suite**

Run: `python3 -m pytest script/daily_post/tests -v`
Expected: PASS. 91 tests across nine files. Nothing skipped except when
`bundle` is unavailable.

- [ ] **Step 10: Verify the repo is still green**

Run:
```bash
python3 script/check_frontmatter.py
script/daily_post/preflight.sh --fast
```
Expected: `OK: 146 posts satisfy the front matter contract` and `preflight OK`.

- [ ] **Step 11: Dry-run the entry point's precondition path**

`gh` is not installed, so this must fail cleanly rather than doing work:

```bash
script/daily_post/run.sh; echo "exit=$?"
```
Expected: `PRECONDITION FAILED: gh is not installed; the PR step needs it` and
`exit=40`. This confirms the guard fires before any expensive work. Install and
authenticate `gh` before the first real run.

- [ ] **Step 12: Commit**

```bash
git add Makefile README.md _config.yml pytest.ini script/daily_post/README.md script/daily_post/tests/test_wiring.py
git commit -m "Wire the daily post pipeline into make, docs and the Jekyll build"
```

---

## Done when

- `make daily-post-test` is green.
- `script/daily_post/preflight.sh --fast` is green and the 146 existing posts still pass.
- `script/daily_post/run.sh` exits 40 with a clear message while `gh` is absent.
- `/daily-post` appears in a fresh Claude Code session in this repo.
- `README.md` documents the pipeline and every exit code.

## Deliberately not built

Scheduling and triggering — the operator wires up `run.sh`. Distribution to IndexNow,
Google Search Console, and dev.to — those stay manual `make` targets. Art beyond the
generated banner. Editing or refreshing existing posts.
