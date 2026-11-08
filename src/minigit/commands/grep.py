"""minigit grep: search the contents of tracked files.

Only *tracked* files are searched: the ones listed in the staging area
(``minigit ls-files``). Untracked files and anything inside ``.minigit`` are
skipped. By default the files are read from the working tree, like Git does.
Give a revision to search the files exactly as they were in that commit:

    minigit grep -n print                # working tree
    minigit grep print v1.0              # the files as they were in tag v1.0
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from minigit.errors import MinigitError
from minigit.index import Index
from minigit.objects import flatten_tree, peel_to_tree, read_object
from minigit.refs import resolve

NAME = "grep"
HELP = "Search the contents of tracked files for a pattern"

# A "gitlink" (submodule) entry has no file content we could read.
_GITLINK_MODE = "160000"


def configure(parser):
    parser.add_argument(
        "-i", "--ignore-case", action="store_true", help="ignore case differences when matching"
    )
    parser.add_argument(
        "-n", "--line-number", action="store_true", help="prefix each matching line with its number"
    )
    parser.add_argument(
        "-c", "--count", action="store_true", help="show how many lines match in each file"
    )
    parser.add_argument(
        "-l",
        "--files-with-matches",
        action="store_true",
        help="show only the names of files that contain a match",
    )
    parser.add_argument("-w", "--word-regexp", action="store_true", help="match only whole words")
    parser.add_argument("pattern", help="regular expression to search for")
    parser.add_argument(
        "revision",
        nargs="?",
        help="search the files as they were in this commit, branch or tag",
    )


def run(args, repo):
    regex = _compile(args.pattern, ignore_case=args.ignore_case, whole_word=args.word_regexp)
    if args.revision is None:
        files = _worktree_files(repo)
    else:
        files = _revision_files(repo, args.revision)

    found = False
    for label, data in files:
        if _grep_file(regex, label, data, args):
            found = True
    # Same exit codes as grep and git grep: 0 = something matched, 1 = nothing did.
    return 0 if found else 1


# -- building the regular expression -------------------------------------


def _compile(pattern: str, *, ignore_case: bool, whole_word: bool) -> re.Pattern[str]:
    flags = re.IGNORECASE if ignore_case else 0
    try:
        regex = re.compile(pattern, flags)
        if whole_word:
            # The match must not touch a letter, digit or underscore on either side.
            # Lookarounds (instead of \b) also work for patterns like "+" or "(a|b)".
            regex = re.compile(rf"(?<!\w)(?:{pattern})(?!\w)", flags)
    except re.error as error:
        raise MinigitError(f"invalid regular expression: {error}") from None
    return regex


# -- where the file contents come from -----------------------------------


def _worktree_files(repo) -> Iterator[tuple[str, bytes]]:
    """Yield ``(path, contents)`` for each tracked file that still exists on disk."""
    for entry in Index.load(repo):
        full = repo.worktree / entry.path
        if full.is_file():  # a tracked file you deleted is silently skipped
            yield entry.path, full.read_bytes()


def _revision_files(repo, revision: str) -> Iterator[tuple[str, bytes]]:
    """Yield ``("<revision>:<path>", contents)`` for every file in that commit."""
    tree_sha = peel_to_tree(repo, resolve(repo, revision))
    for path, entry in sorted(flatten_tree(repo, tree_sha).items()):
        if entry.mode == _GITLINK_MODE:
            continue
        _, data = read_object(repo, entry.sha)
        yield f"{revision}:{path}", data


# -- searching one file --------------------------------------------------


def _grep_file(regex: re.Pattern[str], label: str, data: bytes, args) -> bool:
    """Search one file, print what the options ask for, and say whether it matched."""
    lines = data.decode("utf-8", errors="replace").split("\n")
    if lines[-1] == "":
        lines.pop()  # the "\n" that ends the last line isn't an extra empty line
    hits = [(number, line) for number, line in enumerate(lines, start=1) if regex.search(line)]
    if not hits:
        return False

    if args.files_with_matches:  # -l wins over -c, like Git
        print(label)
    elif args.count:
        print(f"{label}:{len(hits)}")
    elif b"\0" in data:
        print(f"Binary file {label} matches")  # never dump binary junk to the terminal
    else:
        for number, line in hits:
            prefix = f"{label}:{number}:" if args.line_number else f"{label}:"
            print(f"{prefix}{line}")
    return True
