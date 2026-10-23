"""minigit cat-file: look inside an object.

This is the best command for exploring how Git stores things. Try:

    minigit cat-file -p HEAD                 # the commit
    minigit cat-file -p <tree sha from it>   # its top-level directory
    minigit cat-file -e HEAD && echo here    # scripts: exists?
    minigit cat-file --batch-check           # <sha> <type> <size> per stdin line
"""

import argparse
import sys

from minigit.errors import MinigitError
from minigit.objects import object_exists, parse_tree, read_object
from minigit.refs import resolve
from minigit.repo import Repository

NAME = "cat-file"
HELP = "Show the type, size or content of an object"


def configure(parser: argparse.ArgumentParser) -> None:
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("-t", dest="show", action="store_const", const="type", help="show type")
    mode.add_argument("-s", dest="show", action="store_const", const="size", help="show size")
    mode.add_argument("-p", dest="show", action="store_const", const="pretty", help="pretty-print")
    mode.add_argument(
        "-e",
        dest="show",
        action="store_const",
        const="exists",
        help="print nothing; exit 0 if the object exists, 1 if not",
    )
    mode.add_argument(
        "--batch-check",
        dest="show",
        action="store_const",
        const="batch-check",
        help="read object names from stdin and print '<sha> <type> <size>' (or '<name> missing')",
    )
    parser.add_argument(
        "object", nargs="?", help="a SHA, branch, tag or HEAD (not used with --batch-check)"
    )


def _batch_check(repo: Repository) -> int:
    for line in sys.stdin:
        name = line.strip()
        if not name:
            continue
        try:
            sha = resolve(repo, name)
            obj_type, data = read_object(repo, sha)
        except MinigitError:
            print(f"{name} missing")
            continue
        print(f"{sha} {obj_type} {len(data)}")
    return 0


def run(args: argparse.Namespace, repo: Repository | None) -> int:
    assert repo is not None
    if args.show == "exists":
        if not args.object:
            raise MinigitError("cat-file -e needs an object name")
        try:
            sha = resolve(repo, args.object)
        except MinigitError:
            return 1
        return 0 if object_exists(repo, sha) else 1
    if args.show == "batch-check":
        if args.object:
            raise MinigitError("cat-file --batch-check reads object names from stdin")
        return _batch_check(repo)
    if not args.object:
        raise MinigitError("cat-file needs an object name")

    obj_type, data = read_object(repo, resolve(repo, args.object))
    if args.show == "type":
        print(obj_type)
    elif args.show == "size":
        print(len(data))
    elif obj_type == "tree":
        for entry in parse_tree(data):
            print(f"{entry.mode.rjust(6, '0')} {entry.type} {entry.sha}\t{entry.name}")
    else:
        # Write raw bytes: blobs can be binary files, not just text.
        sys.stdout.flush()
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    return 0
