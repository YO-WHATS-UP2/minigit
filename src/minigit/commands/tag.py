"""minigit tag: create, list, or delete tags."""

from minigit.errors import MinigitError
from minigit.refs import iter_refs, read_ref, resolve, update_ref

NAME = "tag"
HELP = "Create, list, or delete tags"


def configure(parser):
    parser.add_argument("-d", "--delete", action="store_true", help="delete a tag")
    parser.add_argument("name", nargs="?", help="tag name")
    parser.add_argument("revision", nargs="?", help="revision to point the tag at")


def run(args, repo):
    if args.delete:
        if not args.name:
            raise MinigitError("tag name required")
        if args.revision:
            raise MinigitError("cannot specify revision when deleting a tag")
        return _delete_tag(repo, args.name)

    if not args.name:
        if args.revision:
            raise MinigitError("cannot specify revision without tag name")
        return _list_tags(repo)

    return _create_tag(repo, args.name, args.revision)


def _list_tags(repo) -> int:
    tags = iter_refs(repo, "refs/tags")
    for name in sorted(tags):
        print(name)
    return 0


def _create_tag(repo, name: str, revision: str | None) -> int:
    ref = f"refs/tags/{name}"
    if read_ref(repo, ref) is not None:
        raise MinigitError(f"tag '{name}' already exists")

    target = revision if revision is not None else "HEAD"
    sha = resolve(repo, target)

    update_ref(repo, ref, sha)
    return 0


def _delete_tag(repo, name: str) -> int:
    ref = f"refs/tags/{name}"
    sha = read_ref(repo, ref)
    if sha is None:
        raise MinigitError(f"tag '{name}' not found")

    tag_file = repo.gitdir / ref
    tag_file.unlink()

    # Clean up empty parent directories up to refs/tags
    parent = tag_file.parent
    tags_dir = repo.gitdir / "refs" / "tags"
    while parent != tags_dir and parent != repo.gitdir:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent

    print(f"Deleted tag '{name}' (was {sha[:7]})")
    return 0
