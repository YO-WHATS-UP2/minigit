"""minigit ls-files: print files in the staging area."""

from __future__ import annotations

import argparse

from minigit.index import Index
from minigit.repo import Repository

NAME = "ls-files"
HELP = "Show information about files in the staging area"


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-s",
        "--stage",
        action="store_true",
        help="show staged contents' mode bits, object name and stage number in the output",
    )


def run(args: argparse.Namespace, repo: Repository | None) -> int:
    assert repo is not None
    index = Index.load(repo)
    for entry in index:
        if args.stage:
            print(f"{entry.mode.rjust(6, '0')} {entry.sha} 0\t{entry.path}")
        else:
            print(entry.path)
    return 0
