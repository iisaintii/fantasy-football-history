import streamlit as st
import plotly.express as px

from db import query

st.title("👤 Manager Careers")

managers = query("""
SELECT
    canonical_name
FROM managers
ORDER BY canonical_name
""")

manager = st.selectbox(
    "Manager",
    managers["canonical_name"].tolist()
)

#
# Career Summary
#

career = query(
    """
    SELECT *
    FROM v_manager_career
    WHERE canonical_name = ?
    """,
    (manager,)
)

if len(career) == 0:
    st.warning("No data found.")
    st.stop()

career = career.iloc[0]

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Games",
    int(career["games"])
)

c2.metric(
    "Wins",
    int(career["wins"])
)

c3.metric(
    "Losses",
    int(career["losses"])
)

c4.metric(
    "Win %",
    f"{career['win_percentage']:.2f}"
)

c5.metric(
    "Avg Score",
    f"{career['avg_score']:.1f}"
)

st.divider()

seasons = query(
    """
    SELECT
        s.year,

        SUM(
            CASE
                WHEN g.result='W'
                THEN 1
                ELSE 0
            END
        ) AS wins,

        SUM(
            CASE
                WHEN g.result='L'
                THEN 1
                ELSE 0
            END
        ) AS losses,

        ROUND(
            AVG(g.points_for),
            2
        ) AS avg_score

    FROM v_games g

    JOIN teams t
        ON t.team_id = g.team_id

    JOIN managers m
        ON m.manager_id = t.manager_id

    JOIN seasons s
        ON s.season_id = g.season_id

    WHERE m.canonical_name = ?

    GROUP BY s.year

    ORDER BY s.year
    """,
    (manager,)
)

st.subheader("📈 Career Trend")

fig = px.line(
    seasons,
    x="year",
    y="wins",
    markers=True
)

fig.update_layout(
    yaxis_title="Wins",
    xaxis_title="Season"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.subheader("📅 Season History")

seasons["Record"] = (
    seasons["wins"].astype(str)
    + "-"
    + seasons["losses"].astype(str)
)

st.dataframe(
    seasons[
        [
            "year",
            "Record",
            "avg_score"
        ]
    ],
    hide_index=True,
    use_container_width=True
)

highest_scores = query(
    """
    SELECT
        g.year,
        g.week,

        t.team_name,

        ROUND(
            g.points_for,
            2
        ) AS score

    FROM v_games g

    JOIN teams t
        ON t.team_id = g.team_id

    JOIN managers m
        ON m.manager_id = t.manager_id

    WHERE m.canonical_name = ?

    ORDER BY g.points_for DESC

    LIMIT 10
    """,
    (manager,)
)

st.subheader("🔥 Highest Scores Ever")

st.dataframe(
    highest_scores,
    hide_index=True,
    use_container_width=True
)

rivals = query(
    """
    SELECT
        opponent,
        wins,
        losses,
        games,
        avg_margin

    FROM v_head_to_head

    WHERE manager = ?

    ORDER BY games DESC

    LIMIT 10
    """,
    (manager,)
)

st.subheader("⚔️ Top Rivalries")

st.dataframe(
    rivals,
    hide_index=True,
    use_container_width=True
)

team_names = query(
    """
    SELECT DISTINCT
        s.year,
        t.team_name

    FROM teams t

    JOIN managers m
        ON m.manager_id = t.manager_id

    JOIN seasons s
        ON s.season_id = t.season_id

    WHERE m.canonical_name = ?

    ORDER BY s.year
    """,
    (manager,)
)

st.subheader("🏷 Team Names Through The Years")

st.dataframe(
    team_names,
    hide_index=True,
    use_container_width=True
)

