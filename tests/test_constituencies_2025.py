import constituencies_2025

import pytest

from pathlib import Path
import pandas as pd

top_level = Path.cwd()
while not (top_level / "pyproject.toml").exists():
    top_level = top_level.parent

package_dir = top_level / "data" / "packages" / "parliament_con_2025"


def test_constituencies_size():
    df = pd.read_parquet(package_dir / "parl_constituencies_2025.parquet")

    assert len(df) == 650, "There should be 650 constituencies"
