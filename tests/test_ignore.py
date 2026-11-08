"""Tests for .minigitignore."""

import pytest

from minigit.changes import untracked_files
from minigit.index import Index
from minigit.worktree import iter_files


@pytest.fixture
def ignore(write):
    """Write a .minigitignore with the given lines."""

    def _ignore(*lines: str) -> None:
        write(".minigitignore", "".join(f"{line}\n" for line in lines))

    return _ignore


def staged(repo) -> list[str]:
    return [entry.path for entry in Index.load(repo)]


# -- the example from the issue ------------------------------------------


def test_add_dot_skips_ignored_files(repo, run, write, ignore):
    ignore("*.log", "build/", "secret.txt")
    write("app.py", "print(1)\n")
    write("app.log", "log\n")
    write("build/out.bin", "bin\n")
    write("secret.txt", "shh\n")
    assert run("add", ".").code == 0
    assert staged(repo) == [".minigitignore", "app.py"]


def test_status_does_not_list_ignored_files_as_untracked(repo, run, write, ignore):
    ignore("*.log", "build/", "secret.txt")
    write("app.py", "print(1)\n")
    write("app.log", "log\n")
    write("build/out.bin", "bin\n")
    write("secret.txt", "shh\n")
    out = run("status").out
    assert "\tapp.py" in out
    assert "app.log" not in out
    assert "build" not in out
    assert "secret.txt" not in out


# -- reading the ignore file ---------------------------------------------


def test_without_an_ignore_file_nothing_is_ignored(repo, write):
    write("app.log", "log\n")
    assert list(iter_files(repo)) == ["app.log"]


def test_blank_lines_and_comments_are_skipped(repo, write, ignore):
    ignore("", "# app.log", "   ", "  # indented comment")
    write("app.log", "log\n")
    write("# app.log", "a file whose name starts with a hash\n")
    assert list(iter_files(repo)) == ["# app.log", ".minigitignore", "app.log"]


def test_windows_line_endings(repo, write):
    write(".minigitignore", "*.log\r\nbuild/\r\n")
    write("app.log", "log\n")
    write("build/out.bin", "bin\n")
    assert list(iter_files(repo)) == [".minigitignore"]


# -- patterns without a slash match in any directory ---------------------


def test_extension_pattern_matches_in_every_directory(repo, write, ignore):
    ignore("*.log")
    write("app.log", "")
    write("src/debug.log", "")
    write("src/deep/trace.log", "")
    write("src/app.py", "")
    write("logbook.txt", "")
    assert list(iter_files(repo)) == [".minigitignore", "logbook.txt", "src/app.py"]


def test_plain_name_matches_files_and_directories_anywhere(repo, write, ignore):
    ignore("secret.txt", "tmp")
    write("secret.txt", "")
    write("docs/secret.txt", "")
    write("tmp/a.txt", "")
    write("src/tmp", "a file called tmp")
    write("docs/readme.md", "")
    assert list(iter_files(repo)) == [".minigitignore", "docs/readme.md"]


def test_matching_is_case_sensitive(repo, write, ignore):
    ignore("*.log")
    write("APP.LOG", "")
    assert list(iter_files(repo)) == [".minigitignore", "APP.LOG"]


# -- patterns ending in "/" match only directories -----------------------


def test_directory_pattern_skips_everything_inside(repo, write, ignore):
    ignore("build/")
    write("build/out.bin", "")
    write("build/sub/more.bin", "")
    write("src/build/nested.bin", "")
    write("src/app.py", "")
    assert list(iter_files(repo)) == [".minigitignore", "src/app.py"]


def test_directory_pattern_does_not_match_a_file(repo, write, ignore):
    ignore("build/")
    write("build", "a file, not a directory")
    assert list(iter_files(repo)) == [".minigitignore", "build"]


def test_directory_pattern_with_a_wildcard(repo, write, ignore):
    ignore("__pycache__/", ".venv/")
    write("__pycache__/a.pyc", "")
    write("src/__pycache__/b.pyc", "")
    write(".venv/bin/python", "")
    write("src/app.py", "")
    assert list(iter_files(repo)) == [".minigitignore", "src/app.py"]


# -- patterns containing "/" are anchored to the root --------------------


def test_slash_pattern_is_relative_to_the_root(repo, write, ignore):
    ignore("docs/secret.txt")
    write("docs/secret.txt", "")
    write("src/docs/secret.txt", "")
    assert list(iter_files(repo)) == [".minigitignore", "src/docs/secret.txt"]


