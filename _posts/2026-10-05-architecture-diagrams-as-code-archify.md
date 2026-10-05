---
title: "Architecture Diagrams That Fail Like Code: Archify in Practice"
description: "Archify validates diagrams like code: it rejected 8 of 9 broken diagrams, kept the last good file through 4 failed deliveries, and labels PR diagram changes."
tags:
    - Developer Tools
    - AI Agents
    - System Design
    - Testing
categories:
    - software-engineering
header:
    overlay_image: /assets/images/architecture-diagrams-as-code-archify/banner.webp
    overlay_filter: 0.5
    teaser: /assets/images/architecture-diagrams-as-code-archify/teaser.webp
toc: true
toc_sticky: true
---

The architecture diagram in your README is a PNG someone exported from a whiteboard tool eight months ago. It still shows the session cache you deleted in spring, and nothing will ever tell you it is wrong, because a picture cannot fail. Ask an AI agent to redraw it and you get a new picture that also cannot fail, plus whatever the agent guessed. [Archify](https://github.com/tt-a1i/archify) makes **architecture diagrams as code** work in practice. The agent writes typed JSON, and a CLI rejects that JSON the way a compiler rejects bad source. You can then review, diff and gate a diagram in CI like any other file. I ran archify 3.0.1 on 20 crafted diagrams and 10 routing questions to see where that holds and where it stops: in short, it catches broken structure and bad citations, but not wrong meaning.

## The design decision: the agent writes JSON, never SVG

Archify is an agent skill for Claude Code, Cursor, Codex CLI and OpenCode (`npx skills add tt-a1i/archify -g`). It draws five diagram types, each output as one self-contained HTML file with inline SVG.

The structural choice that explains the rest is in the README's own list: **"Typed JSON IR — every renderer-backed mode has a schema and reproducible source."** The agent never draws. It writes a JSON file of components, connections and boundaries, and archify's renderer turns that into SVG. Between the two sits a set of validators: schema, layout, label clearance, desktop readability and, when you ask for it, source evidence. A failure comes back as one JSON object with a stable rule code, the exact subject, measured evidence and a list of `supportedFixes`. The agent is told to apply only those fixes, and to report the gap if an issue survives two focused repairs and one evidence-based retry.

The delivery step is the part that makes this safe to automate. Per the README, "only a passing artifact atomically replaces the target." Traced through the CLI, the candidate and the file on disk never meet unless every gate passes:

<iframe src="/assets/htmls/architecture-diagrams-as-code-archify-delivery-gate.html" title="Archify delivery gate workflow" loading="lazy" style="width:100%;height:600px;border:1px solid #ddd;border-radius:8px"></iframe>

[Open full size](/assets/htmls/architecture-diagrams-as-code-archify-delivery-gate.html)

So a failed run leaves your docs exactly as they were, and gives the agent a receipt it can act on. That one property makes the four practical uses below possible.

## The experiment: feeding it broken diagrams

**Archify rejected 8 of 9 broken architecture diagrams, and none of the 4 failed deliveries changed a single byte of the last good HTML.** The ninth "broken" input was an HTML-injection payload, which archify accepted and then rendered harmlessly as text.

The setup: I took the architecture example archify ships (`web-app.architecture.json`, ten components on AWS) and made one edit per fixture. One fixture was the untouched original. The others pointed an edge at a component that does not exist, dragged the API node on top of the load balancer, misspelled a field (`colour`), duplicated a component id, duplicated a connection id, wrapped a boundary around a missing component, moved the database 5,000 pixels away, and put `<script>` and `<img onerror>` payloads in labels. Each ran through `archify validate --quality showcase --json` once. These are deterministic CLI runs (commit `73aaa06`, Node 26.3.0) with no model involved, so each row is one answer, not a rate.

| Fixture | Exit | What archify said |
|---|---|---|
| Original example | 0 | pass |
| Edge to a missing component | 1 | `Connection "HTTPS" references unknown target "ghost"` |
| API node dropped onto the load balancer | 1 | 5 diagnostics: edges through nodes, label clearance; 4 carry a fix |
| Misspelled field `colour` | 1 | `schema/additionalProperties`, fix: `remove unsupported property "colour"` |
| Duplicate component id | 1 | `Component ids must be unique.` |
| Duplicate connection id | 1 | `relationship/duplicate-id` |
| Boundary wraps a missing component | 1 | `wraps unknown component "nobody"` |
| Database moved to x=5000 | 1 | `composition/desktop-readability` |
| `<script>alert(1)</script>` as a label | 1 | label wider than its 120px box |
| `<img src=x onerror=alert(1)>` as a sublabel | 0 | pass |

Most structural rows name their exact subject. That precision is what lets an agent repair one neighbourhood of the JSON instead of regenerating the whole diagram.

The far-away database is the interesting one. The JSON passes the schema and every edge resolves. Archify rejected it because the diagram would be 5,200 units wide, which would shrink its 8px labels to about 2px on a 1,346px desktop budget, below its 6px floor. It checks the diagram a reader will actually see, not just the data.

The `<script>` label was rejected for its width, not its content, which is a lucky outcome rather than a defence. So I kept the `<img onerror>` payload, which fit, and ran it through the full `finalize` pipeline, which passed. The output file contains `&lt;img src=x onerror=alert(1)&gt;`, escaped. Loaded in Chromium, clicking the node, searching for it with `/` and opening the `?` guide fired no dialog and created no `<img>` element. The payload showed up as text.

Then the atomicity claim. I delivered the good example to a target file, then delivered four failing candidates to the same path. All four exited 1, and the file's SHA-256 was identical after each. One unadvertised side effect: a failed delivery leaves a `<name>.delivery-pending.json` sidecar next to the target. Add it to `.gitignore` if your diagrams live in the repo.

## Use 1: review architecture changes in the pull request

Commit the JSON next to the code and the diagram becomes reviewable. `archify compare architecture base.json head.json delta.html --json` renders a Before / Delta / After page and writes a receipt that labels every change. I made three one-line "PRs" against the same example:

- moving the worker node 20px came back as `moved`, classified `geometry`;
- changing Redis's port in its sublabel came back as `changed`, classified `semantic`;
- adding a worker-to-Postgres edge came back as `added`, classified `topology`.

Combined into one PR, the three edits render like this; switch between Before, Delta and After at the top of the frame:

<iframe src="/assets/htmls/architecture-diagrams-as-code-archify-pr-delta.html" title="Architecture Delta for a sample PR" loading="lazy" style="width:100%;height:760px;border:1px solid #ddd;border-radius:8px"></iframe>

[Open full size](/assets/htmls/architecture-diagrams-as-code-archify-pr-delta.html)

That split is what a reviewer needs. A PR that only tidies the layout should not look like a PR that gives a worker direct database access. The receipt is also honest about its limits: "Authored Architecture IR only; no runtime impact, causality, risk, or mergeability is inferred." It diffs what someone *wrote down*, not what the system does.

## Use 2: a repository map that cites its sources

For a diagram of real code, each component can carry up to three `sources` (path, line, end line), and `meta.repository` pins a 40-character commit. Run validation with `--repo-root` and archify checks each citation against the committed bytes at that revision.

Pointed at real code, it looks like this: archify's own deliver path, with every box citing the lines at commit `73aaa06` that back it. Each `SRC` badge opens those lines on GitHub:

<iframe src="/assets/htmls/architecture-diagrams-as-code-archify-repo-map.html" title="archify deliver path, source-backed" loading="lazy" style="width:100%;height:620px;border:1px solid #ddd;border-radius:8px"></iframe>

[Open full size](/assets/htmls/architecture-diagrams-as-code-archify-repo-map.html)

I built a two-file Git repository and cited it seven ways. A correct citation passed. Five bad ones were rejected, each with a message naming the problem: a line past the end of the file (`requests line 40, but app/db.py has 2 lines`), a missing file, a file that exists only in the working tree, a path escaping the repo (`../../secret.txt`) and an unknown revision. The missing file and the working-tree-only file share one code, `repository-evidence/file-missing`, because both are absent at the pinned commit.

Then the seventh citation, and the important limit. I pointed the PostgreSQL node at line 1 of `app/api.py`, which is `from fastapi import FastAPI`. **It passed.** Archify proves a citation *exists* at the pinned commit; it cannot prove the cited line says what the node claims. A source-backed diagram is a diagram whose claims are easy to check, not a diagram that has been checked. Someone still has to click `SRC 1` and read.

## Use 3: make CI reject a broken diagram

Because every failure is exit code 1 plus a JSON receipt, the CLI drops straight into CI. It needs nothing but Node: every run in this post used a bare clone with no `npm install`. A workflow that validates the committed diagram and attaches the PR delta:

{% raw %}
```yaml
# .github/workflows/architecture-diagram.yml
name: architecture-diagram
on: pull_request
jobs:
  diagram:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # the pinned evidence revision must exist in the clone
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - name: Fetch archify at a pinned commit
        run: |
          git clone https://github.com/tt-a1i/archify /tmp/archify
          git -C /tmp/archify checkout 73aaa0696e8f72c232ea710e6fa94fd953f3e773
      - name: Validate the diagram source (fails the job on exit 1)
        run: |
          node /tmp/archify/archify/bin/archify.mjs validate architecture \
            docs/architecture.json --repo-root . --quality showcase --json
      - name: Diff against the base branch
        run: |
          git show "origin/${{ github.base_ref }}:docs/architecture.json" > /tmp/base.json
          node /tmp/archify/archify/bin/archify.mjs compare architecture \
            /tmp/base.json docs/architecture.json delta.html --json > delta.json
      - uses: actions/upload-artifact@v4
        with:
          name: architecture-delta
          path: |
            delta.html
            delta.json
```
{% endraw %}

In the PR that first adds `docs/architecture.json`, the diff step fails because the base branch has no file yet; skip it there. `fetch-depth: 0` matters if you use source evidence: when the pinned revision is missing from the clone, validation fails with "is not available in the local repository". Locally, the same receipt is easy to read:

```bash
# Print each failure's rule code, message and the fixes archify will accept.
node ~/.claude/skills/archify/bin/archify.mjs validate architecture docs/architecture.json \
  --quality showcase --json | jq '.diagnostics[]? | {code, message, supportedFixes}'
```

## Use 4: send it to people who will never open your repo

The output is one HTML file that opens without archify installed, and stable links restore a view: <a href="/assets/htmls/architecture-diagrams-as-code-archify-repo-map.html#focus=commit" data-proofer-ignore>this link</a> opens the map above focused on the commit step. That suits an incident retro, where you link "the path the bad request took" instead of describing it, or a runbook a support team reads. The escaping test above is what makes me comfortable embedding one in a page I host. Each iframe in this post is one.

## Where it gets it wrong

The `guide` command, which recommends a diagram type for a plain-English question, is keyword matching. I gave it ten scenarios and it picked the type I expected for seven. Every one of its five high-confidence answers matched. All three misses were an order status flow, an OAuth code flow and Kubernetes pod phases; each came back `confidence: low` with no matched signals and defaulted to `architecture`. Treat a low-confidence answer as "no idea", which is what it is.

The checks also cannot replace judgement about content. The validators know a box is too far away or a line number does not exist. They do not know that your agent invented a queue. Archify's repository-authoring guide tells the agent to trace call sites and to "never turn a label, package description, or config value into an unobserved service or behavior." That is an instruction to the model, not a check the CLI runs.

## What to do with it

Pick one diagram that matters — the one in your main README, or the one new hires get — and replace the image with archify JSON in the repo, rendered to HTML. Add the `validate` step to CI so a broken edit fails the PR, and attach the `compare` delta so reviewers can see a topology change. If you cite source lines, review them like code; archify guarantees they exist, not that they are right.

## Further reading

- [tt-a1i/archify on GitHub](https://github.com/tt-a1i/archify) — README, CLI usage and design notes
- [archify/SKILL.md](https://github.com/tt-a1i/archify/blob/main/archify/SKILL.md) — the agent contract and the `finalize` command
- [Delivery contract](https://github.com/tt-a1i/archify/blob/main/archify/references/delivery-contract.md) — failed gates and the repair limit
- [Repository-backed authoring](https://github.com/tt-a1i/archify/blob/main/archify/references/repository-authoring.md) — how source evidence is pinned and checked
- [Archify CHANGELOG](https://github.com/tt-a1i/archify/blob/main/CHANGELOG.md) — v3.0.1 release notes
- [Archify Proof Lab gallery](https://tt-a1i.github.io/archify/gallery.html) — the shipped scenarios and their JSON sources
