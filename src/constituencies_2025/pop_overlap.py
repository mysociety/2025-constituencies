from data_common.db.duck import DuckQuery
from pathlib import Path
import pandas as pd


def calculate_population_crossover(area_type_a: str, area_type_b: str) -> pd.DataFrame:
    """
    Based on a precalculated postcode lookup, calculate the population crossover between two areas.
    This works by dividing the population of each small area LSOA (or equiv) by the number of postcodes in that area.
    From this, we can calculate the population crossover in the intersections between areas.
    For NI, we use 2023 datazone centroids as the equiv of postcode centroids.
    """

    duck = DuckQuery()

    duck.set_jinja_variable("area_type_a", area_type_a)
    duck.set_jinja_variable("area_type_b", area_type_b)

    @duck.as_source
    class postcode_lookup:
        # the 'old' postcode lookups, to old constituencies
        source = Path("data", "interim", "combo_postcode_lookup.parquet")

    @duck.as_source
    class lsoa_pop:
        # 2019 populations by lsoa
        source = pd.read_csv(Path("data", "raw", "2019_population.csv"), thousands=",")  # type: ignore

    @duck.as_view
    class lsoa_count:
        # get the count of how many postcodes in each lsoa
        query = """
        SELECT
            LSOA11 as lsoa,
            count(distinct postcode) as count
        FROM
            postcode_lookup
        GROUP BY
            all;
        """

    @duck.as_view
    class lsoa_count_pop:
        # calculate average population per postcode.
        # where this is 0, set to 1 (areas with high commerical, low residence, roughly this works out fine)

        query = """
        SELECT
            lsoa,
            pop,
            count,
            case when cast(pop as float)/cast(count as float) = 0 then 1 else cast(pop as float)/cast(count as float) end as average_pop_per_postcode
        FROM
            lsoa_count
        JOIN
            lsoa_pop using(lsoa)
        """

    @duck.as_view
    class pcon_pop:
        # add up to get total population per pcon

        query = """
        SELECT
            {{ area_type_a }},
            sum(average_pop_per_postcode) as pcon_pop
        FROM
            postcode_lookup
        JOIN
            lsoa_count_pop on (postcode_lookup.LSOA11 = lsoa_count_pop.lsoa)
        GROUP BY
            ALL
        """

    @duck.as_view
    class pop_overlap:
        # this is the poplation overlap between the two geographies
        query = """
        SELECT
            {{ area_type_a }},
            {{ area_type_b }},
            sum(average_pop_per_postcode) as pop_overlap
        FROM
            postcode_lookup
        JOIN
            lsoa_count_pop on (postcode_lookup.LSOA11 = lsoa_count_pop.lsoa)
        GROUP BY
            ALL
        ORDER BY
            {{ area_type_a }}
        """

    @duck.as_view
    class percentage_pop_overlap:
        # bringing back the population of the pcon and the overlap, we can calculate the percentage overlap
        query = """
        SELECT
            {{ area_type_a }},
            {{ area_type_b }},
            pop_overlap/pcon_pop as percentage_overlap_pop,
            pop_overlap as overlap_pop,
            pcon_pop as original_pop
        FROM
            pop_overlap
        JOIN
            pcon_pop using ({{ area_type_a }})
        """

    df = duck.last_query.df()
    df = df.sort_values("percentage_overlap_pop")

    return df
