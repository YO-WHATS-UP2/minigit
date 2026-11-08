"""minigit write-tree: turn the staging area into a tree."""

from minigit.index import Index

NAME = "write-tree"
HELP = "Write the current index to the repository"


def configure(parser):
    pass  # no options yet


def run(args, repo):
    index = Index.load(repo)
    sha = index.write_tree(repo)
    print(sha)
    return 0
