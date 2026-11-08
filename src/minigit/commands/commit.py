"""minigit commit: record a snapshot of the staging area.

1. Turn the index into tree objects (one per directory).
2. Write a commit object pointing at the root tree and at the previous commit.
3. Move the current branch forward to the new commit.
"""

import argparse

from minigit import color
from minigit.errors import MinigitError
from minigit.identity import author_signature
from minigit.index import Index, IndexEntry
from minigit.objects import Commit, read_commit, write_object
from minigit.refs import current_branch, head_commit, update_head
from minigit.repo import Repository

NAME = "commit"
HELP = "Record the staged changes as a new commit"


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-m",
        "--message",
        action="append",
        required=True,
        help="commit message (repeat -m for more paragraphs)",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="stage modified and deleted tracked files before committing",
    )


def run(args: argparse.Namespace, repo: Repository | None) -> int:
    assert repo is not None
    message = "\n\n".join(m.strip() for m in args.message).strip()
    if not message:
        raise MinigitError("aborting commit due to empty commit message")

    index = Index.load(repo)
    if args.all:
        _stage_tracked_changes(repo, index)
        index.save(repo)
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
    print(f"[{branch}{root} {color.yellow(sha[:7])}] {message.splitlines()[0]}")
    return 0


def _stage_tracked_changes(repo, index):
    """Re-stage every file already in the index: drop deleted ones, update changed ones.

    Untracked files are never touched, same as ``git commit -a``.
    """
    for entry in list(index):
        path = repo.worktree / entry.path
        if not path.is_file():
            index.remove(entry.path)
            continue
        sha = write_object(repo, path.read_bytes(), "blob")
        if sha != entry.sha:
            index.add(IndexEntry(entry.mode, sha, entry.path))
