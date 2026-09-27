"""Finding and creating repositories.

A minigit repository is a normal folder (the *working tree*) with a hidden
``.minigit`` folder inside it. ``.minigit`` is laid out exactly like ``.git``:

    .minigit/
        HEAD            which branch you are on, e.g. "ref: refs/heads/main"
        config          repository settings (INI format)
        minigit-index   the staging area (see index.py)
        objects/        every blob, tree and commit, stored by SHA-1
        refs/heads/     one file per branch, holding a commit SHA
        refs/tags/      one file per tag, holding a SHA
"""

from __future__ import annotations

from pathlib import Path

from minigit.errors import MinigitError

GITDIR_NAME = ".minigit"
DEFAULT_BRANCH = "main"

_DEFAULT_CONFIG = """\
[core]
\trepositoryformatversion = 0
\tbare = false
"""


class Repository:
    """A working tree plus its ``.minigit`` directory."""

    def __init__(self, worktree: str | Path) -> None:
        self.worktree = Path(worktree).resolve()
        self.gitdir = self.worktree / GITDIR_NAME

    def __repr__(self) -> str:
        return f"Repository({str(self.worktree)!r})"

    @classmethod
    def find(cls, start: str | Path | None = None) -> Repository:
        """Return the repository containing ``start`` (default: the current directory).

        Like Git, this walks up through parent directories until it finds
        one with a ``.minigit`` folder in it.
        """
        path = Path(start or Path.cwd()).resolve()
        for candidate in (path, *path.parents):
            if (candidate / GITDIR_NAME / "HEAD").is_file():
                return cls(candidate)
        raise MinigitError(
            f"not a minigit repository (or any of the parent directories): {GITDIR_NAME}"
        )

    @classmethod
    def create(cls, path: str | Path) -> Repository:
        """Create the ``.minigit`` skeleton in ``path``.

        Safe to run on an existing repository: nothing already there is overwritten.
        """
        repo = cls(path)
        for directory in ("objects", "refs/heads", "refs/tags"):
            (repo.gitdir / directory).mkdir(parents=True, exist_ok=True)
        head = repo.gitdir / "HEAD"
        if not head.exists():
            head.write_text(f"ref: refs/heads/{DEFAULT_BRANCH}\n")
        config = repo.gitdir / "config"
        if not config.exists():
            config.write_text(_DEFAULT_CONFIG)
        return repo
