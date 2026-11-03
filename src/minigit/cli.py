"""Command-line entry point: ``minigit <command> [options]``."""

from __future__ import annotations

import argparse
import difflib
import os
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
    parser.add_argument(
        "-C",
        dest="C",
        action="append",
        default=[],
        metavar="<path>",
        help="run as if minigit was started in <path>",
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

    i = 0
    c_paths: list[str] = []
    cmd_name: str | None = None
    while i < len(arg_list):
        arg = arg_list[i]
        if arg == "--":
            if i + 1 < len(arg_list):
                cmd_name = arg_list[i + 1]
            break
        if arg == "-C":
            if i + 1 < len(arg_list):
                c_paths.append(arg_list[i + 1])
                i += 2
            else:
                i += 1
        elif arg.startswith("-C") and len(arg) > 2:
            c_paths.append(arg[2:])
            i += 1
        elif arg.startswith("-"):
            i += 1
        else:
            cmd_name = arg
            break

    saved_cwd = os.getcwd()
    try:
        for path in c_paths:
            try:
                os.chdir(path)
            except OSError as err:
                msg = os.strerror(err.errno) if err.errno else "No such file or directory"
                raise MinigitError(f"cannot change to '{path}': {msg}") from None

        if cmd_name is not None and cmd_name not in commands:
            matches = difflib.get_close_matches(cmd_name, commands.keys(), n=len(commands))
            print(
                f"minigit: '{cmd_name}' is not a minigit command. See 'minigit --help'.",
                file=sys.stderr,
            )
            if len(matches) == 1:
                print("The most similar command is", file=sys.stderr)
                print("    " + matches[0], file=sys.stderr)
            elif len(matches) > 1:
                print("The most similar commands are", file=sys.stderr)
                for item in matches:
                    print("    " + item, file=sys.stderr)
            return 1

        args = parser.parse_args(argv)
        color.configure(no_color=args.no_color)
        if args.command is None:
            parser.print_help()
            return 1
        command = commands[args.command]
        repo = Repository.find() if getattr(command, "NEEDS_REPO", True) else None
        return command.run(args, repo) or 0
    except MinigitError as error:
        print(f"fatal: {error}", file=sys.stderr)
        return 128
    finally:
        try:
            os.chdir(saved_cwd)
        except OSError:
            pass
