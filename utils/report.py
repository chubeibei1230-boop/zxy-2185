import pandas as pd
import numpy as np
from io import BytesIO


def _has_col(df, col):
    return col in df.columns and df[col].notna().any()


def generate_report_summary(filtered_df, full_df):
    if filtered_df is None or len(filtered_df) == 0:
        return None

    report = {}
    report["metrics_overview"] = _build_metrics_overview(filtered_df)
    report["anomaly_attribution"] = _build_anomaly_attribution(filtered_df)
    report["session_comparison"] = _build_dimension_comparison(filtered_df, "session_name", "场次")
    report["table_comparison"] = _build_dimension_comparison(filtered_df, "table_no", "桌号")
    report["helper_comparison"] = _build_helper_comparison(filtered_df)
    report["trend_interpretation"] = _build_trend_interpretation(filtered_df)
    report["optimization_suggestions"] = _build_optimization_suggestions(filtered_df)
    return report


def _build_metrics_overview(df):
    metrics = {
        "total_records": len(df),
        "total_sessions": int(df["session_name"].nunique()) if "session_name" in df.columns else 0,
        "total_tables": int(df["table_no"].nunique()) if "table_no" in df.columns else 0,
        "avg_wait": float(df["wait_minutes"].mean()) if _has_col(df, "wait_minutes") else None,
        "max_wait": float(df["wait_minutes"].max()) if _has_col(df, "wait_minutes") else None,
        "median_wait": float(df["wait_minutes"].median()) if _has_col(df, "wait_minutes") else None,
        "avg_prep": float(df["prep_minutes"].mean()) if _has_col(df, "prep_minutes") else None,
        "max_prep": float(df["prep_minutes"].max()) if _has_col(df, "prep_minutes") else None,
        "total_refills": int(df["refill_count"].sum()) if _has_col(df, "refill_count") else 0,
        "anomaly_count": int(df["is_anomaly"].sum()) if "is_anomaly" in df.columns else 0,
        "anomaly_rate": float(df["is_anomaly"].mean() * 100) if "is_anomaly" in df.columns and len(df) > 0 else 0.0,
        "date_range_start": str(df["record_date"].min()) if "record_date" in df.columns else None,
        "date_range_end": str(df["record_date"].max()) if "record_date" in df.columns else None,
    }
    if metrics["total_records"] > 0 and metrics["anomaly_count"] > 0:
        metrics["anomaly_rate"] = round(metrics["anomaly_count"] / metrics["total_records"] * 100, 1)
    else:
        metrics["anomaly_rate"] = 0.0
    return metrics


def _build_anomaly_attribution(df):
    result = {"anomaly_records": [], "top_anomaly_tables": [], "top_anomaly_sessions": [], "issue_notes": []}

    if "is_anomaly" not in df.columns:
        return result

    anomaly_df = df[df["is_anomaly"] == True].copy()
    if len(anomaly_df) == 0:
        return result

    display_cols = ["record_date", "session_name", "table_no", "wait_minutes", "helper_name", "issue_note"]
    cols = [c for c in display_cols if c in anomaly_df.columns]
    records = anomaly_df[cols].copy()
    records = records.sort_values("wait_minutes" if "wait_minutes" in records.columns else "record_date", ascending=False)
    for _, row in records.head(20).iterrows():
        rec = {}
        for c in cols:
            val = row[c]
            if pd.isna(val):
                rec[c] = ""
            elif isinstance(val, float):
                rec[c] = round(val, 1)
            else:
                rec[c] = str(val)
        result["anomaly_records"].append(rec)

    if "table_no" in anomaly_df.columns:
        table_counts = anomaly_df.groupby("table_no").agg(
            anomaly_count=("is_anomaly", "sum"),
            avg_wait=("wait_minutes", "mean") if _has_col(anomaly_df, "wait_minutes") else ("is_anomaly", "count"),
        ).reset_index()
        table_counts = table_counts.sort_values("anomaly_count", ascending=False)
        result["top_anomaly_tables"] = [
            {"table_no": str(r["table_no"]), "anomaly_count": int(r["anomaly_count"]),
             "avg_wait": round(float(r["avg_wait"]), 1) if pd.notna(r["avg_wait"]) else None}
            for _, r in table_counts.head(5).iterrows()
        ]

    if "session_name" in anomaly_df.columns:
        session_counts = anomaly_df.groupby("session_name").agg(
            anomaly_count=("is_anomaly", "sum"),
            avg_wait=("wait_minutes", "mean") if _has_col(anomaly_df, "wait_minutes") else ("is_anomaly", "count"),
        ).reset_index()
        session_counts = session_counts.sort_values("anomaly_count", ascending=False)
        result["top_anomaly_sessions"] = [
            {"session_name": str(r["session_name"]), "anomaly_count": int(r["anomaly_count"]),
             "avg_wait": round(float(r["avg_wait"]), 1) if pd.notna(r["avg_wait"]) else None}
            for _, r in session_counts.head(5).iterrows()
        ]

    if _has_col(anomaly_df, "issue_note"):
        notes = anomaly_df[
            anomaly_df["issue_note"].notna() & (anomaly_df["issue_note"].astype(str).str.strip() != "")
        ][["record_date", "session_name", "table_no", "issue_note"]].copy()
        for _, r in notes.head(10).iterrows():
            result["issue_notes"].append({
                "date": str(r["record_date"]),
                "session": str(r["session_name"]) if "session_name" in notes.columns else "",
                "table": str(r["table_no"]) if "table_no" in notes.columns else "",
                "note": str(r["issue_note"]),
            })

    return result


