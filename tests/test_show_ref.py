"""Tests for minigit show-ref."""

import os
import subprocess

import pytest

from minigit.refs import head_commit


def _real_git_show_ref(workdir, *args):
    env = {**os.environ, "GIT_DIR": str(workdir / ".minigit"), "GIT_WORK_TREE": str(workdir)}
    done = subprocess.run(
        ["git", "show-ref", *args],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def _make_commit_with_tag(repo, run, write):
    write("a.txt", "hello\n")
    run("add", "a.txt")
    run("commit", "-m", "first commit")
    run("tag", "v1.0")
    return head_commit(repo)


def test_show_ref_lists_heads_then_tags(repo, run, write):
    sha = _make_commit_with_tag(repo, run, write)

    result = run("show-ref")
    assert result.code == 0
    assert result.out == f"{sha} refs/heads/main\n{sha} refs/tags/v1.0\n"


def test_show_ref_matches_git(repo, run, write, git, workdir):
    _make_commit_with_tag(repo, run, write)

    assert run("show-ref").out == _real_git_show_ref(workdir)


def test_show_ref_heads_filter(repo, run, write):
    sha = _make_commit_with_tag(repo, run, write)

    result = run("show-ref", "--heads")
    assert result.code == 0
    assert result.out == f"{sha} refs/heads/main\n"


def test_show_ref_tags_filter(repo, run, write):
    sha = _make_commit_with_tag(repo, run, write)

    result = run("show-ref", "--tags")
    assert result.code == 0
    assert result.out == f"{sha} refs/tags/v1.0\n"


def test_show_ref_verify_existing(repo, run, write):
    sha = _make_commit_with_tag(repo, run, write)

    result = run("show-ref", "--verify", "refs/heads/main")
    assert result.code == 0
    assert result.out == f"{sha} refs/heads/main\n"


def test_show_ref_verify_missing(repo, run):
    result = run("show-ref", "--verify", "refs/heads/nope")
    assert result.code == 128
    assert result.out == ""
    assert "fatal: 'refs/heads/nope' - not a valid ref" in result.err


def test_show_ref_empty_repo(repo, run):
    result = run("show-ref")
    assert result.code == 1
    assert result.out == ""
