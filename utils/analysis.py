import streamlit as st
import pandas as pd
import numpy as np


def _has_col(df, col):
    return col in df.columns and df[col].notna().any()


def generate_service_suggestions(filtered_df, full_df):
    st.subheader("💡 服务节奏建议")

    if full_df is None or len(full_df) == 0:
        st.info("📋 暂无数据可分析")
        return

    try:
        full_df_copy = full_df.copy()
        full_df_copy["record_date"] = pd.to_datetime(full_df_copy["record_date"])

        max_date = full_df_copy["record_date"].max()
        if pd.isna(max_date):
            st.info("📋 暂无有效日期数据")
            return

        fourteen_days_ago = max_date - pd.Timedelta(days=13)
        recent_df = full_df_copy[full_df_copy["record_date"] >= fourteen_days_ago]

        if len(recent_df) == 0:
            st.info("📋 近14天暂无数据，无法生成建议")
            return

        col1, col2 = st.columns(2)

        with col1:
            _render_prep_suggestions(recent_df, filtered_df)
            _render_refill_suggestions(recent_df, filtered_df)

        with col2:
            _render_patrol_suggestions(recent_df, filtered_df)
            _render_issue_suggestions(recent_df, filtered_df)

    except Exception as e:
        st.warning(f"⚠️ 分析异常: {str(e)}")


def _render_prep_suggestions(recent_df, filtered_df):
    st.markdown("### ⏰ 需提前准备的场次")

    if not _has_col(recent_df, "prep_minutes") or not _has_col(recent_df, "session_name"):
        st.info("📋 暂无准备时间数据")
        return

    try:
        session_prep = recent_df.groupby("session_name")["prep_minutes"].agg(["mean", "max", "count"]).reset_index()
        session_prep.columns = ["场次", "平均准备时间", "最长准备时间", "服务次数"]

        overall_mean = recent_df["prep_minutes"].mean()
        threshold = max(overall_mean * 1.3, 10)

        need_prep = session_prep[session_prep["平均准备时间"] > threshold].sort_values("平均准备时间", ascending=False)

        if len(need_prep) == 0:
            st.success("✅ 所有场次准备时间正常")
            return

        for _, row in need_prep.iterrows():
            delta = row["平均准备时间"] - overall_mean
            with st.expander(f"🔴 {row['场次']} - 平均需 {row['平均准备时间']:.1f} 分钟", expanded=True):
                st.markdown(f"""
                - **平均准备时间**: {row['平均准备时间']:.1f} 分钟 (超出均值 {delta:.1f} 分钟)
                - **最长准备时间**: {row['最长准备时间']:.1f} 分钟
                - **历史服务次数**: {int(row['服务次数'])} 次
                - **建议**: 该场次需要提前 {int(row['平均准备时间'] * 0.3)} 分钟开始准备，建议增派 1 名助理协助
                """)

    except Exception as e:
        st.warning(f"⚠️ 分析异常: {str(e)}")


def _render_refill_suggestions(recent_df, filtered_df):
    st.markdown("### 💧 续水频次分析")

    if not _has_col(recent_df, "refill_count"):
        st.info("📋 暂无续水次数数据")
        return

    try:
        daily_refill = recent_df.groupby(recent_df["record_date"].dt.date)["refill_count"].sum()

        if len(daily_refill) < 2:
            st.info("📋 数据不足，无法分析续水趋势")
            return

        avg_refill = daily_refill.mean()
        max_refill = daily_refill.max()

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("日均续水", f"{avg_refill:.0f} 次")
        with col_b:
            st.metric("最高续水", f"{max_refill:.0f} 次")
        with col_c:
            trend = "↑" if daily_refill.iloc[-1] > avg_refill else "↓"
            st.metric("趋势", trend)

        if _has_col(recent_df, "session_name"):
            session_refill = recent_df.groupby("session_name")["refill_count"].sum().sort_values(ascending=False)
            if len(session_refill) > 0:
                top_session = session_refill.index[0]
                top_count = session_refill.iloc[0]
                st.info(f"💡 **{top_session}** 续水需求最高 (共 {int(top_count)} 次)，建议在该场次增加巡视频次")

    except Exception as e:
        st.warning(f"⚠️ 分析异常: {str(e)}")


