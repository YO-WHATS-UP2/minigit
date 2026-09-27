"""The staging area (also called the "index").

The index lists the exact file contents that will go into the next commit.
``minigit add`` updates it, and ``minigit commit`` turns it into trees.

Real Git's index is a binary file at ``.git/index``. minigit uses plain text
instead, so you can open ``.minigit/minigit-index`` in an editor and see what
is staged:

    minigit-index 1
    100644 ce013625030ba8dba906f756967f9e9ca394464a hello.txt
    100644 9daeafb9864cf43055ae93beb0afd6c7d144bfa4 src/app.py

Each line is ``<mode> <blob sha> <path>``. Paths always use forward slashes,
even on Windows.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from minigit.errors import MinigitError
from minigit.objects import TREE_MODE, TreeEntry, serialize_tree, write_object

if TYPE_CHECKING:
    from minigit.repo import Repository

HEADER = "minigit-index 1"

# Deliberately *not* called "index": real Git reads any file with that name as
# its binary index and aborts ("index file corrupt") if it can't parse it.
# With a different name, real Git just sees an empty staging area and every
# git command keeps working on a minigit repository.
INDEX_FILE = "minigit-index"


@dataclass(frozen=True)
class IndexEntry:
    mode: str
    sha: str
    path: str


class Index:
    def __init__(self, entries: list[IndexEntry] | None = None) -> None:
        self._entries: dict[str, IndexEntry] = {}
        for entry in entries or []:
            self.add(entry)

    # -- loading and saving -------------------------------------------------

    @classmethod
    def load(cls, repo: Repository) -> Index:
        path = repo.gitdir / INDEX_FILE
        if not path.exists():
            return cls()
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0] != HEADER:
            raise MinigitError(f"unrecognised index file format in {path}")
        entries = []
        for line in lines[1:]:
            mode, sha, file_path = line.split(" ", 2)
            entries.append(IndexEntry(mode, sha, file_path))
        return cls(entries)

    def save(self, repo: Repository) -> None:
        lines = [HEADER] + [f"{e.mode} {e.sha} {e.path}" for e in self]
        (repo.gitdir / INDEX_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")

    # -- reading and changing entries --------------------------------------

    def __iter__(self) -> Iterator[IndexEntry]:
        return iter(sorted(self._entries.values(), key=lambda e: e.path))

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, path: str) -> bool:
        return path in self._entries

    def get(self, path: str) -> IndexEntry | None:
        return self._entries.get(path)

    def add(self, entry: IndexEntry) -> None:
        """Stage ``entry``, replacing any entry that conflicts with its path.

        A path can't be both a file and a directory. Staging ``a/b.txt``
        removes a staged file called ``a``, and staging a file ``a`` removes
        everything staged under ``a/``.
        """
        parts = entry.path.split("/")
        for depth in range(1, len(parts)):
            self._entries.pop("/".join(parts[:depth]), None)
        for path in [p for p in self._entries if p.startswith(entry.path + "/")]:
            del self._entries[path]
        self._entries[entry.path] = entry

    def remove(self, path: str) -> None:
        if path not in self._entries:
            raise MinigitError(f"pathspec '{path}' did not match any staged files")
        del self._entries[path]

    # -- turning the index into trees --------------------------------------

    def write_tree(self, repo: Repository) -> str:
        """Write tree objects for everything staged and return the root tree's SHA."""
        root: dict = {}
        for entry in self:
            *dirs, name = entry.path.split("/")
            node = root
            for directory in dirs:
                node = node.setdefault(directory, {})
            node[name] = entry
        return _write_tree_node(repo, root)


def _write_tree_node(repo: Repository, node: dict) -> str:
    entries = []
    for name, child in node.items():
        if isinstance(child, dict):
            entries.append(TreeEntry(TREE_MODE, name, _write_tree_node(repo, child)))
        else:
            entries.append(TreeEntry(child.mode, name, child.sha))
    return write_object(repo, serialize_tree(entries), "tree")
