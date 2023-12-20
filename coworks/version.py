import tomllib
from pathlib import Path

pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
with open(pyproject, "rb") as f:
    _META = tomllib.load(f)

__version__ = _META["project"]["version"]