def _render_patrol_suggestions(recent_df, filtered_df):
    st.markdown("### 👁️ 需加强巡看的桌号")

    if not _has_col(recent_df, "table_no"):
        st.info("📋 暂无桌号数据")
        return

    try:
        table_scores = pd.DataFrame()
        table_scores["桌号"] = recent_df["table_no"].unique()

        if _has_col(recent_df, "wait_minutes"):
            wait_stats = recent_df.groupby("table_no")["wait_minutes"].agg(["mean", "max"]).reset_index()
            wait_stats.columns = ["桌号", "平均等待", "最长等待"]
            table_scores = table_scores.merge(wait_stats, on="桌号", how="left")

        if _has_col(recent_df, "refill_count"):
            refill_stats = recent_df.groupby("table_no")["refill_count"].sum().reset_index()
            refill_stats.columns = ["桌号", "总续水"]
            table_scores = table_scores.merge(refill_stats, on="桌号", how="left")

        if "is_anomaly" in recent_df.columns:
            anomaly_counts = recent_df[recent_df["is_anomaly"] == True].groupby("table_no").size().reset_index()
            anomaly_counts.columns = ["桌号", "异常次数"]
            table_scores = table_scores.merge(anomaly_counts, on="桌号", how="left")
            table_scores["异常次数"] = table_scores["异常次数"].fillna(0).astype(int)
        else:
            table_scores["异常次数"] = 0

        if _has_col(recent_df, "issue_note"):
            issue_counts = recent_df[
                recent_df["issue_note"].notna() & (recent_df["issue_note"].astype(str).str.strip() != "")
            ].groupby("table_no").size().reset_index()
            issue_counts.columns = ["桌号", "问题次数"]
            table_scores = table_scores.merge(issue_counts, on="桌号", how="left")
            table_scores["问题次数"] = table_scores["问题次数"].fillna(0).astype(int)
        else:
            table_scores["问题次数"] = 0

        table_scores["风险分数"] = (
            table_scores.get("异常次数", 0) * 3 +
            table_scores.get("问题次数", 0) * 2 +
            (table_scores.get("总续水", 0) > table_scores.get("总续水", 0).mean()).astype(int) * 2
        )

        high_risk = table_scores[table_scores["风险分数"] > 0].sort_values("风险分数", ascending=False)

        if len(high_risk) == 0:
            st.success("✅ 所有桌号服务正常")
            return

        for _, row in high_risk.head(5).iterrows():
            risk_level = "🔴 高风险" if row["风险分数"] >= 5 else "🟡 中风险"
            with st.expander(f"{risk_level} - {row['桌号']} 号桌", expanded=True):
                reasons = []
                if row.get("异常次数", 0) > 0:
                    reasons.append(f"异常等待 {int(row['异常次数'])} 次")
                if row.get("问题次数", 0) > 0:
                    reasons.append(f"问题记录 {int(row['问题次数'])} 次")
                if pd.notna(row.get("总续水")) and row["总续水"] > 0:
                    reasons.append(f"续水 {int(row['总续水'])} 次")
                if pd.notna(row.get("平均等待")):
                    reasons.append(f"平均等待 {row['平均等待']:.1f} 分钟")

                st.markdown(f"- **风险原因**: {', '.join(reasons)}")
                st.markdown(f"- **建议**: 每 {max(10 - int(row['风险分数']), 3)} 分钟巡看一次，重点关注续水需求")

    except Exception as e:
        st.warning(f"⚠️ 分析异常: {str(e)}")


def _render_issue_suggestions(recent_df, filtered_df):
    st.markdown("### 📝 问题备注分析")

    if not _has_col(recent_df, "issue_note"):
        st.info("📋 暂无问题备注数据")
        return

    try:
        issues = recent_df[
            recent_df["issue_note"].notna() & (recent_df["issue_note"].astype(str).str.strip() != "")
        ][["record_date", "session_name", "table_no", "issue_note"]].copy()

        if len(issues) == 0:
            st.success("✅ 近期无问题记录")
            return

        issues["record_date"] = issues["record_date"].dt.strftime("%Y-%m-%d")
        issues.columns = ["日期", "场次", "桌号", "问题描述"]

        issue_keywords = ["慢", "等", "久", "茶凉", "不够", "没有", "忘记", "漏"]
        frequent_issues = []

        for keyword in issue_keywords:
            count = issues["问题描述"].astype(str).str.contains(keyword).sum()
            if count > 0:
                frequent_issues.append((keyword, count))

        if frequent_issues:
            st.markdown("**常见问题类型:**")
            for keyword, count in sorted(frequent_issues, key=lambda x: x[1], reverse=True)[:3]:
                st.markdown(f"- 「{keyword}」相关问题: **{count}** 次")

        st.markdown("**最近问题记录:**")
        st.dataframe(
            issues.sort_values("日期", ascending=False).head(5),
            use_container_width=True,
            hide_index=True
        )

    except Exception as e:
        st.warning(f"⚠️ 分析异常: {str(e)}")
