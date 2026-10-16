"""Tests for minigit grep."""

import subprocess

import pytest


@pytest.fixture
def project(repo, run, write):
    """Two tracked files plus one untracked file, all committed except ``notes.txt``."""
    write("hello.txt", "hello\n")
    write("src/app.py", "print(1)\n# TODO: add more\n")
    run("add", "hello.txt", "src/app.py")
    run("commit", "-m", "first")
    write("notes.txt", "print this later\n")  # never added: untracked
    return repo


# -- the examples from the issue -----------------------------------------


def test_line_numbers(project, run):
    result = run("grep", "-n", "print")
    assert result.code == 0
    assert result.out == "src/app.py:1:print(1)\n"


def test_count(project, run):
    result = run("grep", "-c", "hello")
    assert result.code == 0
    assert result.out == "hello.txt:1\n"


def test_files_with_matches(project, run):
    result = run("grep", "-l", "TODO")
    assert result.code == 0
    assert result.out == "src/app.py\n"


def test_plain_output_has_no_line_number(project, run):
    assert run("grep", "print").out == "src/app.py:print(1)\n"


def test_revision(project, run):
    run("tag", "v1.0")
    result = run("grep", "print", "v1.0")
    assert result.code == 0
    assert result.out == "v1.0:src/app.py:print(1)\n"


# -- what gets searched --------------------------------------------------


def test_untracked_files_are_skipped(project, run):
    # notes.txt contains "print" but was never added.
    assert "notes.txt" not in run("grep", "print").out


def test_nothing_inside_minigit_dir_is_searched(project, run):
    result = run("grep", "repositoryformatversion")
    assert result.code == 1
    assert result.out == ""


def test_searches_working_tree_contents_not_the_staged_copy(project, run, write):
    write("hello.txt", "goodbye\n")  # edited after it was staged
    assert run("grep", "goodbye").out == "hello.txt:goodbye\n"
    assert run("grep", "hello").code == 1


def test_deleted_tracked_file_is_skipped(project, run, workdir):
    (workdir / "hello.txt").unlink()
    result = run("grep", "hello")
    assert result.code == 1
    assert result.err == ""


def test_revision_ignores_working_tree_changes(project, run, write):
    write("src/app.py", "changed\n")
    result = run("grep", "print", "HEAD")
    assert result.out == "HEAD:src/app.py:print(1)\n"


def test_revision_can_be_a_branch_name(project, run):
    assert run("grep", "hello", "main").out == "main:hello.txt:hello\n"


# -- options -------------------------------------------------------------


def test_pattern_is_a_regex(project, run):
    assert run("grep", r"pri.t\(\d\)").out == "src/app.py:print(1)\n"


def test_ignore_case(project, run):
    assert run("grep", "HELLO").code == 1
    assert run("grep", "-i", "HELLO").out == "hello.txt:hello\n"
    assert run("grep", "--ignore-case", "HELLO").out == "hello.txt:hello\n"


def test_whole_word(repo, run, write):
    write("w.txt", "helloworld\nsay hello there\nhello_x\n")
    run("add", "w.txt")
    result = run("grep", "-n", "-w", "hello")
    assert result.out == "w.txt:2:say hello there\n"


def test_whole_word_finds_a_later_match_on_the_same_line(repo, run, write):
    write("w.txt", "helloworld hello\n")
    run("add", "w.txt")
    assert run("grep", "-w", "hello").out == "w.txt:helloworld hello\n"


def test_whole_word_with_alternation(repo, run, write):
    write("w.txt", "cat\ncatalog\ndog\n")
    run("add", "w.txt")
    assert run("grep", "-w", "cat|dog").out == "w.txt:cat\nw.txt:dog\n"


def test_count_counts_lines_not_matches(repo, run, write):
    write("a.txt", "x x x\ny\nx\n")
    run("add", "a.txt")
    assert run("grep", "-c", "x").out == "a.txt:2\n"


def test_count_skips_files_with_no_match(project, run):
    assert run("grep", "-c", "TODO").out == "src/app.py:1\n"


def test_files_with_matches_lists_each_file_once(repo, run, write):
    write("a.txt", "x\nx\n")
    write("b.txt", "nope\n")
    write("c.txt", "x\n")
    run("add", ".")
    assert run("grep", "-l", "x").out == "a.txt\nc.txt\n"


def test_l_wins_over_c(project, run):
    assert run("grep", "-c", "-l", "TODO").out == "src/app.py\n"


def test_options_work_with_a_revision(project, run):
    assert run("grep", "-n", "-i", "todo", "HEAD").out == "HEAD:src/app.py:2:# TODO: add more\n"
    assert run("grep", "-c", "print", "HEAD").out == "HEAD:src/app.py:1\n"
    assert run("grep", "-l", "print", "HEAD").out == "HEAD:src/app.py\n"


