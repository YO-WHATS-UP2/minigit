"""minigit hash-object: compute a file's object SHA, and optionally store it."""

from pathlib import Path

from minigit.errors import MinigitError
from minigit.objects import OBJECT_TYPES, hash_object, write_object
from minigit.repo import Repository

NAME = "hash-object"
HELP = "Compute the object ID of a file, and optionally store it"
NEEDS_REPO = False  # only -w needs a repository


def configure(parser):
    parser.add_argument("file")
    parser.add_argument("-w", dest="write", action="store_true", help="write the object")
    parser.add_argument("-t", dest="type", default="blob", choices=OBJECT_TYPES)


def run(args, repo):
    path = Path(args.file)
    if not path.is_file():
        raise MinigitError(f"could not open '{args.file}' for reading")
    data = path.read_bytes()
    if args.write:
        sha = write_object(Repository.find(), data, args.type)
    else:
        sha = hash_object(data, args.type)
    print(sha)
    return 0
