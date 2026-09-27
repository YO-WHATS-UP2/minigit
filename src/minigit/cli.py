"""Command-line entry point: ``minigit <command> [options]``."""

from __future__ import annotations

import argparse
import sys

from minigit import __version__
from minigit.commands import discover
from minigit.errors import MinigitError
from minigit.repo import Repository


def build_parser(commands: dict) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="minigit", description="A small Git, rebuilt from scratch in Python."
    )
    parser.add_argument("--version", action="version", version=f"minigit {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    for name, module in commands.items():
        subparser = subparsers.add_parser(name, help=module.HELP, description=module.HELP)
        module.configure(subparser)
    return parser


def main(argv: list[str] | None = None) -> int:
    commands = discover()
    parser = build_parser(commands)
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    command = commands[args.command]
    try:
        repo = Repository.find() if getattr(command, "NEEDS_REPO", True) else None
        return command.run(args, repo) or 0
    except MinigitError as error:
        print(f"fatal: {error}", file=sys.stderr)
        return 128