def test_files_are_listed_in_path_order(repo, run, write):
    write("b.txt", "hit\n")
    write("a/z.txt", "hit\n")
    write("a.txt", "hit\n")
    run("add", ".")
    assert run("grep", "-l", "hit").out == "a.txt\na/z.txt\nb.txt\n"


def test_empty_file_and_missing_final_newline(repo, run, write):
    write("empty.txt", "")
    write("nonl.txt", "last line")
    run("add", ".")
    assert run("grep", "-n", "line").out == "nonl.txt:1:last line\n"


# -- binary files --------------------------------------------------------


@pytest.fixture
def binary_repo(repo, run, write):
    write("data.bin", b"abc\0print\nprint again\n")
    run("add", "data.bin")
    run("commit", "-m", "binary")
    return repo


def test_binary_file_prints_a_single_notice(binary_repo, run):
    result = run("grep", "print")
    assert result.code == 0
    assert result.out == "Binary file data.bin matches\n"


def test_binary_notice_ignores_line_numbers(binary_repo, run):
    assert run("grep", "-n", "print").out == "Binary file data.bin matches\n"


def test_binary_file_in_a_revision(binary_repo, run):
    assert run("grep", "print", "HEAD").out == "Binary file HEAD:data.bin matches\n"


def test_binary_file_with_count_and_files_only(binary_repo, run):
    assert run("grep", "-c", "print").out == "data.bin:2\n"
    assert run("grep", "-l", "print").out == "data.bin\n"


def test_binary_file_without_a_match_prints_nothing(binary_repo, run):
    result = run("grep", "zzz")
    assert result.code == 1
    assert result.out == ""


# -- exit codes and errors -----------------------------------------------


def test_exit_code_1_when_nothing_matches(project, run):
    result = run("grep", "does-not-appear")
    assert result.code == 1
    assert result.out == ""
    assert result.err == ""


def test_empty_repository_matches_nothing(repo, run):
    assert run("grep", "anything").code == 1


def test_invalid_regex_is_a_fatal_error(project, run):
    result = run("grep", "(")
    assert result.code == 128
    assert result.err.startswith("fatal: invalid regular expression")


def test_unknown_revision_is_a_fatal_error(project, run):
    result = run("grep", "print", "no-such-branch")
    assert result.code == 128
    assert "unknown revision" in result.err


def test_revision_before_first_commit(repo, run):
    assert run("grep", "x", "HEAD").code == 128


def test_pattern_is_required(project, run):
    with pytest.raises(SystemExit) as info:
        run("grep")
    assert info.value.code == 2


# -- must behave exactly like real git grep ------------------------------


@pytest.fixture
def both(repo, run, write, git):
    """The same tracked files in minigit and in real Git, plus a commit tagged v1.0."""
    files = {
        "hello.txt": "hello\nHello World\nhelloworld\n",
        "src/app.py": "print(1)\n# TODO: add more\nPrint(2)\n",
        "src/util.py": "def helper():\n    return print\n",
        "data.bin": b"abc\0print\nprint again\n",
        "empty.txt": "",
    }
    for path, content in files.items():
        write(path, content)
    # Name the files: `git add .` would also track the .minigit folder itself.
    run("add", *files)
    git("add", *files)
    run("commit", "-m", "first")
    run("tag", "v1.0")
    write("src/app.py", "changed print\n")  # so working tree and v1.0 differ
    return repo


CASES = [
    ["print"],
    ["-n", "print"],
    ["-i", "print"],
    ["-i", "-n", "PRINT"],
    ["-c", "print"],
    ["-c", "-i", "print"],
    ["-l", "print"],
    ["-l", "-i", "hello"],
    ["-w", "hello"],
    ["-w", "-i", "hello"],
    ["-w", "-n", "-i", "hello"],
    ["-w", "-c", "-i", "hello"],
    ["-n", "-c", "print"],
    ["-c", "-l", "print"],
    ["p.int"],
    ["TODO"],
    ["nothing-matches-this"],
    ["print", "v1.0"],
    ["-n", "print", "v1.0"],
    ["-i", "-n", "PRINT", "v1.0"],
    ["-c", "print", "v1.0"],
    ["-l", "print", "v1.0"],
    ["-w", "-i", "hello", "v1.0"],
    ["-n", "print", "HEAD"],
]


@pytest.mark.parametrize("options", CASES, ids=lambda case: " ".join(case))
def test_matches_real_git(both, run, git, options):
    ours = run("grep", *options)
    try:
        expected = git("grep", *options)
        expected_code = 0
    except subprocess.CalledProcessError as error:
        expected, expected_code = error.stdout or "", error.returncode
    assert ours.out == expected
    assert ours.code == expected_code
