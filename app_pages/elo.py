import pandas as pd
import plotly.express as px
import streamlit as st

from db import query


# --------------------------------------------------
# Page Header
# --------------------------------------------------

st.title("📈 Elo Ratings & Dynasty Rankings")

st.markdown(
    """
    [What is the Elo rating system?](https://en.wikipedia.org/wiki/Elo_rating_system)

    Elo estimates competitive strength based on game results and
    opponent strength. Beating a highly rated manager produces a larger
    gain than beating a lower-rated manager.
    """
)


# --------------------------------------------------
# Era Selection
# --------------------------------------------------

era = st.radio(
    "Ranking Era",
    options=[
        "Modern Era (2018–2022)",
        "Full Archive (2011–2022)",
    ],
    horizontal=True,
)

if era == "Modern Era (2018–2022)":
    start_year = 2018
    era_caption = (
        "Ratings restart at 1500 in 2018 and include only "
        "matchups and finishes from 2018 through 2022."
    )
else:
    start_year = 2011
    era_caption = (
        "Ratings start at 1500 in 2011 and include the complete "
        "Yahoo archive through 2022."
    )

st.caption(era_caption)


# --------------------------------------------------
# Load Matchups
# --------------------------------------------------

games = query(
    """
    SELECT
        s.year,
        m.week,
        m.matchup_id,
        t1.manager_id AS manager1_id,
        mgr1.canonical_name AS manager1,
        t2.manager_id AS manager2_id,
        mgr2.canonical_name AS manager2,
        m.team1_score,
        m.team2_score
    FROM matchups m
    JOIN seasons s
        ON s.season_id = m.season_id
    JOIN teams t1
        ON t1.team_id = m.team1_id
    JOIN teams t2
        ON t2.team_id = m.team2_id
    JOIN managers mgr1
        ON mgr1.manager_id = t1.manager_id
    JOIN managers mgr2
        ON mgr2.manager_id = t2.manager_id
    WHERE s.year >= ?
    ORDER BY
        s.year,
        m.week,
        m.matchup_id
    """,
    (start_year,),
)


# --------------------------------------------------
# Load Season Finishes
# One row per manager-season
# --------------------------------------------------

season_finishes = query(
    """
    SELECT
        s.year,
        t.manager_id,
        mgr.canonical_name AS manager,
        t.final_rank
    FROM teams t
    JOIN seasons s
        ON s.season_id = t.season_id
    JOIN managers mgr
        ON mgr.manager_id = t.manager_id
    WHERE s.year >= ?
      AND t.manager_id IS NOT NULL
      AND t.final_rank IS NOT NULL
    ORDER BY
        s.year,
        t.final_rank
    """,
    (start_year,),
)

if games.empty:
    st.warning(f"No matchup data was found beginning with {start_year}.")
    st.stop()


# --------------------------------------------------
# Elo Configuration
# --------------------------------------------------

STARTING_ELO = 1500
K_FACTOR = 20


def expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


# --------------------------------------------------
# Elo and Career Tracking
# --------------------------------------------------

ratings = {}
peak_ratings = {}
peak_seasons = {}
career_records = {}
history = []


def initialize_manager(manager_name):
    if manager_name not in ratings:
        ratings[manager_name] = STARTING_ELO
        peak_ratings[manager_name] = STARTING_ELO
        peak_seasons[manager_name] = start_year
        career_records[manager_name] = {
            "games": 0,
            "wins": 0,
            "losses": 0,
            "ties": 0,
        }


# --------------------------------------------------
# Process Matchups Chronologically
# --------------------------------------------------

