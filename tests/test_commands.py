"""End-to-end tests for the built-in commands."""

from minigit.index import Index
from minigit.objects import flatten_tree, read_commit
from minigit.refs import head_commit

HELLO_BLOB = "ce013625030ba8dba906f756967f9e9ca394464a"


# -- cli ----------------------------------------------------------------------


def test_no_command_prints_help(workdir, run):
    result = run()
    assert result.code == 1
    assert "init" in result.out


def test_outside_a_repository(workdir, run):
    result = run("add", "x")
    assert result.code == 128
    assert result.err.startswith("fatal: not a minigit repository")


def test_works_from_a_subdirectory(repo, run, write, monkeypatch):
    write("src/app.py", "print(1)\n")
    monkeypatch.chdir(repo.worktree / "src")
    assert run("add", "app.py").code == 0
    assert "src/app.py" in Index.load(repo)


# -- init ---------------------------------------------------------------------


def test_init_creates_layout(workdir, run):
    result = run("init")
    assert result.code == 0
    assert "Initialized empty minigit repository" in result.out
    gitdir = workdir / ".minigit"
    assert (gitdir / "HEAD").read_text() == "ref: refs/heads/main\n"
    for directory in ("objects", "refs/heads", "refs/tags"):
        assert (gitdir / directory).is_dir()


def test_init_in_directory(workdir, run):
    run("init", "project")
    assert (workdir / "project" / ".minigit" / "HEAD").is_file()


def test_reinit_keeps_data(repo, run):
    (repo.gitdir / "HEAD").write_text("ref: refs/heads/dev\n")
    result = run("init")
    assert "Reinitialized existing" in result.out
    assert (repo.gitdir / "HEAD").read_text() == "ref: refs/heads/dev\n"


# -- hash-object / cat-file ---------------------------------------------------


def test_hash_object(repo, run, write):
    write("hello.txt", "hello\n")
    assert run("hash-object", "hello.txt").out == HELLO_BLOB + "\n"
    assert not (repo.gitdir / "objects" / "ce").exists()
    run("hash-object", "-w", "hello.txt")
    assert (repo.gitdir / "objects" / "ce").is_dir()


def test_hash_object_missing_file(repo, run):
    assert run("hash-object", "nope.txt").code == 128


def test_cat_file_blob(repo, run, write):
    write("hello.txt", "hello\n")
    run("hash-object", "-w", "hello.txt")
    assert run("cat-file", "-t", HELLO_BLOB).out == "blob\n"
    assert run("cat-file", "-s", HELLO_BLOB).out == "6\n"
    assert run("cat-file", "-p", HELLO_BLOB).out == "hello\n"


def test_cat_file_tree_and_commit(repo, run, write):
    write("hello.txt", "hello\n")
    write("src/app.py", "print(1)\n")
    run("add", ".")
    run("commit", "-m", "first")
    commit = run("cat-file", "-p", "HEAD").out
    assert commit.startswith("tree ")
    tree_sha = commit.split()[1]
    listing = run("cat-file", "-p", tree_sha).out.splitlines()
    assert listing[0] == f"100644 blob {HELLO_BLOB}\thello.txt"
    assert listing[1].startswith("040000 tree ") and listing[1].endswith("\tsrc")


def test_cat_file_unknown(repo, run):
    result = run("cat-file", "-p", "nope")
    assert result.code == 128
    assert "unknown revision" in result.err


# -- add ----------------------------------------------------------------------


def test_add_file(repo, run, write):
    write("hello.txt", "hello\n")
    assert run("add", "hello.txt").code == 0
    entry = Index.load(repo).get("hello.txt")
    assert entry.sha == HELLO_BLOB


def test_add_directory_recursively(repo, run, write):
    write("a.txt", "a")
    write("src/b.py", "b")
    write("src/deep/c.py", "c")
    run("add", "src")
    assert [e.path for e in Index.load(repo)] == ["src/b.py", "src/deep/c.py"]
    run("add", ".")
    assert len(Index.load(repo)) == 3


def test_add_updates_changed_file(repo, run, write):
    write("hello.txt", "hello\n")
    run("add", "hello.txt")
    write("hello.txt", "changed\n")
    run("add", "hello.txt")
    assert Index.load(repo).get("hello.txt").sha != HELLO_BLOB


def test_add_never_stages_metadata(repo, run, write):
    write("hello.txt", "hello\n")
    run("add", ".")
    assert all(not e.path.startswith(".minigit") for e in Index.load(repo))
    assert run("add", ".minigit/HEAD").code == 128


def test_add_missing_path(repo, run):
    result = run("add", "ghost.txt")
    assert result.code == 128
    assert "did not match any files" in result.err


def test_add_binary_file(repo, run, write):
    write("image.bin", bytes(range(256)))
    run("add", "image.bin")
    sha = Index.load(repo).get("image.bin").sha
    assert run("cat-file", "-s", sha).out == "256\n"


# -- commit -------------------------------------------------------------------


def test_first_commit(repo, run, write):
    write("hello.txt", "hello\n")
    run("add", "hello.txt")
    result = run("commit", "-m", "First commit")
    assert result.code == 0
    sha = head_commit(repo)
    assert result.out == f"[main (root-commit) {sha[:7]}] First commit\n"
    commit = read_commit(repo, sha)
    assert commit.parents == []
    assert commit.message == "First commit\n"
    assert commit.author.name == "Ada Lovelace"
    assert list(flatten_tree(repo, commit.tree)) == ["hello.txt"]


def test_commit_sha_matches_git(repo, run, write):
    # Same content, author and time always give the same SHA, and it is the
    # SHA real Git would produce (checked against an independent Git
    # implementation).
    write("hello.txt", "hello\n")
    write("src/app.py", "print(1)\n")
    run("add", ".")
    run("commit", "-m", "First commit")
    assert head_commit(repo) == "fb2368536aa0b5238a8c2e1443b3cec6e76a45a0"


def test_second_commit_has_parent(repo, run, write):
    write("a.txt", "1")
    run("add", "a.txt")
    run("commit", "-m", "one")
    first = head_commit(repo)
    write("a.txt", "2")
    run("add", "a.txt")
    result = run("commit", "-m", "two")
    assert result.out.startswith("[main ")
    assert read_commit(repo, head_commit(repo)).parents == [first]


def test_nothing_to_commit(repo, run, write):
    assert run("commit", "-m", "empty").code == 1
    write("a.txt", "1")
    run("add", "a.txt")
    run("commit", "-m", "one")
    result = run("commit", "-m", "again")
    assert result.code == 1
    assert "nothing to commit" in result.out


def test_multiple_messages_become_paragraphs(repo, run, write):
    write("a.txt", "1")
    run("add", "a.txt")
    run("commit", "-m", "Title", "-m", "Body text.")
    assert read_commit(repo, head_commit(repo)).message == "Title\n\nBody text.\n"


def test_empty_message_rejected(repo, run, write):
    write("a.txt", "1")
    run("add", "a.txt")
    assert run("commit", "-m", "   ").code == 128
