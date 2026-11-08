"""minigit log: walk back through history, newest commit first.

Each commit stores its parent's SHA, so the history is a linked list you
follow backwards from HEAD.
"""

import argparse
from datetime import datetime, timedelta, timezone

from minigit.errors import MinigitError
from minigit.objects import read_commit
from minigit.refs import current_branch, head_commit
from minigit.repo import Repository

NAME = "log"
HELP = "Show commit history"


def configure(parser: argparse.ArgumentParser) -> None:
    pass


def _format_date(signature) -> str:
    """Render a signature's time in its own timezone, the way Git does.

    Git pads the day with a space (``Nov  4``), so build it by hand rather
    than with ``%d``, which would give ``Nov 04``.
    """
    hours, minutes = int(signature.tz[1:3]), int(signature.tz[3:5])
    offset = timedelta(hours=hours, minutes=minutes)
    if signature.tz.startswith("-"):
        offset = -offset
    moment = datetime.fromtimestamp(signature.timestamp, tz=timezone(offset))
    return f"{moment:%a %b} {moment.day:>2} {moment:%H:%M:%S %Y} {signature.tz}"


def run(args: argparse.Namespace, repo: Repository | None) -> int:
    assert repo is not None
    sha = head_commit(repo)
    if sha is None:
        branch = current_branch(repo) or "HEAD"
        raise MinigitError(f"your current branch '{branch}' does not have any commits yet")

    first = True
    while sha is not None:
        commit = read_commit(repo, sha)
        if not first:
            print()
        first = False
        print(f"commit {sha}")
        print(f"Author: {commit.author.name} <{commit.author.email}>")
        print(f"Date:   {_format_date(commit.author)}")
        print()
        for line in commit.message.rstrip("\n").split("\n"):
            print(f"    {line}" if line else "")
        # Only the first parent, so a merge doesn't fan out into both sides.
        sha = commit.parents[0] if commit.parents else None
    return 0
