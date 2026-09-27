"""Git objects: blobs, trees and commits.

Everything Git stores is an *object*, named by the SHA-1 hash of its content.
Objects are saved compressed at ``.minigit/objects/<first 2 hex>/<other 38>``:

    zlib.compress(b"<type> <size>\\0" + content)

minigit uses exactly the same format as Git, so real Git can read any object
minigit writes. Try it: ``GIT_DIR=.minigit git cat-file -p HEAD``.

There are three object types you need to know:

* **blob**: the raw bytes of one file. It has no name and no permissions.
* **tree**: one directory listing. Each entry is (mode, name, SHA), where the
  SHA points at a blob (a file) or another tree (a subdirectory).
* **commit**: points at one top-level tree (a snapshot of the whole project),
  lists its parent commits, and records who made it, when and why.
"""

from __future__ import annotations

import hashlib
import re
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from minigit.errors import MinigitError

if TYPE_CHECKING:
    from minigit.repo import Repository

OBJECT_TYPES = ("blob", "tree", "commit", "tag")

# File modes as Git writes them in tree entries.
FILE_MODE = "100644"
EXEC_MODE = "100755"
TREE_MODE = "40000"

_SHA_RE = re.compile(r"[0-9a-f]{40}")


# ---------------------------------------------------------------------------
# Raw object storage
# ---------------------------------------------------------------------------


def _frame(data: bytes, obj_type: str) -> bytes:
    if obj_type not in OBJECT_TYPES:
        raise MinigitError(f"invalid object type: {obj_type}")
    return f"{obj_type} {len(data)}".encode() + b"\0" + data


def hash_object(data: bytes, obj_type: str = "blob") -> str:
    """Return the SHA-1 Git would give ``data``, without storing anything."""
    return hashlib.sha1(_frame(data, obj_type)).hexdigest()


def object_path(repo: Repository, sha: str) -> Path:
    return repo.gitdir / "objects" / sha[:2] / sha[2:]


def object_exists(repo: Repository, sha: str) -> bool:
    return bool(_SHA_RE.fullmatch(sha)) and object_path(repo, sha).is_file()


def write_object(repo: Repository, data: bytes, obj_type: str = "blob") -> str:
    """Store ``data`` as an object and return its SHA-1.

    Writing the same content twice is free: the object is already there.
    """
    framed = _frame(data, obj_type)
    sha = hashlib.sha1(framed).hexdigest()
    path = object_path(repo, sha)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file then rename, so a crash never leaves half an object.
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(zlib.compress(framed))
        tmp.replace(path)
    return sha


def read_object(repo: Repository, sha: str) -> tuple[str, bytes]:
    """Return ``(type, content)`` for the object named ``sha``."""
    if not object_exists(repo, sha):
        raise MinigitError(f"not a valid object name: {sha}")
    raw = zlib.decompress(object_path(repo, sha).read_bytes())
    header, _, data = raw.partition(b"\0")
    obj_type, size = header.decode().split(" ")
    if int(size) != len(data):
        raise MinigitError(f"object {sha} is corrupt")
    return obj_type, data


def _read_typed(repo: Repository, sha: str, expected: str) -> bytes:
    obj_type, data = read_object(repo, sha)
    if obj_type != expected:
        raise MinigitError(f"object {sha} is a {obj_type}, not a {expected}")
    return data


# ---------------------------------------------------------------------------
# Trees
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TreeEntry:
    """One line of a directory listing: a file or a subdirectory."""

    mode: str
    name: str
    sha: str

    @property
    def is_tree(self) -> bool:
        return self.mode == TREE_MODE

    @property
    def type(self) -> str:
        return "tree" if self.is_tree else "blob"


def _tree_sort_key(entry: TreeEntry) -> bytes:
    # Git sorts entries as if directory names had a trailing "/". So "a.txt"
    # comes before directory "a" ("." < "/"), but "a0" comes after it.
    # Get this wrong and your trees get different SHAs from Git's.
    return entry.name.encode() + (b"/" if entry.is_tree else b"")


def serialize_tree(entries: list[TreeEntry]) -> bytes:
    out = bytearray()
    for entry in sorted(entries, key=_tree_sort_key):
        out += f"{entry.mode} {entry.name}".encode() + b"\0" + bytes.fromhex(entry.sha)
    return bytes(out)


