from pathlib import Path
import pandas as pd
from .area_overlap import (
    calculate_percentage_overlap_between_two_geographies,
    Geography,
)
from .pop_overlap import calculate_population_crossover


def calculate_pop_crossovers():
    combos = [
        ("LSOA11", "PARL25"),
        ("PARL10", "PARL25"),
        ("PARL25", "PARL10"),
        ("PARL25", "LAD23"),
        ("PARL10", "LAD23"),
    ]

    for left, right in combos:
        print(f"Calculating overlap between {left} and {right}")
        df = calculate_population_crossover(left, right)
        df_name = f"{left}_{right}_pop_overlap"
        df.to_parquet(Path("data", "interim", "pop_overlap", f"{df_name}.parquet"))


def calculate_area_crossovers():
    """
    Generate area overlaps for overlaps between different kinds of geography
    """

    current_cons = Path(
        "data",
        "raw",
        "external",
        "Westminster_Parliamentary_Constituencies_(Dec_2021)_UK_BFC.parquet",
    )
    future_cons = Path(
        "data", "packages", "parliament_con_2025", "parl_constituencies_2025.parquet"
    )

    lsoa_path = Path("data", "raw", "external", "small_area_data", "*.parquet")

    la_path = Path(
        "data",
        "raw",
        "external",
        "Local_Authority_Districts_May_2023_UK_BFC_V2_179125415192200502.parquet",
    )

    parl_2010 = Geography(current_cons, "PCON21CD", "PARL10")
    parl_2025 = Geography(future_cons, "short_code", "PARL25")
    lsoa_2011 = Geography(lsoa_path, "areacode", "LSOA11")
    la_2023 = Geography(la_path, "LAD23CD", "LAD23")

    combos = [
        (parl_2010, parl_2025),
        (parl_2025, parl_2010),
        (lsoa_2011, parl_2025),
        (parl_2010, la_2023),
        (parl_2025, la_2023),
    ]

    for left, right in combos:
        print(
            f"Calculating overlap between {left.output_code_col} and {right.output_code_col}"
        )
        df = calculate_percentage_overlap_between_two_geographies(left, right)
        df_name = f"{left.output_code_col}_{right.output_code_col}_area_overlap"
        df.to_parquet(Path("data", "interim", "area_overlap", f"{df_name}.parquet"))


def pcon_pop_overlap():
    df = calculate_population_crossover("PARL10", "PARL25")
    df.to_parquet(Path("data", "interim", "2010_2025_pop_overlap.parquet"))


def combine_all_overlaps():
    combos = [
        ("LSOA11", "PARL25"),
        ("PARL10", "PARL25"),
        ("PARL25", "PARL10"),
        ("PARL25", "LAD23"),
        ("PARL10", "LAD23"),
    ]

    for left, right in combos:
        print(f"Combining {left} and {right}")
        combine_overlap(left, right)


def combine_overlap(left_area: str, right_area: str):
    area_df = pd.read_parquet(
        Path(
            "data",
            "interim",
            "area_overlap",
            f"{left_area}_{right_area}_area_overlap.parquet",
        )
    )
    pop_df = pd.read_parquet(
        Path(
            "data",
            "interim",
            "pop_overlap",
            f"{left_area}_{right_area}_pop_overlap.parquet",
        )
    )

    merge_cols = [left_area, right_area]

    df = pd.merge(left=area_df, right=pop_df, on=merge_cols, how="left")
    df = df.fillna(0)

    # sort by first column then second column
    df = df.sort_values(by=[left_area, right_area])

    # reduce area_overlap, pop_overlap to 2 dp
    all_generated_cols = df.columns[2:]

    for col in all_generated_cols:
        df[col] = df[col].round(2)

    final_filename = f"{left_area}_{right_area}_combo_overlap"

    df.to_parquet(Path("data", "interim", "combo_overlap", final_filename + ".parquet"))
    # df.to_csv(
    #    Path("data", "interim", "combo_overlap", final_filename + ".csv"), index=False
    # )
