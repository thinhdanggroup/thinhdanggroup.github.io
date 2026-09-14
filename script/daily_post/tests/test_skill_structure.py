import re
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
    text = (REFS / "gates.md").read_text(encoding="utf-8").lower()
    assert "at most two revision rounds" in text


@pytest.mark.parametrize("name", REFERENCE_FILES)
def test_reference_files_contain_no_placeholders(name: str):
    text = (REFS / name).read_text(encoding="utf-8")
    for marker in ("TODO", "TBD", "FIXME", "XXX"):
        assert marker not in text, f"{name} still contains {marker}"


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


def test_skill_md_returns_to_clean_master_on_every_pr_path():
    """Both the published and blocked paths must independently return to a
    clean master — not just somewhere in the file once.

    Regression guard for Task 9 fix round 1, Finding 1 (critical): a run that
    stops on a feature branch silently breaks the next day's run. Strengthened
    in fix round 3, Finding 8: the original version of this test only checked
    that the phrases appeared *somewhere*, so deleting the cleanup from one
    path while leaving the other in place would still have passed. This scans
    each path's own section independently, the same technique already used by
    test_skill_md_feature_branch_never_stages_the_queue_file.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    green_start = text.index("**Gates green:**")
    blocked_start = text.index("**Gates still blocked")
    stage_5_end = text.index("## Failure handling")
    sections = {
        "published": text[green_start:blocked_start],
        "blocked": text[blocked_start:stage_5_end],
    }
    for name, section in sections.items():
        assert "git switch master" in section, (
            f"the {name} path never returns to master"
        )
        assert "git branch -D" in section, (
            f"the {name} path never deletes the local feature branch"
        )


def test_skill_md_defines_concrete_scratch_path():
    """`research.md` must live at a resolved path, not just 'the scratch directory'.

    Regression guard for Task 9 fix round 1, Finding 2: gate subagents cannot find
    an unresolved path.
    """
    assert "daily-post-scratch" in SKILL_MD.read_text(encoding="utf-8")


def test_skill_md_marks_duplicate_queue_topics_rejected():
    """A duplicate that came from the queue must be marked `rejected`, in Stage 1.

    Regression guard for Task 9 fix round 1, Finding 3: otherwise `next_queued()`
    hands back the same known-duplicate topic on every future run.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.index("## Stage 1")
    end = text.index("## Stage 2")
    stage_one = text[start:end]
    assert "rejected" in stage_one


def test_skill_md_states_queue_state_lives_on_master():
    """SKILL.md must state the rule that queue bookkeeping is committed to
    master directly, never left stranded on an unmerged feature branch.

    Regression guard for Task 9 fix round 2, Finding 4: a claim that only ever
    lands on the feature branch leaves master reading `queued`, so tomorrow's
    run picks the same topic again while today's PR is still open.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "Queue state is pipeline bookkeeping and lives on" in text


def test_skill_md_feature_branch_never_stages_the_queue_file():
    """No `git switch -c "daily-post/...` code block may also stage
    `_data/topic_queue.yml` — that file's state must be committed straight to
    master, never bundled into the feature branch alongside the post.

    Regression guard for Task 9 fix round 2, Finding 4: bundling the queue
    mutation into the feature-branch commit is exactly what let a claim sit
    unmerged on a branch while master kept reading the topic as `queued`.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    branch_blocks = re.findall(r"```bash\n(.*?)```", text, re.DOTALL)
    branch_blocks = [b for b in branch_blocks if 'git switch -c "daily-post/' in b]
    assert branch_blocks, "no feature-branch code block found to check"
    for block in branch_blocks:
        assert "topic_queue.yml" not in block, (
            "a feature-branch code block still stages topic_queue.yml:\n" + block
        )