def parse_tree(data: bytes) -> list[TreeEntry]:
    # Each entry is: b"<mode> <name>\0" followed by the SHA as 20 raw bytes.
    entries = []
    i = 0
    while i < len(data):
        space = data.index(b" ", i)
        nul = data.index(b"\0", space)
        mode = data[i:space].decode()
        name = data[space + 1 : nul].decode()
        sha = data[nul + 1 : nul + 21].hex()
        entries.append(TreeEntry(mode, name, sha))
        i = nul + 21
    return entries


def read_tree(repo: Repository, sha: str) -> list[TreeEntry]:
    return parse_tree(_read_typed(repo, sha, "tree"))


def flatten_tree(repo: Repository, sha: str, prefix: str = "") -> dict[str, TreeEntry]:
    """Return every file under tree ``sha`` as ``{"dir/file.txt": entry}``.

    Useful whenever you need to compare a commit's files with the index or
    the working tree (``status``, ``diff``, ``checkout``, ...). Subtrees are
    expanded, so only files appear in the result.
    """
    files = {}
    for entry in read_tree(repo, sha):
        path = f"{prefix}{entry.name}"
        if entry.is_tree:
            files.update(flatten_tree(repo, entry.sha, prefix=f"{path}/"))
        else:
            files[path] = entry
    return files


# ---------------------------------------------------------------------------
# Commits
# ---------------------------------------------------------------------------

_SIGNATURE_RE = re.compile(r"(?P<name>.*) <(?P<email>.*)> (?P<timestamp>\d+) (?P<tz>[+-]\d{4})")


@dataclass(frozen=True)
class Signature:
    """Who did something and when, e.g. ``Ada <ada@example.com> 1700000000 +0530``."""

    name: str
    email: str
    timestamp: int  # seconds since 1970-01-01 UTC
    tz: str  # offset from UTC as "+HHMM" / "-HHMM"

    def __str__(self) -> str:
        return f"{self.name} <{self.email}> {self.timestamp} {self.tz}"

    @classmethod
    def parse(cls, text: str) -> Signature:
        match = _SIGNATURE_RE.fullmatch(text)
        if not match:
            raise MinigitError(f"malformed signature: {text!r}")
        return cls(match["name"], match["email"], int(match["timestamp"]), match["tz"])


@dataclass(frozen=True)
class Commit:
    tree: str
    parents: list[str]
    author: Signature
    committer: Signature
    message: str

    def serialize(self) -> bytes:
        lines = [f"tree {self.tree}"]
        lines += [f"parent {parent}" for parent in self.parents]
        lines += [f"author {self.author}", f"committer {self.committer}"]
        return ("\n".join(lines) + "\n\n" + self.message).encode()

    @classmethod
    def parse(cls, data: bytes) -> Commit:
        header, _, message = data.decode().partition("\n\n")
        tree = None
        parents = []
        author = committer = None
        for line in header.splitlines():
            if line.startswith(" "):
                continue  # continuation of a multi-line header such as "gpgsig"
            key, _, value = line.partition(" ")
            if key == "tree":
                tree = value
            elif key == "parent":
                parents.append(value)
            elif key == "author":
                author = Signature.parse(value)
            elif key == "committer":
                committer = Signature.parse(value)
        if tree is None or author is None or committer is None:
            raise MinigitError("malformed commit object")
        return cls(tree, parents, author, committer, message)


def read_commit(repo: Repository, sha: str) -> Commit:
    return Commit.parse(_read_typed(repo, sha, "commit"))


def peel_to_tree(repo: Repository, sha: str) -> str:
    """Return the tree SHA for a commit or tree SHA.

    Lets commands accept either: ``ls-tree HEAD`` and ``ls-tree <tree sha>``
    both work. Combine with ``refs.resolve`` to accept branch names too.
    """
    obj_type, data = read_object(repo, sha)
    if obj_type == "commit":
        return Commit.parse(data).tree
    if obj_type == "tree":
        return sha
    raise MinigitError(f"object {sha} is a {obj_type}, not a tree or commit")
