"""Tests for minigit ls-files."""

from minigit.objects import hash_object


def test_empty_index_prints_nothing(repo, run):
    result = run("ls-files")
    assert result.code == 0
    assert result.out == ""

    result_stage = run("ls-files", "-s")
    assert result_stage.code == 0
    assert result_stage.out == ""


def test_ls_files_plain(repo, run, write):
    write("hello.txt", "hello\n")
    write("src/app.py", "print(1)\n")
    run("add", "hello.txt", "src/app.py")

    result = run("ls-files")
    assert result.code == 0
    assert result.out == "hello.txt\nsrc/app.py\n"


def test_ls_files_stage(repo, run, write):
    write("hello.txt", "hello\n")
    write("src/app.py", "print(1)\n")
    run("add", "hello.txt", "src/app.py")

    hello_sha = hash_object(b"hello\n")
    app_sha = hash_object(b"print(1)\n")

    expected = f"100644 {hello_sha} 0\thello.txt\n100644 {app_sha} 0\tsrc/app.py\n"

    result_short = run("ls-files", "-s")
    assert result_short.code == 0
    assert result_short.out == expected

    result_long = run("ls-files", "--stage")
    assert result_long.code == 0
    assert result_long.out == expected


def test_matches_real_git(repo, run, write, git):
    write("hello.txt", "hello\n")
    write("src/app.py", "print(1)\n")
    write("docs/guide.md", "some docs\n")

    run("add", "hello.txt", "src/app.py", "docs/guide.md")
    git("add", "hello.txt", "src/app.py", "docs/guide.md")

    assert run("ls-files").out == git("ls-files")
    assert run("ls-files", "-s").out == git("ls-files", "-s")
    assert run("ls-files", "--stage").out == git("ls-files", "--stage")
