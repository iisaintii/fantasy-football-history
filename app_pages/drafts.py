import pandas as pd
import plotly.express as px
import streamlit as st

from db import query


# --------------------------------------------------
# Page Header
# --------------------------------------------------

st.title("💰 Draft Analytics")
st.caption(
    "Explore Yahoo and Sleeper draft history, manager spending tendencies, "
    "repeat player selections, and value picks."
)


# --------------------------------------------------
# Load Draft History
# --------------------------------------------------

draft_history = query(
    """
    SELECT
        s.year,
        s.platform,
        dp.overall_pick,
        dp.player_name,
        dp.position,
        dp.nfl_team,
        dp.salary,
        dp.manager_id,
        mgr.canonical_name AS manager,
        t.team_name,
        t.final_rank,
        CASE
            WHEN t.final_rank = 1 THEN 'Champion'
            WHEN t.final_rank = 2 THEN 'Runner-Up'
            WHEN t.final_rank = 3 THEN 'Third Place'
            WHEN t.final_rank = 4 THEN 'Fourth Place'
            WHEN t.final_rank IS NULL THEN 'Unknown'
            ELSE 'Other'
        END AS season_finish
    FROM draft_picks dp
    JOIN drafts d
        ON d.draft_id = dp.draft_id
    JOIN seasons s
        ON s.season_id = d.season_id
    LEFT JOIN managers mgr
        ON mgr.manager_id = dp.manager_id
    LEFT JOIN teams t
        ON t.team_id = dp.team_id
    ORDER BY
        s.year DESC,
        dp.overall_pick
    """
)

if draft_history.empty:
    st.warning("No draft data is available.")
    st.stop()

latest_year = int(draft_history["year"].max())
earliest_year = int(draft_history["year"].min())

# Normalize display values without changing the source data.
draft_history["manager"] = draft_history["manager"].fillna("Unmapped")
draft_history["position"] = draft_history["position"].fillna("Unknown")
draft_history["nfl_team"] = draft_history["nfl_team"].fillna("")
draft_history["team_name"] = draft_history["team_name"].fillna("")
draft_history["salary"] = pd.to_numeric(
    draft_history["salary"],
    errors="coerce",
)


# --------------------------------------------------
# Filters
# --------------------------------------------------

filter1, filter2, filter3 = st.columns(3)

with filter1:
    selected_years = st.multiselect(
        "Seasons",
        options=sorted(draft_history["year"].unique(), reverse=True),
        default=sorted(draft_history["year"].unique()),
    )

with filter2:
    selected_platforms = st.multiselect(
        "Platforms",
        options=sorted(draft_history["platform"].dropna().unique()),
        default=sorted(draft_history["platform"].dropna().unique()),
    )

with filter3:
    selected_positions = st.multiselect(
        "Positions",
        options=sorted(draft_history["position"].unique()),
        default=sorted(draft_history["position"].unique()),
    )

filtered = draft_history[
    draft_history["year"].isin(selected_years)
    & draft_history["platform"].isin(selected_platforms)
    & draft_history["position"].isin(selected_positions)
].copy()

if filtered.empty:
    st.warning("No draft picks match the selected filters.")
    st.stop()


# --------------------------------------------------
# Headline Metrics
# --------------------------------------------------

priced = filtered[filtered["salary"].notna()].copy()

most_drafted_player = (
    filtered.groupby("player_name", as_index=False)
    .size()
    .sort_values(["size", "player_name"], ascending=[False, True])
    .iloc[0]
)

most_active_manager = (
    filtered[filtered["manager"] != "Unmapped"]
    .groupby("manager", as_index=False)
    .size()
    .sort_values(["size", "manager"], ascending=[False, True])
    .iloc[0]
)

m1, m2, m3 = st.columns(3)

m1.metric("Draft Seasons", filtered["year"].nunique())
m2.metric("Draft Picks", f"{len(filtered):,}")
m3.metric(
    "Most Drafted Player",
    most_drafted_player["player_name"],
    f"{int(most_drafted_player['size'])} selections",
)

st.caption(
    f"Available draft history spans {earliest_year} through {latest_year}."
)


# --------------------------------------------------
# Tabs
# --------------------------------------------------

history_tab, tendencies_tab, repeat_tab, bargains_tab = st.tabs(
    [
        "Draft History",
        "Manager Tendencies",
        "Most Drafted Players",
        "Value Picks",
    ]
)


# ==================================================
# Draft History
# ==================================================

