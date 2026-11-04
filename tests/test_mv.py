"""Tests for minigit mv."""

from __future__ import annotations

from minigit.index import Index


def test_mv_single_file(repo, run, write):
    write("hello.txt", "hello\n")
    run("add", "hello.txt")

    result = run("mv", "hello.txt", "greeting.txt")
    assert result.code == 0

    assert not (repo.worktree / "hello.txt").exists()
    assert (repo.worktree / "greeting.txt").read_text() == "hello\n"

    index = Index.load(repo)
    assert "hello.txt" not in index
    assert "greeting.txt" in index


def test_mv_into_existing_directory(repo, run, write):
    write("notes.txt", "my notes\n")
    write("docs/readme.txt", "docs\n")
    run("add", "notes.txt", "docs/readme.txt")

    result = run("mv", "notes.txt", "docs/")
    assert result.code == 0

    assert not (repo.worktree / "notes.txt").exists()
    assert (repo.worktree / "docs" / "notes.txt").read_text() == "my notes\n"

    index = Index.load(repo)
    assert "notes.txt" not in index
    assert "docs/notes.txt" in index


def test_mv_into_existing_directory_without_trailing_slash(repo, run, write):
    write("notes.txt", "my notes\n")
    write("docs/readme.txt", "docs\n")
    run("add", "notes.txt", "docs/readme.txt")

    result = run("mv", "notes.txt", "docs")
    assert result.code == 0

    assert not (repo.worktree / "notes.txt").exists()
    assert (repo.worktree / "docs" / "notes.txt").read_text() == "my notes\n"

    index = Index.load(repo)
    assert "notes.txt" not in index
    assert "docs/notes.txt" in index


def test_mv_creates_parent_folders(repo, run, write):
    write("notes.txt", "hello\n")
    run("add", "notes.txt")

    result = run("mv", "notes.txt", "a/b/c/notes.txt")
    assert result.code == 0

    assert not (repo.worktree / "notes.txt").exists()
    assert (repo.worktree / "a" / "b" / "c" / "notes.txt").read_text() == "hello\n"

    index = Index.load(repo)
    assert "notes.txt" not in index
    assert "a/b/c/notes.txt" in index


def test_mv_whole_tracked_directory(repo, run, write):
    write("src/app.py", "print(1)\n")
    write("src/sub/util.py", "print(2)\n")
    run("add", "src/app.py", "src/sub/util.py")

    result = run("mv", "src", "lib")
    assert result.code == 0

    assert not (repo.worktree / "src").exists()
    assert (repo.worktree / "lib" / "app.py").read_text() == "print(1)\n"
    assert (repo.worktree / "lib" / "sub" / "util.py").read_text() == "print(2)\n"

    index = Index.load(repo)
    assert "src/app.py" not in index
    assert "src/sub/util.py" not in index
    assert "lib/app.py" in index
    assert "lib/sub/util.py" in index


def test_mv_directory_into_existing_directory(repo, run, write):
    write("src/app.py", "print(1)\n")
    write("docs/readme.txt", "docs\n")
    run("add", "src/app.py", "docs/readme.txt")

    result = run("mv", "src", "docs")
    assert result.code == 0

    assert not (repo.worktree / "src").exists()
    assert (repo.worktree / "docs" / "src" / "app.py").read_text() == "print(1)\n"

    index = Index.load(repo)
    assert "src/app.py" not in index
    assert "docs/src/app.py" in index


def test_mv_directory_destination_exists_error(repo, run, write):
    write("src/app.py", "print(1)\n")
    write("dest/other.txt", "other\n")
    run("add", "src/app.py", "dest/other.txt")

    # Trying to move directory into an already existing directory where target dir exists
    write("dest/src/app.py", "old\n")
    result = run("mv", "src", "dest")
    assert result.code == 128
    assert "destination already exists, source=src, destination=dest/src" in result.err


def test_mv_directory_force_overwrite(repo, run, write):
    write("src/app.py", "new app\n")
    write("dest/src/app.py", "old app\n")
    run("add", "src/app.py", "dest/src/app.py")

    result = run("mv", "-f", "src", "dest")
    assert result.code == 0

    assert not (repo.worktree / "src").exists()
    assert (repo.worktree / "dest" / "src" / "app.py").read_text() == "new app\n"

    index = Index.load(repo)
    assert "src/app.py" not in index
    assert "dest/src/app.py" in index


def test_mv_fails_when_source_does_not_exist(repo, run):
    result = run("mv", "ghost.txt", "x.txt")
    assert result.code == 128
    assert "bad source, source=ghost.txt, destination=x.txt" in result.err


def test_mv_fails_when_source_is_untracked(repo, run, write):
    write("ghost.txt", "untracked\n")
    result = run("mv", "ghost.txt", "x.txt")
    assert result.code == 128
    assert "not under version control, source=ghost.txt, destination=x.txt" in result.err


def test_mv_fails_when_destination_directory_does_not_exist(repo, run, write):
    write("hello.txt", "content\n")
    run("add", "hello.txt")

    result = run("mv", "hello.txt", "nonexistent/")
    assert result.code == 128
    assert (
        "destination directory does not exist, source=hello.txt, destination=nonexistent/"
        in result.err
    )


def test_mv_fails_when_destination_exists_without_force(repo, run, write):
    write("a.txt", "a\n")
    write("b.txt", "b\n")
    run("add", "a.txt", "b.txt")

    result = run("mv", "a.txt", "b.txt")
    assert result.code == 128
    assert "destination exists, source=a.txt, destination=b.txt" in result.err


def test_mv_force_overwrites_destination(repo, run, write):
    write("a.txt", "content a\n")
    write("b.txt", "content b\n")
    run("add", "a.txt", "b.txt")

    result = run("mv", "-f", "a.txt", "b.txt")
    assert result.code == 0

    assert not (repo.worktree / "a.txt").exists()
    assert (repo.worktree / "b.txt").read_text() == "content a\n"

    index = Index.load(repo)
    assert "a.txt" not in index
    assert "b.txt" in index


def test_mv_cannot_move_into_itself(repo, run, write):
    write("a.txt", "hello\n")
    run("add", "a.txt")

    result = run("mv", "a.txt", "a.txt")
    assert result.code == 128
    assert "can not move directory into itself" in result.err

    write("dir/sub.txt", "sub\n")
    run("add", "dir/sub.txt")

    result_dir = run("mv", "dir", "dir/child")
    assert result_dir.code == 128
    assert "can not move directory into itself" in result_dir.err


def test_mv_updates_status_and_agrees_with_git(repo, run, write, git):
    write("notes.txt", "hello world\n")
    run("add", "notes.txt")
    run("commit", "-m", "first")

    result = run("mv", "notes.txt", "docs/notes.txt")
    assert result.code == 0

    status_out = run("status").out
    assert "new file:   docs/notes.txt" in status_out
    assert "deleted:    notes.txt" in status_out

    run("commit", "-m", "move notes into docs")
    assert git("ls-tree", "-r", "--name-only", "HEAD").splitlines() == ["docs/notes.txt"]
    git("fsck", "--strict", "--no-dangling")
