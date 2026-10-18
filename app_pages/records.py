import streamlit as st
import pandas as pd
from db import query


# --------------------------------------------------
# Page Header
# --------------------------------------------------

st.title("🏆 League Records")

st.caption(
    "Single-game, season, playoff, and championship records. "
    "Zero-score matchups are excluded by default because the 2018 "
    "phantom-team scores were not preserved correctly by Yahoo."
)


# --------------------------------------------------
# Filters
# --------------------------------------------------

filter_col1, filter_col2 = st.columns(2)

with filter_col1:
    era = st.radio(
        "Record Era",
        options=[
            "Modern Era (2019–2022)",
            "All-Time (2011–2022)",
        ],
        horizontal=True,
    )

with filter_col2:
    exclude_zero_games = st.toggle(
        "Exclude matchups containing a zero score",
        value=True,
        help=(
            "Recommended. Yahoo preserved some 2018 phantom-team "
            "matchups as zeroes even though scores were later adjusted."
        ),
    )

start_year = 2019 if era == "Modern Era (2019–2022)" else 2011
zero_game_filter = (
    "AND g.points_for > 0 AND g.points_against > 0"
    if exclude_zero_games
    else ""
)
zero_matchup_filter = (
    "AND m.team1_score > 0 AND m.team2_score > 0"
    if exclude_zero_games
    else ""
)


# --------------------------------------------------
# Headline Records
# --------------------------------------------------

highest_score = query(
    f"""
    SELECT
        g.year,
        g.week,
        COALESCE(mgr.canonical_name, t.team_name) AS manager,
        t.team_name,
        ROUND(g.points_for, 2) AS score
    FROM v_games g
    JOIN teams t
        ON t.team_id = g.team_id
    LEFT JOIN managers mgr
        ON mgr.manager_id = t.manager_id
    WHERE g.year >= ?
      {zero_game_filter}
    ORDER BY g.points_for DESC
    LIMIT 1
    """,
    (start_year,),
).iloc[0]

largest_blowout = query(
    f"""
    SELECT
        s.year,
        m.week,

        COALESCE(mgr1.canonical_name, t1.team_name) AS manager1,
        ROUND(m.team1_score,2) AS score1,

        COALESCE(mgr2.canonical_name, t2.team_name) AS manager2,
        ROUND(m.team2_score,2) AS score2,

        ROUND(
            ABS(m.team1_score - m.team2_score),
            2
        ) AS margin

    FROM matchups m

    JOIN seasons s
        ON s.season_id = m.season_id

    JOIN teams t1
        ON t1.team_id = m.team1_id

    JOIN teams t2
        ON t2.team_id = m.team2_id

    LEFT JOIN managers mgr1
        ON mgr1.manager_id = t1.manager_id

    LEFT JOIN managers mgr2
        ON mgr2.manager_id = t2.manager_id

    WHERE s.year >= ?
    {zero_matchup_filter}

    ORDER BY margin DESC

    LIMIT 1
    """,
    (start_year,),
).iloc[0]

closest_game = query(
    f"""
    SELECT
        s.year,
        m.week,

        COALESCE(mgr1.canonical_name, t1.team_name) AS manager1,
        t1.team_name AS team1,
        ROUND(m.team1_score, 2) AS score1,

        COALESCE(mgr2.canonical_name, t2.team_name) AS manager2,
        t2.team_name AS team2,
        ROUND(m.team2_score, 2) AS score2,

        ROUND(
            ABS(m.team1_score - m.team2_score),
            2
        ) AS margin

    FROM matchups m

    JOIN seasons s
        ON s.season_id = m.season_id

    JOIN teams t1
        ON t1.team_id = m.team1_id

    JOIN teams t2
        ON t2.team_id = m.team2_id

    LEFT JOIN managers mgr1
        ON mgr1.manager_id = t1.manager_id

    LEFT JOIN managers mgr2
        ON mgr2.manager_id = t2.manager_id

    WHERE s.year >= ?
    AND m.team1_score <> m.team2_score
    {zero_matchup_filter}

    ORDER BY margin ASC
    LIMIT 1
    """,
    (start_year,),
).iloc[0]

