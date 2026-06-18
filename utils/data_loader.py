import pandas as pd
import numpy as np

REQUIRED_FIELDS = ["record_date", "session_name", "table_no"]
OPTIONAL_FIELDS = ["prep_minutes", "wait_minutes", "refill_count", "helper_name", "issue_note"]
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

DATE_FORMAT_MAP = {
    "YYYY-MM-DD": "%Y-%m-%d",
    "DD/MM/YYYY": "%d/%m/%Y",
    "MM/DD/YYYY": "%m/%d/%Y",
    "YYYY/MM/DD": "%Y/%m/%d",
    "DD-MM-YYYY": "%d-%m-%Y",
    "MM-DD-YYYY": "%m-%d-%Y"
}

ANOMALY_THRESHOLD = 15


def load_csv(uploaded_file):
    df = pd.read_csv(uploaded_file)
    return df


def map_columns(raw_df, field_mapping):
    mapped_df = pd.DataFrame()

    for field, source_col in field_mapping.items():
        if source_col in raw_df.columns:
            mapped_df[field] = raw_df[source_col]

    for field in OPTIONAL_FIELDS:
        if field not in mapped_df.columns:
            if field in ["prep_minutes", "wait_minutes", "refill_count"]:
                mapped_df[field] = np.nan
            else:
                mapped_df[field] = ""

    return mapped_df


def parse_dates(df, date_format_str):
    if "record_date" not in df.columns:
        return df

    fmt = DATE_FORMAT_MAP.get(date_format_str, "%Y-%m-%d")

    try:
        df["record_date"] = pd.to_datetime(df["record_date"], format=fmt, errors="coerce")
    except Exception:
        df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce")

    valid_dates = df["record_date"].notna().sum()
    if valid_dates < len(df) * 0.5:
        df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce")

    return df


def validate_required_fields(df):
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in df.columns:
            errors.append(f"缺少必填字段: {field}")
        elif df[field].isna().all():
            errors.append(f"必填字段 '{field}' 全部为空")

    if "record_date" in df.columns:
        if df["record_date"].isna().all():
            errors.append("日期字段解析失败，请检查日期格式设置")
        else:
            na_count = df["record_date"].isna().sum()
            if na_count > 0:
                errors.append(f"有 {na_count} 条记录的日期无法解析")

    if "prep_minutes" in df.columns and df["prep_minutes"].notna().any():
        non_numeric = pd.to_numeric(df["prep_minutes"], errors="coerce").isna().sum()
        if non_numeric > 0 and non_numeric < len(df):
            errors.append(f"准备时间字段有 {non_numeric} 条非数值数据")

    if "wait_minutes" in df.columns and df["wait_minutes"].notna().any():
        non_numeric = pd.to_numeric(df["wait_minutes"], errors="coerce").isna().sum()
        if non_numeric > 0 and non_numeric < len(df):
            errors.append(f"等待时间字段有 {non_numeric} 条非数值数据")

    if "refill_count" in df.columns and df["refill_count"].notna().any():
        non_numeric = pd.to_numeric(df["refill_count"], errors="coerce").isna().sum()
        if non_numeric > 0 and non_numeric < len(df):
            errors.append(f"续水次数字段有 {non_numeric} 条非数值数据")

    return errors


def detect_anomalies(df):
    if "prep_minutes" in df.columns:
        df["prep_minutes"] = pd.to_numeric(df["prep_minutes"], errors="coerce")

    if "wait_minutes" in df.columns:
        df["wait_minutes"] = pd.to_numeric(df["wait_minutes"], errors="coerce")

    if "refill_count" in df.columns:
        df["refill_count"] = pd.to_numeric(df["refill_count"], errors="coerce")

    df["is_anomaly"] = False

    if "wait_minutes" in df.columns:
        wait_mean = df["wait_minutes"].mean()
        wait_std = df["wait_minutes"].std()

        if pd.notna(wait_std) and wait_std > 0:
            threshold = max(ANOMALY_THRESHOLD, wait_mean + 2 * wait_std)
            df["is_anomaly"] = df["is_anomaly"] | (
                df["wait_minutes"].fillna(0) > threshold
            )
        else:
            df["is_anomaly"] = df["is_anomaly"] | (
                df["wait_minutes"].fillna(0) > ANOMALY_THRESHOLD
            )

    df["record_date"] = pd.to_datetime(df["record_date"]).dt.date

    return df
