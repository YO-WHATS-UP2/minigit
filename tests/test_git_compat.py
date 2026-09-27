"""Real Git must be able to read everything minigit writes.

These tests run the real ``git`` binary against a ``.minigit`` folder. They
are skipped if Git isn't installed, but they always run in CI.
"""


def _make_history(run, write):
    write("hello.txt", "hello\n")
    write("src/app.py", "print(1)\n")
    run("add", ".")
    run("commit", "-m", "First commit")
    write("src/app.py", "print(2)\n")
    run("add", "src/app.py")
    run("commit", "-m", "Second commit")


def test_git_fsck_is_happy(repo, run, write, git):
    _make_history(run, write)
    git("fsck", "--strict", "--no-dangling")


def test_git_reads_history(repo, run, write, git):
    _make_history(run, write)
    assert git("log", "--format=%s|%an|%ae").splitlines() == [
        "Second commit|Ada Lovelace|ada@example.com",
        "First commit|Ada Lovelace|ada@example.com",
    ]


def test_git_agrees_on_tree_contents(repo, run, write, git):
    _make_history(run, write)
    assert git("ls-tree", "-r", "--name-only", "HEAD").splitlines() == ["hello.txt", "src/app.py"]
    assert git("show", "HEAD:src/app.py") == "print(2)\n"


def test_git_agrees_on_hashes(repo, run, write, git):
    write("hello.txt", "hello\n")
    assert run("hash-object", "hello.txt").out == git("hash-object", "hello.txt")


def test_git_does_not_choke_on_minigit_index(repo, run, write, git):
    # minigit's text index uses its own filename, so real Git sees an empty
    # staging area instead of aborting with "index file corrupt".
    _make_history(run, write)
    git("status")
