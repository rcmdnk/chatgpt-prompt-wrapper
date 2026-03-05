import importlib
from pathlib import Path

import pytest
from git import Repo
from git.exc import InvalidGitRepositoryError

from chatgpt_prompt_wrapper import __version__


def test_version() -> None:
    try:
        tomllib = importlib.import_module("tomllib")
    except ModuleNotFoundError:
        tomllib = importlib.import_module("tomli")

    with (Path(__file__).parents[1] / "pyproject.toml").open("rb") as f:
        version = tomllib.load(f)["project"]["version"]
    assert version == __version__


def test_tag() -> None:
    try:
        repo = Repo(Path(__file__).parents[1])
    except InvalidGitRepositoryError:
        pytest.skip("Not a git repo.")
    tags = repo.git.tag(sort="creatordate").splitlines()
    if len(tags) > 0:
        latest_tag = tags[-1]
        assert latest_tag == "v" + __version__
