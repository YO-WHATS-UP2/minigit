"""Repository creation through the shared API."""

import pytest

from minigit.errors import MinigitError
from minigit.refs import current_branch
from minigit.repo import Repository


def test_create_with_initial_branch(tmp_path):
    repo = Repository.create(tmp_path / "project", initial_branch="trunk")
    assert current_branch(repo) == "trunk"
    assert (repo.gitdir / "config").is_file()


def test_create_rejects_invalid_branch_before_writing(tmp_path):
    path = tmp_path / "project"
    with pytest.raises(MinigitError, match="invalid initial branch name"):
        Repository.create(path, initial_branch="bad name")
    assert not path.exists()


def test_create_preserves_existing_head_and_config(tmp_path):
    repo = Repository.create(tmp_path, initial_branch="dev")
    config = repo.gitdir / "config"
    config.write_text("[core]\n\tbare = false\n[custom]\n\tvalue = keep\n")
    original_config = config.read_bytes()
    Repository.create(tmp_path, initial_branch="bad name")
    assert current_branch(repo) == "dev"
    assert config.read_bytes() == original_config