with history_tab:
    st.subheader("Draft History")

    player_search = st.text_input(
        "Search player",
        placeholder="Enter all or part of a player name",
    )

    manager_options = ["All Managers"] + sorted(
        filtered["manager"].unique().tolist()
    )
    history_manager = st.selectbox(
        "Manager",
        manager_options,
        key="draft_history_manager",
    )

    history_view = filtered.copy()

    if player_search.strip():
        history_view = history_view[
            history_view["player_name"].str.contains(
                player_search.strip(),
                case=False,
                na=False,
            )
        ]

    if history_manager != "All Managers":
        history_view = history_view[
            history_view["manager"] == history_manager
        ]

    history_view = history_view.rename(
        columns={
            "year": "Year",
            "platform": "Platform",
            "overall_pick": "Pick",
            "manager": "Manager",
            "team_name": "Fantasy Team",
            "player_name": "Player",
            "position": "Position",
            "nfl_team": "NFL Team",
            "salary": "Cost",
            "season_finish": "Season Finish",
        }
    )

    st.dataframe(
        history_view[
            [
                "Year",
                "Platform",
                "Pick",
                "Manager",
                "Fantasy Team",
                "Player",
                "Position",
                "NFL Team",
                "Cost",
                "Season Finish",
            ]
        ],
        hide_index=True,
        use_container_width=True,
        column_config={
            "Cost": st.column_config.NumberColumn(
                "Cost",
                format="$%d",
            )
        },
    )


# ==================================================
# Manager Tendencies
# ==================================================

with tendencies_tab:
    st.subheader("Manager Draft Tendencies")

    managers = sorted(
        manager
        for manager in filtered["manager"].unique()
        if manager != "Unmapped"
    )

    selected_manager = st.selectbox(
        "Select Manager",
        managers,
        key="tendency_manager",
    )

    manager_picks = filtered[
        filtered["manager"] == selected_manager
    ].copy()

    manager_priced = manager_picks[
        manager_picks["salary"].notna()
    ].copy()

    summary1, summary2, summary3, summary4 = st.columns(4)

    summary1.metric(
        "Drafts Represented",
        manager_picks["year"].nunique(),
    )
    summary2.metric(
        "Total Picks",
        len(manager_picks),
    )
    summary3.metric(
        "Average Pick",
        f"{manager_picks['overall_pick'].mean():.1f}",
    )
    summary4.metric(
        "Average Cost",
        (
            f"${manager_priced['salary'].mean():.1f}"
            if not manager_priced.empty
            else "N/A"
        ),
    )

    position_counts = (
        manager_picks.groupby("position", as_index=False)
        .size()
        .rename(columns={"size": "Picks", "position": "Position"})
        .sort_values("Picks", ascending=False)
    )

    left, right = st.columns(2)

    with left:
        count_chart = px.bar(
            position_counts,
            x="Position",
            y="Picks",
            title=f"{selected_manager}: Picks by Position",
            text_auto=True,
        )
        count_chart.update_layout(showlegend=False)
        st.plotly_chart(count_chart, use_container_width=True)

    with right:
        if manager_priced.empty:
            st.info(
                "No auction-cost data is available for this manager "
                "within the selected filters."
            )
        else:
            position_spend = (
                manager_priced.groupby("position", as_index=False)
                .agg(
                    Total_Spend=("salary", "sum"),
                    Average_Cost=("salary", "mean"),
                    Picks=("player_name", "count"),
                )
                .rename(columns={"position": "Position"})
                .sort_values("Total_Spend", ascending=False)
            )

            spend_chart = px.bar(
                position_spend,
                x="Position",
                y="Total_Spend",
                title=f"{selected_manager}: Auction Spend by Position",
                hover_data=["Average_Cost", "Picks"],
                text_auto=True,
            )
            spend_chart.update_layout(
                yaxis_title="Total Spend",
                showlegend=False,
            )
            st.plotly_chart(spend_chart, use_container_width=True)

    st.subheader("Position Detail")

    tendencies = (
        manager_picks.groupby("position", as_index=False)
        .agg(
            Picks=("player_name", "count"),
            Average_Pick=("overall_pick", "mean"),
            Earliest_Pick=("overall_pick", "min"),
        )
        .rename(columns={"position": "Position"})
    )

    if not manager_priced.empty:
        priced_tendencies = (
            manager_priced.groupby("position", as_index=False)
            .agg(
                Average_Cost=("salary", "mean"),
                Highest_Cost=("salary", "max"),
                Total_Spend=("salary", "sum"),
            )
            .rename(columns={"position": "Position"})
        )
        tendencies = tendencies.merge(
            priced_tendencies,
            on="Position",
            how="left",
        )
    else:
        tendencies["Average_Cost"] = pd.NA
        tendencies["Highest_Cost"] = pd.NA
        tendencies["Total_Spend"] = pd.NA

    tendencies = tendencies.sort_values(
        "Picks",
        ascending=False,
    )

    st.dataframe(
        tendencies,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Average_Pick": st.column_config.NumberColumn(
                "Average Pick",
                format="%.1f",
            ),
            "Earliest_Pick": "Earliest Pick",
            "Average_Cost": st.column_config.NumberColumn(
                "Average Cost",
                format="$%.1f",
            ),
            "Highest_Cost": st.column_config.NumberColumn(
                "Highest Cost",
                format="$%.0f",
            ),
            "Total_Spend": st.column_config.NumberColumn(
                "Total Spend",
                format="$%.0f",
            ),
        },
    )


# ==================================================
# Most Drafted Players
# ==================================================

