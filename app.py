import streamlit as st


st.set_page_config(
    page_title="Fantasy Football History",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)


pages = {
    "League": [
        st.Page(
            "app_pages/home.py",
            title="League Home",
            icon="🏠"
        ),
        st.Page(
            "app_pages/records.py",
            title="League Records",
            icon="🏆"
        ),
        st.Page(
            "app_pages/seasons.py",
            title="Seasons",
            icon="📅"
        ),
    ],
    "Managers": [
        st.Page(
            "app_pages/managers.py",
            title="Manager Careers",
            icon="👤"
        ),
        st.Page(
            "app_pages/head_to_head.py",
            title="Head-to-Head",
            icon="⚔️"
        ),
    ],
    "Rankings": [
    st.Page(
        "app_pages/elo.py",
        title="ELO Ratings",
        icon="📈"
    )
    ],
    "Drafts": [
        st.Page(
            "app_pages/drafts.py",
            title="Draft Analytics",
            icon="💰"
        ),
    ],
}


navigation = st.navigation(
    pages,
    position="sidebar"
)

navigation.run()