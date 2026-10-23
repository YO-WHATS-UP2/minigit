"""minigit archive: write the files of a commit into a .zip, .tar or .tar.gz.

    minigit archive -o release.zip v1.0
    minigit archive --format=tar.gz --prefix=minigit-1.0/ -o release.tar.gz HEAD

The archive is built from the stored objects, never from the working tree,
so uncommitted edits don't leak in and no files on disk are touched.

Building the same commit twice gives byte-identical archives. To make that
true, every file gets the commit's timestamp instead of "now", the owner is
always blank, and the gzip header carries no file name or clock time.
"""

from __future__ import annotations

import argparse
import gzip
import io
import stat
import tarfile
import time
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import IO

from minigit.errors import MinigitError
from minigit.objects import (
    EXEC_MODE,
    FILE_MODE,
    flatten_tree,
    peel_to_tree,
    read_commit,
    read_object,
)
from minigit.refs import resolve
from minigit.repo import Repository

NAME = "archive"
HELP = "Create a zip or tar archive of the files in a commit"

FORMATS = ("zip", "tar", "tar.gz")

# Ends-of-filename that tell us the format when --format is not given.
_SUFFIXES = ((".tar.gz", "tar.gz"), (".tgz", "tar.gz"), (".tar", "tar"), (".zip", "zip"))

# The zip format cannot store dates before 1980-01-01 (00:00:00 UTC).
_ZIP_EPOCH = 315532800

# One file to archive: (name inside the archive, is executable, content).
_Item = tuple[str, bool, bytes]


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        metavar="<file>",
        help="write the archive to <file>",
    )
    parser.add_argument(
        "--format",
        choices=FORMATS,
        help="archive format (default: guessed from the name given to -o)",
    )
    parser.add_argument(
        "--prefix",
        default="",
        metavar="<dir/>",
        help="put every file inside this folder, e.g. minigit-1.0/",
    )
    parser.add_argument("revision", help="a commit (HEAD, branch, tag or SHA) or a tree SHA")


def guess_format(filename: str) -> str:
    """Return ``"zip"``, ``"tar"`` or ``"tar.gz"`` based on how ``filename`` ends."""
    lowered = filename.lower()
    for suffix, archive_format in _SUFFIXES:
        if lowered.endswith(suffix):
            return archive_format
    raise MinigitError(
        f"cannot guess the archive format from '{filename}'; use --format=zip, tar or tar.gz"
    )


def _normalize_prefix(prefix: str) -> str:
    """Make ``prefix`` a folder name ending in ``/``, or reject it if it could escape."""
    if not prefix:
        return ""
    # Anyone who unpacks the archive would have files land outside their folder.
    if prefix.startswith("/") or ".." in prefix.split("/"):
        raise MinigitError(f"invalid prefix: '{prefix}'")
    return prefix if prefix.endswith("/") else prefix + "/"


def _items(repo: Repository, tree_sha: str, prefix: str) -> Iterator[_Item]:
    """Yield every file of the tree, reading each blob only when it is needed."""
    for path, entry in flatten_tree(repo, tree_sha).items():
        if entry.mode not in (FILE_MODE, EXEC_MODE):
            # Symlinks and submodules: better to stop than to archive them wrongly.
            raise MinigitError(f"cannot archive '{path}': unsupported file mode {entry.mode}")
        _, data = read_object(repo, entry.sha)
        yield prefix + path, entry.mode == EXEC_MODE, data


def _zip_date(timestamp: int) -> tuple[int, int, int, int, int, int]:
    # UTC, so the archive is the same on every machine whatever its timezone.
    moment = time.gmtime(max(timestamp, _ZIP_EPOCH))
    return (
        moment.tm_year,
        moment.tm_mon,
        moment.tm_mday,
        moment.tm_hour,
        moment.tm_min,
        moment.tm_sec,
    )


def _write_zip(out: IO[bytes], items: Iterator[_Item], timestamp: int) -> None:
    with zipfile.ZipFile(out, "w") as archive:
        for name, executable, data in items:
            info = zipfile.ZipInfo(name, date_time=_zip_date(timestamp))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3  # "Unix", so Windows doesn't write different bytes
            info.external_attr = (stat.S_IFREG | (0o755 if executable else 0o644)) << 16
            archive.writestr(info, data)


def _fill_tar(archive: tarfile.TarFile, items: Iterator[_Item], timestamp: int) -> None:
    for name, executable, data in items:
        info = tarfile.TarInfo(name)
        info.size = len(data)
        info.mtime = timestamp
        info.mode = 0o755 if executable else 0o644
        archive.addfile(info, io.BytesIO(data))


def _write_tar(out: IO[bytes], items: Iterator[_Item], timestamp: int) -> None:
    with tarfile.open(fileobj=out, mode="w", format=tarfile.PAX_FORMAT) as archive:
        _fill_tar(archive, items, timestamp)


def _write_tar_gz(out: IO[bytes], items: Iterator[_Item], timestamp: int) -> None:
    # tarfile's own "w:gz" mode would stamp the current time and the file name
    # into the gzip header, which makes every run produce different bytes.
    with gzip.GzipFile(filename="", mode="wb", fileobj=out, mtime=timestamp) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as archive:
            _fill_tar(archive, items, timestamp)


_WRITERS: dict[str, Callable[[IO[bytes], Iterator[_Item], int], None]] = {
    "zip": _write_zip,
    "tar": _write_tar,
    "tar.gz": _write_tar_gz,
}


def run(args: argparse.Namespace, repo: Repository | None) -> int:
    assert repo is not None
    archive_format = args.format or guess_format(args.output)
    prefix = _normalize_prefix(args.prefix)

    sha = resolve(repo, args.revision)
    obj_type, _ = read_object(repo, sha)
    # A commit knows when it was made. A bare tree doesn't, so use the epoch.
    timestamp = read_commit(repo, sha).committer.timestamp if obj_type == "commit" else 0
    items = _items(repo, peel_to_tree(repo, sha), prefix)

    # Write next to the target and rename at the end, so a failure part-way
    # never leaves a broken archive that looks finished.
    output = Path(args.output)
    tmp = output.with_name(output.name + ".tmp")
    try:
        with tmp.open("wb") as out:
            _WRITERS[archive_format](out, items, timestamp)
        tmp.replace(output)
    except OSError as error:
        raise MinigitError(f"cannot write '{args.output}': {error.strerror or error}") from error
    finally:
        tmp.unlink(missing_ok=True)
    return 0
