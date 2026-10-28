import argparse

import pytest

from minigit.commands import discover
from minigit.errors import MinigitError
from minigit.index import HEADER, INDEX_FILE, Index, IndexEntry
from minigit.objects import flatten_tree

SHA = "ce013625030ba8dba906f756967f9e9ca394464a"


def test_save_and_load(repo):
    index = Index([IndexEntry("100644", SHA, "b.txt"), IndexEntry("100644", SHA, "a/c.txt")])
    index.save(repo)
    loaded = Index.load(repo)
    assert [e.path for e in loaded] == ["a/c.txt", "b.txt"]
    assert (repo.gitdir / INDEX_FILE).read_text().startswith("minigit-index 1\n")


def test_missing_index_is_empty(repo):
    assert len(Index.load(repo)) == 0


def test_bad_header(repo):
    (repo.gitdir / INDEX_FILE).write_text("DIRC binary stuff\n")
    with pytest.raises(MinigitError, match="unrecognised index"):
        Index.load(repo)


def test_file_replaces_directory_and_vice_versa():
    index = Index([IndexEntry("100644", SHA, "a/b.txt"), IndexEntry("100644", SHA, "a/c.txt")])
    index.add(IndexEntry("100644", SHA, "a"))
    assert [e.path for e in index] == ["a"]
    index.add(IndexEntry("100644", SHA, "a/d.txt"))
    assert [e.path for e in index] == ["a/d.txt"]


def test_remove():
    index = Index([IndexEntry("100644", SHA, "x")])
    index.remove("x")
    assert "x" not in index
    with pytest.raises(MinigitError):
        index.remove("x")


def test_write_tree_nests_directories(repo):
    index = Index([IndexEntry("100644", SHA, p) for p in ["top.txt", "src/a.py", "src/pkg/b.py"]])
    tree = index.write_tree(repo)
    assert sorted(flatten_tree(repo, tree)) == ["src/a.py", "src/pkg/b.py", "top.txt"]


def test_empty_index_writes_empty_tree(repo):
    assert Index().write_tree(repo) == "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def test_line_break_in_path_is_rejected():
    # A newline (or any str line break) in a file name would silently split
    # the entry into two lines and corrupt the index for every later command.
    for bad in ["a\nb.txt", "a\rb", "a\vb", "a\x85b", "a b"]:
        index = Index()
        with pytest.raises(MinigitError, match="line breaks"):
            index.add(IndexEntry("100644", SHA, bad))


def test_line_break_in_path_via_add_command(repo):
    (repo.worktree / "we\nird.txt").write_text("x")
    (repo.worktree / "ok.txt").write_text("y")
    add = discover()["add"].run
    with pytest.raises(MinigitError, match="line breaks"):
        add(argparse.Namespace(paths=["we\nird.txt", "ok.txt"]), repo)
    # The staging area stays usable: nothing was written for the bad name.
    assert list(Index.load(repo)) == []
    assert (repo.worktree / ".minigit" / "minigit-index").exists() is False


def test_corrupt_index_line_is_a_minigit_error(repo):
    (repo.gitdir / INDEX_FILE).write_text(f"{HEADER}\nnot-a-valid-line\n")
    with pytest.raises(MinigitError, match="corrupt line"):
        Index.load(repo)
