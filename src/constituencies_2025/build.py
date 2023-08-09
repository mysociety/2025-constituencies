from data_common.management.run_notebook import run_notebook
from pathlib import Path
from constituencies_2025.pcon_overlap import (
    combine_all_overlaps,
    calculate_pop_crossovers,
    calculate_area_crossovers,
)
import shutil

top_level = Path.cwd()
while not (top_level / "pyproject.toml").exists():
    top_level = top_level.parent


def build_2025_constituencies_geodata():
    notebook_path = top_level / "notebooks" / "geo_combine.ipynb"
    run_notebook(notebook_path, save=False)


def build_postcode_lookup():
    notebook_path = top_level / "notebooks" / "create_postcode_lookup.ipynb"
    run_notebook(notebook_path, save=False)


def build_lookups():
    calculate_area_crossovers()
    calculate_pop_crossovers()
    combine_all_overlaps()


def move_lookups():
    """
    Just move lookups when the package is being built
    """
    source_folder = top_level / "data" / "interim" / "combo_overlap"
    dest_folder = top_level / "data" / "packages" / "geographic_overlaps"

    # copy all files in source_folder to dest_folder
    for f in source_folder.iterdir():
        dest_file_name = dest_folder / f.name
        shutil.copy(f, dest_file_name)


if __name__ == "__main__":
    build_lookups()
