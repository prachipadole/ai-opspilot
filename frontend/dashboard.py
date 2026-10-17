"""
dashboard.py – AI-OpsPilot Streamlit Dashboard
============================================================
Pages:
  🏠 Overview      – live KPIs + charts
  🚨 Incidents     – list, create, investigate
  📊 Anomalies     – unacknowledged feed + acknowledge
  📋 Logs          – recent log stream + bulk ingest
  🤖 Analysis      – trigger LLM analysis + view results
  🔧 Remediation   – suggest, approve, execute actions
"""

import time
from datetime import datetime

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import frontend.api_client as api
from frontend.components.kpi_cards import render_kpi_card
from frontend.components.remediation_panel import render_pending_approvals

FAVICON_PATH = os.path.join(os.path.dirname(__file__), "favicon.png")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI-OpsPilot",
    page_icon=FAVICON_PATH if os.path.exists(FAVICON_PATH) else "🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Dark sidebar */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
    border-right: 1px solid #30363d;
  }
  [data-testid="stSidebar"] * { color: #c9d1d9 !important; }

  /* KPI cards */
  .kpi-card {
    background: linear-gradient(135deg, #1c2128 0%, #22272e 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
    transition: transform .2s;
  }
  .kpi-card:hover { transform: translateY(-2px); }
  .kpi-value { font-size: 2.2rem; font-weight: 700; margin: 0; }
  .kpi-label { font-size: 0.85rem; color: #8b949e; margin: 0; }

  /* Severity badges */
  .badge-critical { background:#ff444455; color:#ff4444; border:1px solid #ff4444;
                    border-radius:6px; padding:2px 8px; font-size:.75rem; }
  .badge-high     { background:#ff800055; color:#ff8000; border:1px solid #ff8000;
                    border-radius:6px; padding:2px 8px; font-size:.75rem; }
  .badge-medium   { background:#ffcc0055; color:#ffcc00; border:1px solid #ffcc00;
                    border-radius:6px; padding:2px 8px; font-size:.75rem; }
  .badge-low      { background:#00cc8855; color:#00cc88; border:1px solid #00cc88;
                    border-radius:6px; padding:2px 8px; font-size:.75rem; }

  /* Section header */
  .section-header {
    font-size: 1.3rem; font-weight: 600;
    border-left: 4px solid #58a6ff;
    padding-left: 12px; margin: 16px 0 8px;
  }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
SEVERITY_COLOR = {"critical": "#ff4444", "high": "#ff8000", "medium": "#ffcc00", "low": "#00cc88"}
STATUS_COLOR   = {"open": "#ff4444", "investigating": "#ff8000", "resolved": "#00cc88", "closed": "#8b949e"}


def badge(text: str, kind: str = "medium") -> str:
    return f'<span class="badge-{kind}">{text}</span>'


def safe_api(fn, *args, default=None, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        st.toast(f"⚠️ API error: {e}", icon="⚠️")
        return default


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    if os.path.exists(FAVICON_PATH):
        st.image(FAVICON_PATH, width=54)
    st.markdown("## AI-OpsPilot")
    st.markdown("---")
    page = st.radio(
        "Navigation",
        ["🏠 Overview", "🚨 Incidents", "📊 Anomalies", "📋 Logs", "🤖 Analysis", "🔧 Remediation"],
        label_visibility="collapsed",
    )
    st.markdown("---")

    # Backend status
    try:
        api.health_check()
        st.success("● Backend connected", icon="✅")
    except Exception:
        st.error("● Backend offline", icon="🔴")

    st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Overview
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Overview":
    st.markdown("# 🛡️ AI-OpsPilot — Operations Dashboard")
    st.markdown("Real-time monitoring · Anomaly detection · LLM-powered incident analysis")
    st.divider()

    incidents = safe_api(api.list_incidents, limit=200, default=[])
    anomalies = safe_api(api.list_anomalies, limit=200, default=[])

    open_inc     = sum(1 for i in incidents if i["status"] == "open")
    critical_inc = sum(1 for i in incidents if i["severity"] == "critical")
    unack_anom   = sum(1 for a in anomalies if not a.get("is_acknowledged"))
    resolved_inc = sum(1 for i in incidents if i["status"] == "resolved")

    col1, col2, col3, col4 = st.columns(4)
    for col, value, label, color in [
        (col1, open_inc,     "Open Incidents",         "#ff4444"),
        (col2, critical_inc, "Critical Incidents",     "#ff8000"),
        (col3, unack_anom,   "Unacknowledged Anomalies","#ffcc00"),
        (col4, resolved_inc, "Resolved Today",         "#00cc88"),
    ]:
        with col:
            render_kpi_card(value, label, color)

    st.divider()
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<p class="section-header">Incidents by Severity</p>', unsafe_allow_html=True)
        if incidents:
            sev_counts = pd.Series([i["severity"] for i in incidents]).value_counts().reset_index()
            sev_counts.columns = ["severity", "count"]
            fig = px.pie(
                sev_counts, values="count", names="severity",
                color="severity",
                color_discrete_map=SEVERITY_COLOR,
                hole=0.5,
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#c9d1d9", legend_font_color="#c9d1d9", margin=dict(t=20, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No incidents yet.")

    with col_b:
        st.markdown('<p class="section-header">Anomaly Score Distribution</p>', unsafe_allow_html=True)
        if anomalies:
            df = pd.DataFrame(anomalies)
            fig = px.histogram(
                df, x="anomaly_score", nbins=20,
                color_discrete_sequence=["#58a6ff"],
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#c9d1d9", margin=dict(t=20, b=20),
                xaxis_title="Anomaly Score", yaxis_title="Count",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No anomalies detected yet.")

    st.markdown('<p class="section-header">Recent Incidents</p>', unsafe_allow_html=True)
    if incidents:
        df_inc = pd.DataFrame(incidents[:10])[["title", "severity", "status", "created_at"]]
        st.dataframe(df_inc, use_container_width=True, hide_index=True)
    else:
        st.info("No incidents yet. Ingest some logs to get started!")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Incidents
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🚨 Incidents":
    st.markdown("# 🚨 Incidents")

    tab1, tab2 = st.tabs(["📋 All Incidents", "➕ Create Incident"])

    with tab1:
        status_filter = st.selectbox("Filter by status", ["All", "open", "investigating", "resolved", "closed"])
        status_arg    = None if status_filter == "All" else status_filter
        incidents     = safe_api(api.list_incidents, status=status_arg, limit=100, default=[])

        if incidents:
            for inc in incidents:
                sev = inc["severity"]
                with st.expander(f"{'🔴' if sev=='critical' else '🟠' if sev=='high' else '🟡' if sev=='medium' else '🟢'} {inc['title']}  |  {inc['status'].upper()}"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Severity", sev.capitalize())
                    c2.metric("Status",   inc["status"].capitalize())
                    c3.metric("Source",   inc.get("source") or "—")
                    st.text_area("Raw Log", inc.get("raw_log") or "—", height=80, disabled=True)

                    bc1, bc2, bc3 = st.columns(3)
                    with bc1:
                        if st.button("🔍 Investigate", key=f"inv_{inc['id']}"):
                            with st.spinner("Running LangGraph investigation …"):
                                result = safe_api(api.investigate_incident, inc["id"], default={})
                            if result:
                                st.success("Investigation complete!")
                                st.json(result)
                    with bc2:
                        if st.button("✅ Mark Resolved", key=f"res_{inc['id']}"):
                            safe_api(api.update_incident_status, inc["id"], "resolved")
                            st.rerun()
                    with bc3:
                        if st.button("🤖 AI Analysis", key=f"anal_{inc['id']}"):
                            with st.spinner("Asking Ollama …"):
                                result = safe_api(api.run_analysis, inc["id"], default={})
                            if result:
                                st.write("**Root Cause:**", result.get("root_cause"))
                                st.write("**Summary:**",    result.get("summary"))
        else:
            st.info("No incidents found.")

    with tab2:
        with st.form("create_incident_form"):
            title    = st.text_input("Title *")
            severity = st.selectbox("Severity", ["low", "medium", "high", "critical"])
            source   = st.text_input("Source (service name)")
            raw_log  = st.text_area("Paste raw log (optional)", height=120)
            submitted = st.form_submit_button("🚀 Create Incident")
            if submitted and title:
                result = safe_api(api.create_incident, title, severity, source, raw_log, default=None)
                if result:
                    st.success(f"✅ Incident created: {result['id']}")
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Anomalies
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Anomalies":
    st.markdown("# 📊 Anomalies")
    anomalies = safe_api(api.list_anomalies, limit=200, default=[])

    if anomalies:
        df = pd.DataFrame(anomalies)

        # Score gauge chart
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=df["anomaly_score"].mean() * 100,
            title={"text": "Average Anomaly Score (%)"},
            gauge={
                "axis":  {"range": [0, 100]},
                "bar":   {"color": "#58a6ff"},
                "steps": [
                    {"range": [0, 30],  "color": "#00cc88"},
                    {"range": [30, 60], "color": "#ffcc00"},
                    {"range": [60, 100],"color": "#ff4444"},
                ],
            },
        ))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#c9d1d9", height=260)
        st.plotly_chart(fig, use_container_width=True)

        st.divider()
        unack = [a for a in anomalies if not a.get("is_acknowledged")]
        st.markdown(f"**{len(unack)} unacknowledged anomalies**")

        for anom in unack[:20]:
            score = anom["anomaly_score"]
            color = "#ff4444" if score > 0.7 else "#ffcc00" if score > 0.5 else "#00cc88"
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                c1.markdown(f"**{anom['metric_name']}**")
                c2.markdown(f"Value: `{anom['metric_value']:.3f}`")
                c3.markdown(f"Score: <span style='color:{color}'>{score:.3f}</span>", unsafe_allow_html=True)
                if c4.button("✓", key=f"ack_{anom['id']}"):
                    safe_api(api.acknowledge_anomaly, anom["id"])
                    st.rerun()
            st.divider()
    else:
        st.info("No anomalies detected. Ingest logs to start detection.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Logs
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Logs":
    st.markdown("# 📋 Log Stream")

    tab1, tab2 = st.tabs(["📡 Recent Logs", "📤 Ingest Logs"])

    with tab1:
        logs = safe_api(api.recent_logs, limit=200, default=[])
        if logs:
            df = pd.DataFrame(logs)[["timestamp", "service", "level", "message"]]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No logs yet.")

    with tab2:
        st.markdown("Paste one log line per row:")
        sample = """Oct 17 09:23:11 app-01 nginx[1234]: [ERROR] upstream timed out (110)
{"service":"payment","level":"ERROR","message":"DB connection refused","response_time":5200}
Oct 17 09:23:14 app-01 api[5678]: [WARN] memory usage at 94%
{"service":"auth","level":"INFO","message":"User login successful","response_time":45}"""
        raw_input = st.text_area("Log lines", value=sample, height=200)
        if st.button("📤 Ingest Logs", type="primary"):
            lines  = [l for l in raw_input.splitlines() if l.strip()]
            result = safe_api(api.ingest_logs, lines, default={})
            if result:
                st.success(f"✅ Ingested {result.get('ingested', '?')} logs — anomaly detection running in background.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Analysis
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 Analysis":
    st.markdown("# 🤖 LLM Incident Analysis")
    st.caption("Powered by Ollama (local) + RAG runbook retrieval")

    incidents = safe_api(api.list_incidents, limit=50, default=[])
    if not incidents:
        st.info("Create an incident first before running analysis.")
    else:
        options    = {f"{i['title']} ({i['severity']})": i["id"] for i in incidents}
        selection  = st.selectbox("Select incident", list(options.keys()))
        inc_id     = options[selection]

        if st.button("🧠 Run AI Analysis", type="primary"):
            with st.spinner("🤖 Ollama is thinking …"):
                result = safe_api(api.run_analysis, inc_id, default=None)
            if result:
                st.success("Analysis complete!")
                st.markdown("### 🔍 Root Cause")
                st.info(result.get("root_cause", "N/A"))
                st.markdown("### 📋 Summary")
                st.write(result.get("summary", ""))
                if result.get("runbooks_used"):
                    st.markdown("### 📚 Runbooks Referenced")
                    for rb in result["runbooks_used"]:
                        st.markdown(f"- `{rb}`")

        # Show past analyses
        st.divider()
        st.markdown("### Past Analyses")
        past = safe_api(api.get_analyses, inc_id, default=[])
        for analysis in past:
            with st.expander(f"Analysis — {analysis['created_at'][:19]}"):
                st.markdown(f"**Root Cause:** {analysis.get('root_cause', '—')}")
                st.markdown(f"**Summary:** {analysis.get('summary', '—')}")
                st.markdown(f"**Model:** `{analysis.get('llm_model', '—')}`")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Remediation
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔧 Remediation":
    st.markdown("# 🔧 Remediation")

    tab1, tab2, tab3 = st.tabs(["💡 Suggestions", "🔬 Action Catalogue", "⏳ Pending Approvals"])

    with tab1:
        incidents = safe_api(api.list_incidents, limit=50, default=[])
        if not incidents:
            st.info("No incidents to remediate.")
        else:
            options   = {f"{i['title']} ({i['severity']})": i["id"] for i in incidents}
            selection = st.selectbox("Select incident", list(options.keys()), key="rem_select")
            inc_id    = options[selection]

            if st.button("💡 Get AI Suggestions"):
                result = safe_api(api.suggest_actions, inc_id, default={})
                if result:
                    suggestions = result.get("suggested_actions", [])
                    st.markdown(f"**Suggested actions:** {', '.join(suggestions)}")

                    for action in suggestions:
                        if st.button(f"📋 Propose: {action}", key=f"prop_{action}"):
                            r = safe_api(api.create_remediation, inc_id, action, default={})
                            if r:
                                st.success(f"✅ Remediation proposed: `{r['id']}`")
                                st.rerun()

    with tab2:
        actions = safe_api(api.list_actions, default=[])
        if actions:
            df = pd.DataFrame(actions)[["name", "description", "risk", "simulated_duration_s"]]
            df.columns = ["Action", "Description", "Risk Level", "Est. Duration (s)"]
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tab3:
        st.markdown("### ⏳ Remediation Approval & Execution Queue")
        pending_items = safe_api(api.pending_remediations, default=[])
        render_pending_approvals(
            pending_items=pending_items,
            on_approve=lambda r_id, approver, status: safe_api(api.approve_remediation, r_id, approver, status),
            on_execute=lambda r_id, dry_run: safe_api(api.execute_remediation, r_id, dry_run),
        )
