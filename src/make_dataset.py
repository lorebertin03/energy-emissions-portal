import sqlite3
from pathlib import Path

import pandas as pd


def build_dataset():
    """Import the data, select the columns and save final database"""
    db_dir = Path("../data/processed")
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "owid_energy.db"

    # columns to select
    energy_columns = {
        "country",
        "year",
        "iso_code",
        "biofuels_energy_twh",
        "coal_energy_twh",
        "gas_energy_twh",
        "hydro_energy_twh",
        "low_carbon_energy_per_capita_kwh",
        "nuclear_energy_twh",
        "oil_energy_twh",
        "other_renewables_including_bioenergy_energy_twh",
        "solar_energy_twh",
        "total_energy_twh",
        "wind_energy_twh",
    }

    co2_columns = {
        "country",
        "year",
        "population",
        "gdp",
        "iso_code",
        "co2_including_luc",
        "co2_including_luc_per_capita",
        "cumulative_co2_including_luc",
        "ghg_per_capita",
        "share_global_co2_including_luc",
        "share_global_cumulative_co2",
        "total_ghg",
    }

    # reading csvs
    df_energy = pd.read_csv(
        "https://catalog.ourworldindata.org/energy/owid_energy/owid_energy.csv",
        usecols=energy_columns,
    )

    df_co2 = pd.read_csv(
        "https://raw.githubusercontent.com/owid/co2-data/"
        "refs/heads/master/owid-co2-data.csv",
        usecols=co2_columns,
    )

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # clearing if existing
        cursor.execute("DROP VIEW IF EXISTS country_data;")
        cursor.execute("DROP TABLE IF EXISTS country_data;")

        # Creating SQL tables
        df_co2.to_sql("co2_emissions", conn, if_exists="replace", index=False)
        df_energy.to_sql("energy_mix", conn, if_exists="replace", index=False)

        # Creating indexes on key (country, year)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_co2_cy ON co2_emissions (country, year);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_en_cy ON energy_mix (country, year);"
        )

        # Creating VIEW with LEFT JOIN
        cursor.execute(
            """
            CREATE VIEW country_data AS
            SELECT
                -- CO2 and Greenhouse Gasses
                c.country,
                c.iso_code,
                c.year,
                c.population,
                c.gdp,
                -- GDP per capita
                (c.gdp / NULLIF(c.population, 0)) AS gdp_per_capita,
                c.co2_including_luc AS co2,
                c.co2_including_luc_per_capita AS co2_per_capita,
                c.cumulative_co2_including_luc AS cumulative_co2,
                c.ghg_per_capita,
                c.share_global_co2_including_luc AS share_global_co2,
                c.share_global_cumulative_co2,
                c.total_ghg,
                -- Energy sources
                e.biofuel_energy_twh,
                e.coal_energy_twh,
                e.gas_energy_twh,
                e.hydro_energy_twh,
                e.low_carbon_energy_per_capita_kwh,
                e.nuclear_energy_twh,
                e.oil_energy_twh,
                e.other_renewables_including_bioenergy_energy_twh,
                e.solar_energy_twh,
                e.total_energy_twh,
                e.wind_energy_twh
            FROM co2_emissions c
            LEFT JOIN energy_mix e
                ON c.country = e.country
               AND c.year = e.year;
            """
        )
        conn.commit()

    print(
        f"Relational database imported\n"
        f"   - 'co2_emissions' table: {len(df_co2):,} rows\n"
        f"   - 'energy_mix' table:    {len(df_energy):,} rows\n"
        f"   - 'country_data' VIEW."
    )


if __name__ == "__main__":
    build_dataset()
