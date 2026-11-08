"""Tests for the rev-parse command."""

import pytest

from minigit.refs import head_commit


def _commit(repo, run, write, content: str, message: str) -> str:
    write("a.txt", content)
    run("add", "a.txt")
    assert run("commit", "-m", message).code == 0
    return head_commit(repo)


@pytest.fixture
def history(repo, run, write):
    """Two commits on main, with a tag on the first one. Returns the SHAs."""
    first = _commit(repo, run, write, "1\n", "first")
    run("tag", "v1.0")
    second = _commit(repo, run, write, "2\n", "second")
    return {"first": first, "second": second}


# Acceptance: accepts HEAD, branch names, tag names and full SHAs


def test_head_prints_full_sha(run, history):
    result = run("rev-parse", "HEAD")
    assert result.code == 0
    assert result.out == history["second"] + "\n"


def test_branch_name_prints_full_sha(run, history):
    result = run("rev-parse", "main")
    assert result.code == 0
    assert result.out == history["second"] + "\n"


def test_tag_name_prints_full_sha(run, history):
    result = run("rev-parse", "v1.0")
    assert result.code == 0
    assert result.out == history["first"] + "\n"


def test_full_sha_is_returned_unchanged(run, history):
    result = run("rev-parse", history["first"])
    assert result.code == 0
    assert result.out == history["first"] + "\n"


def test_output_is_forty_hex_characters(run, history):
    out = run("rev-parse", "HEAD").out.strip()
    assert len(out) == 40
    assert set(out) <= set("0123456789abcdef")


def test_matches_real_git(run, history, git):
    assert run("rev-parse", "HEAD").out == git("rev-parse", "HEAD")
    assert run("rev-parse", "v1.0").out == git("rev-parse", "v1.0")


# Acceptance: --short prints the first 7 characters


def test_short_prints_seven_characters(run, history):
    result = run("rev-parse", "--short", "main")
    assert result.code == 0
    assert result.out == history["second"][:7] + "\n"


def test_short_with_full_sha(run, history):
    result = run("rev-parse", "--short", history["first"])
    assert result.out == history["first"][:7] + "\n"


def test_short_with_head(run, history):
    result = run("rev-parse", "--short", "HEAD")
    assert result.out == history["second"][:7] + "\n"


# Acceptance: multiple revisions print one SHA per line


def test_multiple_revisions_one_per_line(run, history):
    result = run("rev-parse", "HEAD", "main", "v1.0")
    assert result.code == 0
    assert result.out == f"{history['second']}\n{history['second']}\n{history['first']}\n"


def test_multiple_revisions_with_short(run, history):
    result = run("rev-parse", "--short", "HEAD", "v1.0")
    assert result.out == f"{history['second'][:7]}\n{history['first'][:7]}\n"


def test_unknown_revision_among_many_prints_nothing(run, history):
    result = run("rev-parse", "HEAD", "nope")
    assert result.code == 128
    assert result.out == ""
    assert "fatal: unknown revision: nope" in result.err


# Error cases


def test_unknown_revision_is_fatal(run, history):
    result = run("rev-parse", "nope")
    assert result.code == 128
    assert result.out == ""
    assert result.err == "fatal: unknown revision: nope\n"


def test_head_before_first_commit_is_fatal(repo, run):
    result = run("rev-parse", "HEAD")
    assert result.code == 128
    assert "HEAD does not point to a commit yet" in result.err


def test_requires_at_least_one_revision(run, history):
    with pytest.raises(SystemExit) as excinfo:
        run("rev-parse")
    assert excinfo.value.code == 2
