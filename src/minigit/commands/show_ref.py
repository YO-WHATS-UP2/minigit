"""show-ref: list the references (branches and tags) stored in the repository."""

import sys

from minigit.refs import iter_refs, read_ref

NAME = "show-ref"
HELP = "List the references stored in the repository"


def configure(parser):
    parser.add_argument(
        "--heads", action="store_true", help="only list refs under refs/heads"
    )
    parser.add_argument(
        "--tags", action="store_true", help="only list refs under refs/tags"
    )
    parser.add_argument(
        "--verify",
        metavar="<ref>",
        help="verify that a single, fully qualified reference exists",
    )


def run(args, repo):
    if args.verify is not None:
        return _verify(repo, args.verify)

    prefixes = []
    if args.heads:
        prefixes.append("refs/heads")
    if args.tags:
        prefixes.append("refs/tags")
    if not prefixes:
        prefixes.append("refs")

    listed = False
    for prefix in prefixes:
        for short_name, sha in iter_refs(repo, prefix).items():
            print(f"{sha} {prefix}/{short_name}")
            listed = True
    return 0 if listed else 1


def _verify(repo, ref: str) -> int:
    sha = read_ref(repo, ref)
    if sha is None:
        print(f"fatal: '{ref}' - not a valid ref", file=sys.stderr)
        return 1
    print(f"{sha} {ref}")
    return 0