for _, game in games.iterrows():
    manager1 = game["manager1"]
    manager2 = game["manager2"]

    initialize_manager(manager1)
    initialize_manager(manager2)

    rating1 = ratings[manager1]
    rating2 = ratings[manager2]

    expected1 = expected_score(rating1, rating2)
    expected2 = expected_score(rating2, rating1)

    if game["team1_score"] > game["team2_score"]:
        actual1 = 1.0
        actual2 = 0.0
        career_records[manager1]["wins"] += 1
        career_records[manager2]["losses"] += 1
    elif game["team1_score"] < game["team2_score"]:
        actual1 = 0.0
        actual2 = 1.0
        career_records[manager1]["losses"] += 1
        career_records[manager2]["wins"] += 1
    else:
        actual1 = 0.5
        actual2 = 0.5
        career_records[manager1]["ties"] += 1
        career_records[manager2]["ties"] += 1

    career_records[manager1]["games"] += 1
    career_records[manager2]["games"] += 1

    new_rating1 = rating1 + K_FACTOR * (actual1 - expected1)
    new_rating2 = rating2 + K_FACTOR * (actual2 - expected2)

    ratings[manager1] = new_rating1
    ratings[manager2] = new_rating2

    if new_rating1 > peak_ratings[manager1]:
        peak_ratings[manager1] = new_rating1
        peak_seasons[manager1] = int(game["year"])

    if new_rating2 > peak_ratings[manager2]:
        peak_ratings[manager2] = new_rating2
        peak_seasons[manager2] = int(game["year"])

    history.append(
        {
            "Year": int(game["year"]),
            "Week": int(game["week"]),
            "Manager": manager1,
            "Elo": new_rating1,
        }
    )

    history.append(
        {
            "Year": int(game["year"]),
            "Week": int(game["week"]),
            "Manager": manager2,
            "Elo": new_rating2,
        }
    )


# --------------------------------------------------
# Build Elo Rankings
# --------------------------------------------------

elo_rows = []

for manager, rating in ratings.items():
    record = career_records[manager]
    elo_rows.append(
        {
            "Manager": manager,
            "Current Elo": round(rating),
            "Peak Elo": round(peak_ratings[manager]),
            "Peak Season": peak_seasons[manager],
            "Games": record["games"],
            "Wins": record["wins"],
            "Losses": record["losses"],
            "Ties": record["ties"],
        }
    )

rankings = pd.DataFrame(elo_rows)
rankings = rankings.sort_values(
    ["Current Elo", "Peak Elo"], ascending=[False, False]
).reset_index(drop=True)
rankings.insert(0, "Rank", range(1, len(rankings) + 1))


# --------------------------------------------------
# Power Rankings
# --------------------------------------------------

st.divider()
st.subheader("⚡ Power Rankings")

top_current = rankings.iloc[0]
top_peak = rankings.sort_values("Peak Elo", ascending=False).iloc[0]

e1, e2, e3, e4 = st.columns(4)
e1.metric("Current #1", top_current["Manager"])
e2.metric("Current Elo", int(top_current["Current Elo"]))
e3.metric("Highest Peak Elo", int(top_peak["Peak Elo"]))
e4.metric("Peak Elo Manager", top_peak["Manager"])

st.dataframe(
    rankings,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Current Elo": st.column_config.NumberColumn("Current Elo", format="%d"),
        "Peak Elo": st.column_config.NumberColumn("Peak Elo", format="%d"),
    },
)


# --------------------------------------------------
# Manager Elo History
# --------------------------------------------------

st.divider()
selected_manager = st.selectbox(
    "Select Manager for Elo History",
    rankings["Manager"].sort_values().tolist(),
)

history_df = pd.DataFrame(history)
manager_history = history_df[
    history_df["Manager"] == selected_manager
].copy().reset_index(drop=True)
manager_history["Career Game"] = range(1, len(manager_history) + 1)

selected_row = rankings[
    rankings["Manager"] == selected_manager
].iloc[0]

h1, h2, h3, h4 = st.columns(4)
h1.metric("Current Elo", int(selected_row["Current Elo"]))
h2.metric("Peak Elo", int(selected_row["Peak Elo"]))
h3.metric("Peak Season", int(selected_row["Peak Season"]))
h4.metric(
    "Era Record",
    (
        f"{int(selected_row['Wins'])}-"
        f"{int(selected_row['Losses'])}-"
        f"{int(selected_row['Ties'])}"
    ),
)

