"""Remediation panel components for approvals and execution."""

import json
from typing import Callable, Dict, List
import streamlit as st


def render_pending_approvals(
    pending_items: List[Dict],
    on_approve: Callable[[str, str, bool], Dict],
    on_execute: Callable[[str, bool], Dict],
):
    """Render interactive pending remediations list with approve/reject and execute options."""
    if not pending_items:
        st.success("🎉 No pending remediation approvals. Everything is clear!")
        return

    st.markdown(f"**Found {len(pending_items)} remediation(s) requiring attention:**")

    for item in pending_items:
        rem_id = item["id"]
        status = item.get("status", "pending")
        action = item.get("action_name", "Unknown action")
        params = item.get("parameters", {})
        created_at = item.get("created_at", "")[:19]

        status_color = "#ffcc00" if status == "pending" else "#00cc88" if status == "approved" else "#ff4444"

        with st.expander(f"⚙️ {action}  —  Status: {status.upper()}", expanded=(status == "pending")):
            c1, c2, c3 = st.columns([2, 2, 2])
            c1.markdown(f"**Incident ID:** `{item.get('incident_id', 'N/A')}`")
            c2.markdown(f"**Status:** <span style='color:{status_color}; font-weight:600;'>{status.upper()}</span>", unsafe_allow_html=True)
            c3.markdown(f"**Created:** `{created_at}`")

            st.markdown("**Parameters:**")
            st.code(json.dumps(params, indent=2), language="json")

            if status == "pending":
                approver_name = st.text_input(
                    "Operator / Approver Name",
                    value="sre-operator",
                    key=f"approver_{rem_id}",
                )
                btn_col1, btn_col2 = st.columns([1, 1])
                with btn_col1:
                    if st.button("✅ Approve Action", key=f"btn_app_{rem_id}", type="primary"):
                        res = on_approve(rem_id, approver_name, True)
                        if res:
                            st.success(f"Action approved by {approver_name}!")
                            st.rerun()
                with btn_col2:
                    if st.button("❌ Reject Action", key=f"btn_rej_{rem_id}"):
                        res = on_approve(rem_id, approver_name, False)
                        if res:
                            st.warning("Action rejected.")
                            st.rerun()

            elif status == "approved":
                st.info(f"Approved by: **{item.get('approved_by', 'Unknown')}**")
                exec_col1, exec_col2 = st.columns([1, 1])
                with exec_col1:
                    if st.button("🛡️ Execute (Dry Run - Safe)", key=f"btn_dry_{rem_id}"):
                        with st.spinner("Executing dry-run simulation..."):
                            res = on_execute(rem_id, True)
                        if res:
                            st.success(f"Dry-run executed! Status: {res.get('status')}")
                            st.rerun()
                with exec_col2:
                    if st.button("⚡ Execute (LIVE)", key=f"btn_live_{rem_id}", type="primary"):
                        with st.spinner("Executing live action..."):
                            res = on_execute(rem_id, False)
                        if res:
                            st.success(f"Live action executed! Status: {res.get('status')}")
                            st.rerun()
