from pathlib import Path
import pandas as pd

top_level = Path.cwd()
while not (top_level / "pyproject.toml").exists():
    top_level = top_level.parent

package_dir = (
    top_level / "data" / "packages" / "senedd_scottish_parliament_2026_constituencies"
)


def test_devolved_unique_mysoc_id():
    df = pd.read_parquet(
        package_dir / "devolved_constituencies_2026.parquet"
    )

    assert df["mysoc_id"].nunique() == len(df), "mysoc_id is not unique"


def test_scottish_constituency_count():
    df = pd.read_parquet(package_dir / "devolved_constituencies_2026.parquet")
    scottish = df[df["country"] == "Scotland"]
    assert len(scottish) == 73, f"Expected 73 Scottish constituencies, got {len(scottish)}"


def test_scottish_region_count():
    df = pd.read_parquet(package_dir / "devolved_constituencies_2026.parquet")
    scottish = df[df["country"] == "Scotland"]
    assert scottish["region_name"].nunique() == 8, (
        f"Expected 8 Scottish regions, got {scottish['region_name'].nunique()}"
    )


def test_senedd_constituency_count():
    df = pd.read_parquet(package_dir / "devolved_constituencies_2026.parquet")
    senedd = df[df["country"] == "Wales"]
    assert len(senedd) == 16, f"Expected 16 Senedd constituencies, got {len(senedd)}"
