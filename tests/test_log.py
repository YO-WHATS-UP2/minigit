"""Tests for ``minigit log``."""


def commit(run, write, name, message):
    write(name, f"{name}\n")
    run("add", name)
    run("commit", "-m", message)


def test_log_shows_one_commit(repo, run, write):
    commit(run, write, "a.txt", "First commit")
    result = run("log")
    assert result.code == 0
    assert "Author: Ada Lovelace <ada@example.com>" in result.out
    assert "Date:   Wed Nov 15 03:43:20 2023 +0530" in result.out
    assert "\n    First commit\n" in result.out


def test_log_shows_newest_first(repo, run, write):
    for name, message in (("a.txt", "First"), ("b.txt", "Second"), ("c.txt", "Third")):
        commit(run, write, name, message)
    out = run("log").out
    assert out.count("commit ") == 3
    assert out.index("Third") < out.index("Second") < out.index("First")


def test_log_separates_commits_with_a_blank_line(repo, run, write):
    commit(run, write, "a.txt", "First")
    commit(run, write, "b.txt", "Second")
    assert "\n\ncommit " in run("log").out


def test_log_without_commits_fails_like_git(repo, run):
    result = run("log")
    assert result.code == 128
    assert result.err.strip() == "fatal: your current branch 'main' does not have any commits yet"


def test_log_uses_the_authors_own_timezone(repo, run, write, monkeypatch):
    # Same instant, written by someone in UTC-08:00 rather than +05:30.
    monkeypatch.setenv("MINIGIT_AUTHOR_DATE", "1700000000 -0800")
    commit(run, write, "a.txt", "First")
    assert "Date:   Tue Nov 14 14:13:20 2023 -0800" in run("log").out


def test_log_pads_a_single_digit_day_like_git(repo, run, write, monkeypatch):
    # 4 Nov 2023, where Git prints "Nov  4" rather than "Nov 04".
    monkeypatch.setenv("MINIGIT_AUTHOR_DATE", "1699056000 +0000")
    commit(run, write, "a.txt", "First")
    assert "Date:   Sat Nov  4 00:00:00 2023 +0000" in run("log").out


def test_log_matches_real_git(repo, run, write, git):
    commit(run, write, "a.txt", "First commit")
    commit(run, write, "b.txt", "Second commit")
    assert run("log").out == git("--no-pager", "log")
