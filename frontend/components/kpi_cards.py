"""KPI card components for Streamlit frontend."""

import streamlit as st


def render_kpi_card(value: int | str, label: str, color: str = "#58a6ff"):
    """Render a styled KPI card metric."""
    st.markdown(
        f"""
        <div class="kpi-card">
          <p class="kpi-value" style="color:{color}">{value}</p>
          <p class="kpi-label">{label}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
