import json
import logging
import tempfile
from http import HTTPStatus
from pathlib import Path

from celery import shared_task
from flask import Flask, request

from src import background, build, code, deploy, handle

app = Flask(__name__)
app.config.from_prefixed_env()
app.logger.setLevel(logging.INFO)
app.config.from_mapping(
    CELERY=dict(
        broker_url="redis://10.1.168.227:6379",
        result_backend="redis://10.1.168.227:6379",
        task_ignore_result=True,
    ),
)
celery_app = background.init(app)


REPO_KEY = "repo"
BRNCH_KEY = "branch"


@shared_task(ignore_result=False)
def handle_push(repo_url: str, branch_name: str, commit_sha: str) -> None:
    """Handle a push to a repo.

    Args:
        repo_url: The URL to a repo.
        branch_name: The name of the branch.
        commit_sha: The commit SHA of the push.
    """
    handle(repo_url=repo_url, branch_name=branch_name, commit_sha=commit_sha)


@app.route("/test", methods=["POST"])
def test():
    request_json = request.json
    app.logger.info("received %s", json.dumps(request.json))

    repo_url = request_json["repository"]["clone_url"]
    if "ref" in request_json and (
        len(ref_parts := request_json["ref"].split("/")) == 3
    ):
        branch_name = ref_parts[-1]
        commit_sha = request_json["after"]

        app.logger.info("got %s %s", repo_url, branch_name)

        result = handle_push.delay(
            repo_url=repo_url, branch_name=branch_name, commit_sha=commit_sha
        )

        return "push with branch"
    return "push without branch"


@app.route("/", methods=["POST"])
def index():
    request_json = request.json

    if not request_json:
        return "data not JSON", HTTPStatus.BAD_REQUEST
    for key in (REPO_KEY, BRNCH_KEY):
        if key not in request_json:
            return f"required key {key} missing in request data", HTTPStatus.BAD_REQUEST

    repo_url = request_json[REPO_KEY]
    branch_name = request_json[BRNCH_KEY]
    repo = code.Repo(url=repo_url, branch=branch_name)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        code.get(repo=repo, path=temp_path)
        build_output = build.run(temp_path)
        deploy.run(repo=repo, path=temp_path, build_output=build_output)

    return f"got {repo=}\n"


if __name__ == "__main__":
    app.run()