highest_losing_score = query(
    f"""
    SELECT
        g.year,
        g.week,
        COALESCE(mgr.canonical_name, t.team_name) AS manager,
        ROUND(g.points_for, 2) AS score
    FROM v_games g
    JOIN teams t
        ON t.team_id = g.team_id
    LEFT JOIN managers mgr
        ON mgr.manager_id = t.manager_id
    WHERE g.year >= ?
      AND g.result = 'L'
      {zero_game_filter}
    ORDER BY g.points_for DESC
    LIMIT 1
    """,
    (start_year,),
).iloc[0]

lowest_winning_score = query(
    f"""
    SELECT
        g.year,
        g.week,
        COALESCE(mgr.canonical_name, t.team_name) AS manager,
        t.team_name,
        ROUND(g.points_for, 2) AS score
    FROM v_games g
    JOIN teams t
        ON t.team_id = g.team_id
    LEFT JOIN managers mgr
        ON mgr.manager_id = t.manager_id
    WHERE g.year >= ?
      AND g.result = 'W'
      {zero_game_filter}
    ORDER BY g.points_for ASC
    LIMIT 1
    """,
    (start_year,),
).iloc[0]

# --------------------------------------------------
# Playoff and Championship Records
# --------------------------------------------------

st.divider()
st.header("🏆 Playoff & Championship Records")

playoff_records = query(
    """
    SELECT
        mgr.manager_id,
        mgr.canonical_name AS Manager,
        COUNT(DISTINCT s.year) AS Seasons,
        SUM(CASE WHEN t.final_rank <= 4 THEN 1 ELSE 0 END) AS Playoffs,
        SUM(CASE WHEN t.final_rank = 1 THEN 1 ELSE 0 END) AS Championships,
        SUM(CASE WHEN t.final_rank = 2 THEN 1 ELSE 0 END) AS Runner_Ups,
        SUM(CASE WHEN t.final_rank = 3 THEN 1 ELSE 0 END) AS Third_Places,
        SUM(CASE WHEN t.final_rank = 4 THEN 1 ELSE 0 END) AS Fourth_Places
    FROM teams t
    JOIN seasons s
        ON s.season_id = t.season_id
    JOIN managers mgr
        ON mgr.manager_id = t.manager_id
    WHERE s.year >= ?
    
    GROUP BY
        mgr.manager_id,
        mgr.canonical_name
    ORDER BY
        Championships DESC,
        Playoffs DESC,
        Runner_Ups DESC,
        Third_Places DESC
    """,
    (start_year,),
)

champ_leader = (
    playoff_records
    .sort_values(
        ["Championships", "Playoffs"],
        ascending=False
    )
    .iloc[0]
)

top4_leader = (
    playoff_records
    .sort_values(
        ["Playoffs", "Championships"],
        ascending=False
    )
    .iloc[0]
)

championship_history = query(
    """
    SELECT
        s.year AS Year,
        COALESCE(champ_mgr.canonical_name, champ.team_name) AS Champion,
        champ.team_name AS Champion_Team,
        COALESCE(runner_mgr.canonical_name, runner.team_name) AS Runner_Up,
        runner.team_name AS Runner_Up_Team,
        COALESCE(third_mgr.canonical_name, third.team_name) AS Third_Place,
        third.team_name AS Third_Place_Team
    FROM seasons s
    LEFT JOIN teams champ
        ON champ.season_id = s.season_id
       AND champ.final_rank = 1
    LEFT JOIN managers champ_mgr
        ON champ_mgr.manager_id = champ.manager_id
    LEFT JOIN teams runner
        ON runner.season_id = s.season_id
       AND runner.final_rank = 2
    LEFT JOIN managers runner_mgr
        ON runner_mgr.manager_id = runner.manager_id
    LEFT JOIN teams third
        ON third.season_id = s.season_id
       AND third.final_rank = 3
    LEFT JOIN managers third_mgr
        ON third_mgr.manager_id = third.manager_id
    WHERE s.year >= ?
    ORDER BY s.year DESC
    """,
    (start_year,),
)

r1, r2, r3 = st.columns(3)
r4, r5, r6 = st.columns(3)

r1.metric(
    "Highest Score",
    f"{highest_score['score']:.2f}",
    help=(
        f"{highest_score['manager']} ({highest_score['team_name']}), "
        f"{int(highest_score['year'])} Week {int(highest_score['week'])}"
    ),
)

