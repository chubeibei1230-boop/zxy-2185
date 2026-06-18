import streamlit as st
import pandas as pd


def render_filter_sidebar(data):
    with st.sidebar:
        st.markdown("---")
        st.header("🔍 筛选条件")

        filter_params = {}

        if "record_date" in data.columns:
            dates = sorted(data["record_date"].dropna().unique())
            if len(dates) >= 2:
                date_range = st.date_input(
                    "选择日期范围",
                    value=(dates[0], dates[-1]),
                    min_value=dates[0],
                    max_value=dates[-1]
                )
                filter_params["date_range"] = date_range

        if "session_name" in data.columns:
            sessions = sorted(data["session_name"].dropna().astype(str).unique())
            selected_sessions = st.multiselect(
                "选择场次",
                options=sessions,
                default=sessions
            )
            filter_params["sessions"] = selected_sessions

        if "table_no" in data.columns:
            tables = sorted(data["table_no"].dropna().astype(str).unique())
            selected_tables = st.multiselect(
                "选择桌号",
                options=tables,
                default=tables
            )
            filter_params["tables"] = selected_tables

        if "helper_name" in data.columns:
            helpers = sorted(data["helper_name"].dropna().astype(str).unique())
            if len(helpers) > 0 and any(h.strip() for h in helpers):
                selected_helpers = st.multiselect(
                    "选择助理",
                    options=helpers,
                    default=helpers
                )
                filter_params["helpers"] = selected_helpers

        if "is_anomaly" in data.columns:
            anomaly_options = ["全部", "仅异常", "仅正常"]
            anomaly_filter = st.selectbox(
                "异常状态",
                options=anomaly_options,
                index=0
            )
            filter_params["anomaly"] = anomaly_filter

        if st.button("🔄 重置筛选", type="secondary"):
            filter_params = {}
            st.rerun()

        return filter_params


def apply_filters(data, filter_params):
    filtered = data.copy()

    if not filter_params:
        return filtered

    if "date_range" in filter_params:
        date_range = filter_params["date_range"]
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            filtered = filtered[
                (filtered["record_date"] >= start_date) &
                (filtered["record_date"] <= end_date)
            ]

    if "sessions" in filter_params and filter_params["sessions"]:
        filtered = filtered[filtered["session_name"].astype(str).isin(filter_params["sessions"])]

    if "tables" in filter_params and filter_params["tables"]:
        filtered = filtered[filtered["table_no"].astype(str).isin(filter_params["tables"])]

    if "helpers" in filter_params and filter_params["helpers"]:
        filtered = filtered[filtered["helper_name"].astype(str).isin(filter_params["helpers"])]

    if "anomaly" in filter_params and "is_anomaly" in filtered.columns:
        anomaly_filter = filter_params["anomaly"]
        if anomaly_filter == "仅异常":
            filtered = filtered[filtered["is_anomaly"] == True]
        elif anomaly_filter == "仅正常":
            filtered = filtered[filtered["is_anomaly"] == False]

    return filtered
