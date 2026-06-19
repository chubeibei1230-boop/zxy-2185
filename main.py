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

tab1, tab2, tab3 = st.tabs(["📈 分析看板", "📋 数据明细", "💡 服务建议"])

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
