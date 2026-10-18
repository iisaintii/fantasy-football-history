import streamlit as st

from db import query

st.title("⚔️ Head-to-Head")

managers = query("""
SELECT
    manager_id,
    canonical_name
FROM managers
ORDER BY canonical_name
""")

manager_names = managers["canonical_name"].tolist()

col1, col2 = st.columns(2)

with col1:
    manager1 = st.selectbox(
        "Manager 1",
        manager_names,
        index=0
    )

with col2:
    manager2 = st.selectbox(
        "Manager 2",
        manager_names,
        index=1
    )

if manager1 != manager2:

    summary = query(
        """
        SELECT *
        FROM v_head_to_head
        WHERE manager = ?
          AND opponent = ?
        """,
        (manager1, manager2)
    )

    if len(summary):

        row = summary.iloc[0]

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            manager1,
            row["wins"]
        )

        c2.metric(
            manager2,
            row["losses"]
        )

        c3.metric(
            "Games",
            row["games"]
        )

        c4.metric(
            "Avg Margin",
            f"{row['avg_margin']:.2f}"
        )

        st.subheader(
            f"{manager1} vs {manager2}"
        )

        record = (
            f"{row['wins']}-"
            f"{row['losses']}-"
            f"{row['ties']}"
        )

        st.write(
            f"**Record:** {record}"
        )

        st.write(
            f"**Points For:** "
            f"{row['points_for']:.2f}"
        )

        st.write(
            f"**Points Against:** "
            f"{row['points_against']:.2f}"
        )

    history = query(
        """
        SELECT
            g.year,
            g.week,

            tm.team_name AS team,

            ROUND(g.points_for,2)
                AS points_for,

            ROUND(g.points_against,2)
                AS points_against,

            g.result

        FROM v_games g

        JOIN teams tm
            ON tm.team_id = g.team_id

        JOIN teams opp
            ON opp.team_id =
                g.opponent_id

        JOIN managers m
            ON m.manager_id =
                tm.manager_id

        JOIN managers o
            ON o.manager_id =
                opp.manager_id

        WHERE m.canonical_name = ?
          AND o.canonical_name = ?

        ORDER BY
            g.year DESC,
            g.week DESC
        """,
        (manager1, manager2)
    )

    st.subheader(
        "Matchup History"
    )

    st.dataframe(
        history,
        hide_index=True,
        use_container_width=True
    )