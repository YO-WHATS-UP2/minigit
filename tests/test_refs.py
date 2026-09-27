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


def test_ref_names_cannot_escape_gitdir(repo):
    with pytest.raises(MinigitError, match="invalid ref name"):
        read_ref(repo, "../../etc/passwd")
