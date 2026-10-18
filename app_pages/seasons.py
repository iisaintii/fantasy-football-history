import streamlit as st
from db import query

# --------------------------------------------------
# Page Header
# --------------------------------------------------

st.title("📅 Seasons")
st.caption(
    "View standings, playoff finishes, draft results, and season awards."
)

# --------------------------------------------------
# Season Selector
# --------------------------------------------------

season_options = query(
    """
    SELECT
        year,
        platform
    FROM seasons
    ORDER BY year DESC
    """
)

selected_year = st.selectbox(
    "Season",
    season_options["year"].tolist()
)

# --------------------------------------------------
# Load Season Teams
# --------------------------------------------------

season_teams = query(
    """
    SELECT
        t.team_id,
        t.team_name,
        t.final_rank,
        t.wins,
        t.losses,
        t.ties,
        ROUND(t.points_for, 2) AS points_for,
        ROUND(t.points_against, 2) AS points_against,

        mgr.canonical_name AS manager,

        s.platform

    FROM teams t

    JOIN seasons s
        ON s.season_id = t.season_id

    JOIN managers mgr
        ON mgr.manager_id = t.manager_id

    WHERE s.year = ?
    """,
    (selected_year,),
)

if season_teams.empty:
    st.warning("No season data found.")
    st.stop()

# --------------------------------------------------
# Header Cards
# --------------------------------------------------

champion = season_teams[
    season_teams["final_rank"] == 1
]

runner_up = season_teams[
    season_teams["final_rank"] == 2
]

last_place = season_teams.sort_values(
    "final_rank",
    ascending=False
).iloc[0]

best_record = season_teams.sort_values(
    ["wins", "points_for"],
    ascending=False
).iloc[0]

most_points = season_teams.sort_values(
    "points_for",
    ascending=False
).iloc[0]

platform = season_teams["platform"].iloc[0]

st.subheader(
    f"{selected_year} ({platform.title()})"
)

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    if not champion.empty:
        c = champion.iloc[0]
        st.metric(
            "🏆 Champion",
            c["manager"]
        )

with c2:
    if not runner_up.empty:
        r = runner_up.iloc[0]
        st.metric(
            "🥈 Runner-Up",
            r["manager"]
        )

with c3:
    st.metric(
        "💀 Last Place",
        last_place["manager"]
    )

with c4:
    st.metric(
        "📈 Best Record",
        f"{int(best_record['wins'])}-{int(best_record['losses'])}"
    )

with c5:
    st.metric(
        "🔥 Most Points",
        f"{most_points['points_for']:.2f}"
    )

# --------------------------------------------------
# Tabs
# --------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Standings",
        "Playoffs",
        "Draft",
        "Awards"
    ]
)

# ==================================================
# STANDINGS
# ==================================================

with tab1:

    standings = season_teams.copy()

    standings["Record"] = (
        standings["wins"].astype(int).astype(str)
        + "-"
        + standings["losses"].astype(int).astype(str)
        + "-"
        + standings["ties"].astype(int).astype(str)
    )

    standings = standings.rename(
        columns={
            "final_rank": "Rank",
            "manager": "Manager",
            "team_name": "Team",
            "points_for": "Points For",
            "points_against": "Points Against",
        }
    )

    standings = standings.sort_values(
        "Rank"
    )

    st.dataframe(
        standings[
            [
                "Rank",
                "Manager",
                "Team",
                "Record",
                "Points For",
                "Points Against",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )

# ==================================================
# PLAYOFFS
# ==================================================

with tab2:

    playoff_results = season_teams.copy()

    playoff_results = playoff_results.rename(
        columns={
            "final_rank": "Finish",
            "manager": "Manager",
            "team_name": "Team",
        }
    )

    playoff_results = playoff_results.sort_values(
        "Finish"
    )

    st.dataframe(
        playoff_results[
            [
                "Finish",
                "Manager",
                "Team",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )

# ==================================================
# DRAFT
# ==================================================

with tab3:

    draft_picks = query(
        """
        SELECT
            dp.overall_pick AS Pick,

            mgr.canonical_name AS Manager,

            dp.player_name AS Player,

            dp.position AS Position,

            dp.nfl_team AS NFL_Team,

            dp.salary AS Cost

        FROM draft_picks dp

        JOIN drafts d
            ON d.draft_id = dp.draft_id

        JOIN seasons s
            ON s.season_id = d.season_id

        LEFT JOIN managers mgr
            ON mgr.manager_id = dp.manager_id

        WHERE s.year = ?

        ORDER BY
            dp.overall_pick
        """,
        (selected_year,),
    )

    if draft_picks.empty:

        st.info(
            "No draft data available for this season."
        )

    else:

        st.dataframe(
            draft_picks,
            hide_index=True,
            use_container_width=True,
            column_config={
                "NFL_Team": "NFL Team",
            },
        )

# ==================================================
# AWARDS
# ==================================================

with tab4:

    highest_score = query(
        """
        SELECT
            g.week,
            mgr.canonical_name AS manager,
            ROUND(g.points_for, 2) AS score
        FROM v_games g
        JOIN teams t
            ON t.team_id = g.team_id
        JOIN managers mgr
            ON mgr.manager_id = t.manager_id
        WHERE g.year = ?
        ORDER BY g.points_for DESC
        LIMIT 1
        """,
        (selected_year,),
    ).iloc[0]

    lowest_score = query(
        """
        SELECT
            g.week,
            mgr.canonical_name AS manager,
            ROUND(g.points_for, 2) AS score
        FROM v_games g
        JOIN teams t
            ON t.team_id = g.team_id
        JOIN managers mgr
            ON mgr.manager_id = t.manager_id
        WHERE g.year = ?
        ORDER BY g.points_for ASC
        LIMIT 1
        """,
        (selected_year,),
    ).iloc[0]

    largest_blowout = query(
        """
        SELECT
            ROUND(
                ABS(team1_score - team2_score),
                2
            ) AS margin
        FROM matchups m
        JOIN seasons s
            ON s.season_id = m.season_id
        WHERE s.year = ?
        ORDER BY margin DESC
        LIMIT 1
        """,
        (selected_year,),
    ).iloc[0]

    closest_game = query(
        """
        SELECT
            ROUND(
                ABS(team1_score - team2_score),
                2
            ) AS margin
        FROM matchups m
        JOIN seasons s
            ON s.season_id = m.season_id
        WHERE s.year = ?
          AND team1_score <> team2_score
        ORDER BY margin ASC
        LIMIT 1
        """,
        (selected_year,),
    ).iloc[0]

    a1, a2 = st.columns(2)

    with a1:

        st.info(
            f"🔥 Highest Score\n\n"
            f"{highest_score['manager']} scored "
            f"{highest_score['score']:.2f}"
        )

        st.info(
            f"💥 Largest Blowout\n\n"
            f"{largest_blowout['margin']:.2f} points"
        )

    with a2:

        st.info(
            f"🥶 Lowest Score\n\n"
            f"{lowest_score['manager']} scored "
            f"{lowest_score['score']:.2f}"
        )

        st.info(
            f"🎯 Closest Game\n\n"
            f"{closest_game['margin']:.2f} points"
        )