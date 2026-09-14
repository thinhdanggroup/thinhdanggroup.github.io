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
