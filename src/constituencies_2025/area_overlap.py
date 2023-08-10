from pathlib import Path
import pandas as pd
import geopandas as gpd
from dataclasses import dataclass, field
from data_common.helpers.parquet import open_geo_file


@dataclass
class Geography:
    path: Path
    code_col: str
    output_code_col: str = ""
    gdf: gpd.GeoDataFrame = field(init=False)

    def __post_init__(self):
        # if the file is a parquet
        if self.output_code_col == "":
            self.output_code_col = self.code_col

        self.gdf = open_geo_file(self.path)

        # for area overlaps, convert all to british grid system
        self.gdf = self.gdf.to_crs("EPSG:27700")  # type: ignore

        if self.gdf is None:
            raise ValueError(f"Could not read file {self.path}")

        if self.code_col not in self.gdf.columns:
            raise ValueError(
                f"code_col {self.code_col} not in columns. Current columns: {self.gdf.columns}"
            )

    @property
    def geo_column(self) -> str:
        return f"{self.code_col}_geo"


def calculate_percentage_overlap_between_two_geographies(
    left_geo: Geography,
    right_geo: Geography,
) -> pd.DataFrame:
    """
    Create overlap of area between constituencies and local authorities as of 2022 from shapefile
    """

    # check left geo and right geo share a common CRS
    if not left_geo.gdf.crs == right_geo.gdf.crs:
        raise ValueError("CRS do not match for left and right geo.")

    # fix geometry
    print("fixing left geometry")
    left_geo.gdf["geometry"] = left_geo.gdf["geometry"].buffer(0)  # type: ignore
    print("fixing right geometry")
    right_geo.gdf["geometry"] = right_geo.gdf["geometry"].buffer(0)  # type: ignore

    # combine all left geometries series into one shape reflecting the outer boundary
    print("combining left geometries")
    left_mask = left_geo.gdf["geometry"].convex_hull.unary_union  # type: ignore
    print("combining right geometries")
    right_mask = right_geo.gdf["geometry"].convex_hull.unary_union  # type: ignore

    # clip both geographies so any non-overlapping areas are removed
    print("clipping left geometry")
    left_geo.gdf: gpd.GeoDataFrame = gpd.clip(left_geo.gdf, right_mask)  # type: ignore
    print("clipping right geo")
    right_geo.gdf: gpd.GeoDataFrame = gpd.clip(right_geo.gdf, left_mask)  # type: ignore

    print("merging geographies")
    # merge both on geometry
    df = left_geo.gdf.sjoin(right_geo.gdf, how="left")[
        [left_geo.code_col, right_geo.code_col]
    ]

    print("getting geometry columns in same df")
    # get the geometry column back in
    for geo in [left_geo, right_geo]:
        df = df.merge(geo.gdf[[geo.code_col, "geometry"]], on=geo.code_col).rename(
            columns={"geometry": f"{geo.code_col}_geo"}
        )
        # geo.gdf = None  # blank here to save memory

    print("calculating percentage overlap")
    # calculate the percentage overlap between two geographies based on area

    intersection = df.apply(
        lambda row: row[left_geo.geo_column].intersection(row[right_geo.geo_column]),
        axis=1,
    )
    df["overlap_area"] = intersection.apply(lambda x: x.area)
    df["original_area"] = df[left_geo.geo_column].apply(lambda x: x.area)
    df["percentage_overlap_area"] = df["overlap_area"] / df["original_area"]

    print("finalising")
    df = (
        df[df["percentage_overlap_area"] >= 0.01]
        .sort_values("percentage_overlap_area")
        .drop(columns=[x for x in df.columns if x.endswith("_geo")])
    )

    df = df.rename(
        columns={g.code_col: g.output_code_col for g in [left_geo, right_geo]}
    )

    return df
