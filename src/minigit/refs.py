"""References: human-friendly names for commits.

A branch is just a text file holding a commit SHA:

    .minigit/refs/heads/main      ->  "3b18e512dba79e4c8300dd08aeb37f8e728b8dad\\n"

``HEAD`` says which branch you are on. Usually it is a *symbolic* ref that
points at a branch:

    .minigit/HEAD                 ->  "ref: refs/heads/main\\n"

If HEAD holds a SHA directly, you are in "detached HEAD" state.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from minigit.errors import MinigitError
from minigit.objects import object_exists

if TYPE_CHECKING:
    from minigit.repo import Repository

_SYMBOLIC_PREFIX = "ref: "
_FULL_SHA_RE = re.compile(r"[0-9a-f]{40}")


def _ref_file(repo: Repository, ref: str):
    if ".." in ref.split("/") or ref.startswith("/"):
        raise MinigitError(f"invalid ref name: {ref}")
    return repo.gitdir / ref


def read_ref(repo: Repository, ref: str) -> str | None:
    """Return the SHA that ``ref`` (e.g. ``"refs/heads/main"`` or ``"HEAD"``) points to.

    Symbolic refs are followed. Returns ``None`` if the ref doesn't exist
    yet, which is normal for ``main`` before the first commit.
    """
    path = _ref_file(repo, ref)
    if not path.is_file():
        return None
    content = path.read_text().strip()
    if content.startswith(_SYMBOLIC_PREFIX):
        return read_ref(repo, content[len(_SYMBOLIC_PREFIX) :])
    return content


def update_ref(repo: Repository, ref: str, sha: str) -> None:
    path = _ref_file(repo, ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sha + "\n")


def iter_refs(repo: Repository, prefix: str = "refs/heads") -> dict[str, str]:
    """Return ``{short name: sha}`` for every ref under ``prefix``, sorted by name.

    ``iter_refs(repo, "refs/heads")`` lists branches, and
    ``iter_refs(repo, "refs/tags")`` lists tags.
    """
    base = _ref_file(repo, prefix)
    if not base.is_dir():
        return {}
    refs = {}
    for path in sorted(p for p in base.rglob("*") if p.is_file()):
        refs[path.relative_to(base).as_posix()] = path.read_text().strip()
    return refs


# ---------------------------------------------------------------------------
# HEAD
# ---------------------------------------------------------------------------


def head_target(repo: Repository) -> str | None:
    """Return the ref HEAD points to (``"refs/heads/main"``), or ``None`` if detached."""
    content = (repo.gitdir / "HEAD").read_text().strip()
    if content.startswith(_SYMBOLIC_PREFIX):
        return content[len(_SYMBOLIC_PREFIX) :]
    return None


def current_branch(repo: Repository) -> str | None:
    """Return the checked-out branch name (``"main"``), or ``None`` if detached."""
    target = head_target(repo)
    if target and target.startswith("refs/heads/"):
        return target[len("refs/heads/") :]
    return None


def head_commit(repo: Repository) -> str | None:
    """Return the SHA of the current commit, or ``None`` before the first commit."""
    return read_ref(repo, "HEAD")


def update_head(repo: Repository, sha: str) -> None:
    """Move the current branch to ``sha`` (or HEAD itself, if detached)."""
    update_ref(repo, head_target(repo) or "HEAD", sha)


def set_head(repo: Repository, target: str, symbolic: bool = True) -> None:
    """Point HEAD at a branch ref (``symbolic=True``) or directly at a commit SHA."""
    content = f"{_SYMBOLIC_PREFIX}{target}" if symbolic else target
    (repo.gitdir / "HEAD").write_text(content + "\n")


# ---------------------------------------------------------------------------
# Turning what the user typed into a SHA
# ---------------------------------------------------------------------------


def resolve(repo: Repository, name: str) -> str:
    """Turn a revision the user typed (``HEAD``, ``main``, ``v1.0``, a SHA) into a full SHA.

    Names are looked up in the same order Git uses: the exact ref, then
    tags, then branches.
    """
    if name == "HEAD":
        sha = head_commit(repo)
        if sha is None:
            raise MinigitError("HEAD does not point to a commit yet")
        return sha
    for ref in (name, f"refs/tags/{name}", f"refs/heads/{name}"):
        sha = read_ref(repo, ref)
        if sha is not None:
            return sha
    if _FULL_SHA_RE.fullmatch(name) and object_exists(repo, name):
        return name
    raise MinigitError(f"unknown revision: {name}")
