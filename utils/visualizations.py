import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


def _safe_column(df, col):
    return col in df.columns and df[col].notna().any()


def render_prep_time_chart(df):
    st.subheader("⏱️ 各场次准备耗时")

    if not _safe_column(df, "session_name") or not _safe_column(df, "prep_minutes"):
        st.info("📋 暂无准备时间数据")
        return

    try:
        session_prep = df.groupby("session_name")["prep_minutes"].agg(["mean", "count"]).reset_index()
        session_prep.columns = ["场次", "平均准备时间", "记录数"]
        session_prep = session_prep.sort_values("平均准备时间", ascending=False)

        fig = px.bar(
            session_prep,
            x="场次",
            y="平均准备时间",
            text="平均准备时间",
            color="平均准备时间",
            color_continuous_scale="Blues",
            title="各场次平均准备时间(分钟)"
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.warning(f"⚠️ 图表渲染异常: {str(e)}")


def render_wait_time_distribution(df):
    st.subheader("⌛ 等待时间分布")

    if not _safe_column(df, "wait_minutes"):
        st.info("📋 暂无等待时间数据")
        return

    try:
        wait_data = df["wait_minutes"].dropna()

        if len(wait_data) == 0:
            st.info("📋 暂无等待时间数据")
            return

        fig = px.histogram(
            df,
            x="wait_minutes",
            nbins=20,
            color_discrete_sequence=["#FF6B6B"],
            title="等待时间分布(分钟)",
            labels={"wait_minutes": "等待时间(分钟)", "count": "次数"}
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("平均等待", f"{wait_data.mean():.1f} 分钟")
        with col2:
            st.metric("最长等待", f"{wait_data.max():.0f} 分钟")
        with col3:
            st.metric("中位数", f"{wait_data.median():.1f} 分钟")

    except Exception as e:
        st.warning(f"⚠️ 图表渲染异常: {str(e)}")


def render_refill_trend(df):
    st.subheader("💧 续水次数趋势")

    if not _safe_column(df, "record_date") or not _safe_column(df, "refill_count"):
        st.info("📋 暂无续水次数数据")
        return

    try:
        daily_refill = df.groupby("record_date")["refill_count"].sum().reset_index()
        daily_refill.columns = ["日期", "续水次数"]

        fig = px.line(
            daily_refill,
            x="日期",
            y="续水次数",
            markers=True,
            title="每日续水次数趋势",
            color_discrete_sequence=["#4ECDC4"]
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.warning(f"⚠️ 图表渲染异常: {str(e)}")


def render_helper_workload(df):
    st.subheader("👥 助理负载分析")

    if not _safe_column(df, "helper_name"):
        st.info("📋 暂无助理数据")
        return

    try:
        helper_data = df[df["helper_name"].notna() & (df["helper_name"].astype(str).str.strip() != "")]

        if len(helper_data) == 0:
            st.info("📋 暂无助理数据")
            return

        helper_stats = helper_data.groupby("helper_name").agg(
            服务桌数=("table_no", "nunique"),
            平均等待时间=("wait_minutes", "mean"),
            总续水次数=("refill_count", "sum")
        ).reset_index()

        helper_stats.columns = ["助理", "服务桌数", "平均等待时间", "总续水次数"]
        helper_stats["平均等待时间"] = helper_stats["平均等待时间"].fillna(0)
        helper_stats["总续水次数"] = helper_stats["总续水次数"].fillna(0).astype(int)

        fig = px.bar(
            helper_stats,
            x="助理",
            y=["服务桌数", "总续水次数"],
            barmode="group",
            title="各助理服务负载",
            color_discrete_map={"服务桌数": "#45B7D1", "总续水次数": "#96CEB4"}
        )
        fig.update_layout(height=300, legend_title="指标")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.warning(f"⚠️ 图表渲染异常: {str(e)}")


def render_issue_tables(df):
    st.subheader("⚠️ 问题桌号列表")

    try:
        has_issues = False
        issue_data = None

        if "is_anomaly" in df.columns:
            anomaly_df = df[df["is_anomaly"] == True].copy()
            if len(anomaly_df) > 0:
                has_issues = True
                issue_data = anomaly_df

        if _safe_column(df, "issue_note"):
            note_df = df[df["issue_note"].notna() & (df["issue_note"].astype(str).str.strip() != "")].copy()
            if len(note_df) > 0:
                if issue_data is None:
                    issue_data = note_df
                else:
                    issue_data = pd.concat([issue_data, note_df]).drop_duplicates()
                has_issues = True

        if not has_issues or issue_data is None or len(issue_data) == 0:
            st.success("✅ 暂无问题记录")
            return

        display_cols = ["record_date", "session_name", "table_no", "wait_minutes", "issue_note"]
        display_cols = [c for c in display_cols if c in issue_data.columns]
        issue_display = issue_data[display_cols].copy()

        if "wait_minutes" in issue_display.columns:
            issue_display["wait_minutes"] = issue_display["wait_minutes"].fillna(0).astype(float).map("{:.1f}".format)

        issue_display = issue_display.rename(columns={
            "record_date": "日期",
            "session_name": "场次",
            "table_no": "桌号",
            "wait_minutes": "等待时间(分)",
            "issue_note": "问题备注"
        })

        st.dataframe(
            issue_display,
            use_container_width=True,
            height=250,
            hide_index=True
        )

    except Exception as e:
        st.warning(f"⚠️ 列表渲染异常: {str(e)}")


def render_14day_trend(df):
    st.subheader("📅 近14天变化趋势")

    if not _safe_column(df, "record_date"):
        st.info("📋 暂无日期数据")
        return

    try:
        df_copy = df.copy()
        df_copy["record_date"] = pd.to_datetime(df_copy["record_date"])

        max_date = df_copy["record_date"].max()
        if pd.isna(max_date):
            st.info("📋 暂无有效日期数据")
            return

        fourteen_days_ago = max_date - pd.Timedelta(days=13)
        recent_df = df_copy[df_copy["record_date"] >= fourteen_days_ago]

        if len(recent_df) == 0:
            st.info("📋 近14天暂无数据")
            return

        daily_stats = recent_df.groupby(recent_df["record_date"].dt.date).agg(
            平均准备时间=("prep_minutes", "mean"),
            平均等待时间=("wait_minutes", "mean"),
            总续水次数=("refill_count", "sum")
        ).reset_index()

        daily_stats.columns = ["日期", "平均准备时间", "平均等待时间", "总续水次数"]
        daily_stats = daily_stats.sort_values("日期")

        fig = go.Figure()

        if daily_stats["平均等待时间"].notna().any():
            fig.add_trace(go.Scatter(
                x=daily_stats["日期"],
                y=daily_stats["平均等待时间"],
                mode="lines+markers",
                name="平均等待时间",
                line=dict(color="#FF6B6B", width=2)
            ))

        if daily_stats["平均准备时间"].notna().any():
            fig.add_trace(go.Scatter(
                x=daily_stats["日期"],
                y=daily_stats["平均准备时间"],
                mode="lines+markers",
                name="平均准备时间",
                line=dict(color="#4ECDC4", width=2)
            ))

        fig.update_layout(
            title="近14天平均时间变化(分钟)",
            height=300,
            legend_title="指标",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.warning(f"⚠️ 图表渲染异常: {str(e)}")
