"""Streamlit entry point for the SmartPark application."""

import streamlit as st

from dashboard import show_dashboard, show_locations, show_traffic, show_reports
from init_data import init_sample_data
from prediction import show_parking_prediction
from settings import show_settings
from utils.theme import footer, load_css


try:
    init_sample_data()
except Exception as error:
    print(f"Data initialization note: {error}")

st.set_page_config(
    page_title="SmartPark AI",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_css()

if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"


def main():
    load_css()

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-header">
                <div class="sidebar-brand">🅿 SmartPark AI</div>
                <div class="sidebar-version">Parking management</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sidebar-nav">', unsafe_allow_html=True)
        nav_options = [
            ("◈  Overview", "Dashboard"),
            ("⌁  Prediction Center", "Predictions"),
            ("⌖  Locations", "Locations"),
            ("⇄  Traffic Analytics", "Traffic"),
            ("▤  Reports & Data", "Reports"),
            ("⚙  About & Settings", "Settings"),
        ]
        for label, key in nav_options:
            if st.button(label, width="stretch", key=f"nav_{key}"):
                st.session_state.current_page = key
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    current = st.session_state.current_page
    if current not in {"Dashboard", "Predictions", "Locations", "Traffic", "Reports", "Settings"}:
        current = "Dashboard"
        st.session_state.current_page = current

    if current == "Dashboard":
        show_dashboard()
    elif current == "Predictions":
        show_parking_prediction()
    elif current == "Locations":
        show_locations()
    elif current == "Traffic":
        show_traffic()
    elif current == "Reports":
        show_reports()
    else:
        show_settings()

    footer()


if __name__ == "__main__":
    main()