def test_skill_md_checks_open_prs_before_claiming():
    """Stage 1 must check open PRs for the same topic before claiming a
    candidate, not just the mechanical dupe_check score.

    Regression guard for Task 9 fix round 4, Finding 9: a topic with no queue
    entry (discovered) or an unmerged PR sitting open for days is invisible to
    both `next_queued()` and `dupe_check` (which only sees `_posts/`), so
    nothing previously stopped the same topic being picked again while its PR
    was still open.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.index("## Stage 1")
    end = text.index("## Stage 2")
    stage_one = text[start:end]
    assert "gh pr list" in stage_one


# --- final-review regression guards -----------------------------------------
#
# These are text guards. They prove the instructions SAY the right thing; they
# cannot prove that an agent following them behaves correctly. That gap is real
# and is why the mechanical backstops live in run.sh (the publish-boundary
# check) and in the command form itself (`git clean`, which cannot delete a
# tracked file no matter what the model substitutes).


def test_skill_md_never_uses_rm_rf_on_a_substituted_path():
    """C1: `rm -rf "assets/images/<slug>"` with a model-filled `<slug>`.

    An empty or stale slug turns that into `rm -rf assets/images/`, destroying
    the artwork for every published post — unattended, with no confirmation.
    The replacement is `git clean`, which by construction can only remove
    untracked files.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    for block in re.findall(r"```bash\n(.*?)```", text, re.DOTALL):
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue  # a comment saying "never rm -rf" is the fix, not the hazard
            assert not re.search(r"\brm\s+-[a-zA-Z]*[rR]", stripped), (
                "a SKILL.md command block issues a recursive rm; use "
                "`git clean -fdx -- <path>` instead:\n" + line
            )


def test_skill_md_guards_the_slug_before_cleaning_up():
    """C1: the cleanup path must refuse to run at all on an empty slug."""
    text = SKILL_MD.read_text(encoding="utf-8")
    assert 'slug is empty; refusing to clean up' in text
    assert text.count('[[ -n "$slug" ]]') >= 2, (
        "both preflight-failed cleanup paths must guard the slug"
    )


def test_skill_md_cleans_generated_images_with_git_clean():
    """C1: only untracked files may ever be removed by the cleanup.

    S1: and never `-x`. The generated banner.webp/teaser.webp are untracked but
    not gitignored, so `-fd` removes them just as well, while `-x` would put
    every ignored file in range — .env, script/**/credentials.json,
    script/**/token.json — for any slug that escaped the directory.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    assert text.count('git clean -fd -- "assets/images/$slug"') == 2
    for block in re.findall(r"```bash\n(.*?)```", text, re.DOTALL):
        for line in block.splitlines():
            if line.strip().startswith("#"):
                continue
            assert "git clean" not in line or "-x" not in line, (
                "a SKILL.md command block runs `git clean` with -x, putting "
                "ignored files (.env, credentials) in range:\n" + line
            )
    assert "git clean -fdx" not in text, (
        "SKILL.md still recommends `git clean -fdx` somewhere, including in prose"
    )


def test_skill_md_validates_the_slug_shape_before_cleaning_up():
    """S1: an empty-check alone is not enough.

    A slug of `../..` escapes assets/images/ and lands on the repo root, where
    `git clean` reaches this repo's ignored files — .env, credentials.json,
    token.json, the dev.to and Medium configs. Shape validation makes that
    impossible by construction rather than by luck; globs, whitespace and path
    separators go with it.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    assert text.count('[[ "$slug" =~ ^[a-z0-9-]+$ ]]') == 2, (
        "both cleanup paths must validate the slug's shape, not just its emptiness"
    )
    assert text.count("is not a plain [a-z0-9-] slug") == 2


def test_skill_md_failure_handling_forbids_x_and_free_paths():
    """S1: the prose discard step must carry the same rules as the code."""
    text = SKILL_MD.read_text(encoding="utf-8")
    section = text[text.index("## Failure handling"):]
    assert "git clean -fd -- <literal path>" in section
    assert "no `-x`" in section
    assert "assets/images/" in section


