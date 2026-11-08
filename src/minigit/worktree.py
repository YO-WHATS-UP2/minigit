"""The working tree: the files you actually edit, outside ``.minigit``.

Files matching a pattern in ``.minigitignore`` (at the repository root) are
left out, so no command ever sees them as untracked or stages them by accident:

    # comments and blank lines are skipped
    *.log           no slash: matches the name in any directory
    build/          trailing slash: only directories, and everything inside them
    docs/notes.txt  slash in the middle: matched from the repository root
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from fnmatch import fnmatchcase
from pathlib import Path
from typing import TYPE_CHECKING

from minigit.errors import MinigitError
from minigit.repo import GITDIR_NAME

if TYPE_CHECKING:
    from minigit.repo import Repository

IGNORE_FILE = ".minigitignore"

# Never treat these as project files. ".git" is here so running minigit inside
# a real Git checkout doesn't stage Git's own internals.
_SKIP_DIRS = {GITDIR_NAME, ".git"}


def iter_files(repo: Repository) -> Iterator[str]:
    """Yield every file in the working tree as a repo-relative path like ``"src/app.py"``.

    Paths use forward slashes on every OS and come out in sorted order.
    This is the one place that decides which files minigit can see, so
    ignored files and directories are skipped here.
    """
    patterns = ignore_patterns(repo)
    for dirpath, dirnames, filenames in os.walk(repo.worktree):
        relative_dir = Path(dirpath).relative_to(repo.worktree).as_posix()
        prefix = "" if relative_dir == "." else f"{relative_dir}/"
        # Pruning dirnames stops os.walk from going into ignored directories at all.
        dirnames[:] = sorted(
            d
            for d in dirnames
            if d not in _SKIP_DIRS and not _matches(f"{prefix}{d}", True, patterns)
        )
        for filename in sorted(filenames):
            if not _matches(f"{prefix}{filename}", False, patterns):
                yield f"{prefix}{filename}"


# ---------------------------------------------------------------------------
# Ignore rules
# ---------------------------------------------------------------------------


def ignore_patterns(repo: Repository) -> list[str]:
    """Return the patterns in ``.minigitignore``, without blank lines and comments."""
    path = repo.worktree / IGNORE_FILE
    if not path.is_file():
        return []
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def is_ignored(path: str, patterns: list[str], is_dir: bool = False) -> bool:
    """Say whether repo path ``path``, or any directory above it, matches ``patterns``."""
    parts = path.split("/")
    for depth in range(1, len(parts)):
        if _matches("/".join(parts[:depth]), True, patterns):
            return True
    return _matches(path, is_dir, patterns)


def _matches(path: str, is_dir: bool, patterns: list[str]) -> bool:
    """Say whether ``path`` itself (not its parents) matches any pattern."""
    for pattern in patterns:
        if pattern.endswith("/"):
            if not is_dir:
                continue
            pattern = pattern.rstrip("/")
        if "/" in pattern:
            # Anchored to the root. Compare segment by segment so "*" never
            # crosses a "/": "src/*.py" matches "src/a.py" but not "src/pkg/b.py".
            pattern_parts = pattern.lstrip("/").split("/")
            path_parts = path.split("/")
            if len(pattern_parts) == len(path_parts) and all(
                map(fnmatchcase, path_parts, pattern_parts)
            ):
                return True
        elif fnmatchcase(path.rsplit("/", 1)[-1], pattern):
            return True
    return False


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
