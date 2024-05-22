"""Deploy the flask application."""

import asyncio
import logging
import platform
import subprocess
from pathlib import Path
from typing import NamedTuple

import yaml
from juju.controller import Controller
from juju.model import Model

from . import build, code

logger = logging.getLogger("app")

ARCH_MAP = {"aarch64": "arm64", "arm64": "arm64", "x86_64": "x86"}


class Info(NamedTuple):
    """Information about the deployment.

    Attributes:
        rock_name: The name of the OCI image.
        rock_version: The version of the OCI image.
        charm_name: The name of the charm.
    """

    rock_name: str
    rock_version: str
    charm_name: str


def run(repo: code.Repo, path: Path, build_output: build.Output) -> None:
    """Deploy the app.

    Args:
        repo: The repo to deploy for.
        path: The location of the project files.
        build_output: The build artefacts.
    """
    asyncio.run(_run(repo=repo, path=path, build_output=build_output))


async def _run(repo: code.Repo, path: Path, build_output: build.Output) -> None:
    """Async version of run.

    Args:
        repo: The repo to deploy for.
        path: The location of the project files.
        build_output: The build artefacts.
    """
    model = await _get_or_create_model(repo=repo)
    info = _read_info(path=path)
    print(info)
    await _deploy_or_refresh_app(
        model=model, build_output=build_output, info=info, path=path
    )


async def _get_or_create_model(repo: code.Repo) -> Model:
    """Get or create the model for the repo.

    Args:
        repo: The repo to create a model for.
    """
    repo_model_name = _model_name_from_repo(repo=repo)
    logger.info("creating or getting model %s", repo_model_name)

    controller = Controller()
    await controller.connect()
    if not next(
        (name for name in await controller.get_models() if name == repo_model_name),
        None,
    ):
        await controller.add_model(model_name=repo_model_name)

    return await controller.get_model(repo_model_name)


def _model_name_from_repo(repo: code.Repo) -> str:
    """Get the model name from a repo.

    Args:
        repo: The repo to get the model name for.
    """
    return f"{repo.url.replace('://', '-').replace('/', '-').replace('.', '-')}-{repo.branch}"


def _read_info(path: Path) -> Info:
    """Read the deployment information.

    Args:
        path: The directory with code.

    Returns:
        Information about the deployment.
    """
    rockfile_yaml = yaml.safe_load(
        (path / "rockcraft.yaml").read_text(encoding="utf-8")
    )
    charmcraft_yaml = yaml.safe_load(
        (path / "charm" / "charmcraft.yaml").read_text(encoding="utf-8")
    )
    return Info(
        rock_name=rockfile_yaml["name"],
        rock_version=rockfile_yaml["version"],
        charm_name=charmcraft_yaml["name"],
    )


async def _deploy_or_refresh_app(
    model: Model, build_output: build.Output, info: Info, path: Path
) -> None:
    """Deploy or refresh app.

    Args:
        model: The model to deploy into.
        build_outputs: The rock and charm to deploy.
        path: The directory with the code.
    """
    logger.info(
        "uploading rock %s to registry as %s:%s",
        build_output.rock,
        info.rock_name,
        info.rock_version,
    )
    flask_app_image = f"localhost:32000/{info.rock_name}:{info.rock_version}"
    skopeo_output = subprocess.check_output(
        f"skopeo --insecure-policy copy --dest-tls-verify=false oci-archive:{build_output.rock} "
        f"docker://{flask_app_image}",
        shell=True,
        cwd=str(path),
        stderr=subprocess.STDOUT,
    ).decode(encoding="utf-8")
    logger.info(skopeo_output)

    logger.info(
        "currently deployed applications %s", ", ".join(model.applications.keys())
    )
    charm_resources = {"flask-app-image": flask_app_image}
    if info.charm_name not in model.applications:
        logger.info("deploying app into %s", model.name)
        await model.deploy(
            build_output.charm,
            application_name=info.charm_name,
            resources=charm_resources,
            constraints=f"arch={ARCH_MAP[platform.processor().lower()]}",
        )
    else:
        logger.info("refreshing app in %s", model.name)
        application = model.applications[info.charm_name]
        await application.refresh(path=build_output.charm, resources=charm_resources)
    logger.info("app deployed")
