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

    # get counts of different values in 'nation' column
    counts = df["nation"].value_counts()

    assert len(df) == 650, "There should be 650 constituencies"
    assert counts["England"] == 543, "There should be 543 English constituencies"
    assert counts["Scotland"] == 57, "There should be 57 Scottish constituencies"
    assert counts["Wales"] == 32, "There should be 32 Welsh constituencies"
    assert (
        counts["Northern Ireland"] == 18
    ), "There should be 18 Northern Irish constituencies"


def test_has_unique_id():
    df = pd.read_parquet(package_dir / "parl_constituencies_2025.parquet")

    id_cols = ["short_code", "full_code"]

    for col in id_cols:
        assert df[col].nunique() == len(df), f"{col} is not unique"