with repeat_tab:
    st.subheader("Most Drafted Players")

    repeats = (
        filtered.groupby(
            ["player_name", "position"],
            as_index=False,
        )
        .agg(
            Times_Drafted=("year", "count"),
            Seasons=("year", "nunique"),
            Managers=("manager", "nunique"),
            First_Year=("year", "min"),
            Latest_Year=("year", "max"),
            Average_Pick=("overall_pick", "mean"),
            Average_Cost=("salary", "mean"),
        )
        .sort_values(
            ["Times_Drafted", "Seasons", "player_name"],
            ascending=[False, False, True],
        )
        .rename(
            columns={
                "player_name": "Player",
                "position": "Position",
                "Times_Drafted": "Times Drafted",
                "First_Year": "First Year",
                "Latest_Year": "Latest Year",
                "Average_Pick": "Average Pick",
                "Average_Cost": "Average Cost",
            }
        )
    )

    st.dataframe(
        repeats.head(100),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Average Pick": st.column_config.NumberColumn(
                "Average Pick",
                format="%.1f",
            ),
            "Average Cost": st.column_config.NumberColumn(
                "Average Cost",
                format="$%.1f",
            ),
        },
    )

    st.subheader("Player Draft Timeline")

    selected_player = st.selectbox(
        "Select Player",
        sorted(filtered["player_name"].dropna().unique()),
        key="player_timeline",
    )

    player_history = filtered[
        filtered["player_name"] == selected_player
    ].copy()

    player_history = player_history.rename(
        columns={
            "year": "Year",
            "platform": "Platform",
            "manager": "Manager",
            "team_name": "Fantasy Team",
            "overall_pick": "Pick",
            "position": "Position",
            "salary": "Cost",
            "season_finish": "Season Finish",
        }
    )

    st.dataframe(
        player_history[
            [
                "Year",
                "Platform",
                "Manager",
                "Fantasy Team",
                "Pick",
                "Position",
                "Cost",
                "Season Finish",
            ]
        ].sort_values("Year"),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Cost": st.column_config.NumberColumn(
                "Cost",
                format="$%d",
            )
        },
    )


# ==================================================
# Value Picks / Bargain Proxy
# ==================================================

with bargains_tab:
    st.subheader("Value Picks")

    st.info(
        "Player-season fantasy production is not currently stored in "
        "the database, so a true bargain ranking cannot yet compare "
        "draft cost with player output. This is a work in progress"
    )

    top_finish_picks = filtered[
        filtered["final_rank"].between(1, 4, inclusive="both")
    ].copy()

    bargain_mode = st.radio(
        "Value Method",
        options=[
            "Auction Cost",
            "Late-Round / Overall Pick",
        ],
        horizontal=True,
    )

    if bargain_mode == "Auction Cost":
        bargains = top_finish_picks[
            top_finish_picks["salary"].notna()
            & (top_finish_picks["salary"] > 0)
        ].copy()

        if bargains.empty:
            st.info(
                "No positive auction-cost values are available for the "
                "selected filters."
            )
        else:
            bargains["Value Score"] = (
                (5 - bargains["final_rank"]) * 100
                - bargains["salary"]
            )

            bargains = bargains.sort_values(
                ["Value Score", "salary"],
                ascending=[False, True],
            ).rename(
                columns={
                    "year": "Year",
                    "platform": "Platform",
                    "manager": "Manager",
                    "player_name": "Player",
                    "position": "Position",
                    "salary": "Cost",
                    "final_rank": "Team Finish",
                    "season_finish": "Finish",
                }
            )

            st.dataframe(
                bargains[
                    [
                        "Year",
                        "Platform",
                        "Manager",
                        "Player",
                        "Position",
                        "Cost",
                        "Team Finish",
                        "Finish",
                        "Value Score",
                    ]
                ].head(50),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Cost": st.column_config.NumberColumn(
                        "Cost",
                        format="$%d",
                    )
                },
            )

    else:
        bargains = top_finish_picks.copy()
        bargains["Value Score"] = (
            bargains["overall_pick"]
            + (5 - bargains["final_rank"]) * 100
        )

        bargains = bargains.sort_values(
            ["Value Score", "overall_pick"],
            ascending=[False, False],
        ).rename(
            columns={
                "year": "Year",
                "platform": "Platform",
                "manager": "Manager",
                "player_name": "Player",
                "position": "Position",
                "overall_pick": "Pick",
                "final_rank": "Team Finish",
                "season_finish": "Finish",
            }
        )

        st.dataframe(
            bargains[
                [
                    "Year",
                    "Platform",
                    "Manager",
                    "Player",
                    "Position",
                    "Pick",
                    "Team Finish",
                    "Finish",
                    "Value Score",
                ]
            ].head(50),
            hide_index=True,
            use_container_width=True,
        )

    with st.expander("How should true bargain scoring work later?"):
        st.markdown(
            """
            A player-level bargain metric needs season-long
            player production. Once player fantasy points or end-of-season
            positional rank is imported, the proxy can be replaced with a
            result like:

            **Auction value:** player fantasy points per auction dollar

            **Draft value:** production above the expected production for
            the player's overall pick or position

            Team finish should remain contextual information but not the
            primary indicator of a pick.
            """
        )
