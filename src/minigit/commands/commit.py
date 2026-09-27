"""minigit commit: record a snapshot of the staging area.

1. Turn the index into tree objects (one per directory).
2. Write a commit object pointing at the root tree and at the previous commit.
3. Move the current branch forward to the new commit.
"""

from minigit.errors import MinigitError
from minigit.identity import author_signature
from minigit.index import Index
from minigit.objects import Commit, read_commit, write_object
from minigit.refs import current_branch, head_commit, update_head

NAME = "commit"
HELP = "Record the staged changes as a new commit"


def configure(parser):
    parser.add_argument(
        "-m",
        "--message",
        action="append",
        required=True,
        help="commit message (repeat -m for more paragraphs)",
    )


def run(args, repo):
    message = "\n\n".join(m.strip() for m in args.message).strip()
    if not message:
        raise MinigitError("aborting commit due to empty commit message")

    index = Index.load(repo)
    tree = index.write_tree(repo)
    parent = head_commit(repo)
    if (parent is None and len(index) == 0) or (
        parent is not None and read_commit(repo, parent).tree == tree
    ):
        print("nothing to commit")
        return 1

    signature = author_signature()
    commit = Commit(
        tree=tree,
        parents=[parent] if parent else [],
        author=signature,
        committer=signature,
        message=message + "\n",
    )
    sha = write_object(repo, commit.serialize(), "commit")
    update_head(repo, sha)

    branch = current_branch(repo) or "detached HEAD"
    root = " (root-commit)" if parent is None else ""
    print(f"[{branch}{root} {sha[:7]}] {message.splitlines()[0]}")
    return 0
