"""minigit add: stage file contents for the next commit.

For each file, ``add`` stores its content as a blob object and records
``path -> blob sha`` in the index. Staged entries whose files no longer
exist are removed, so ``add`` stages deletions like Git does.

``--all`` stages the whole repository from any directory, ``--dry-run``
and ``--verbose`` report ``add '<path>'`` / ``remove '<path>'`` for the
changes that reach the index — the dry run stages nothing.
"""

import argparse
import stat
import sys
from pathlib import Path

from minigit.errors import MinigitError
from minigit.index import Index, IndexEntry
from minigit.objects import EXEC_MODE, FILE_MODE, hash_object, write_object
from minigit.repo import Repository
from minigit.worktree import IGNORE_FILE, ignore_patterns, is_ignored, iter_files, repo_relative

NAME = "add"
HELP = "Add file contents to the staging area"


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("paths", nargs="*", help="files or directories to stage")
    parser.add_argument(
        "-A", "--all", action="store_true", help="stage the whole repository, from any directory"
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true", help="show what would be staged, without staging it"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="show what is staged as it happens"
    )


def run(args: argparse.Namespace, repo: Repository | None) -> int:
    assert repo is not None
    if not args.paths and not args.all:
        raise MinigitError("nothing specified, nothing added")
    index = Index.load(repo)
    patterns = ignore_patterns(repo)
    ignored = []
    report = args.dry_run or args.verbose
    for raw in args.paths or [str(repo.worktree)]:
        _stage_deletions(index, repo, raw, report, args.dry_run)
        if not Path(raw).exists():
            continue
        if _is_ignored(repo, raw, index, patterns):
            ignored.append(raw)
            continue
        for path in _expand(repo, raw, index):
            data = (repo.worktree / path).read_bytes()
            mode = _mode_for(repo, path, index)
            # A file Git would not change is not reported either, not even by -v.
            entry = index.get(path)
            if entry is not None and entry.mode == mode:
                sha = hash_object(data, "blob")
                if entry.sha == sha:
                    continue
            if report:
                print(f"add '{path}'")
            if not args.dry_run:
                sha = write_object(repo, data, "blob")
                index.add(IndexEntry(mode, sha, path))
    if not args.dry_run:
        index.save(repo)
    # Like Git, stage everything else first and only then complain.
    if ignored:
        raise MinigitError(
            f"the following paths are ignored by {IGNORE_FILE}:\n" + "\n".join(ignored)
        )
    return 0


def _mode_for(repo: Repository, path: str, index: Index) -> str:
    """Choose FILE_MODE or EXEC_MODE for ``path``."""
    if sys.platform == "win32":
        entry = index.get(path)
        return entry.mode if entry is not None else FILE_MODE
    st = (repo.worktree / path).stat()
    return EXEC_MODE if bool(st.st_mode & stat.S_IXUSR) else FILE_MODE


def _is_ignored(repo, raw, index, patterns):
    """Say whether ``raw`` names an untracked path that ``.minigitignore`` excludes.

    Files that are already staged can still be added, as in Git: ignore rules
    only keep *new* files out.
    """
    relative = repo_relative(repo, raw)
    if relative == "" or relative in index:
        return False
    return is_ignored(relative, patterns, is_dir=Path(raw).is_dir())


def _stage_deletions(index, repo, raw, report=False, dry_run=False):
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
        if report:
            print(f"remove '{path}'")
        if not dry_run:
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