fig = px.line(
    manager_history,
    x="Career Game",
    y="Elo",
    markers=True,
    hover_data=["Year", "Week"],
    title=f"{selected_manager} Elo History",
)
fig.add_hline(
    y=STARTING_ELO,
    line_dash="dash",
    line_color="gray",
    annotation_text="Starting Elo",
)
fig.update_layout(
    xaxis_title="Career Game",
    yaxis_title="Elo Rating",
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# Dynasty Rankings
# --------------------------------------------------

st.divider()
st.subheader("👑 Dynasty Rankings")
st.caption(
    "Dynasty Score rewards championships, top-four finishes, "
    "matchup wins, and peak competitive strength."
)

dynasty_rows = []

for manager in ratings.keys():
    manager_finishes = season_finishes[
        season_finishes["manager"] == manager
    ]

    seasons_played = int(manager_finishes["year"].nunique())
    playoff_appearances = int(
        (manager_finishes["final_rank"] <= 4).sum()
    )
    championships = int(
        (manager_finishes["final_rank"] == 1).sum()
    )
    runner_ups = int(
        (manager_finishes["final_rank"] == 2).sum()
    )
    third_places = int(
        (manager_finishes["final_rank"] == 3).sum()
    )
    fourth_places = int(
        (manager_finishes["final_rank"] == 4).sum()
    )

    wins = career_records[manager]["wins"]
    peak_elo = round(peak_ratings[manager])
    peak_elo_bonus = max(peak_elo - STARTING_ELO, 0)

    achievement_score = (
        championships * 100
        + runner_ups * 50
        + third_places * 30
        + fourth_places * 15
        + wins
    )

    dynasty_score = achievement_score + peak_elo_bonus

    dynasty_rows.append(
        {
            "Manager": manager,
            "Seasons": seasons_played,
            "Playoffs": playoff_appearances,
            "Titles": championships,
            "Runner-Ups": runner_ups,
            "Third Places": third_places,
            "Fourth Places": fourth_places,
            "Wins": wins,
            "Peak Elo": peak_elo,
            "Dynasty Score": dynasty_score,
        }
    )

dynasty = pd.DataFrame(dynasty_rows)
dynasty = dynasty.sort_values(
    ["Dynasty Score", "Titles", "Playoffs", "Wins"],
    ascending=[False, False, False, False],
).reset_index(drop=True)
dynasty.insert(0, "Rank", range(1, len(dynasty) + 1))

dynasty_leader = dynasty.iloc[0]

d1, d2, d3, d4 = st.columns(4)
d1.metric("Dynasty Leader", dynasty_leader["Manager"])
d2.metric("Dynasty Score", int(dynasty_leader["Dynasty Score"]))
d3.metric("Championships", int(dynasty_leader["Titles"]))
d4.metric("Playoff Appearances", int(dynasty_leader["Playoffs"]))

st.dataframe(
    dynasty[
        [
            "Rank",
            "Manager",
            "Dynasty Score",
            "Seasons",
            "Titles",
            "Runner-Ups",
            "Third Places",
            "Fourth Places",
            "Playoffs",
            "Wins",
            "Peak Elo",
        ]
    ],
    hide_index=True,
    use_container_width=True,
    column_config={
        "Dynasty Score": st.column_config.NumberColumn(
            "Dynasty Score",
            help=(
                "Placement points + matchup wins "
                "+ Peak Elo above 1500"
            ),
        ),
        "Peak Elo": st.column_config.NumberColumn(
            "Peak Elo",
            format="%d",
        ),
    },
)


# --------------------------------------------------
# Scoring Explanation
# --------------------------------------------------

with st.expander("How are Elo and Dynasty Score calculated?"):
    st.markdown(
        """
        ### Elo

        Every manager begins the selected era at **1500 Elo**.

        - Beating a stronger opponent earns more rating points.
        - Beating a weaker opponent earns fewer rating points.
        - Losing to a weaker opponent costs more rating points.
        - Playoff matchups affect Elo like all other matchups.
        - The calculation uses a **K-factor of 20**.

        ### Dynasty Score

        - Championship: **100 points**
        - Runner-up: **50 points**
        - Third place: **30 points**
        - Fourth place: **15 points**
        - Each matchup win: **1 point**
        - Peak Elo above 1500: **1 point per Elo point**

        Each top-four finish is counted once per season.
        """
    )
