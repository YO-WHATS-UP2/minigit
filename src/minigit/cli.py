"""Command-line entry point: ``minigit <command> [options]``."""

from __future__ import annotations

import argparse
import difflib
import sys

from minigit import __version__, color
from minigit.commands import discover
from minigit.errors import MinigitError
from minigit.repo import Repository


def build_parser(commands: dict) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="minigit", description="A small Git, rebuilt from scratch in Python."
    )
    parser.add_argument("--version", action="version", version=f"minigit {__version__}")
    parser.add_argument(
        "--no-color",
        action="store_true",
        default=False,
        help="disable coloured output",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    for name, module in commands.items():
        subparser = subparsers.add_parser(name, help=module.HELP, description=module.HELP)
        module.configure(subparser)
    return parser


def main(argv: list[str] | None = None) -> int:
    commands = discover()
    parser = build_parser(commands)

    arg_list = argv if argv is not None else sys.argv[1:]

    if arg_list != []:
        if not arg_list[0].startswith("-") and arg_list[0] not in commands:
            matches = difflib.get_close_matches(arg_list[0], commands.keys(), n=len(commands))
            print(
                f"minigit: '{arg_list[0]}' is not a minigit command. See 'minigit --help'.",
                file=sys.stderr,
            )
            if len(matches) == 1:
                print("The most similar command is", file=sys.stderr)
                print("    " + matches[0], file=sys.stderr)
            elif len(matches) > 1:
                print("The most similar commands are", file=sys.stderr)
                for i in matches:
                    print("    " + i, file=sys.stderr)
            return 1
    args = parser.parse_args(argv)
    color.configure(no_color=args.no_color)
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
