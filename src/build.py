"""Builds the artefacts."""

import logging
import re
import subprocess
from multiprocessing import Pool
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger("app")


class BuildError(Exception):
    """The build failed."""


class Output(NamedTuple):
    """Contains the output artefacts.

    Attributes:
        rock: The path to the generated rock.
        charm: The path to the generated charm.
    """

    rock: Path
    charm: Path


def run(path: Path) -> Output:
    """Build the required artefacts.

    Args:
        path: The directory containing the source.
    """
    charm_dir = path / "charm"
    with Pool(2) as pool:
        rockcraft_out, charmcraft_out = pool.starmap(
            _run_one,
            [
                ("rockcraft clean && rockcraft pack", path),
                ("charmcraft clean && charmcraft pack", charm_dir),
            ],
        )

    rock_path = path / re.search(
        "^Packed (.*\.rock)$", rockcraft_out, re.MULTILINE
    ).group(1)
    charm_path = charm_dir / re.search(
        "^Packed (.*\.charm)$", charmcraft_out, re.MULTILINE
    ).group(1)
    return Output(rock=rock_path, charm=charm_path)


def _run_one(args: str, path: Path) -> str:
    """Run one build command.

    Args:
        args: The command to run.
        path: The directory to run the command in.

    Returns:
        The stdout and stderr.
    """
    logger.info("running %s in %s", args, str(path))
    out = subprocess.check_output(
        args=args,
        shell=True,
        cwd=str(path),
        stderr=subprocess.STDOUT,
    ).decode(encoding="utf-8")
    logger.info(out)
    return out
