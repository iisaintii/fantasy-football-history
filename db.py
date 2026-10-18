from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st


DB_PATH = Path(
    r"C:\FantasyFootballHistory\data\fantasy.db"
)


def get_connection():
    return sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )


@st.cache_data(ttl=300)
def query(sql, parameters=None):

    if parameters is None:
        parameters = ()

    with get_connection() as conn:
        return pd.read_sql_query(
            sql,
            conn,
            params=parameters
        )


@st.cache_data(ttl=300)
def get_summary():

    sql = """
    SELECT
        (SELECT COUNT(*) FROM seasons) AS seasons,
        (SELECT COUNT(*) FROM managers) AS managers,
        (SELECT COUNT(*) FROM teams) AS season_teams,
        (SELECT COUNT(*) FROM matchups) AS matchups,
        (SELECT COUNT(*) FROM draft_picks) AS draft_picks
    """

    return query(sql).iloc[0]


@st.cache_data(ttl=300)
def get_managers():

    return query(
        """
        SELECT
            manager_id,
            COALESCE(display_name, canonical_name)
                AS manager_name
        FROM managers
        ORDER BY manager_name
        """
    )