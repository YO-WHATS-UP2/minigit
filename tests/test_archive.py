"""Tests for minigit archive."""

from __future__ import annotations

import itertools
import tarfile
import time
import zipfile
from pathlib import Path

import pytest

from minigit.objects import EXEC_MODE, FILE_MODE, TreeEntry, serialize_tree, write_object

COMMIT_TIME = 1700000000  # the fixed author date used by the test fixtures

FILES = {
    "README.md": b"# hello\n",
    "src/app.py": b"print(1)\n",
    "data.bin": b"\x00\xff\r\n",  # binary and CRLF must survive untouched
}


def _commit(run, write, files: dict[str, bytes]) -> None:
    for path, content in files.items():
        write(path, content)
    assert run("add", *files).code == 0
    assert run("commit", "-m", "first").code == 0


def _commit_tree(repo, run, entries: list[tuple[str, str, bytes]]) -> str:
    """Commit a hand-made flat tree of (mode, name, content); `add` can't set modes."""
    tree_entries = [TreeEntry(mode, name, write_object(repo, data)) for mode, name, data in entries]
    tree = write_object(repo, serialize_tree(tree_entries), "tree")
    return run("commit-tree", tree, "-m", "hand-made").out.strip()


def _contents(path: Path) -> dict[str, bytes]:
    """Open a zip or tar(.gz) and return {name: bytes}."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            return {name: zf.read(name) for name in zf.namelist()}
    with tarfile.open(path, "r:*") as tf:
        return {m.name: tf.extractfile(m).read() for m in tf.getmembers()}  # type: ignore[union-attr]


def _kind(path: Path) -> str:
    if zipfile.is_zipfile(path):
        return "zip"
    if path.read_bytes()[:2] == b"\x1f\x8b":
        return "tar.gz"
    tarfile.open(path, "r:").close()  # raises if this is not a plain tar
    return "tar"


@pytest.fixture
def committed(repo, run, write):
    _commit(run, write, FILES)
    return repo


# The two examples from the issue


def test_zip_of_a_tag(committed, run, workdir):
    run("tag", "v1.0")
    assert run("archive", "-o", "release.zip", "v1.0").code == 0
    assert _contents(workdir / "release.zip") == FILES


def test_tar_gz_with_prefix(committed, run, workdir):
    result = run("archive", "--format=tar.gz", "--prefix=minigit-1.0/", "-o", "r.tar.gz", "HEAD")
    assert result.code == 0
    assert _kind(workdir / "r.tar.gz") == "tar.gz"
    assert _contents(workdir / "r.tar.gz") == {f"minigit-1.0/{p}": c for p, c in FILES.items()}


# --format and guessing from the filename


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("r.zip", "zip"), ("r.tar", "tar"), ("r.tar.gz", "tar.gz"), ("r.tgz", "tar.gz")],
)
def test_format_is_guessed_from_filename(committed, run, workdir, filename, expected):
    assert run("archive", "-o", filename, "HEAD").code == 0
    assert _kind(workdir / filename) == expected


def test_explicit_format_wins_over_filename(committed, run, workdir):
    assert run("archive", "--format=tar", "-o", "out.zip", "HEAD").code == 0
    assert _kind(workdir / "out.zip") == "tar"


def test_unguessable_name_needs_a_format(committed, run, workdir):
    result = run("archive", "-o", "release.rar", "HEAD")
    assert result.code == 128
    assert "cannot guess the archive format" in result.err
    assert not (workdir / "release.rar").exists()


# --prefix


@pytest.mark.parametrize("prefix", ["proj/", "proj"])
def test_prefix_puts_everything_in_a_folder(committed, run, workdir, prefix):
    assert run("archive", f"--prefix={prefix}", "-o", "p.tar", "HEAD").code == 0
    assert set(_contents(workdir / "p.tar")) == {f"proj/{p}" for p in FILES}


@pytest.mark.parametrize("bad", ["/abs/", "../escape/"])
def test_prefix_cannot_escape_the_folder(committed, run, bad):
    result = run("archive", f"--prefix={bad}", "-o", "bad.zip", "HEAD")
    assert result.code == 128
    assert "invalid prefix" in result.err


# Timestamps and reproducibility


def test_files_get_the_commit_timestamp(committed, run, workdir):
    assert run("archive", "-o", "t.zip", "HEAD").code == 0
    assert run("archive", "-o", "t.tar", "HEAD").code == 0
    with zipfile.ZipFile(workdir / "t.zip") as zf:
        assert {i.date_time for i in zf.infolist()} == {time.gmtime(COMMIT_TIME)[:6]}
    with tarfile.open(workdir / "t.tar") as tf:
        assert {m.mtime for m in tf.getmembers()} == {COMMIT_TIME}


def test_zip_clamps_dates_before_1980(repo, run, write, workdir, monkeypatch):
    monkeypatch.setenv("MINIGIT_AUTHOR_DATE", "0 +0000")
    _commit(run, write, {"a.txt": b"a\n"})
    assert run("archive", "-o", "old.zip", "HEAD").code == 0
    with zipfile.ZipFile(workdir / "old.zip") as zf:
        assert zf.getinfo("a.txt").date_time == (1980, 1, 1, 0, 0, 0)


@pytest.mark.parametrize("ext", ["zip", "tar", "tar.gz"])
def test_same_commit_gives_identical_bytes(committed, run, workdir, monkeypatch, ext):
    # Tick the clock between runs: a gzip header that records "now" would differ.
    clock = itertools.count(1900000000, 5)
    monkeypatch.setattr(time, "time", lambda: float(next(clock)))
    assert run("archive", "-o", f"one.{ext}", "HEAD").code == 0
    assert run("archive", "-o", f"two.{ext}", "HEAD").code == 0
    assert (workdir / f"one.{ext}").read_bytes() == (workdir / f"two.{ext}").read_bytes()


# Executable files


def test_executable_files_are_marked(repo, run, workdir):
    entries = [(FILE_MODE, "notes.txt", b"hi\n"), (EXEC_MODE, "run.sh", b"#!/bin/sh\n")]
    sha = _commit_tree(repo, run, entries)
    assert run("archive", "-o", "x.tar", sha).code == 0
    assert run("archive", "-o", "x.zip", sha).code == 0
    with tarfile.open(workdir / "x.tar") as tf:
        assert {m.name: m.mode for m in tf.getmembers()} == {"notes.txt": 0o644, "run.sh": 0o755}
    with zipfile.ZipFile(workdir / "x.zip") as zf:
        modes = {i.filename: (i.external_attr >> 16) & 0o777 for i in zf.infolist()}
    assert modes == {"notes.txt": 0o644, "run.sh": 0o755}


# Working tree and failures


def test_uses_the_commit_not_the_working_tree(committed, run, write, workdir):
    write("README.md", b"# uncommitted edit\n")
    write("untracked.txt", b"never added\n")

    assert run("archive", "-o", "now.zip", "HEAD").code == 0

    contents = _contents(workdir / "now.zip")
    assert contents["README.md"] == FILES["README.md"]
    assert "untracked.txt" not in contents
    assert (workdir / "README.md").read_bytes() == b"# uncommitted edit\n"


def test_unknown_revision_fails(committed, run, workdir):
    result = run("archive", "-o", "x.zip", "nope")
    assert result.code == 128
    assert "unknown revision: nope" in result.err
    assert not (workdir / "x.zip").exists()


def test_failure_leaves_no_half_written_file(repo, run, workdir):
    # "a.txt" is written first, then the symlink entry stops the archive part-way.
    sha = _commit_tree(repo, run, [(FILE_MODE, "a.txt", b"a\n"), ("120000", "link", b"a.txt")])
    (workdir / "keep.zip").write_bytes(b"previous good archive")

    result = run("archive", "-o", "keep.zip", sha)

    assert result.code == 128
    assert "unsupported file mode 120000" in result.err
    assert (workdir / "keep.zip").read_bytes() == b"previous good archive"
    assert not (workdir / "keep.zip.tmp").exists()