def test_leading_slash_anchors_to_the_root(repo, write, ignore):
    ignore("/todo.txt")
    write("todo.txt", "")
    write("src/todo.txt", "")
    assert list(iter_files(repo)) == [".minigitignore", "src/todo.txt"]


def test_star_does_not_cross_a_slash(repo, write, ignore):
    ignore("src/*.py")
    write("src/a.py", "")
    write("src/pkg/b.py", "")
    assert list(iter_files(repo)) == [".minigitignore", "src/pkg/b.py"]


def test_anchored_directory_pattern(repo, write, ignore):
    ignore("docs/build/")
    write("docs/build/index.html", "")
    write("build/keep.txt", "")
    assert list(iter_files(repo)) == [".minigitignore", "build/keep.txt"]


# -- explicitly adding an ignored path -----------------------------------


def test_adding_an_ignored_file_is_an_error(repo, run, write, ignore):
    ignore("secret.txt")
    write("secret.txt", "shh\n")
    result = run("add", "secret.txt")
    assert result.code == 128
    assert result.err == "fatal: the following paths are ignored by .minigitignore:\nsecret.txt\n"
    assert "secret.txt" not in staged(repo)


def test_adding_a_file_inside_an_ignored_directory_is_an_error(repo, run, write, ignore):
    ignore("build/")
    write("build/out.bin", "bin\n")
    result = run("add", "build/out.bin")
    assert result.code == 128
    assert ".minigitignore" in result.err
    assert staged(repo) == []


def test_adding_an_ignored_directory_is_an_error(repo, run, write, ignore):
    ignore("build/")
    write("build/out.bin", "bin\n")
    result = run("add", "build")
    assert result.code == 128
    assert ".minigitignore" in result.err


def test_other_paths_are_still_staged(repo, run, write, ignore):
    ignore("*.log")
    write("app.py", "print(1)\n")
    write("app.log", "log\n")
    write("debug.log", "log\n")
    result = run("add", "app.py", "app.log", "debug.log")
    assert result.code == 128
    assert result.err.endswith("ignored by .minigitignore:\napp.log\ndebug.log\n")
    assert staged(repo) == ["app.py"]


def test_an_already_tracked_file_can_still_be_added(repo, run, write, ignore):
    write("app.log", "first\n")
    run("add", "app.log")
    ignore("*.log")
    write("app.log", "second\n")
    assert run("add", "app.log").code == 0
    assert run("cat-file", "-p", Index.load(repo).get("app.log").sha).out == "second\n"


def test_add_dot_still_stages_changes_to_tracked_files(repo, run, write, ignore):
    write("app.log", "first\n")
    run("add", "app.log")
    run("commit", "-m", "first")
    ignore("*.log")
    write("app.log", "second\n")
    write("new.log", "untracked, so still ignored\n")
    assert run("add", ".").code == 0
    assert staged(repo) == [".minigitignore", "app.log"]
    assert run("cat-file", "-p", Index.load(repo).get("app.log").sha).out == "second\n"


def test_add_dot_stages_tracked_files_inside_an_ignored_directory(repo, run, write, ignore):
    write("build/keep.txt", "first\n")
    run("add", "build/keep.txt")
    ignore("build/")
    write("build/keep.txt", "second\n")
    write("build/new.bin", "untracked, so still ignored\n")
    assert run("add", ".").code == 0
    assert staged(repo) == [".minigitignore", "build/keep.txt"]
    assert run("cat-file", "-p", Index.load(repo).get("build/keep.txt").sha).out == "second\n"


def test_ignored_file_works_from_a_subdirectory(repo, run, write, ignore, monkeypatch):
    ignore("*.log")
    write("src/debug.log", "log\n")
    monkeypatch.chdir(repo.worktree / "src")
    result = run("add", "debug.log")
    assert result.code == 128
    assert ".minigitignore" in result.err


# -- must agree with real Git --------------------------------------------


def test_untracked_files_match_real_git(repo, write, ignore, git):
    ignore("# comment", "", "*.log", "build/", "/todo.txt", "docs/secret.txt", "src/*.py")
    for path in [
        "app.log",
        "src/deep/trace.log",
        "build/out.bin",
        "src/build/x.bin",
        "build.txt",
        "todo.txt",
        "src/todo.txt",
        "docs/secret.txt",
        "src/docs/secret.txt",
        "src/a.py",
        "src/pkg/b.py",
        "keep.txt",
    ]:
        write(path, "x\n")
    expected = git("ls-files", "--others", "--exclude-from=.minigitignore", "--exclude=/.minigit/")
    assert sorted(untracked_files(repo)) == sorted(expected.splitlines())
