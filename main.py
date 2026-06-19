import streamlit as st
import pandas as pd
from io import BytesIO
from utils.data_loader import (
    load_csv, map_columns, parse_dates, validate_required_fields,
    detect_anomalies, REQUIRED_FIELDS, OPTIONAL_FIELDS, ALL_FIELDS
)
from utils.filters import apply_filters, render_filter_sidebar
from utils.visualizations import (
    render_prep_time_chart, render_wait_time_distribution,
    render_refill_trend, render_helper_workload,
    render_issue_tables, render_14day_trend
)
from utils.analysis import generate_service_suggestions
from utils.report import generate_report_summary, export_report_excel

st.set_page_config(
    page_title="茶会服务节奏分析看板",
    page_icon="🍵",
    layout="wide"
)

st.title("🍵 茶会服务节奏分析看板")
st.markdown("---")

if "data" not in st.session_state:
    st.session_state.data = None
if "filtered_data" not in st.session_state:
    st.session_state.filtered_data = None
if "field_mapping" not in st.session_state:
    st.session_state.field_mapping = {}
if "date_format" not in st.session_state:
    st.session_state.date_format = "YYYY-MM-DD"
if "filter_reset" not in st.session_state:
    st.session_state.filter_reset = False

with st.sidebar:
    st.header("📁 数据上传")
    uploaded_file = st.file_uploader("上传 CSV 文件", type=["csv"])

    if uploaded_file is not None:
        try:
            raw_df = load_csv(uploaded_file)
            st.success(f"✅ 成功加载 {len(raw_df)} 条数据")

            with st.expander("🔄 字段映射配置", expanded=True):
                st.info("请将 CSV 列映射到对应字段")
                csv_columns = list(raw_df.columns)
                field_mapping = {}

                for field in ALL_FIELDS:
                    is_required = field in REQUIRED_FIELDS
                    label = f"{field} {'*' if is_required else ''}"
                    default_idx = 0
                    if field in csv_columns:
                        default_idx = csv_columns.index(field) + 1

                    options = ["-- 不映射 --"] + csv_columns
                    selected = st.selectbox(
                        label, options, index=default_idx,
                        key=f"map_{field}"
                    )
                    if selected != "-- 不映射 --":
                        field_mapping[field] = selected

                st.session_state.field_mapping = field_mapping

            with st.expander("📅 日期格式设置", expanded=False):
                date_formats = [
                    "YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY",
                    "YYYY/MM/DD", "DD-MM-YYYY", "MM-DD-YYYY"
                ]
                st.session_state.date_format = st.selectbox(
                    "选择日期格式", date_formats, index=0
                )

            if st.button("✅ 确认并处理数据", type="primary"):
                mapped_df = map_columns(raw_df, field_mapping)
                parsed_df = parse_dates(mapped_df, st.session_state.date_format)
                validation_errors = validate_required_fields(parsed_df)

                if validation_errors:
                    for err in validation_errors:
                        st.error(f"❌ {err}")
                else:
                    processed_df = detect_anomalies(parsed_df)
                    st.session_state.data = processed_df
                    st.session_state.filtered_data = processed_df.copy()
                    st.success("🎉 数据处理完成！")

        except Exception as e:
            st.error(f"❌ 处理数据时出错: {str(e)}")

    st.markdown("---")
    st.caption("* 必填字段")
    st.caption("数据仅在当前会话中处理")

