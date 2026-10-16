from minigit.commands import write_tree


def test_write_tree_empty_index(repo, capsys):
    assert write_tree.run(None, repo) == 0
    assert capsys.readouterr().out == "4b825dc642cb6eb9a060e54bf8d69288fbee4904\n"


def test_write_tree_uses_staged_content(repo, run, write, capsys):
    write("hello.txt", "hello\n")
    run("add", "hello.txt")
    assert write_tree.run(None, repo) == 0
    staged_tree = capsys.readouterr().out

    write("hello.txt", "unstaged edit\n")
    assert write_tree.run(None, repo) == 0
    assert capsys.readouterr().out == staged_tree


def test_write_tree_sha_matches_git(repo, run, write, git, capsys):
    write("hello.txt", "hello\n")
    write("src/app.py", "print(1)\n")
    run("add", ".")
    git("add", "hello.txt", "src/app.py")

    assert write_tree.run(None, repo) == 0
    assert capsys.readouterr().out == git("write-tree")