def test_skill_md_preserves_the_draft_on_a_preflight_failure():
    """I6: exit 50 says "investigate", so the draft must survive.

    Deleting the failed draft destroys the only artifact that makes the
    investigation possible.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    assert text.count("failed-draft.md") >= 2, (
        "both preflight-failed paths must keep the draft"
    )
    assert "draft kept at .git/daily-post-scratch" in text, (
        "the log line must name where the draft was kept"
    )


def test_skill_md_creates_the_needs_work_label_before_using_it():
    """I5: `gh pr edit --add-label needs-work` fails when the label does not
    exist — and this is the failure-visibility path, the one most likely to
    fire on day one."""
    text = SKILL_MD.read_text(encoding="utf-8")
    label_at = text.index("gh label create needs-work")
    edit_at = text.index("gh pr edit --add-label needs-work")
    assert label_at < edit_at, "the label must be created before it is used"
    assert "--force" in text[label_at:label_at + 120], "label creation must be idempotent"
    after_edit = text[edit_at:edit_at + 220]
    assert "||" in after_edit, (
        "a label failure must not sink an otherwise-good run"
    )


def test_skill_md_does_not_restate_the_word_count_bound():
    """The bound belongs in voice.md alone; two copies drift."""
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "1,000" not in text and "1,500" not in text
    assert "references/voice.md" in text


def test_gate_3_forbids_executing_generated_code():
    """C2: Gate 3 used to run model-written snippets "in the scratch
    directory" — i.e. unsandboxed, inside a repo holding push rights and
    credentials, with the scratch dir under `.git/`. It is static-only now, and
    the text must not leave that readable as optional.
    """
    text = (REFS / "gates.md").read_text(encoding="utf-8")
    gate_3 = text[text.index("## Gate 3"):text.index("## Gate 4")]
    lowered = gate_3.lower()
    assert "never executes" in lowered
    assert "static analysis only" in lowered
    for permissive in (
        "run the snippets",
        "runnable snippet that errors",
        "in the scratch directory.",
        "sandbox where one is feasible",
    ):
        assert permissive not in lowered, (
            f"Gate 3 still tells the agent to execute code: {permissive!r}"
        )
    # the parse-only checkers are what replaced execution
    assert "bash -n" in gate_3 and "py_compile" in gate_3


def test_design_spec_and_gate_3_agree_about_execution():
    """C2: the spec's "sandbox where one is feasible" wording is what got lost
    in implementation. Spec and gate must now say the same thing."""
    spec = (
        REPO / "docs" / "superpowers" / "specs"
        / "2026-09-14-daily-post-pipeline-design.md"
    ).read_text(encoding="utf-8")
    assert "never executes the draft's code" in spec


def _slug_guard_script() -> str:
    """The literal guard lines SKILL.md tells the agent to run, lifted out of
    the document so the test exercises the real text rather than a copy."""
    text = SKILL_MD.read_text(encoding="utf-8")
    tail = 'is not a plain [a-z0-9-] slug; refusing to clean up" >&2; exit 1; }'
    start = text.index('[[ -n "$slug" ]]')
    end = text.index(tail, start) + len(tail)
    # The guard sits inside a markdown list item, so every line but the first
    # carries list indentation; strip it. The `\` continuations survive.
    guard = "\n".join(line.lstrip() for line in text[start:end].splitlines())
    return 'set -u\nslug="$1"\n' + guard + '\necho WOULD-CLEAN "assets/images/$slug"\n'


@pytest.mark.parametrize(
    "hostile",
    [
        "",           # the original C1 hazard: expands to the whole archive
        "../..",      # escapes assets/images/ and reaches the repo root
        "..",
        "../secrets",
        ".",
        "/",
        "a/b",        # any path separator at all
        "*",          # a glob
        "foo bar",    # whitespace
        "Foo",        # uppercase is not a slug
        "foo;rm -rf /",
        "$(whoami)",
        "foo\ttab",
    ],
)
def test_the_slug_guard_refuses_hostile_values(hostile: str):
    """S1: the reviewer proved `slug="../.."` escaped assets/images/ and put
    this repo's ignored files — .env, credentials.json, token.json — inside
    `git clean`'s range. The guard must refuse anything that is not a plain
    lowercase slug, before either destructive command runs.
    """
    import subprocess

    result = subprocess.run(
        ["bash", "-c", _slug_guard_script(), "guard", hostile],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        f"the guard accepted a hostile slug {hostile!r}:\n{result.stdout}"
    )
    assert "WOULD-CLEAN" not in result.stdout, (
        f"cleanup would have run for slug {hostile!r}"
    )
    assert "refusing to clean up" in result.stderr


@pytest.mark.parametrize("good", ["a", "my-post", "post-2026-09-14", "abc123"])
def test_the_slug_guard_accepts_real_slugs(good: str):
    """The counterpart: a guard that refused everything would be useless."""
    import subprocess

    result = subprocess.run(
        ["bash", "-c", _slug_guard_script(), "guard", good],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"WOULD-CLEAN assets/images/{good}" in result.stdout


def test_skill_md_uses_git_switch_not_git_checkout():
    """The harness permission classifier denied `git checkout -b ...` on the first
    real run while `git switch -c ...` was allowed. The skill's literal commands
    have to be the ones that actually run unattended.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    offenders = [
        line for line in text.splitlines() if "git checkout" in line
    ]
    assert not offenders, (
        "SKILL.md still issues `git checkout`; use `git switch`:\n"
        + "\n".join(offenders)
    )
    assert 'git switch -c "daily-post/' in text, "no branch creation found"
    assert "git switch master" in text, "nothing returns to master"


