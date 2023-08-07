from data_common.management.run_notebook import run_notebook
from pathlib import Path

top_level = Path.cwd()
while not (top_level / "pyproject.toml").exists():
    top_level = top_level.parent


def build_2025_constituencies_geodata():
    notebook_path = top_level / "notebooks" / "geo_combine.ipynb"
    run_notebook(notebook_path)
