from argparse import ArgumentParser, Namespace

import pytest

from minigit.commands import commit_tree, write_tree
from minigit.errors import MinigitError
from minigit.identity import author_signature
from minigit.index import Index
from minigit.objects import read_commit, write_object
from minigit.refs import head_commit, head_target, iter_refs


def test_write_tree_empty_index(repo, capsys):
    assert write_tree.run(None, repo) == 0
    assert capsys.readouterr().out == "4b825dc642cb6eb9a060e54bf8d69288fbee4904\n"


def test_write_tree_uses_staged_content(repo, run, write, capsys):
    write("hello.txt", "hello\n")
    run("add", "hello.txt")
    assert write_tree.run(None, repo) == 0
    staged_tree = capsys.readouterr().out

    write("hello.txt", "unstaged edit\n")
    assert write_tree.run(None, repo) == 0
    assert capsys.readouterr().out == staged_tree


def test_write_tree_sha_matches_git(repo, run, write, git, capsys):
    write("hello.txt", "hello\n")
    write("src/app.py", "print(1)\n")
    run("add", ".")
    git("add", "hello.txt", "src/app.py")

    assert write_tree.run(None, repo) == 0
    assert capsys.readouterr().out == git("write-tree")


def test_commit_tree_creates_root_commit(repo, capsys):
    tree = Index().write_tree(repo)
    args = Namespace(tree=tree, parent=[], message=["Title", "Body text."])
    assert commit_tree.run(args, repo) == 0
    commit = read_commit(repo, capsys.readouterr().out.strip())
    assert commit.tree == tree
    assert commit.parents == []
    assert commit.message == "Title\n\nBody text.\n"
    assert head_target(repo) == "refs/heads/main"
    assert head_commit(repo) is None
    assert iter_refs(repo) == {}


def test_commit_tree_parents_do_not_move_branch(repo, run, write, capsys):
    write("hello.txt", "hello\n")
    run("add", ".")
    run("commit", "-m", "first")
    first = head_commit(repo)
    tree = read_commit(repo, first).tree

    args = Namespace(tree=tree, parent=[first], message=["second"])
    assert commit_tree.run(args, repo) == 0
    second = capsys.readouterr().out.strip()
    assert read_commit(repo, second).parents == [first]

    args = Namespace(tree=tree, parent=[first, second], message=["merge"])
    assert commit_tree.run(args, repo) == 0
    merge = capsys.readouterr().out.strip()
    assert read_commit(repo, merge).parents == [first, second]
    assert head_target(repo) == "refs/heads/main"
    assert head_commit(repo) == first
    assert iter_refs(repo) == {"main": first}


def test_commit_tree_rejects_non_tree(repo):
    blob = write_object(repo, b"hello\n")
    args = Namespace(tree=blob, parent=[], message=["first"])
    with pytest.raises(MinigitError, match="not a tree"):
        commit_tree.run(args, repo)


def test_commit_tree_rejects_non_commit_parent(repo):
    tree = Index().write_tree(repo)
    args = Namespace(tree=tree, parent=[tree], message=["first"])
    with pytest.raises(MinigitError, match="not a commit"):
        commit_tree.run(args, repo)


def test_commit_tree_sha_matches_git(repo, run, write, git, monkeypatch, capsys):
    write("hello.txt", "hello\n")
    write("src/app.py", "print(1)\n")
    run("add", ".")
    tree = Index.load(repo).write_tree(repo)
    signature = author_signature()
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", signature.name)
        monkeypatch.setenv(f"GIT_{role}_EMAIL", signature.email)
        monkeypatch.setenv(f"GIT_{role}_DATE", f"{signature.timestamp} {signature.tz}")

    parser = ArgumentParser()
    commit_tree.configure(parser)
    args = parser.parse_args([tree, "-m", "Title", "-m", "Body text."])
    assert commit_tree.run(args, repo) == 0
    assert capsys.readouterr().out == git("commit-tree", tree, "-m", "Title", "-m", "Body text.")
