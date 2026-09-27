"""The working tree: the files you actually edit, outside ``.minigit``."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from minigit.errors import MinigitError
from minigit.repo import GITDIR_NAME

if TYPE_CHECKING:
    from minigit.repo import Repository

# Never treat these as project files. ".git" is here so running minigit inside
# a real Git checkout doesn't stage Git's own internals.
_SKIP_DIRS = {GITDIR_NAME, ".git"}


def iter_files(repo: Repository) -> Iterator[str]:
    """Yield every file in the working tree as a repo-relative path like ``"src/app.py"``.

    Paths use forward slashes on every OS and come out in sorted order.
    This is the one place that decides which files minigit can see, so
    ignore rules belong here too.
    """
    for dirpath, dirnames, filenames in os.walk(repo.worktree):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS)
        for filename in sorted(filenames):
            full = Path(dirpath, filename)
            yield full.relative_to(repo.worktree).as_posix()


def repo_relative(repo: Repository, path: str | Path) -> str:
    """Convert a path the user typed (relative to the current directory) to a repo path.

    Returns ``""`` for the repository root itself.
    """
    absolute = Path(path).resolve()
    try:
        relative = absolute.relative_to(repo.worktree).as_posix()
    except ValueError:
        raise MinigitError(f"'{path}' is outside repository at '{repo.worktree}'") from None
    relative = "" if relative == "." else relative
    if relative.split("/")[0] in _SKIP_DIRS:
        raise MinigitError(f"'{path}' is inside the repository's metadata directory")
    return relative
