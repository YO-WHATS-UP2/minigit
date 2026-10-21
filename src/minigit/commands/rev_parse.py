"""minigit rev-parse: print the full SHA a name refers to.

minigit rev-parse HEAD              # full SHA of the current commit
minigit rev-parse --short main      # first 7 characters of main's SHA
minigit rev-parse HEAD main v1.0    # one SHA per line
"""

from minigit.refs import resolve

NAME = "rev-parse"
HELP = "Print the full SHA that a name (HEAD, branch, tag or SHA) refers to"

SHORT_LENGTH = 7


def configure(parser):
    parser.add_argument(
        "--short", action="store_true", help=f"print the first {SHORT_LENGTH} characters"
    )
    parser.add_argument("revisions", nargs="+", metavar="revision", help="a name to resolve")


def run(args, repo):
    # Resolve everything first so that an unknown name prints nothing at all.
    shas = [resolve(repo, revision) for revision in args.revisions]
    for sha in shas:
        print(sha[:SHORT_LENGTH] if args.short else sha)
    return 0
