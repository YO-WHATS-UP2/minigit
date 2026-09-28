"""Tests for minigit tag command."""

from minigit.refs import head_commit


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
