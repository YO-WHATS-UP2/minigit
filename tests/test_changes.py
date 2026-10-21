"""Tests for the HEAD / index / working tree comparison."""

from minigit.changes import staged_changes, unstaged_changes, untracked_files


def test_nothing_staged_in_a_fresh_repository(repo):
    assert staged_changes(repo) == {}
    assert unstaged_changes(repo) == {}
    assert untracked_files(repo) == []


def test_before_the_first_commit_every_staged_file_is_added(repo, run, write):
    write("a.txt", "a\n")
    run("add", "a.txt")
    assert staged_changes(repo) == {"a.txt": "added"}


def test_staged_modification_and_deletion(repo, run, write):
    write("a.txt", "a\n")
    write("b.txt", "b\n")
    run("add", "a.txt", "b.txt")
    run("commit", "-m", "first")

    write("a.txt", "changed\n")
    (repo.worktree / "b.txt").unlink()
    run("add", "a.txt", "b.txt")

    assert staged_changes(repo) == {"a.txt": "modified", "b.txt": "deleted"}


def test_committed_file_left_alone_is_not_a_change(repo, run, write):
    write("a.txt", "a\n")
    run("add", "a.txt")
    run("commit", "-m", "first")
    assert staged_changes(repo) == {}
    assert unstaged_changes(repo) == {}


def test_unstaged_edit_and_delete(repo, run, write):
    write("a.txt", "a\n")
    write("b.txt", "b\n")
    run("add", "a.txt", "b.txt")
    run("commit", "-m", "first")

    write("a.txt", "edited\n")
    (repo.worktree / "b.txt").unlink()

    assert unstaged_changes(repo) == {"a.txt": "modified", "b.txt": "deleted"}
    assert staged_changes(repo) == {}


def test_untracked_files_exclude_staged_ones(repo, run, write):
    write("tracked.txt", "t\n")
    write("loose.txt", "l\n")
    write("nested/deep.txt", "d\n")
    run("add", "tracked.txt")
    assert untracked_files(repo) == ["loose.txt", "nested/deep.txt"]


def test_staging_an_edit_moves_it_from_unstaged_to_staged(repo, run, write):
    write("a.txt", "a\n")
    run("add", "a.txt")
    run("commit", "-m", "first")

    write("a.txt", "edited\n")
    assert unstaged_changes(repo) == {"a.txt": "modified"}

    run("add", "a.txt")
    assert unstaged_changes(repo) == {}
    assert staged_changes(repo) == {"a.txt": "modified"}
