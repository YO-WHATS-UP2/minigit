"""minigit add: stage file contents for the next commit.

For each file, ``add`` stores its content as a blob object and records
``path -> blob sha`` in the index.
"""

from pathlib import Path

from minigit.errors import MinigitError
from minigit.index import Index, IndexEntry
from minigit.objects import FILE_MODE, write_object
from minigit.worktree import iter_files, repo_relative

NAME = "add"
HELP = "Add file contents to the staging area"


def configure(parser):
    parser.add_argument("paths", nargs="+", help="files or directories to stage")


def run(args, repo):
    index = Index.load(repo)
    for raw in args.paths:
        for path in _expand(repo, raw):
            sha = write_object(repo, (repo.worktree / path).read_bytes(), "blob")
            index.add(IndexEntry(FILE_MODE, sha, path))
    index.save(repo)
    return 0


def _expand(repo, raw):
    """Turn one path argument into the list of files it names."""
    path = Path(raw)
    if not path.exists():
        raise MinigitError(f"pathspec '{raw}' did not match any files")
    relative = repo_relative(repo, path)
    if not path.is_dir():
        return [relative]
    prefix = f"{relative}/" if relative else ""
    return [f for f in iter_files(repo) if f.startswith(prefix)]
