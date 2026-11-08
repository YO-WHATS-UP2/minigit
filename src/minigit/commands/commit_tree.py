"""minigit commit-tree: create a commit without moving a branch."""

from minigit.errors import MinigitError
from minigit.identity import author_signature
from minigit.objects import Commit, read_commit, read_tree, write_object
from minigit.refs import resolve

NAME = "commit-tree"
HELP = "Create a new commit object"


def configure(parser):
    parser.add_argument("tree", help="an existing tree object")
    parser.add_argument(
        "-p", action="append", default=[], dest="parent", help="id of a parent commit object"
    )
    parser.add_argument(
        "-m",
        "--message",
        action="append",
        required=True,
        help="a paragraph in the commit log message. this can be given more than once\n"
        "and each <message> becomes its own paragraph.",
    )


def run(args, repo):
    tree = resolve(repo, args.tree)
    read_tree(repo, tree)
    parents = [resolve(repo, parent) for parent in args.parent]
    for parent in parents:
        read_commit(repo, parent)

    message = "\n\n".join(m.strip() for m in args.message).strip()
    if not message:
        raise MinigitError("aborting commit due to empty commit message")

    signature = author_signature()
    commit = Commit(
        tree=tree,
        parents=parents,
        author=signature,
        committer=signature,
        message=message + "\n",
    )
    sha = write_object(repo, commit.serialize(), "commit")
    print(sha)
    return 0
