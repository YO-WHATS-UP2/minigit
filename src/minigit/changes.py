"""Comparing the three snapshots Git keeps: HEAD, the index and the working tree.

``status`` reports all three, and ``diff``, ``checkout`` and ``commit -a`` each
need part of the same comparison, so the logic lives here rather than in one
command.

Each function returns ``{path: "added" | "modified" | "deleted"}``, except
``untracked_files``, which returns a sorted list of paths.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from minigit.index import Index
from minigit.objects import flatten_tree, hash_object, peel_to_tree
from minigit.refs import head_commit
from minigit.worktree import iter_files

if TYPE_CHECKING:
    from minigit.repo import Repository


def head_files(repo: Repository) -> dict[str, str]:
    """Return ``{path: blob sha}`` for the current commit, or ``{}`` before the first one."""
    head = head_commit(repo)
    if head is None:
        return {}
    return {path: entry.sha for path, entry in flatten_tree(repo, peel_to_tree(repo, head)).items()}


def staged_changes(repo: Repository) -> dict[str, str]:
    """What ``commit`` would record: the index compared with HEAD."""
    head = head_files(repo)
    index = {entry.path: entry.sha for entry in Index.load(repo)}
    changes = {
        path: "added" if path not in head else "modified"
        for path, sha in index.items()
        if head.get(path) != sha
    }
    changes.update({path: "deleted" for path in head if path not in index})
    return changes


def unstaged_changes(repo: Repository) -> dict[str, str]:
    """What ``add`` would pick up: the working tree compared with the index.

    A staged path can't be "added" here, since the index already knows it.
    """
    changes = {}
    for entry in Index.load(repo):
        file = repo.worktree / entry.path
        if not file.is_file():
            changes[entry.path] = "deleted"
        elif hash_object(file.read_bytes()) != entry.sha:
            changes[entry.path] = "modified"
    return changes


def untracked_files(repo: Repository) -> list[str]:
    """Files in the working tree that the index has never heard of."""
    index = Index.load(repo)
    return [path for path in iter_files(repo) if path not in index]
