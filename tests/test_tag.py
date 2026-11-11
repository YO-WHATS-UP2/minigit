"""Tests for minigit tag command."""

import subprocess

import pytest

from minigit.refs import head_commit, update_ref

VALID_NAMES = ["v1.0", "release/2.0", "nightly/2023/11", "v1.lock.bak", "lock", "v1@", "v1{x"]

# Names real Git refuses: see `git help check-ref-format`.
INVALID_NAMES = [
    "",
    "bad name",
    "v1..2",
    "v1.lock",
    "v1.lock/x",
    "v1~1",
    "v1^",
    "v1:x",
    "v1?",
    "v1*",
    "v1[",
    "v1\\x",
    ".hidden",
    "v1/.hidden",
    "v1.",
    "/v1",
    "v1/",
    "v1//x",
    "v1@{0}",
    "v1\tx",
    "v1\nx",
    "v1\x7fx",
]


def test_tag_creates_at_head(repo, run, write):
    write("a.txt", "hello\n")
    run("add", "a.txt")
    run("commit", "-m", "first commit")
    sha = head_commit(repo)

    result = run("tag", "v1.0")
    assert result.code == 0
    assert (repo.gitdir / "refs" / "tags" / "v1.0").read_text().strip() == sha


def test_tag_creates_at_explicit_revision(repo, run, write):
    write("a.txt", "1\n")
    run("add", "a.txt")
    run("commit", "-m", "first")
    first_sha = head_commit(repo)

    write("a.txt", "2\n")
    run("add", "a.txt")
    run("commit", "-m", "second")
    second_sha = head_commit(repo)
    assert first_sha != second_sha

    result = run("tag", "v1.0", first_sha)
    assert result.code == 0
    assert (repo.gitdir / "refs" / "tags" / "v1.0").read_text().strip() == first_sha

    result2 = run("tag", "v2.0", "HEAD")
    assert result2.code == 0
    assert (repo.gitdir / "refs" / "tags" / "v2.0").read_text().strip() == second_sha


def test_tag_list_empty(repo, run):
    result = run("tag")
    assert result.code == 0
    assert result.out == ""


def test_tag_list_sorted(repo, run, write):
    write("a.txt", "hello\n")
    run("add", "a.txt")
    run("commit", "-m", "first")

    run("tag", "v2.0")
    run("tag", "v1.0")
    run("tag", "beta")
    run("tag", "alpha")

    result = run("tag")
    assert result.code == 0
    assert result.out == "alpha\nbeta\nv1.0\nv2.0\n"


def test_tag_refuse_duplicate(repo, run, write):
    write("a.txt", "hello\n")
    run("add", "a.txt")
    run("commit", "-m", "first")

    assert run("tag", "v1.0").code == 0

    result = run("tag", "v1.0")
    assert result.code == 128
    assert "tag 'v1.0' already exists" in result.err


def test_delete_tag(repo, run, write):
    write("a.txt", "hello\n")
    run("add", "a.txt")
    run("commit", "-m", "first")
    sha = head_commit(repo)
    assert sha is not None

    run("tag", "v1.0")
    assert (repo.gitdir / "refs" / "tags" / "v1.0").is_file()

    result = run("tag", "-d", "v1.0")
    assert result.code == 0
    assert result.out == f"Deleted tag 'v1.0' (was {sha[:7]})\n"
    assert not (repo.gitdir / "refs" / "tags" / "v1.0").exists()


def test_delete_missing_tag(repo, run):
    result = run("tag", "-d", "nonexistent")
    assert result.code == 128
    assert "tag 'nonexistent' not found" in result.err


def test_resolve_tag_via_cat_file(repo, run, write):
    write("a.txt", "hello\n")
    run("add", "a.txt")
    run("commit", "-m", "first commit")
    sha = head_commit(repo)
    assert sha is not None

    run("tag", "v1.0")
    result = run("cat-file", "-p", "v1.0")
    assert result.code == 0
    assert result.out.startswith("tree ")
    assert f"[main (root-commit) {sha[:7]}]" not in result.out  # ensure it printed commit object
    assert "first commit" in result.out


def test_tag_without_commits_fails(repo, run):
    result = run("tag", "v1.0")
    assert result.code == 128
    assert "HEAD does not point to a commit yet" in result.err


def test_tag_invalid_revision_fails(repo, run, write):
    write("a.txt", "hello\n")
    run("add", "a.txt")
    run("commit", "-m", "first")

    result = run("tag", "v1.0", "nonexistent-branch-or-sha")
    assert result.code == 128
    assert "unknown revision: nonexistent-branch-or-sha" in result.err


def test_tag_rejects_non_sha_file_as_revision(repo, run):
    (repo.gitdir / "config").write_text("[core]\nrepositoryformatversion = 0\n")

    result = run("tag", "badtag", "config")

    assert result.code == 128
    assert "unknown revision: config" in result.err
    assert not (repo.gitdir / "refs" / "tags" / "badtag").exists()


