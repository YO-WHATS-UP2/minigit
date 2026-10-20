from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from minigit import refs
from minigit.errors import MinigitError

if TYPE_CHECKING:
    from minigit.repo import Repository

NAME = "symbolic-ref"
HELP = "read or change what HEAD points to"


def configure(parser: argparse.ArgumentParser) -> None:
    # I named the command with hyphen for CLI interface, instead of the name of file
    parser.add_argument("name", help="the symbolic ref to read (usually HEAD)")
    parser.add_argument("target", nargs="?", help="the new ref to point to")
    parser.add_argument("--short", action="store_true", help="strip refs/heads/ from output")

def run(args: argparse.Namespace, repo: Repository) -> None:
    
    if args.target:
        if not args.target.startswith("refs/"):
            raise MinigitError("only accepts refs starting with refs/")

        refs.set_head(repo, args.target, symbolic=True)
        return
    
    # Rely on the existing refs.head_target function
    target = refs.head_target(repo)
    
    # Handle error cases for the detached HEAD state 
    if target is None:
        raise MinigitError(f"ref {args.name} is not a symbolic ref")
    
    if args.short and target.startswith("refs/"):
        target = target[len("refs/heads/"):]
    # Output the target for the basic read operation
    print(target)
