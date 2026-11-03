"""Tests for the global ``-C <path>`` option."""

from pathlib import Path

import pytest


def test_c_missing_directory(workdir, run):
    result = run("-C", "nonexistent", "status")
    assert result.code == 128
    assert result.out == ""
    assert result.err == "fatal: cannot change to 'nonexistent': No such file or directory\n"


def test_c_missing_directory_multiple(workdir, run):
    (workdir / "sub").mkdir()
    result = run("-C", "sub", "-C", "nonexistent", "status")
    assert result.code == 128
    assert result.out == ""
    assert result.err == "fatal: cannot change to 'nonexistent': No such file or directory\n"


def test_c_not_a_directory(workdir, run, write):
    write("file.txt", "hello\n")
    result = run("-C", "file.txt", "status")
    assert result.code == 128
    assert result.out == ""
    assert result.err == "fatal: cannot change to 'file.txt': Not a directory\n"


def test_c_init_in_subdirectory(workdir, run):
    (workdir / "sub").mkdir()
    result = run("-C", "sub", "init")
    assert result.code == 0
    assert "Initialized empty minigit repository" in result.out
    assert (workdir / "sub" / ".minigit").is_dir()
    assert not (workdir / ".minigit").exists()


def test_c_multiple_options_combine(workdir, run):
    (workdir / "a" / "b").mkdir(parents=True)
    result = run("-C", "a", "-C", "b", "init")
    assert result.code == 0
    assert (workdir / "a" / "b" / ".minigit").is_dir()
    assert not (workdir / "a" / ".minigit").exists()
    assert not (workdir / ".minigit").exists()


def test_c_with_commands_workflow(workdir, run, write):
    sub = workdir / "repo_dir"
    sub.mkdir()
    assert run("-C", "repo_dir", "init").code == 0

    write("repo_dir/hello.txt", "hello world\n")
    assert run("-C", "repo_dir", "add", "hello.txt").code == 0

    commit_res = run("-C", "repo_dir", "commit", "-m", "first commit")
    assert commit_res.code == 0
    assert "first commit" in commit_res.out

    status_res = run("-C", "repo_dir", "status")
    assert status_res.code == 0
    assert "nothing to commit, working tree clean" in status_res.out

    log_res = run("-C", "repo_dir", "log")
    assert log_res.code == 0
    assert "first commit" in log_res.out

    ls_res = run("-C", "repo_dir", "ls-files")
    assert ls_res.code == 0
    assert "hello.txt\n" == ls_res.out


def test_c_does_not_leak_chdir(workdir, run):
    start = Path.cwd()
    (workdir / "sub").mkdir()
    run("-C", "sub", "init")
    assert Path.cwd() == start

    run("-C", "nonexistent", "status")
    assert Path.cwd() == start


def test_c_without_space(workdir, run):
    (workdir / "sub2").mkdir()
    result = run("-Csub2", "init")
    assert result.code == 0
    assert (workdir / "sub2" / ".minigit").is_dir()


def test_c_unknown_command(workdir, run):
    (workdir / "sub").mkdir()
    result = run("-C", "sub", "comit")
    assert result.code == 1
    assert "minigit: 'comit' is not a minigit command. See 'minigit --help'." in result.err
    assert "commit" in result.err


def test_c_with_double_dash(workdir, run):
    (workdir / "sub3").mkdir()
    result = run("-C", "sub3", "--", "init")
    assert result.code == 0
    assert (workdir / "sub3" / ".minigit").is_dir()


def test_c_missing_argument(workdir, run, capsys):
    with pytest.raises(SystemExit) as exc:
        run("-C")
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "error: argument -C: expected one argument" in captured.err


def test_c_in_help(workdir, run):
    result = run()
    assert result.code == 1
    assert "-C <path>" in result.out
    assert "run as if minigit was started in <path>" in result.out