r2.metric(
    "Highest Losing Score",
    f"{highest_losing_score['score']:.2f}",
    help=(
        f"{highest_losing_score['manager']}, "
        f"{int(highest_losing_score['year'])} "
        f"Week {int(highest_losing_score['week'])}"
    ),
)

r3.metric(
    "Largest Blowout",
    f"{largest_blowout['margin']:.2f}",
    help=(
        f"{largest_blowout['manager1']} "
        f"({largest_blowout['score1']:.2f}) vs "
        f"{largest_blowout['manager2']} "
        f"({largest_blowout['score2']:.2f}) | "
        f"{int(largest_blowout['year'])} "
        f"Week {int(largest_blowout['week'])}"
    ),
)

r4.metric(
    "Lowest Winning Score",
    f"{lowest_winning_score['score']:.2f}",
    help=(
        f"{lowest_winning_score['manager']} "
        f"({lowest_winning_score['team_name']}) "
        f"{int(lowest_winning_score['year'])} "
        f"Week {int(lowest_winning_score['week'])}"
    ),
)

r5.metric(
    "Championship Leader",
    champ_leader["Manager"],
    f"{int(champ_leader['Championships'])} Titles"
)

r6.metric(
    "🎯 Most Top-4 Finishes",
    top4_leader["Manager"],
    f"{int(top4_leader['Playoffs'])} Top-4s"
)

st.info(
    f"Closest Game: "
    f"{closest_game['manager1']} "
    f"({closest_game['score1']:.2f}) vs "
    f"{closest_game['manager2']} "
    f"({closest_game['score2']:.2f}) "
    f"| Margin: {closest_game['margin']:.2f} "
    f"| {int(closest_game['year'])} Week {int(closest_game['week'])}"
)

# --------------------------------------------------
# Single-Game Records
# --------------------------------------------------

st.divider()
st.header("🏈 Single-Game Records")

single_tab1, single_tab2, single_tab3 = st.tabs(
    [
        "Highest Losing Scores",
        "Lowest Winning Scores",
        "Largest Blowouts"
    ]
)

with single_tab1:
    highest_losing_scores = query(
        f"""
        SELECT
            g.year AS Year,
            g.week AS Week,
            COALESCE(mgr.canonical_name, t.team_name) AS Manager,
            t.team_name AS Team,
            ROUND(g.points_for, 2) AS Score,
            ROUND(g.points_against, 2) AS Opponent_Score,
            ROUND(g.points_against - g.points_for, 2) AS Margin
        FROM v_games g
        JOIN teams t
            ON t.team_id = g.team_id
        LEFT JOIN managers mgr
            ON mgr.manager_id = t.manager_id
        WHERE g.year >= ?
          AND g.result = 'L'
          {zero_game_filter}
        ORDER BY g.points_for DESC
        LIMIT 25
        """,
        (start_year,),
    )

    st.dataframe(
        highest_losing_scores,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Opponent_Score": "Opponent Score",
        },
    )
    
with single_tab2:

    lowest_winning_scores = query(
        f"""
        SELECT
            g.year AS Year,
            g.week AS Week,
            COALESCE(
                mgr.canonical_name,
                t.team_name
            ) AS Manager,
            t.team_name AS Team,
            ROUND(g.points_for, 2) AS Score,
            ROUND(g.points_against, 2) AS Opponent_Score,
            ROUND(
                g.points_for -
                g.points_against,
                2
            ) AS Margin
        FROM v_games g

        JOIN teams t
            ON t.team_id = g.team_id

        LEFT JOIN managers mgr
            ON mgr.manager_id = t.manager_id

        WHERE g.year >= ?
          AND g.result = 'W'
          {zero_game_filter}

        ORDER BY g.points_for ASC

        LIMIT 25
        """,
        (start_year,),
    )

    st.dataframe(
        lowest_winning_scores,
        hide_index=True,
        use_container_width=True
    )