def _build_dimension_comparison(df, dim_col, dim_label):
    comparison = {"dimension": dim_label, "column": dim_col, "items": []}

    if dim_col not in df.columns:
        return comparison

    agg_dict = {}
    if _has_col(df, "wait_minutes"):
        agg_dict["avg_wait"] = ("wait_minutes", "mean")
        agg_dict["max_wait"] = ("wait_minutes", "max")
    if _has_col(df, "prep_minutes"):
        agg_dict["avg_prep"] = ("prep_minutes", "mean")
    if _has_col(df, "refill_count"):
        agg_dict["total_refills"] = ("refill_count", "sum")
    if "is_anomaly" in df.columns:
        agg_dict["anomaly_count"] = ("is_anomaly", "sum")
    agg_dict["record_count"] = (dim_col, "count")

    if not agg_dict:
        return comparison

    grouped = df.groupby(dim_col).agg(**agg_dict).reset_index()

    for _, row in grouped.iterrows():
        item = {"name": str(row[dim_col]), "record_count": int(row["record_count"])}
        if "avg_wait" in grouped.columns:
            item["avg_wait"] = round(float(row["avg_wait"]), 1) if pd.notna(row["avg_wait"]) else None
        if "max_wait" in grouped.columns:
            item["max_wait"] = round(float(row["max_wait"]), 1) if pd.notna(row["max_wait"]) else None
        if "avg_prep" in grouped.columns:
            item["avg_prep"] = round(float(row["avg_prep"]), 1) if pd.notna(row["avg_prep"]) else None
        if "total_refills" in grouped.columns:
            item["total_refills"] = int(row["total_refills"]) if pd.notna(row["total_refills"]) else 0
        if "anomaly_count" in grouped.columns:
            item["anomaly_count"] = int(row["anomaly_count"])
        comparison["items"].append(item)

    if _has_col(df, "wait_minutes") and comparison["items"]:
        comparison["items"].sort(key=lambda x: x.get("avg_wait", 0) or 0, reverse=True)

    return comparison


def _build_helper_comparison(df):
    comparison = {"dimension": "助理", "column": "helper_name", "items": []}

    if not _has_col(df, "helper_name"):
        return comparison

    helper_df = df[df["helper_name"].notna() & (df["helper_name"].astype(str).str.strip() != "")].copy()
    if len(helper_df) == 0:
        return comparison

    agg_dict = {}
    agg_dict["tables_served"] = ("table_no", "nunique")
    agg_dict["record_count"] = ("helper_name", "count")
    if _has_col(helper_df, "wait_minutes"):
        agg_dict["avg_wait"] = ("wait_minutes", "mean")
    if _has_col(helper_df, "refill_count"):
        agg_dict["total_refills"] = ("refill_count", "sum")
    if "is_anomaly" in helper_df.columns:
        agg_dict["anomaly_count"] = ("is_anomaly", "sum")

    grouped = helper_df.groupby("helper_name").agg(**agg_dict).reset_index()

    for _, row in grouped.iterrows():
        item = {
            "name": str(row["helper_name"]),
            "tables_served": int(row["tables_served"]),
            "record_count": int(row["record_count"]),
        }
        if "avg_wait" in grouped.columns:
            item["avg_wait"] = round(float(row["avg_wait"]), 1) if pd.notna(row["avg_wait"]) else None
        if "total_refills" in grouped.columns:
            item["total_refills"] = int(row["total_refills"]) if pd.notna(row["total_refills"]) else 0
        if "anomaly_count" in grouped.columns:
            item["anomaly_count"] = int(row["anomaly_count"])
        comparison["items"].append(item)

    if comparison["items"]:
        comparison["items"].sort(key=lambda x: x.get("avg_wait", 0) or 0, reverse=True)

    return comparison


