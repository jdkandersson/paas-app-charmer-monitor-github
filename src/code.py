"""Retrieves files from a git repo"""

import logging
from pathlib import Path
from typing import NamedTuple

from git import Repo as GitRepo

logger = logging.getLogger("app")


class Repo(NamedTuple):
    """Information about a repo.

    Attributes:
        url: The URL to the repo.
        branch: The name of a branch.
    """

    url: str
    branch: str


def get(repo: Repo, path: Path) -> None:
    """Get the files from a repo into a local directory.

    Args:
        repo: The repository to get the files from.
        branch: The branch to get the files from.
        path: The directory to clone the repo into.
    """
    logger.info("cloning repo %s branch %s", repo.url, repo.branch)
    GitRepo.clone_from(url=repo.url, to_path=path, branch=repo.branch)