with single_tab3:
    blowouts = query(
        f"""
        SELECT
            s.year AS Year,
            m.week AS Week,
            COALESCE(mgr1.canonical_name, t1.team_name) AS Manager_1,
            t1.team_name AS Team_1,
            ROUND(m.team1_score, 2) AS Score_1,
            COALESCE(mgr2.canonical_name, t2.team_name) AS Manager_2,
            t2.team_name AS Team_2,
            ROUND(m.team2_score, 2) AS Score_2,
            ROUND(ABS(m.team1_score - m.team2_score), 2) AS Margin
        FROM matchups m
        JOIN seasons s
            ON s.season_id = m.season_id
        JOIN teams t1
            ON t1.team_id = m.team1_id
        JOIN teams t2
            ON t2.team_id = m.team2_id
        LEFT JOIN managers mgr1
            ON mgr1.manager_id = t1.manager_id
        LEFT JOIN managers mgr2
            ON mgr2.manager_id = t2.manager_id
        WHERE s.year >= ?
          {zero_matchup_filter}
        ORDER BY Margin DESC
        LIMIT 25
        """,
        (start_year,),
    )

    st.dataframe(
        blowouts,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Manager_1": "Manager 1",
            "Team_1": "Team 1",
            "Score_1": "Score 1",
            "Manager_2": "Manager 2",
            "Team_2": "Team 2",
            "Score_2": "Score 2",
        },
    )


# --------------------------------------------------
# Season Records
# --------------------------------------------------

st.divider()
st.header("📅 Season Records")

season_summary = query(
    f"""
    SELECT
        g.year,
        g.team_id,
        COALESCE(mgr.canonical_name, t.team_name) AS manager,
        t.team_name,
        COUNT(*) AS games,
        SUM(CASE WHEN g.result = 'W' THEN 1 ELSE 0 END) AS wins,
        SUM(CASE WHEN g.result = 'L' THEN 1 ELSE 0 END) AS losses,
        SUM(CASE WHEN g.result = 'T' THEN 1 ELSE 0 END) AS ties,
        ROUND(SUM(g.points_for), 2) AS points_for,
        ROUND(AVG(g.points_for), 2) AS average_score
    FROM v_games g
    JOIN teams t
        ON t.team_id = g.team_id
    LEFT JOIN managers mgr
        ON mgr.manager_id = t.manager_id
    WHERE g.year >= ?
      {zero_game_filter}
    GROUP BY
        g.year,
        g.team_id,
        manager,
        t.team_name
    """,
    (start_year,),
)

season_tab1, season_tab2, season_tab3 = st.tabs(
    [
        "Most Wins",
        "Most Points",
        "Highest Scoring Average",
    ]
)

