import pytest

from minigit.errors import MinigitError
from minigit.objects import (
    FILE_MODE,
    TREE_MODE,
    Commit,
    Signature,
    TreeEntry,
    flatten_tree,
    hash_object,
    parse_tree,
    peel_to_tree,
    read_commit,
    read_object,
    serialize_tree,
    write_object,
)

# Well-known SHAs you can reproduce with real Git:
#   printf 'hello\n' | git hash-object --stdin
HELLO_BLOB = "ce013625030ba8dba906f756967f9e9ca394464a"
#   git hash-object -t tree /dev/null
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def test_hash_matches_git():
    assert hash_object(b"hello\n") == HELLO_BLOB
    assert hash_object(b"", "tree") == EMPTY_TREE


def test_write_then_read_roundtrip(repo):
    sha = write_object(repo, b"hello\n")
    assert sha == HELLO_BLOB
    assert (repo.gitdir / "objects" / "ce" / HELLO_BLOB[2:]).is_file()
    assert read_object(repo, sha) == ("blob", b"hello\n")


def test_writing_twice_is_harmless(repo):
    assert write_object(repo, b"same") == write_object(repo, b"same")


def test_read_missing_object(repo):
    with pytest.raises(MinigitError, match="not a valid object name"):
        read_object(repo, "0" * 40)


def test_tree_entries_sorted_like_git():
    blob = hash_object(b"x")
    entries = [
        TreeEntry(FILE_MODE, "a0", blob),
        TreeEntry(TREE_MODE, "a", EMPTY_TREE),
        TreeEntry(FILE_MODE, "a.txt", blob),
        TreeEntry(FILE_MODE, "a-b", blob),
    ]
    data = serialize_tree(entries)
    # Directory "a" sorts as "a/", so it lands between "a.txt" and "a0".
    assert [e.name for e in parse_tree(data)] == ["a-b", "a.txt", "a", "a0"]
    # Checked against an independent Git implementation.
    assert hash_object(data, "tree") == "b9944b550ee8921f97ae66a5a63a8122431ca48c"


def test_tree_roundtrip():
    entries = [
        TreeEntry(FILE_MODE, "hello.txt", HELLO_BLOB),
        TreeEntry(TREE_MODE, "src", EMPTY_TREE),
    ]
    assert parse_tree(serialize_tree(entries)) == entries


def test_flatten_tree(repo):
    inner = write_object(repo, serialize_tree([TreeEntry(FILE_MODE, "b.txt", HELLO_BLOB)]), "tree")
    outer = write_object(
        repo,
        serialize_tree(
            [TreeEntry(FILE_MODE, "a.txt", HELLO_BLOB), TreeEntry(TREE_MODE, "d", inner)]
        ),
        "tree",
    )
    assert sorted(flatten_tree(repo, outer)) == ["a.txt", "d/b.txt"]


def test_signature_roundtrip():
    text = "Ada Lovelace <ada@example.com> 1700000000 +0530"
    signature = Signature.parse(text)
    assert signature.name == "Ada Lovelace"
    assert signature.timestamp == 1700000000
    assert str(signature) == text


def test_commit_roundtrip(repo):
    who = Signature("Ada", "ada@example.com", 1700000000, "+0530")
    commit = Commit(EMPTY_TREE, ["1" * 40], who, who, "Hello\n\nMore detail.\n")
    sha = write_object(repo, commit.serialize(), "commit")
    assert read_commit(repo, sha) == commit


def test_commit_parse_skips_multiline_headers():
    data = (
        f"tree {EMPTY_TREE}\n"
        "author A <a@x> 1 +0000\n"
        "committer A <a@x> 1 +0000\n"
        "gpgsig -----BEGIN PGP SIGNATURE-----\n"
        " abcdef\n"
        " -----END PGP SIGNATURE-----\n"
        "\n"
        "signed\n"
    ).encode()
    assert Commit.parse(data).message == "signed\n"


def test_read_commit_rejects_other_types(repo):
    with pytest.raises(MinigitError, match="not a commit"):
        read_commit(repo, write_object(repo, b"hello\n"))


def test_peel_to_tree(repo):
    who = Signature("Ada", "ada@example.com", 1700000000, "+0530")
    tree = write_object(repo, b"", "tree")
    commit = write_object(repo, Commit(tree, [], who, who, "x\n").serialize(), "commit")
    assert peel_to_tree(repo, commit) == tree
    assert peel_to_tree(repo, tree) == tree
    with pytest.raises(MinigitError, match="not a tree or commit"):
        peel_to_tree(repo, write_object(repo, b"blob"))
