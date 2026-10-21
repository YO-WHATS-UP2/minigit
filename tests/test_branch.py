"""All branch command tests"""

from minigit.refs import head_commit


def test_branch_lists_sorted(repo, run, write):
    write("a.txt", "hello")
    run("add", "a.txt")
    run("commit", "-m", "first")

    run("branch", "zebra")
    run("branch", "alpha")

    result = run("branch")

    assert result.code == 0
    assert result.out.splitlines() == [
        "  alpha",
        "* main",
        "  zebra",
    ]


def test_branch_creates_at_head(repo, run, write):
    write("a.txt", "hello")
    run("add", "a.txt")
    run("commit", "-m", "first")
    head = head_commit(repo)

    result = run("branch", "feature")

    assert result.code == 0
    assert (repo.gitdir / "refs/heads/feature").read_text().strip() == head
    assert head_commit(repo) == head


def test_branch_creates_at_start_point(repo, run, write):
    write("a.txt", "one")
    run("add", "a.txt")
    run("commit", "-m", "first")
    first = head_commit(repo)

    write("a.txt", "two")
    run("add", "a.txt")
    run("commit", "-m", "second")

    result = run("branch", "feature", first)

    assert result.code == 0
    assert (repo.gitdir / "refs/heads/feature").read_text().strip() == first


def test_branch_rejects_duplicate_name(repo, run, write):
    write("a.txt", "hello")
    run("add", "a.txt")
    run("commit", "-m", "first")

    run("branch", "feature")
    result = run("branch", "feature")

    assert result.code == 128
    assert "already exists" in result.err


def test_branch_rejects_invalid_names(repo, run, write):
    write("a.txt", "hello")
    run("add", "a.txt")
    run("commit", "-m", "first")

    invalid_names = [
        "",
        "my branch",
        "feature..test",
        "-- -feature",  # additional -- as if not anyways parser would reject this
        "feature/",
        "feature.lock",
    ]

    for name in invalid_names:
        result = run("branch", name)
        assert result.code == 128, f"Expected rejection for {name!r}"


def test_branch_without_commits(repo, run):
    result = run("branch", "feature")

    assert result.code != 0
    assert "commit" in result.err.lower()
