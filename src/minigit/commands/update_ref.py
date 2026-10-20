from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from minigit import refs
from minigit.errors import MinigitError

if TYPE_CHECKING:
    from minigit.repo import Repository

NAME = "update-ref"
HELP = "update the object name stored in a ref safely"


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-d", action="store_true", dest="delete", help="delete the reference")
    parser.add_argument("ref", help="the reference to update or delete (e.g., refs/heads/main)")
    # nargs="?" makes newvalue optional so the -d flag works without it
    parser.add_argument("newvalue", nargs="?", help="the new SHA or revision")
    parser.add_argument("oldvalue", nargs="?", help="safely update only if current value matches")


def run(args: argparse.Namespace, repo: Repository) -> None:
    # Deletion Mode
    if args.delete:
        path = repo.gitdir / args.ref
        if path.exists():
            path.unlink()  # Deletes the file
        return

    # Validation for Update Mode
    if not args.newvalue:
        raise MinigitError("update-ref requires a newvalue unless -d is used")

    # Resolve the revision to a full SHA
    # This turns inputs like "HEAD" or short hashes into a 40-character SHA string
    sha = refs.resolve(repo, args.newvalue)

    # Optional Safety Check (Acceptance criteria)
    if args.oldvalue:
        current_sha = refs.read_ref(repo, args.ref)
        if current_sha != args.oldvalue:
            raise MinigitError(
                f"cannot lock ref '{args.ref}': is at {current_sha} but expected {args.oldvalue}"
            )

    # Perform the Update
    refs.update_ref(repo, args.ref, sha)