def test_tag_delete_without_name_fails(repo, run):
    result = run("tag", "-d")
    assert result.code == 128
    assert "tag name required" in result.err


def test_tag_delete_with_revision_fails(repo, run, write):
    write("a.txt", "hello\n")
    run("add", "a.txt")
    run("commit", "-m", "first")
    run("tag", "v1.0")

    result = run("tag", "-d", "v1.0", "HEAD")
    assert result.code == 128
    assert "cannot specify revision when deleting a tag" in result.err


def test_tag_git_compat(repo, run, write, git):
    write("hello.txt", "hello\n")
    run("add", "hello.txt")
    run("commit", "-m", "First commit")
    run("tag", "v1.0")

    # Real git can list and resolve the tag created by minigit
    assert git("tag").strip() == "v1.0"
    assert git("rev-parse", "v1.0").strip() == head_commit(repo)


def test_tag_lists_and_protects_packed_tags(repo, run):
    (repo.gitdir / "packed-refs").write_text("2" * 40 + " refs/tags/v1.0\n")
    assert run("tag").out == "v1.0\n"
    result = run("tag", "v1.0", "HEAD")
    assert result.code != 0
    assert "already exists" in result.err


def test_tag_delete_packed_tag_is_a_clear_error(repo, run):
    (repo.gitdir / "packed-refs").write_text("2" * 40 + " refs/tags/v1.0\n")
    result = run("tag", "-d", "v1.0")
    assert result.code != 0
    assert "cannot delete packed tag" in result.err


# -- tag names ----------------------------------------------------------------


@pytest.mark.parametrize("name", VALID_NAMES)
def test_tag_accepts_valid_name(repo, run, write, name):
    write("a.txt", "hello\n")
    run("add", "a.txt")
    run("commit", "-m", "first")

    result = run("tag", name)
    assert result.code == 0
    assert result.err == ""
    assert run("tag").out == f"{name}\n"
    assert run("rev-parse", name).out == head_commit(repo) + "\n"


@pytest.mark.parametrize("name", INVALID_NAMES)
def test_tag_rejects_invalid_name(repo, run, write, name):
    write("a.txt", "hello\n")
    run("add", "a.txt")
    run("commit", "-m", "first")

    result = run("tag", name)
    assert result.code == 128
    assert result.out == ""
    assert result.err == f"fatal: '{name}' is not a valid tag name.\n"
    # Nothing was written: on Windows "v1:x" used to leave a broken tag called "v1".
    assert list((repo.gitdir / "refs" / "tags").iterdir()) == []


def test_tag_rejects_leading_dash(repo, run, write):
    write("a.txt", "hello\n")
    run("add", "a.txt")
    run("commit", "-m", "first")

    # "--" stops argparse from reading "-v1" as an option.
    result = run("tag", "--", "-v1")
    assert result.code == 128
    assert result.err == "fatal: '-v1' is not a valid tag name.\n"
    assert run("tag").out == ""


def test_tag_invalid_name_with_revision_fails(repo, run, write):
    write("a.txt", "hello\n")
    run("add", "a.txt")
    run("commit", "-m", "first")

    result = run("tag", "bad name", "HEAD")
    assert result.code == 128
    assert "'bad name' is not a valid tag name." in result.err
    assert run("tag").out == ""


def test_tag_empty_name_is_not_a_request_to_list(repo, run, write):
    write("a.txt", "hello\n")
    run("add", "a.txt")
    run("commit", "-m", "first")
    run("tag", "v1.0")

    result = run("tag", "")
    assert result.code == 128
    assert result.out == ""
    assert result.err == "fatal: '' is not a valid tag name.\n"


def test_tag_with_invalid_name_can_still_be_deleted(repo, run):
    # Left behind by a minigit that didn't check tag names yet.
    update_ref(repo, "refs/tags/bad name", "1" * 40)

    result = run("tag", "-d", "bad name")
    assert result.code == 0
    assert run("tag").out == ""


def test_tag_names_match_real_git(repo, run, write, git):
    write("a.txt", "hello\n")
    run("add", "a.txt")
    run("commit", "-m", "first")

    for name in VALID_NAMES + INVALID_NAMES:
        ours = run("tag", name).code == 0
        if ours:
            run("tag", "-d", name)  # make room for real Git's tag of the same name
        try:
            git("tag", name)
            theirs = True
        except subprocess.CalledProcessError:
            theirs = False
        assert ours == theirs, f"minigit and git disagree about {name!r}"

    # Real Git made exactly the tags minigit accepted, and both list them all.
    assert sorted(git("tag").splitlines()) == sorted(VALID_NAMES)
    assert run("tag").out.splitlines() == sorted(VALID_NAMES)
