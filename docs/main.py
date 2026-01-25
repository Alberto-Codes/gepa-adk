"""MkDocs macros hook for dynamic content."""

import tomllib
from pathlib import Path


def define_env(env):
    """Define variables and macros for MkDocs.

    Reads version from pyproject.toml so release-please updates propagate
    automatically to docs without manual sync.
    """
    # Read version from pyproject.toml (single source of truth)
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        pyproject = tomllib.load(f)

    version = pyproject["project"]["version"]

    # Make available as {{ project_version }} in templates
    env.variables["project_version"] = version

    # Also update extra.version so theme templates get the correct value
    env.conf["extra"]["version"] = version
