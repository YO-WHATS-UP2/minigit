"""Tests for minigit ls-tree, including comparisons with real Git."""

import pytest

from minigit.objects import (
    EXEC_MODE,
    FILE_MODE,
    TREE_MODE,
    TreeEntry,
    object_path,
    read_commit,
    read_tree,
    serialize_tree,
    write_object,
)
from minigit.refs import resolve, update_ref


@pytest.fixture
def committed(repo, run, write):
    for path in ("hello.txt", "src/app.py", "src/lib/util.py", "a.c", "a/b.txt", "a0"):
        write(path, f"contents of {path}\n")
    assert run("add", ".").code == 0
    assert run("commit", "-m", "first").code == 0
    assert run("branch", "topic").code == 0
    return repo


@pytest.mark.parametrize(
    "revision", ["HEAD", "topic", "commit", "short-commit", "tree", "short-tree"]
)
@pytest.mark.parametrize("flags", [(), ("-r",), ("--name-only",), ("--name-only", "-r")])
def test_matches_git(committed, run, git, revision, flags):
    commit = resolve(committed, "HEAD")
    tree = read_commit(committed, commit).tree
    revision = {
        "commit": commit,
        "short-commit": commit[:7],
        "tree": tree,
        "short-tree": tree[:7],
    }.get(revision, revision)

    result = run("ls-tree", *flags, revision)

    assert result.code == 0
    assert result.err == ""
    assert result.out == git("ls-tree", *flags, revision)


def test_recursive_paths_and_order(committed, run, git):
    result = run("ls-tree", "-r", "--name-only", "HEAD")
    assert result.code == 0
    assert result.out == "a.c\na/b.txt\na0\nhello.txt\nsrc/app.py\nsrc/lib/util.py\n"
    assert result.out == git("ls-tree", "-r", "--name-only", "HEAD")


def test_modes_types_and_shas(repo, run, git):
    blob = write_object(repo, b"hello\n")
    subtree = write_object(repo, serialize_tree([TreeEntry(FILE_MODE, "app.py", blob)]), "tree")
    tree = write_object(
        repo,
        serialize_tree(
            [
                TreeEntry(FILE_MODE, "hello.txt", blob),
                TreeEntry(EXEC_MODE, "run.sh", blob),
                TreeEntry(TREE_MODE, "src", subtree),
            ]
        ),
        "tree",
    )

    result = run("ls-tree", tree)
    assert result.code == 0
    assert result.out == (
        f"100644 blob {blob}\thello.txt\n100755 blob {blob}\trun.sh\n040000 tree {subtree}\tsrc\n"
    )
    assert result.out == git("ls-tree", tree)
    assert run("ls-tree", "-r", tree).out == git("ls-tree", "-r", tree)


@pytest.mark.parametrize("flags", [(), ("-r",), ("--name-only",), ("-r", "--name-only")])
def test_empty_tree(repo, run, git, flags):
    tree = write_object(repo, b"", "tree")
    result = run("ls-tree", *flags, tree)
    assert result.code == 0
    assert result.out == git("ls-tree", *flags, tree) == ""


@pytest.mark.parametrize("flags", [(), ("-r",)])
def test_empty_subdirectory(repo, run, git, flags):
    empty = write_object(repo, b"", "tree")
    tree = write_object(repo, serialize_tree([TreeEntry(TREE_MODE, "empty", empty)]), "tree")
    result = run("ls-tree", *flags, tree)
    assert result.code == 0
    assert result.out == git("ls-tree", *flags, tree)


@pytest.mark.parametrize("revision", ["no-such-revision", "0" * 40])
def test_invalid_revision(repo, run, revision):
    result = run("ls-tree", revision)
    assert result.code == 128
    assert result.out == ""
    assert f"fatal: unknown revision: {revision}" in result.err


def test_unborn_head(repo, run):
    result = run("ls-tree", "HEAD")
    assert result.code == 128
    assert result.out == ""
    assert "fatal: HEAD does not point to a commit yet" in result.err


@pytest.mark.parametrize("obj_type", ["blob", "tag"])
def test_non_tree_or_commit(repo, run, obj_type):
    sha = write_object(repo, b"hello\n", obj_type)
    result = run("ls-tree", sha)
    assert result.code == 128
    assert result.out == ""
    assert f"fatal: object {sha} is a {obj_type}, not a tree or commit" in result.err


def test_missing_object(repo, run):
    missing = "0" * 40
    update_ref(repo, "refs/heads/broken", missing)
    result = run("ls-tree", "broken")
    assert result.code == 128
    assert result.out == ""
    assert f"fatal: not a valid object name: {missing}" in result.err


@pytest.mark.parametrize("recursive", [False, True])
def test_missing_tree(committed, run, recursive):
    tree = read_commit(committed, resolve(committed, "HEAD")).tree
    if recursive:
        tree = next(entry.sha for entry in read_tree(committed, tree) if entry.is_tree)
    object_path(committed, tree).unlink()

    result = run("ls-tree", *(["-r"] if recursive else []), "HEAD")
    assert result.code == 128
    assert result.out == ""
    assert f"fatal: not a valid object name: {tree}" in result.err


def test_uses_committed_snapshot(committed, run, write, git):
    expected = git("ls-tree", "-r", "HEAD")
    write("hello.txt", "uncommitted edit\n")
    write("untracked.txt", "untracked\n")
    assert run("add", "hello.txt", "untracked.txt").code == 0
    result = run("ls-tree", "-r", "HEAD")
    assert result.code == 0
    assert result.out == expected
