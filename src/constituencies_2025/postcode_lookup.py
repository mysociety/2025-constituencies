from pathlib import Path
import pandas as pd
import geopandas as gpd
from tqdm import tqdm

from data_common.helpers.typing import ValidationTest, enforce_types

from typing import Annotated


GeoPolygonPath = Annotated[
    Path,
    ValidationTest(
        Path,
        lambda x: x.suffix in [".parquet", ".shp", ".geojson", ".gpkg"],
        lambda x: ValueError(f"Path {str(x)} is not a valid geofile"),
    ),
]

ParquetPath = Annotated[
    Path,
    ValidationTest(
        Path,
        lambda x: x.suffix in [".parquet"],
        lambda x: ValueError(f"Path suffix {x.suffix} is not parquet"),
    ),
]


def create_fake_ni_postcodes():
    pass


def create_all():
    create_2025_small_area_lookup()
    create_2025_la_lookup()
    create_2010_con_lookup()
    create_2025_con_lookup()
    combine_outputs()


def create_2010_con_lookup():
    parl_data_loc = (
        Path("data")
        / "raw"
        / "external"
        / "Westminster_Parliamentary_Constituencies_(Dec_2021)_UK_BFC.gpkg"
    )
    output_loc = (
        Path("data") / "interim" / "postcode_lookups" / "parl_cons_2010.parquet"
    )

    print("Creating postcode lookup with 2010 constituencies")
    create_postcode_lookup(
        input_path=parl_data_loc,
        input_id_col="PCON21CD",
        output_path=output_loc,
        output_id_col="PARL10",
    )


def combine_outputs():
    print("combining outputs")
    interim_folder = Path("data") / "interim" / "postcode_lookups"
    output_loc = Path("data") / "interim" / "combo_postcode_lookup.parquet"

    dfs = []
    df = None

    for file in tqdm(list(interim_folder.glob("*.parquet"))):
        if df is None:
            df = pd.read_parquet(file)
            continue

        df = pd.merge(df, pd.read_parquet(file), on="postcode", how="outer")
        dfs.append(pd.read_parquet(file))

    if df is None:
        raise ValueError("No files found")

    df.to_parquet(output_loc)


def create_2025_con_lookup():
    parl_data_loc = (
        Path("data")
        / "packages"
        / "parliament_con_2025"
        / "parl_constituencies_2025.parquet"
    )
    output_loc = (
        Path("data") / "interim" / "postcode_lookups" / "parl_cons_2025.parquet"
    )

    print("Creating postcode lookup with 2025 constituencies")
    create_postcode_lookup(
        input_path=parl_data_loc,
        input_id_col="short_code",
        output_path=output_loc,
        output_id_col="PARL25",
    )


def create_2025_small_area_lookup():
    la_data_loc = (
        Path("data") / "raw" / "external" / "uk-small-area-lsoa-soa-dz-apr-2021.parquet"
    )

    output_loc = Path("data") / "interim" / "postcode_lookups" / "lsoa_2011.parquet"

    print("Creating postcode lookup with lsoa lookup")
    create_postcode_lookup(
        input_path=la_data_loc,
        input_id_col="areacode",
        output_path=output_loc,
        output_id_col="LSOA11",
    )


def create_2025_la_lookup():
    la_data_loc = (
        Path("data")
        / "raw"
        / "external"
        / "Local_Authority_Districts_May_2023_UK_BFC_V2_179125415192200502.gpkg"
    )
    output_loc = Path("data") / "interim" / "postcode_lookups" / "la_2023.parquet"

    print("Creating postcode lookup for local authority lookup")
    create_postcode_lookup(
        input_path=la_data_loc,
        input_id_col="LAD23CD",
        output_path=output_loc,
        output_id_col="LAD23",
    )


@enforce_types
def create_postcode_lookup(
    *,
    input_path: GeoPolygonPath,
    input_id_col: str,
    output_path: ParquetPath,
    output_id_col: str,
) -> None:
    """
    Create a postcode lookup given a shapefile of polygons and a column to join on
    """

    codepoint_dir = Path("data") / "raw" / "external" / "codepo"
    csv_dir = codepoint_dir / "csv"
    header_file = codepoint_dir / "header.csv"

    # read in first line of header file as comma separated list
    with header_file.open("r") as f:
        header = f.readline().strip().split(",")

    # for each file in csv_dir - read in as dataframe using header and write out as parquet with a new geometry column

    # if parquet file
    if input_path.suffix == ".parquet":
        poly_file = gpd.read_parquet(input_path).to_crs(epsg=4326)
    else:
        poly_file = gpd.read_file(input_path).to_crs(epsg=4326)

    if poly_file is None:
        raise ValueError(f"Could not read {input_path}")

    if input_id_col not in poly_file.columns:
        raise ValueError(
            f"Column {input_id_col} not in {input_path}. Available columns: {poly_file.columns}"
        )

    all_data = []

    for csv_file in tqdm(list(csv_dir.glob("*.csv"))):
        df = pd.read_csv(csv_file, names=header)
        # from Eastings,Northings, we want to create a geopandas dataframe with a geometry column of point data
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df["Eastings"], df["Northings"]),  # type: ignore
            crs="EPSG:27700",  # type: ignore
        )
        # gdf.to_parquet(parquet_dir / csv_file.with_suffix(".parquet").name)
        gdf = gdf.to_crs(epsg=4326)

        joined = gpd.sjoin(gdf, poly_file, how="left", predicate="within")[
            ["Postcode", input_id_col]
        ]
        joined = joined.rename(columns={"Postcode": "postcode"})

        all_data.append(joined)

    df = pd.concat(all_data)

    df = df.rename(columns={input_id_col: output_id_col})  # type: ignore

    # sort by postcode
    df = df.sort_values("postcode")  # type: ignore

    df.to_parquet(output_path)


if __name__ == "__main__":
    create_all()
