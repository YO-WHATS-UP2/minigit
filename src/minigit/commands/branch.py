"""branch: create a new branches or lists current ones."""

from minigit.errors import MinigitError
from minigit.refs import current_branch, is_valid_ref_name, iter_refs, resolve, update_ref

NAME = "branch"
HELP = "Create new branches or list current ones"


def configure(parser):
    parser.add_argument("name", nargs="?", help="Branch name")
    parser.add_argument("start_point", nargs="?", help="Optional start point")


def run(args, repo):
    if args.name is None:
        list_branches(repo)
    else:
        add_branch(repo, args.name, args.start_point)
    return 0


def add_branch(repo, name: str, start_point=None):
    """Creates a new branch and adds it in the repo"""
    if not is_valid_ref_name(name):
        raise MinigitError(f"'{name}' is not a valid branch name")
    bref = f"refs/heads/{name}"
    current_refs = iter_refs(repo)  # default is "refs/heads"

    if name in current_refs:
        raise MinigitError("Branch name already exists")

    target = start_point if start_point is not None else "HEAD"

    commit_hash = resolve(repo, target)

    update_ref(repo, bref, commit_hash)


def list_branches(repo):
    """Lists all branches in this repo in sorted order and with * before the current one"""
    brefs = iter_refs(repo)
    current = current_branch(repo)

    for branch in brefs:
        prefix = "* " if branch == current else "  "
        print(f"{prefix}{branch}")
