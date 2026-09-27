"""minigit init: create an empty repository."""

from pathlib import Path

from minigit.repo import GITDIR_NAME, Repository

NAME = "init"
HELP = "Create an empty minigit repository"
NEEDS_REPO = False


def configure(parser):
    parser.add_argument("directory", nargs="?", default=".", help="where to create it")


def run(args, repo):
    path = Path(args.directory)
    path.mkdir(parents=True, exist_ok=True)
    existed = (path / GITDIR_NAME / "HEAD").is_file()
    repo = Repository.create(path)
    verb = "Reinitialized existing" if existed else "Initialized empty"
    print(f"{verb} minigit repository in {repo.gitdir}")
    return 0
