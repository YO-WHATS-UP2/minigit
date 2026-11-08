"""minigit add: stage file contents for the next commit.

For each file, ``add`` stores its content as a blob object and records
``path -> blob sha`` in the index.
"""

import argparse
from pathlib import Path

from minigit.errors import MinigitError
from minigit.index import Index, IndexEntry
from minigit.objects import FILE_MODE, write_object
from minigit.repo import Repository
from minigit.worktree import IGNORE_FILE, ignore_patterns, is_ignored, iter_files, repo_relative

NAME = "add"
HELP = "Add file contents to the staging area"


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("paths", nargs="+", help="files or directories to stage")


def run(args: argparse.Namespace, repo: Repository | None) -> int:
    assert repo is not None
    index = Index.load(repo)
    patterns = ignore_patterns(repo)
    ignored = []
    for raw in args.paths:
        _stage_deletions(index, repo, raw)
        if not Path(raw).exists():
            continue
        if _is_ignored(repo, raw, index, patterns):
            ignored.append(raw)
            continue
        for path in _expand(repo, raw, index):
            sha = write_object(repo, (repo.worktree / path).read_bytes(), "blob")
            index.add(IndexEntry(FILE_MODE, sha, path))
    index.save(repo)
    # Like Git, stage everything else first and only then complain.
    if ignored:
        raise MinigitError(
            f"the following paths are ignored by {IGNORE_FILE}:\n" + "\n".join(ignored)
        )
    return 0


def _is_ignored(repo, raw, index, patterns):
    """Say whether ``raw`` names an untracked path that ``.minigitignore`` excludes.

    Files that are already staged can still be added, as in Git: ignore rules
    only keep *new* files out.
    """
    relative = repo_relative(repo, raw)
    if relative == "" or relative in index:
        return False
    return is_ignored(relative, patterns, is_dir=Path(raw).is_dir())


def _stage_deletions(index, repo, raw):
    """Remove staged entries under ``raw`` whose files no longer exist on disk.

    Raises if ``raw`` doesn't exist and nothing staged matches it.
    """
    relative = repo_relative(repo, raw)
    deleted = [
        e.path
        for e in index
        if (relative == "" or e.path == relative or e.path.startswith(relative + "/"))
        and not (repo.worktree / e.path).exists()
    ]
    for path in deleted:
        index.remove(path)
    if not deleted and not Path(raw).exists():
        raise MinigitError(f"pathspec '{raw}' did not match any files")


def _expand(repo, raw, index):
    """Turn one path argument into the list of files it names.

    For a directory that's every file ``iter_files`` sees under it, plus any
    tracked file there that ``.minigitignore`` hides: like in Git, ignore rules
    don't stop changes to tracked files from being staged.
    """
    path = Path(raw)
    relative = repo_relative(repo, path)
    if not path.is_dir():
        return [relative]
    prefix = f"{relative}/" if relative else ""
    files = {f for f in iter_files(repo) if f.startswith(prefix)}
    files.update(
        e.path for e in index if e.path.startswith(prefix) and (repo.worktree / e.path).is_file()
    )
    return sorted(files)
