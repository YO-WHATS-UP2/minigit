import pytest

from minigit.errors import MinigitError
from minigit.objects import write_object
from minigit.refs import (
    current_branch,
    head_commit,
    head_target,
    iter_refs,
    read_ref,
    resolve,
    set_head,
    update_head,
    update_ref,
)


def test_fresh_repo_head(repo):
    assert head_target(repo) == "refs/heads/main"
    assert current_branch(repo) == "main"
    assert head_commit(repo) is None


def test_update_head_moves_current_branch(repo):
    update_head(repo, "a" * 40)
    assert read_ref(repo, "refs/heads/main") == "a" * 40
    assert head_commit(repo) == "a" * 40


def test_detached_head(repo):
    set_head(repo, "b" * 40, symbolic=False)
    assert current_branch(repo) is None
    update_head(repo, "c" * 40)
    assert (repo.gitdir / "HEAD").read_text() == "c" * 40 + "\n"


def test_iter_refs(repo):
    update_ref(repo, "refs/heads/main", "1" * 40)
    update_ref(repo, "refs/heads/feature/login", "2" * 40)
    update_ref(repo, "refs/tags/v1", "3" * 40)
    assert iter_refs(repo) == {"feature/login": "2" * 40, "main": "1" * 40}
    assert iter_refs(repo, "refs/tags") == {"v1": "3" * 40}


def test_resolve(repo):
    blob = write_object(repo, b"x")
    update_ref(repo, "refs/heads/main", "1" * 40)
    update_ref(repo, "refs/tags/v1", "2" * 40)
    assert resolve(repo, "HEAD") == "1" * 40
    assert resolve(repo, "main") == "1" * 40
    assert resolve(repo, "v1") == "2" * 40
    assert resolve(repo, blob) == blob


def test_resolve_prefers_tags_over_branches(repo):
    update_ref(repo, "refs/heads/same", "1" * 40)
    update_ref(repo, "refs/tags/same", "2" * 40)
    assert resolve(repo, "same") == "2" * 40


def test_resolve_errors(repo):
    with pytest.raises(MinigitError, match="HEAD does not point"):
        resolve(repo, "HEAD")
    with pytest.raises(MinigitError, match="unknown revision"):
        resolve(repo, "nope")


def test_resolve_unique_short_sha(repo):
    blob = write_object(repo, b"short")
    assert resolve(repo, blob[:4]) == blob
    assert resolve(repo, blob[:7]) == blob
    assert resolve(repo, blob[:39]) == blob


def test_resolve_ambiguous_short_sha(repo):
    for sha in ("ab12" + "0" * 36, "ab12" + "1" * 36):
        path = repo.gitdir / "objects" / sha[:2] / sha[2:]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    with pytest.raises(MinigitError, match="ambiguous"):
        resolve(repo, "ab12")


def test_branch_name_beats_short_sha(repo):
    blob = write_object(repo, b"branchy")
    update_ref(repo, f"refs/heads/{blob[:4]}", "1" * 40)
    assert resolve(repo, blob[:4]) == "1" * 40


def test_too_short_sha_is_not_a_revision(repo):
    blob = write_object(repo, b"tiny")
    with pytest.raises(MinigitError, match="unknown revision"):
        resolve(repo, blob[:3])


def test_ref_names_cannot_escape_gitdir(repo):
    with pytest.raises(MinigitError, match="invalid ref name"):
        read_ref(repo, "../../etc/passwd")


# ---------------------------------------------------------------------------
# packed-refs
# ---------------------------------------------------------------------------

PACKED_REFS = (
    "# pack-refs with: peeled fully-peeled sorted\n"
    + "1" * 40
    + " refs/heads/old-feature\n"
    + "2" * 40
    + " refs/tags/v1.0\n"
    + "^"
    + "3" * 40
    + "\n"
)


def write_packed_refs(repo, text=PACKED_REFS):
    (repo.gitdir / "packed-refs").write_text(text)


def test_read_ref_from_packed_refs(repo):
    write_packed_refs(repo)
    assert read_ref(repo, "refs/heads/old-feature") == "1" * 40
    assert read_ref(repo, "refs/tags/v1.0") == "2" * 40
    assert read_ref(repo, "refs/heads/missing") is None


def test_no_packed_refs_file_is_fine(repo):
    assert read_ref(repo, "refs/heads/old-feature") is None
    assert iter_refs(repo) == {}


def test_loose_ref_wins_over_packed(repo):
    write_packed_refs(repo)
    update_ref(repo, "refs/heads/old-feature", "9" * 40)
    assert read_ref(repo, "refs/heads/old-feature") == "9" * 40
    assert iter_refs(repo) == {"old-feature": "9" * 40}


def test_iter_refs_merges_loose_and_packed(repo):
    write_packed_refs(repo)
    update_ref(repo, "refs/heads/main", "4" * 40)
    update_ref(repo, "refs/tags/v2.0", "5" * 40)
    assert iter_refs(repo) == {"main": "4" * 40, "old-feature": "1" * 40}
    # The "^" line is not a ref, and each tag shows up exactly once.
    assert iter_refs(repo, "refs/tags") == {"v1.0": "2" * 40, "v2.0": "5" * 40}


def test_iter_refs_with_only_packed_refs(repo):
    # `git pack-refs --all` removes the loose files, so the folder can be gone.
    (repo.gitdir / "refs" / "heads").rmdir()
    write_packed_refs(repo)
    assert iter_refs(repo) == {"old-feature": "1" * 40}


def test_resolve_finds_packed_refs(repo):
    write_packed_refs(repo)
    assert resolve(repo, "v1.0") == "2" * 40
    assert resolve(repo, "old-feature") == "1" * 40


def test_head_follows_packed_branch(repo):
    write_packed_refs(repo, "4" * 40 + " refs/heads/main\n")
    assert head_commit(repo) == "4" * 40


def test_broken_packed_refs_is_an_error(repo):
    write_packed_refs(repo, "not-a-sha refs/heads/x\n")
    with pytest.raises(MinigitError, match="broken packed-refs"):
        read_ref(repo, "refs/heads/x")
