"""Handle a new push."""

import tempfile
from pathlib import Path

from . import build, code, deploy


def handle(repo_url: str, branch_name: str, commit_sha: str) -> None:
    """Handle a push to a repo.

    Args:
        repo_url: The URL to a repo.
        branch_name: The name of the branch.
        commit_sha: The commit SHA of the push.
    """
    repo = code.Repo(url=repo_url, branch=branch_name, commit_sha=commit_sha)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        code.get(repo=repo, path=temp_path)
        build_output = build.run(temp_path)
        deploy.run(repo=repo, path=temp_path, build_output=build_output)
