import streamlit as st
import plotly.express as px

from db import get_summary, query


st.title("Fantasy Football Archives")

st.caption(
    "Fantasy league history, matchup records, "
    "manager careers, and auction draft analytics."
)


summary = get_summary()

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    "Seasons",
    f"{int(summary['seasons']):,}"
)

col2.metric(
    "Managers",
    f"{int(summary['managers']):,}"
)

col3.metric(
    "Season Teams",
    f"{int(summary['season_teams']):,}"
)

col4.metric(
    "Matchups",
    f"{int(summary['matchups']):,}"
)

col5.metric(
    "Draft Picks",
    f"{int(summary['draft_picks']):,}"
)


st.divider()

left, right = st.columns(2)

highest_score = query(
    """
    SELECT
        m.canonical_name AS manager,
        t.team_name,
        s.year,
        g.week,
        ROUND(g.points_for, 2) AS score
    FROM v_games g
    JOIN teams t
        ON t.team_id = g.team_id
    JOIN managers m
        ON m.manager_id = t.manager_id
    JOIN seasons s
        ON s.season_id = g.season_id
    ORDER BY g.points_for DESC
    LIMIT 1
    """
).iloc[0]

largest_blowout = query(
    """
    SELECT
        s.year,
        m.week,
        ROUND(ABS(m.team1_score - m.team2_score), 2) AS margin
    FROM matchups m
    JOIN seasons s
        ON s.season_id = m.season_id
    ORDER BY margin DESC
    LIMIT 1
    """
).iloc[0]

closest_win = query(
    """
    SELECT
        s.year,
        m.week,
        ROUND(ABS(m.team1_score - m.team2_score), 2) AS margin
    FROM matchups m
    JOIN seasons s
        ON s.season_id = m.season_id
    WHERE ABS(m.team1_score - m.team2_score) > 0
    ORDER BY margin ASC
    LIMIT 1
    """
).iloc[0]

most_wins = query(
    """
    SELECT
        canonical_name,
        wins
    FROM v_manager_career
    ORDER BY wins DESC
    LIMIT 1
    """
).iloc[0]

st.subheader("🏆 All-Time Records")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Highest Score",
    f"{highest_score['score']:.2f}",
    help=(
        f"{highest_score['manager']} "
        f"({highest_score['team_name']}) "
        f"- Week {highest_score['week']}, "
        f"{highest_score['year']}"
    )
)

c2.metric(
    "Largest Blowout",
    f"{largest_blowout['margin']:.2f}",
    help=(
        f"Week {largest_blowout['week']}, "
        f"{largest_blowout['year']}"
    )
)

c3.metric(
    "Closest Win",
    f"{closest_win['margin']:.2f}",
    help=(
        f"Week {closest_win['week']}, "
        f"{closest_win['year']}"
    )
)

c4.metric(
    "Most Career Wins",
    f"{most_wins['wins']}",
    help=most_wins["canonical_name"]
)

st.divider()

with left:

        st.subheader("All-Time Standings")

        careers = query(
            """
            SELECT
                canonical_name AS Manager,
                wins || '-' || losses || '-' || ties AS Record,
                ROUND(win_percentage, 2) AS WinPct,
                ROUND(points_for, 1) AS PF,
                ROUND(points_against, 1) AS PA,
                ROUND(avg_score, 1) AS AvgScore
            FROM v_manager_career
            ORDER BY win_percentage DESC
            """
        )

        st.dataframe(
            careers,
            hide_index=True,
            use_container_width=True
        )


with right:

    st.subheader("Highest Single-Game Scores")

    scores = query(
        """
        SELECT
            s.year AS Year,
            g.week AS Week,
            m.canonical_name AS Manager,
            t.team_name AS Team,
            ROUND(g.points_for, 2) AS Score
        FROM v_games g

        JOIN seasons s
            ON s.season_id = g.season_id

        JOIN teams t
            ON t.team_id = g.team_id

        JOIN managers m
            ON m.manager_id = t.manager_id

        ORDER BY g.points_for DESC
        LIMIT 10
        """
    )

    st.dataframe(
        scores,
        hide_index=True,
        use_container_width=True
    )


st.divider()

st.subheader("Scoring by Season")

season_scoring = query(
    """
    SELECT
        year AS Year,
        ROUND(AVG(points_for), 2) AS Average_Score,
        ROUND(MAX(points_for), 2) AS Highest_Score,
        ROUND(MIN(points_for), 2) AS Lowest_Score
    FROM v_games
    GROUP BY year
    ORDER BY year
    """
)

fig = px.line(
    season_scoring,
    x="Year",
    y=[
        "Average_Score",
        "Highest_Score",
        "Lowest_Score"
    ],
    markers=True,
    labels={
        "value": "Points",
        "variable": "Metric"
    }
)

st.plotly_chart(
    fig,
    use_container_width=True
)