import json
import logging
import sys
import tempfile
from http import HTTPStatus
from pathlib import Path

from flask import Flask, request

from src import build, code, deploy

app = Flask(__name__)
app.config.from_prefixed_env()
app.logger.setLevel(logging.INFO)


REPO_KEY = "repo"
BRNCH_KEY = "branch"


@app.route("/test", methods=["POST"])
def test():
    request_json = request.json
    app.logger.info("received %s", json.dumps(request.json))

    repo_url = request_json["repository"]["clone_url"]
    if "ref" in request_json and (
        len(ref_parts := request_json["ref"].split("/")) == 3
    ):
        branch_name = ref_parts[-1]

        app.logger.info("got %s %s", repo_url, branch_name)

        return "chaneg update"
    return "not a change update"


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