if st.session_state.data is None:
    st.info("👈 请在左侧上传 CSV 文件开始分析")

    with st.expander("📋 字段说明", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**必填字段:**")
            for f in REQUIRED_FIELDS:
                st.markdown(f"- `{f}`")
        with col2:
            st.markdown("**可选字段:**")
            for f in OPTIONAL_FIELDS:
                st.markdown(f"- `{f}`")

    st.stop()

data = st.session_state.data
filter_params = render_filter_sidebar(data)
filtered_data = apply_filters(data, filter_params)
st.session_state.filtered_data = filtered_data

st.subheader("📊 数据概览")
metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
with metric_col1:
    st.metric("总场次", f"{len(filtered_data['session_name'].unique())}")
with metric_col2:
    st.metric("总桌数", f"{len(filtered_data['table_no'].unique())}")
with metric_col3:
    avg_wait = filtered_data["wait_minutes"].mean() if "wait_minutes" in filtered_data else 0
    st.metric("平均等待时间", f"{avg_wait:.1f} 分钟")
with metric_col4:
    total_refill = filtered_data["refill_count"].sum() if "refill_count" in filtered_data else 0
    st.metric("总续水次数", f"{int(total_refill)}")
with metric_col5:
    anomaly_count = filtered_data["is_anomaly"].sum() if "is_anomaly" in filtered_data else 0
    st.metric("异常等待", f"{int(anomaly_count)} 次", delta_color="inverse")

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📈 分析看板", "📋 数据明细", "💡 服务建议", "📄 服务复盘报告"])

with tab1:
    col_left, col_right = st.columns(2)

    with col_left:
        render_prep_time_chart(filtered_data)
        render_refill_trend(filtered_data)
        render_issue_tables(filtered_data)

    with col_right:
        render_wait_time_distribution(filtered_data)
        render_helper_workload(filtered_data)
        render_14day_trend(filtered_data)

with tab2:
    st.subheader("📋 数据明细")

    display_cols = [c for c in ALL_FIELDS if c in filtered_data.columns]
    if "is_anomaly" in filtered_data.columns:
        display_cols.append("is_anomaly")

    display_df = filtered_data[display_cols].copy()

    if "is_anomaly" in display_df.columns:
        display_df["is_anomaly"] = display_df["is_anomaly"].map({True: "⚠️ 异常", False: "正常"})
        display_df = display_df.rename(columns={"is_anomaly": "异常状态"})

    st.dataframe(display_df, use_container_width=True, height=400)

    st.markdown("---")
    col_export1, col_export2 = st.columns([1, 4])

    with col_export1:
        if st.button("📥 导出筛选数据", type="primary"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                filtered_data.to_excel(writer, index=False, sheet_name="茶会数据")
            output.seek(0)

            st.download_button(
                label="⬇️ 下载 Excel 文件",
                data=output,
                file_name=f"茶会服务数据_{pd.Timestamp.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with col_export2:
        csv_output = filtered_data.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ 下载 CSV 文件",
            data=csv_output,
            file_name=f"茶会服务数据_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

with tab3:
    render_service_suggestions = st.container()
    with render_service_suggestions:
        generate_service_suggestions(filtered_data, data)

with tab4:
    st.subheader("📄 服务复盘报告")

    st.markdown("""
    基于当前筛选条件生成服务复盘摘要，报告涵盖核心指标概览、异常归因、多维度对比、趋势解读和优化建议。
    更改左侧筛选条件后，点击「生成报告」即可刷新。
    """)

    filter_summary_parts = []
    if "record_date" in filtered_data.columns:
        d_min = filtered_data["record_date"].min()
        d_max = filtered_data["record_date"].max()
        filter_summary_parts.append(f"日期: {d_min} ~ {d_max}")
    if "session_name" in filtered_data.columns:
        sessions = filtered_data["session_name"].unique()
        filter_summary_parts.append(f"场次: {', '.join(sorted(sessions.astype(str)))}")
    if "table_no" in filtered_data.columns:
        tables = filtered_data["table_no"].unique()
        filter_summary_parts.append(f"桌号: {', '.join(sorted(tables.astype(str)))}")
    if "helper_name" in filtered_data.columns:
        helpers = filtered_data["helper_name"].dropna().unique()
        non_empty = [h for h in helpers.astype(str) if h.strip()]
        if non_empty:
            filter_summary_parts.append(f"助理: {', '.join(sorted(non_empty))}")
    if "is_anomaly" in filtered_data.columns:
        anomaly_vals = filtered_data["is_anomaly"].unique()
        if set(anomaly_vals) == {True}:
            filter_summary_parts.append("异常状态: 仅异常")
        elif set(anomaly_vals) == {False}:
            filter_summary_parts.append("异常状态: 仅正常")

    st.info(f"🔍 当前筛选范围 — {' | '.join(filter_summary_parts)} | 共 {len(filtered_data)} 条记录")

    generate_col1, generate_col2 = st.columns([1, 4])
    with generate_col1:
        generate_btn = st.button("📝 生成报告", type="primary", key="generate_report_btn")
    with generate_col2:
        pass

    if generate_btn or st.session_state.get("report_generated", False):
        if generate_btn:
            st.session_state.report_generated = True

        with st.spinner("正在生成服务复盘报告..."):
            report = generate_report_summary(filtered_data, data)

        if report is None:
            st.warning("⚠️ 当前筛选范围内无数据，无法生成报告")
            st.session_state.report_generated = False
        else:
            st.session_state.current_report = report

            m = report["metrics_overview"]
            st.markdown("## 一、核心指标概览")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            with kpi1:
                st.metric("总记录数", m["total_records"])
                st.metric("总场次数", m["total_sessions"])
            with kpi2:
                st.metric("平均等待时间", f'{m["avg_wait"]:.1f} 分钟' if m["avg_wait"] is not None else "N/A")
                st.metric("最长等待时间", f'{m["max_wait"]:.1f} 分钟' if m["max_wait"] is not None else "N/A")
            with kpi3:
                st.metric("平均准备时间", f'{m["avg_prep"]:.1f} 分钟' if m["avg_prep"] is not None else "N/A")
                st.metric("异常等待", f'{m["anomaly_count"]} 次 ({m["anomaly_rate"]}%)')
            with kpi4:
                st.metric("总续水次数", m["total_refills"])
                st.metric("总桌数", m["total_tables"])

            st.markdown("---")

            anomaly = report["anomaly_attribution"]
            st.markdown("## 二、异常等待与问题桌号归因")
            if anomaly["anomaly_records"]:
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    st.markdown("### 🔴 异常等待高发桌号")
                    if anomaly["top_anomaly_tables"]:
                        for item in anomaly["top_anomaly_tables"]:
                            wait_str = f"，平均等待 {item['avg_wait']} 分钟" if item.get("avg_wait") is not None else ""
                            st.markdown(f"- **{item['table_no']} 号桌**: 异常 {item['anomaly_count']} 次{wait_str}")
                    else:
                        st.info("暂无异常桌号数据")

                with col_a2:
                    st.markdown("### 🔴 异常等待高发场次")
                    if anomaly["top_anomaly_sessions"]:
                        for item in anomaly["top_anomaly_sessions"]:
                            wait_str = f"，平均等待 {item['avg_wait']} 分钟" if item.get("avg_wait") is not None else ""
                            st.markdown(f"- **{item['session_name']}**: 异常 {item['anomaly_count']} 次{wait_str}")
                    else:
                        st.info("暂无异常场次数据")

                with st.expander("📋 异常等待明细", expanded=False):
                    anomaly_detail_df = pd.DataFrame(anomaly["anomaly_records"])
                    col_rename = {
                        "record_date": "日期", "session_name": "场次", "table_no": "桌号",
                        "wait_minutes": "等待时间", "helper_name": "助理", "issue_note": "问题备注"
                    }
                    anomaly_detail_df = anomaly_detail_df.rename(
                        columns={k: v for k, v in col_rename.items() if k in anomaly_detail_df.columns}
                    )
                    st.dataframe(anomaly_detail_df, use_container_width=True, hide_index=True)

                if anomaly["issue_notes"]:
                    with st.expander("📝 问题备注汇总", expanded=False):
                        for note in anomaly["issue_notes"]:
                            st.markdown(f"- **{note['date']}** {note['session']} {note['table']} — {note['note']}")
            else:
                st.success("✅ 当前筛选范围内无异常等待记录")

            st.markdown("---")

            st.markdown("## 三、维度表现对比")
            dim_col1, dim_col2, dim_col3 = st.columns(3)

            with dim_col1:
                st.markdown("### 📊 场次对比")
                session_comp = report["session_comparison"]
                if session_comp["items"]:
                    session_df = pd.DataFrame(session_comp["items"])
                    display_cols = ["name", "avg_wait", "anomaly_count"]
                    display_cols = [c for c in display_cols if c in session_df.columns]
                    session_display = session_df[display_cols].copy()
                    rename_map = {"name": "场次", "avg_wait": "平均等待(分)", "anomaly_count": "异常次数"}
                    session_display = session_display.rename(columns={k: v for k, v in rename_map.items() if k in session_display.columns})
                    st.dataframe(session_display, use_container_width=True, hide_index=True)
                else:
                    st.info("暂无场次对比数据")

            with dim_col2:
                st.markdown("### 📊 桌号对比")
                table_comp = report["table_comparison"]
                if table_comp["items"]:
                    table_df = pd.DataFrame(table_comp["items"])
                    display_cols = ["name", "avg_wait", "anomaly_count"]
                    display_cols = [c for c in display_cols if c in table_df.columns]
                    table_display = table_df[display_cols].copy()
                    rename_map = {"name": "桌号", "avg_wait": "平均等待(分)", "anomaly_count": "异常次数"}
                    table_display = table_display.rename(columns={k: v for k, v in rename_map.items() if k in table_display.columns})
                    st.dataframe(table_display, use_container_width=True, hide_index=True)
                else:
                    st.info("暂无桌号对比数据")

            with dim_col3:
                st.markdown("### 📊 助理对比")
                helper_comp = report["helper_comparison"]
                if helper_comp["items"]:
                    helper_df = pd.DataFrame(helper_comp["items"])
                    display_cols = ["name", "tables_served", "avg_wait", "anomaly_count"]
                    display_cols = [c for c in display_cols if c in helper_df.columns]
                    helper_display = helper_df[display_cols].copy()
                    rename_map = {"name": "助理", "tables_served": "服务桌数", "avg_wait": "平均等待(分)", "anomaly_count": "异常次数"}
                    helper_display = helper_display.rename(columns={k: v for k, v in rename_map.items() if k in helper_display.columns})
                    st.dataframe(helper_display, use_container_width=True, hide_index=True)
                else:
                    st.info("暂无助理对比数据")

            st.markdown("---")

            trend = report["trend_interpretation"]
            st.markdown("## 四、近14天趋势解读")
            if trend["has_trend"]:
                if trend["daily_stats"]:
                    trend_df = pd.DataFrame(trend["daily_stats"])
                    col_rename = {
                        "date": "日期", "avg_wait": "平均等待(分)", "avg_prep": "平均准备(分)",
                        "total_refills": "总续水次数", "record_count": "记录数"
                    }
                    trend_display = trend_df.rename(
                        columns={k: v for k, v in col_rename.items() if k in trend_df.columns}
                    )
                    st.dataframe(trend_display, use_container_width=True, hide_index=True)

                if trend["interpretations"]:
                    st.markdown("### 📈 趋势解读")
                    for interp in trend["interpretations"]:
                        st.markdown(f"- {interp}")
                else:
                    st.info("数据不足，暂无趋势解读")
            else:
                st.info("近14天暂无足够数据，无法进行趋势解读")

            st.markdown("---")

            suggestions = report["optimization_suggestions"]
            st.markdown("## 五、服务优化建议")
            high_suggestions = [s for s in suggestions if s["priority"] == "高"]
            medium_suggestions = [s for s in suggestions if s["priority"] == "中"]
            low_suggestions = [s for s in suggestions if s["priority"] in ("低", "信息")]

            if high_suggestions:
                st.markdown("### 🔴 高优先级")
                for s in high_suggestions:
                    st.markdown(f"- **[{s['category']}]** {s['suggestion']}")

            if medium_suggestions:
                st.markdown("### 🟡 中优先级")
                for s in medium_suggestions:
                    st.markdown(f"- **[{s['category']}]** {s['suggestion']}")

            if low_suggestions:
                st.markdown("### 🟢 低优先级 / 信息")
                for s in low_suggestions:
                    st.markdown(f"- **[{s['category']}]** {s['suggestion']}")

            st.markdown("---")

            st.markdown("## 📥 导出报告")
            export_col1, export_col2 = st.columns([1, 4])
            with export_col1:
                if st.button("📥 导出完整报告 (Excel)", type="primary", key="export_report_btn"):
                    try:
                        excel_output = export_report_excel(report)
                        st.download_button(
                            label="⬇️ 下载复盘报告 Excel",
                            data=excel_output,
                            file_name=f"服务复盘报告_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_report_excel"
                        )
                    except Exception as e:
                        st.error(f"❌ 导出失败: {str(e)}")
