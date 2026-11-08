"""minigit hash-object: compute a file's object SHA, and optionally store it."""

import argparse
import sys
from pathlib import Path

from minigit.errors import MinigitError
from minigit.objects import OBJECT_TYPES, hash_object, write_object
from minigit.repo import Repository

NAME = "hash-object"
HELP = "Compute the object ID of a file, and optionally store it"
NEEDS_REPO = False  # only -w needs a repository


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("file", nargs="*")
    parser.add_argument("--stdin", action="store_true", help="read from standard input")
    parser.add_argument("-w", dest="write", action="store_true", help="write the object")
    parser.add_argument("-t", dest="type", default="blob", choices=OBJECT_TYPES)


def run(args: argparse.Namespace, repo: Repository | None) -> int:
    if args.stdin and args.file:
        raise MinigitError("--stdin cannot be used with file paths")

    if args.stdin:
        data = sys.stdin.buffer.read()
        if args.write:
            sha = write_object(Repository.find(), data, args.type)
        else:
            sha = hash_object(data, args.type)
        print(sha)
        return 0

    if not args.file:
        raise MinigitError("specify a file or use --stdin")

    for filename in args.file:
        path = Path(filename)
        if not path.is_file():
            raise MinigitError(f"could not open '{filename}' for reading")

        data = path.read_bytes()
        if args.write:
            sha = write_object(Repository.find(), data, args.type)
        else:
            sha = hash_object(data, args.type)
        print(sha)

    return 0
