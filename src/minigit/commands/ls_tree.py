"""minigit ls-tree: list the contents of a tree or commit."""

import argparse

from minigit.objects import flatten_tree, peel_to_tree, read_tree
from minigit.refs import resolve
from minigit.repo import Repository

NAME = "ls-tree"
HELP = "List the contents of a tree or commit"


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-r", action="store_true", help="recurse into subdirectories")
    parser.add_argument("--name-only", action="store_true", help="print only names or paths")
    parser.add_argument("tree_ish", metavar="<tree-ish>", help="a commit, tree SHA, branch or HEAD")


def run(args: argparse.Namespace, repo: Repository | None) -> int:
    assert repo is not None
    tree = peel_to_tree(repo, resolve(repo, args.tree_ish))
    if args.r:
        # flatten_tree preserves Git's depth-first tree order; do not re-sort paths.
        entries = flatten_tree(repo, tree)
    else:
        entries = {entry.name: entry for entry in read_tree(repo, tree)}
    for path, entry in entries.items():
        if args.name_only:
            print(path)
        else:
            print(f"{entry.mode.rjust(6, '0')} {entry.type} {entry.sha}\t{path}")
    return 0