def _build_trend_interpretation(df):
    result = {"has_trend": False, "days_count": 0, "interpretations": [], "daily_stats": []}

    if not _has_col(df, "record_date"):
        return result

    try:
        df_copy = df.copy()
        df_copy["record_date"] = pd.to_datetime(df_copy["record_date"])
        max_date = df_copy["record_date"].max()
        if pd.isna(max_date):
            return result

        fourteen_days_ago = max_date - pd.Timedelta(days=13)
        recent_df = df_copy[df_copy["record_date"] >= fourteen_days_ago]

        if len(recent_df) == 0:
            return result

        result["has_trend"] = True
        result["days_count"] = int(recent_df["record_date"].dt.date.nunique())

        agg_dict = {}
        if _has_col(recent_df, "wait_minutes"):
            agg_dict["avg_wait"] = ("wait_minutes", "mean")
        if _has_col(recent_df, "prep_minutes"):
            agg_dict["avg_prep"] = ("prep_minutes", "mean")
        if _has_col(recent_df, "refill_count"):
            agg_dict["total_refills"] = ("refill_count", "sum")
        agg_dict["record_count"] = ("record_date", "count")

        if len(agg_dict) <= 1:
            return result

        daily_stats = recent_df.groupby(recent_df["record_date"].dt.date).agg(**agg_dict).reset_index()
        daily_stats = daily_stats.sort_values("record_date")

        for _, row in daily_stats.iterrows():
            day_data = {"date": str(row["record_date"])}
            if "avg_wait" in daily_stats.columns:
                day_data["avg_wait"] = round(float(row["avg_wait"]), 1) if pd.notna(row["avg_wait"]) else None
            if "avg_prep" in daily_stats.columns:
                day_data["avg_prep"] = round(float(row["avg_prep"]), 1) if pd.notna(row["avg_prep"]) else None
            if "total_refills" in daily_stats.columns:
                day_data["total_refills"] = int(row["total_refills"]) if pd.notna(row["total_refills"]) else 0
            day_data["record_count"] = int(row["record_count"])
            result["daily_stats"].append(day_data)

        if len(daily_stats) >= 3 and "avg_wait" in daily_stats.columns:
            first_third = daily_stats.iloc[:len(daily_stats) // 3]["avg_wait"].mean()
            last_third = daily_stats.iloc[-(len(daily_stats) // 3):]["avg_wait"].mean()
            if pd.notna(first_third) and pd.notna(last_third):
                diff = last_third - first_third
                if diff > 1:
                    result["interpretations"].append(
                        f"近14天平均等待时间呈上升趋势，后期较前期上升 {diff:.1f} 分钟，需关注服务节奏是否放缓"
                    )
                elif diff < -1:
                    result["interpretations"].append(
                        f"近14天平均等待时间呈下降趋势，后期较前期改善 {abs(diff):.1f} 分钟，服务节奏持续优化"
                    )
                else:
                    result["interpretations"].append(
                        "近14天平均等待时间保持稳定，服务节奏整体平稳"
                    )

        if len(daily_stats) >= 3 and "avg_prep" in daily_stats.columns:
            first_third = daily_stats.iloc[:len(daily_stats) // 3]["avg_prep"].mean()
            last_third = daily_stats.iloc[-(len(daily_stats) // 3):]["avg_prep"].mean()
            if pd.notna(first_third) and pd.notna(last_third):
                diff = last_third - first_third
                if diff > 2:
                    result["interpretations"].append(
                        f"准备时间呈上升趋势（+{diff:.1f} 分钟），建议检查备茶流程是否存在瓶颈"
                    )
                elif diff < -2:
                    result["interpretations"].append(
                        f"准备时间呈下降趋势（{diff:.1f} 分钟），备茶效率在提升"
                    )

        if len(daily_stats) >= 2 and "total_refills" in daily_stats.columns:
            max_refill_day = daily_stats.loc[daily_stats["total_refills"].idxmax()]
            result["interpretations"].append(
                f"续水需求最高日为 {max_refill_day['record_date']}（{int(max_refill_day['total_refills'])} 次），可据此安排高峰人力"
            )

        if "is_anomaly" in recent_df.columns:
            anomaly_by_day = recent_df[recent_df["is_anomaly"] == True].groupby(
                recent_df["record_date"].dt.date
            ).size()
            if len(anomaly_by_day) > 0:
                worst_day = anomaly_by_day.idxmax()
                worst_count = int(anomaly_by_day.max())
                result["interpretations"].append(
                    f"异常等待集中日为 {worst_day}（{worst_count} 次），建议复盘当日排班与客流情况"
                )

    except Exception:
        pass

    return result


def _build_optimization_suggestions(df):
    suggestions = []

    if _has_col(df, "wait_minutes"):
        avg_wait = df["wait_minutes"].mean()
        if avg_wait > 10:
            suggestions.append({
                "priority": "高",
                "category": "等待时间",
                "suggestion": f"当前平均等待 {avg_wait:.1f} 分钟，超过10分钟警戒线，建议增加高峰时段助理配置，缩短客人等待"
            })

    if "is_anomaly" in df.columns:
        anomaly_rate = df["is_anomaly"].mean() * 100
        if anomaly_rate > 15:
            suggestions.append({
                "priority": "高",
                "category": "异常等待",
                "suggestion": f"异常等待比例达 {anomaly_rate:.1f}%，建议排查异常高发时段和桌号，针对性增派人力"
            })

    if _has_col(df, "session_name") and _has_col(df, "wait_minutes"):
        session_wait = df.groupby("session_name")["wait_minutes"].mean()
        if len(session_wait) >= 2:
            worst_session = session_wait.idxmax()
            worst_val = session_wait.max()
            best_session = session_wait.idxmin()
            best_val = session_wait.min()
            gap = worst_val - best_val
            if gap > 5:
                suggestions.append({
                    "priority": "中",
                    "category": "场次差异",
                    "suggestion": f"「{worst_session}」平均等待 {worst_val:.1f} 分钟，比「{best_session}」高出 {gap:.1f} 分钟，建议在「{worst_session}」提前备茶并增加助理"
                })

    if _has_col(df, "table_no") and _has_col(df, "wait_minutes"):
        table_wait = df.groupby("table_no")["wait_minutes"].mean()
        if len(table_wait) >= 2:
            worst_table = table_wait.idxmax()
            worst_val = table_wait.max()
            overall_avg = df["wait_minutes"].mean()
            if worst_val > overall_avg * 1.5:
                suggestions.append({
                    "priority": "中",
                    "category": "桌号差异",
                    "suggestion": f"「{worst_table}」号桌平均等待 {worst_val:.1f} 分钟，超出整体均值 {((worst_val - overall_avg) / overall_avg * 100):.0f}%，建议优化该桌的巡看频次"
                })

    if _has_col(df, "helper_name"):
        helper_df = df[df["helper_name"].notna() & (df["helper_name"].astype(str).str.strip() != "")]
        if len(helper_df) > 0:
            helper_load = helper_df.groupby("helper_name")["table_no"].nunique()
            if len(helper_load) >= 2:
                max_load = helper_load.max()
                min_load = helper_load.min()
                if max_load > min_load * 1.5:
                    busiest = helper_load.idxmax()
                    suggestions.append({
                        "priority": "中",
                        "category": "助理负载",
                        "suggestion": f"助理「{busiest}」负责 {max_load} 桌，负载较其他助理偏高，建议重新分配桌号或增派人手"
                    })

    if _has_col(df, "prep_minutes"):
        avg_prep = df["prep_minutes"].mean()
        if avg_prep > 12:
            suggestions.append({
                "priority": "低",
                "category": "准备效率",
                "suggestion": f"平均准备时间 {avg_prep:.1f} 分钟，建议标准化备茶流程、提前预判高场次需求"
            })

    if _has_col(df, "issue_note"):
        issues = df[df["issue_note"].notna() & (df["issue_note"].astype(str).str.strip() != "")]
        if len(issues) > 0:
            issue_keywords = ["慢", "等", "久", "茶凉", "不够", "忘记", "漏", "不及时"]
            keyword_hits = []
            for kw in issue_keywords:
                count = issues["issue_note"].astype(str).str.contains(kw).sum()
                if count > 0:
                    keyword_hits.append((kw, count))
            if keyword_hits:
                top_kw = sorted(keyword_hits, key=lambda x: x[1], reverse=True)[0]
                suggestions.append({
                    "priority": "低",
                    "category": "问题反馈",
                    "suggestion": f"客人反馈中「{top_kw[0]}」类问题出现 {top_kw[1]} 次，建议针对此类问题制定专项改善措施"
                })

    if not suggestions:
        suggestions.append({
            "priority": "信息",
            "category": "整体评价",
            "suggestion": "当前筛选范围内各项指标正常，暂无突出优化建议，请继续保持现有服务水准"
        })

    return suggestions


def export_report_excel(report):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        m = report["metrics_overview"]
        overview_data = {
            "指标": [
                "数据总条数", "总场次数", "总桌数",
                "平均等待时间(分钟)", "最长等待时间(分钟)", "中位等待时间(分钟)",
                "平均准备时间(分钟)", "最长准备时间(分钟)",
                "总续水次数", "异常等待次数", "异常等待比例(%)",
                "数据起始日期", "数据截止日期",
            ],
            "数值": [
                m["total_records"], m["total_sessions"], m["total_tables"],
                _fmt(m["avg_wait"]), _fmt(m["max_wait"]), _fmt(m["median_wait"]),
                _fmt(m["avg_prep"]), _fmt(m["max_prep"]),
                m["total_refills"], m["anomaly_count"], m["anomaly_rate"],
                m["date_range_start"] or "", m["date_range_end"] or "",
            ]
        }
        pd.DataFrame(overview_data).to_excel(writer, sheet_name="核心指标概览", index=False)

        anomaly = report["anomaly_attribution"]
        if anomaly["anomaly_records"]:
            anomaly_df = pd.DataFrame(anomaly["anomaly_records"])
            col_rename = {
                "record_date": "日期", "session_name": "场次", "table_no": "桌号",
                "wait_minutes": "等待时间", "helper_name": "助理", "issue_note": "问题备注"
            }
            anomaly_df = anomaly_df.rename(columns={k: v for k, v in col_rename.items() if k in anomaly_df.columns})
            anomaly_df.to_excel(writer, sheet_name="异常等待归因", index=False)

        for comp_key, sheet_suffix in [
            ("session_comparison", "场次对比"), ("table_comparison", "桌号对比"), ("helper_comparison", "助理对比")
        ]:
            comp = report[comp_key]
            if comp["items"]:
                comp_df = pd.DataFrame(comp["items"])
                col_rename = {
                    "name": comp["dimension"], "record_count": "记录数",
                    "avg_wait": "平均等待(分)", "max_wait": "最长等待(分)",
                    "avg_prep": "平均准备(分)", "total_refills": "总续水次数",
                    "anomaly_count": "异常次数", "tables_served": "服务桌数",
                }
                comp_df = comp_df.rename(columns={k: v for k, v in col_rename.items() if k in comp_df.columns})
                comp_df.to_excel(writer, sheet_name=sheet_suffix, index=False)

        trend = report["trend_interpretation"]
        if trend["daily_stats"]:
            trend_df = pd.DataFrame(trend["daily_stats"])
            col_rename = {
                "date": "日期", "avg_wait": "平均等待(分)", "avg_prep": "平均准备(分)",
                "total_refills": "总续水次数", "record_count": "记录数"
            }
            trend_df = trend_df.rename(columns={k: v for k, v in col_rename.items() if k in trend_df.columns})
            trend_df.to_excel(writer, sheet_name="近14天趋势", index=False)

        if trend["interpretations"]:
            interp_df = pd.DataFrame({"趋势解读": trend["interpretations"]})
            interp_df.to_excel(writer, sheet_name="趋势解读", index=False)

        if report["optimization_suggestions"]:
            sug_df = pd.DataFrame(report["optimization_suggestions"])
            sug_df = sug_df.rename(columns={"priority": "优先级", "category": "类别", "suggestion": "建议内容"})
            sug_df.to_excel(writer, sheet_name="优化建议", index=False)

    output.seek(0)
    return output


def _fmt(val):
    if val is None:
        return ""
    return round(val, 1)
