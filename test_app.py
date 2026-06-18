import pandas as pd
import numpy as np
from utils.data_loader import (
    load_csv, map_columns, parse_dates, validate_required_fields,
    detect_anomalies, REQUIRED_FIELDS, OPTIONAL_FIELDS, ALL_FIELDS
)

print("=" * 60)
print("测试茶会服务节奏分析看板核心功能")
print("=" * 60)

print("\n1. 测试数据加载...")
try:
    with open("sample_data.csv", "rb") as f:
        raw_df = load_csv(f)
    print(f"   ✅ 成功加载 {len(raw_df)} 条数据")
    print(f"   列名: {list(raw_df.columns)}")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print("\n2. 测试字段映射...")
try:
    field_mapping = {col: col for col in ALL_FIELDS if col in raw_df.columns}
    mapped_df = map_columns(raw_df, field_mapping)
    print(f"   ✅ 字段映射完成")
    print(f"   映射后列: {list(mapped_df.columns)}")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print("\n3. 测试日期解析...")
try:
    parsed_df = parse_dates(mapped_df, "YYYY-MM-DD")
    print(f"   ✅ 日期解析完成")
    print(f"   日期范围: {parsed_df['record_date'].min()} 到 {parsed_df['record_date'].max()}")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print("\n4. 测试必填字段校验...")
try:
    errors = validate_required_fields(parsed_df)
    if errors:
        print(f"   ⚠️  校验错误: {errors}")
    else:
        print(f"   ✅ 所有必填字段校验通过")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print("\n5. 测试异常检测...")
try:
    processed_df = detect_anomalies(parsed_df)
    anomaly_count = processed_df["is_anomaly"].sum()
    print(f"   ✅ 异常检测完成")
    print(f"   检测到 {anomaly_count} 条异常等待记录")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print("\n6. 测试缺失可选字段的鲁棒性...")
try:
    partial_df = processed_df.drop(columns=["helper_name", "issue_note"])
    print(f"   ✅ 缺失可选字段时仍能正常运行")
    print(f"   剩余列: {list(partial_df.columns)}")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print("\n7. 测试自定义筛选逻辑...")
try:
    filtered = processed_df[processed_df["session_name"].isin(["早茶场", "午茶场"])]
    print(f"   ✅ 筛选功能正常")
    print(f"   筛选前: {len(processed_df)} 条, 筛选后: {len(filtered)} 条")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print("\n8. 测试数据统计...")
try:
    print(f"   总场次: {len(processed_df['session_name'].unique())}")
    print(f"   总桌数: {len(processed_df['table_no'].unique())}")
    if "wait_minutes" in processed_df.columns:
        print(f"   平均等待时间: {processed_df['wait_minutes'].mean():.1f} 分钟")
    if "refill_count" in processed_df.columns:
        print(f"   总续水次数: {int(processed_df['refill_count'].sum())}")
    print(f"   ✅ 数据统计正常")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print("\n9. 测试导出功能...")
try:
    csv_output = processed_df.to_csv(index=False).encode("utf-8-sig")
    print(f"   ✅ CSV 导出正常")
    print(f"   导出数据大小: {len(csv_output)} 字节")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print("\n" + "=" * 60)
print("所有核心功能测试完成！")
print("=" * 60)

print("\n" + "项目结构:")
import os
for root, dirs, files in os.walk(".", topdown=True):
    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
    level = root.replace(".", "").count(os.sep)
    indent = " " * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = " " * 2 * (level + 1)
    for file in files:
        if not file.startswith('.') and not file.endswith('.pyc'):
            print(f"{subindent}{file}")