with season_tab1:
    most_wins = season_summary.sort_values(
        ["wins", "points_for"],
        ascending=[False, False],
    ).head(25).copy()

    most_wins["Record"] = (
        most_wins["wins"].astype(str)
        + "-"
        + most_wins["losses"].astype(str)
        + "-"
        + most_wins["ties"].astype(str)
    )

    most_wins = most_wins.rename(
        columns={
            "year": "Year",
            "manager": "Manager",
            "team_name": "Team",
            "wins": "Wins",
            "points_for": "Points For",
        }
    )

    st.dataframe(
        most_wins[
            [
                "Year",
                "Manager",
                "Team",
                "Record",
                "Points For",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )

with season_tab2:
    most_points = season_summary.sort_values(
        "points_for",
        ascending=False,
    ).head(25).rename(
        columns={
            "year": "Year",
            "manager": "Manager",
            "team_name": "Team",
            "games": "Games",
            "points_for": "Points",
            "average_score": "Average",
        }
    )

    st.dataframe(
        most_points[
            [
                "Year",
                "Manager",
                "Team",
                "Games",
                "Points",
                "Average",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )

with season_tab3:
    highest_average = season_summary.sort_values(
        ["average_score", "points_for"],
        ascending=[False, False],
    ).head(25).rename(
        columns={
            "year": "Year",
            "manager": "Manager",
            "team_name": "Team",
            "games": "Games",
            "average_score": "Average Score",
            "points_for": "Points",
        }
    )

    st.dataframe(
        highest_average[
            [
                "Year",
                "Manager",
                "Team",
                "Games",
                "Average Score",
                "Points",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )




playoff_tab1, playoff_tab2 = st.tabs(
    [
        "Playoff Leaderboard",
        "Championship History",
    ]
)

with playoff_tab1:
    st.dataframe(
        playoff_records.drop(columns=["manager_id"]),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Runner_Ups": "Runner-Ups",
            "Third_Places": "Third Places",
            "Fourth_Places": "Fourth Places",
        },
    )

with playoff_tab2:
    st.dataframe(
        championship_history,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Champion_Team": "Champion Team",
            "Runner_Up": "Runner-Up",
            "Runner_Up_Team": "Runner-Up Team",
            "Third_Place": "Third Place",
            "Third_Place_Team": "Third Place Team",
        },
    )

# --------------------------------------------------
# Career Records
# --------------------------------------------------

st.divider()
st.header("👤 Career Records")

career_records = query(
    """
    SELECT
        mgr.canonical_name AS Manager,

        SUM(
            CASE
                WHEN g.result = 'W'
                THEN 1
                ELSE 0
            END
        ) AS Wins,

        SUM(
            CASE
                WHEN g.result = 'L'
                THEN 1
                ELSE 0
            END
        ) AS Losses,

        SUM(
            CASE
                WHEN g.result = 'T'
                THEN 1
                ELSE 0
            END
        ) AS Ties,

        COUNT(*) AS Games,

        ROUND(
            SUM(
                CASE
                    WHEN g.result = 'W'
                    THEN 1
                    ELSE 0
                END
            ) * 100.0 / COUNT(*),
            1
        ) AS Win_Pct

    FROM v_games g

    JOIN teams t
        ON t.team_id = g.team_id

    JOIN managers mgr
        ON mgr.manager_id = t.manager_id

    GROUP BY
        mgr.canonical_name
    """
)

career_tab1, career_tab2 = st.tabs(
    [
        "Most Career Wins",
        "Most Career Losses",
    ]
)

with career_tab1:

    st.dataframe(
        career_records.sort_values(
            "Wins",
            ascending=False
        ),
        hide_index=True,
        use_container_width=True,
    )

with career_tab2:

    st.dataframe(
        career_records.sort_values(
            "Losses",
            ascending=False
        ),
        hide_index=True,
        use_container_width=True,
    )

# --------------------------------------------------
# Streak Records
# --------------------------------------------------

st.divider()
st.header("🔥 Streak Records")

streak_games = query(
    """
    SELECT
        s.year,
        m.week,

        mgr.canonical_name AS Manager,

        CASE
            WHEN t.team_id = m.team1_id
                 AND m.team1_score > m.team2_score
            THEN 'W'

            WHEN t.team_id = m.team2_id
                 AND m.team2_score > m.team1_score
            THEN 'W'

            WHEN t.team_id = m.team1_id
                 AND m.team1_score < m.team2_score
            THEN 'L'

            WHEN t.team_id = m.team2_id
                 AND m.team2_score < m.team1_score
            THEN 'L'

            ELSE 'T'
        END AS Result

    FROM teams t

    JOIN managers mgr
        ON mgr.manager_id = t.manager_id

    JOIN seasons s
        ON s.season_id = t.season_id

    JOIN matchups m
        ON (
            m.team1_id = t.team_id
            OR
            m.team2_id = t.team_id
        )

    WHERE s.year >= ?

    ORDER BY
        mgr.canonical_name,
        s.year,
        m.week
    """,
    (start_year,),
)

win_streaks = []
lose_streaks = []

for manager in streak_games["Manager"].unique():

    mgr_games = streak_games[
        streak_games["Manager"] == manager
    ]

    current_win = 0
    current_loss = 0

    best_win = 0
    best_loss = 0

    for result in mgr_games["Result"]:

        if result == "W":

            current_win += 1
            current_loss = 0

            best_win = max(
                best_win,
                current_win
            )

        elif result == "L":

            current_loss += 1
            current_win = 0

            best_loss = max(
                best_loss,
                current_loss
            )

        else:

            current_win = 0
            current_loss = 0

    win_streaks.append(
        {
            "Manager": manager,
            "Winning Streak": best_win
        }
    )

    lose_streaks.append(
        {
            "Manager": manager,
            "Losing Streak": best_loss
        }
    )
    
win_df = pd.DataFrame(win_streaks)
loss_df = pd.DataFrame(lose_streaks)

streak_tab1, streak_tab2 = st.tabs(
    [
        "Longest Winning Streaks",
        "Longest Losing Streaks"
    ]
)

with streak_tab1:

    st.dataframe(
        win_df.sort_values(
            "Winning Streak",
            ascending=False
        ),
        hide_index=True,
        use_container_width=True
    )

with streak_tab2:

    st.dataframe(
        loss_df.sort_values(
            "Losing Streak",
            ascending=False
        ),
        hide_index=True,
        use_container_width=True
    )