# --- preflight exit 1 vs exit 2 -------------------------------------------------

def _preflight_exit_2_section() -> str:
    """Stage 5's environment-failure branch, on its own."""
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.index("**If preflight exits 2 (environment):**")
    end = text.index("**If preflight exits 1 (red):**")
    return text[start:end]


def test_skill_md_distinguishes_a_broken_environment_from_a_broken_post():
    """The first real run's worst latent bug: preflight exited 1 whether the
    post was broken or bundler was merely off PATH, and Stage 5 read any red
    preflight as "this run produced a broken post". A cron PATH problem would
    have reverted the topic and moved a good, finished post aside.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    assert "**If preflight exits 2 (environment):**" in text
    assert "**If preflight exits 1 (red):**" in text
    assert text.index("**If preflight exits 2 (environment):**") < text.index(
        "**If preflight exits 1 (red):**"
    ), "the environment case must be handled before the red case"


def test_skill_md_preserves_everything_on_an_environment_failure():
    """On exit 2 the post was never checked, so nothing about it may be undone."""
    section = _preflight_exit_2_section()
    assert "queued" in section and "Do not** revert" in section, (
        "the exit-2 path must say explicitly not to revert the topic"
    )
    assert "Do not** move the draft aside" in section
    assert "preflight-failed" in section, (
        "the operator still has to investigate a broken environment"
    )
    # Nothing in this branch may undo the run's work.
    assert "mark(" not in section, "the exit-2 path must not mutate the queue"
    assert "git clean" not in section, "the exit-2 path must not clean anything"
    assert "failed-draft.md" not in section, "the exit-2 path must not move the draft"


def test_skill_md_reads_the_preflight_exit_code():
    text = SKILL_MD.read_text(encoding="utf-8")
    assert 'echo "preflight exit code: $?"' in text, (
        "Stage 5 must actually read the exit code it branches on"
    )


# --- Stage 1: claiming when the open-PR check was skipped -----------------------

def test_stage_1_claims_even_when_the_open_pr_check_was_skipped():
    """The run's top-reported ambiguity: Stage 1 said to log-and-continue when
    `gh pr list` fails, but never said whether the claim is still written.
    Skipping the claim is strictly worse than skipping the guard.
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    stage_one = text[text.index("## Stage 1"):text.index("## Stage 2")]
    assert "the claim below is still written" in stage_one
    assert "*possible*" in stage_one and "*likely*" in stage_one, (
        "the reason (possible vs likely duplicate) must be stated, not just the rule"
    )


# --- the word-count rule --------------------------------------------------------

def test_voice_md_defines_what_counts_toward_the_word_count():
    """An unstated counting convention made two gates invent their own rule and
    cost the first run real effort compressing correct prose.
    """
    text = (REFS / "voice.md").read_text(encoding="utf-8")
    assert "What counts toward the word count" in text
    assert "prose words only" in text
    for excluded in ("front matter", "fenced code blocks", "closing link list"):
        assert excluded in text, f"voice.md does not exclude {excluded!r}"


def test_gate_4_defers_to_voice_md_for_the_bound():
    """Gate 4 measures; voice.md defines. Two copies of the numbers drift."""
    text = (REFS / "gates.md").read_text(encoding="utf-8")
    assert "1,000" not in text and "1,500" not in text, (
        "gates.md restates the word-count numbers; voice.md owns them"
    )
    gate_4 = text[text.index("## Gate 4"):]
    assert "voice.md" in gate_4
    assert "python3" in gate_4, "Gate 4 must give a concrete way to count"
