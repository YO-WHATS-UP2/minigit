"""Shared test fixtures.

Most tests look like this:

    def test_something(repo, run, write):
        write("hello.txt", "hello\\n")
        run("add", "hello.txt")
        result = run("commit", "-m", "first")
        assert result.code == 0
        assert "first" in result.out
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from minigit.cli import main
from minigit.repo import Repository

# A fixed author and time, so every commit gets the same SHA on every run.
AUTHOR_ENV = {
    "MINIGIT_AUTHOR_NAME": "Ada Lovelace",
    "MINIGIT_AUTHOR_EMAIL": "ada@example.com",
    "MINIGIT_AUTHOR_DATE": "1700000000 +0530",
}


@dataclass
class Result:
    code: int
    out: str
    err: str


@pytest.fixture
def workdir(tmp_path, monkeypatch) -> Path:
    """An empty directory that the test runs inside, with a fixed commit author."""
    monkeypatch.chdir(tmp_path)
    for key, value in AUTHOR_ENV.items():
        monkeypatch.setenv(key, value)
    return tmp_path


@pytest.fixture
def run(capsys):
    """Run a minigit command in-process and capture what it prints."""

    def _run(*args: str) -> Result:
        code = main(list(args))
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)

    return _run


@pytest.fixture
def repo(workdir, run) -> Repository:
    """A freshly initialised, empty repository in ``workdir``."""
    assert run("init").code == 0
    return Repository(workdir)


@pytest.fixture
def write(workdir):
    """Create a file (and any parent folders) in the working tree."""

    def _write(path: str, content: str | bytes) -> Path:
        full = workdir / path
        full.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            full.write_text(content, encoding="utf-8", newline="")
        else:
            full.write_bytes(content)
        return full

    return _write


@pytest.fixture
def git(workdir):
    """Run *real* Git against the minigit repository to check compatibility.

    Tests that use this are skipped automatically if Git isn't installed.
    """
    if shutil.which("git") is None:
        pytest.skip("real git is not installed")

    def _git(*args: str) -> str:
        env = {**os.environ, "GIT_DIR": str(workdir / ".minigit"), "GIT_WORK_TREE": str(workdir)}
        done = subprocess.run(
            ["git", *args], cwd=workdir, env=env, capture_output=True, text=True, check=True
        )
        return done.stdout

    return _git
