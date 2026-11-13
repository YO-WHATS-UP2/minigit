"""minigit show-ref lists references the same way real Git does."""

from minigit.refs import read_ref


def _make_refs(run, write):
    write("hello.txt", "hello\n")
    run("add", "hello.txt")
    run("commit", "-m", "first")
    run("branch", "feature")
    run("tag", "v1.0")


def test_show_ref_lists_heads_and_tags(repo, run, write):
    _make_refs(run, write)
    main_sha = read_ref(repo, "refs/heads/main")
    feature_sha = read_ref(repo, "refs/heads/feature")
    tag_sha = read_ref(repo, "refs/tags/v1.0")

    result = run("show-ref")

    assert result.code == 0
    assert result.out.splitlines() == [
        f"{main_sha} refs/heads/feature",
        f"{main_sha} refs/heads/main",
        f"{tag_sha} refs/tags/v1.0",
    ]
    assert feature_sha == main_sha


def test_show_ref_heads_and_tags_filters(repo, run, write):
    _make_refs(run, write)

    heads = run("show-ref", "--heads")
    assert heads.code == 0
    assert [line.split()[1] for line in heads.out.splitlines()] == [
        "refs/heads/feature",
        "refs/heads/main",
    ]

    tags = run("show-ref", "--tags")
    assert tags.code == 0
    assert [line.split()[1] for line in tags.out.splitlines()] == [
        "refs/tags/v1.0",
    ]


def test_show_ref_verify(repo, run, write):
    _make_refs(run, write)
    main_sha = read_ref(repo, "refs/heads/main")

    ok = run("show-ref", "--verify", "refs/heads/main")
    assert ok.code == 0
    assert ok.out.splitlines() == [f"{main_sha} refs/heads/main"]

    missing = run("show-ref", "--verify", "refs/heads/nope")
    assert missing.code == 1
    assert missing.out == ""
    assert "not a valid ref" in missing.err

    # A short name is not a fully qualified ref, just like in real Git.
    short = run("show-ref", "--verify", "main")
    assert short.code == 1
    assert "not a valid ref" in short.err


def test_show_ref_empty_repo_exits_one(repo, run):
    result = run("show-ref")
    assert result.code == 1
    assert result.out == ""


def test_show_ref_matches_real_git(repo, run, write, git):
    _make_refs(run, write)
    write("other.txt", "other\n")
    run("add", "other.txt")
    run("commit", "-m", "second")
    run("branch", "topic/nested")
    run("tag", "v1.1")

    for args in (["show-ref"], ["show-ref", "--heads"], ["show-ref", "--tags"]):
        git_output = git(*args)
        mine = run(*args)
        assert mine.code == 0, args
        assert mine.out == git_output, args

    git_sha = git("show-ref", "--verify", "refs/heads/main").split()[0]
    mine = run("show-ref", "--verify", "refs/heads/main")
    assert mine.out == f"{git_sha} refs/heads/main\n"
