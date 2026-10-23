"""minigit show-ref: list every branch and tag with the SHA it points to."""

import argparse
import sys

from minigit.refs import iter_refs, read_ref
from minigit.repo import Repository

NAME = "show-ref"
HELP = "List branches and tags with the SHA each points to"


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--heads", action="store_true", help="only list branches")
    parser.add_argument("--tags", action="store_true", help="only list tags")
    parser.add_argument(
        "--verify",
        metavar="ref",
        help="check that one exact ref (e.g. refs/heads/main) exists",
    )


def run(args: argparse.Namespace, repo: Repository | None) -> int:
    assert repo is not None
    if args.verify:
        sha = read_ref(repo, args.verify)
        if sha is None:
            print(f"fatal: '{args.verify}' - not a valid ref", file=sys.stderr)
            return 128
        print(f"{sha} {args.verify}")
        return 0

    prefixes = ["refs/heads", "refs/tags"]
    if args.heads or args.tags:
        prefixes = [p for p in prefixes if (p == "refs/heads") == bool(args.heads)]

    listed = 0
    for prefix in prefixes:
        for short, sha in iter_refs(repo, prefix).items():
            print(f"{sha} {prefix}/{short}")
            listed += 1
    return 0 if listed else 1
