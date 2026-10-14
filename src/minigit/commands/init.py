"""minigit init: create an empty repository."""

import sys
from pathlib import Path

from minigit.repo import DEFAULT_BRANCH, GITDIR_NAME, Repository

NAME = "init"
HELP = "Create an empty minigit repository"
NEEDS_REPO = False


def configure(parser):
    parser.add_argument("directory", nargs="?", default=".", help="where to create it")
    parser.add_argument("-b", "--initial-branch", metavar="BRANCH", help="initial branch name")
    parser.add_argument("-q", "--quiet", action="store_true", help="suppress the success message")


def run(args, repo):
    path = Path(args.directory)
    existed = (path / GITDIR_NAME / "HEAD").is_file()
    branch = args.initial_branch if args.initial_branch is not None else DEFAULT_BRANCH
    repo = Repository.create(path, initial_branch=branch)
    if existed and args.initial_branch is not None:
        print(f"warning: re-init: ignored --initial-branch={args.initial_branch}", file=sys.stderr)
    if not args.quiet:
        verb = "Reinitialized existing" if existed else "Initialized empty"
        print(f"{verb} minigit repository in {repo.gitdir}")
    return 0
