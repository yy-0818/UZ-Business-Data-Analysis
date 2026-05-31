# -*- coding: utf-8 -*-
"""Data cleaning and standardization module."""

import re
import pandas as pd
import numpy as np
from datetime import datetime


def parse_chinese_date(val):
    """Parse Chinese-style date like '2025年3月1日'."""
    if pd.isna(val):
        return pd.NaT
    if isinstance(val, (datetime, pd.Timestamp)):
        return pd.to_datetime(val)
    val = str(val).strip()
    patterns = [
        (r"(\d{4})年(\d{1,2})月(\d{1,2})日", r"\1-\2-\3"),
        (r"(\d{4})-(\d{1,2})-(\d{1,2})", r"\1-\2-\3"),
        (r"(\d{4})/(\d{1,2})/(\d{1,2})", r"\1/\2/\3"),
    ]
    for pattern, replacement in patterns:
        val = re.sub(pattern, replacement, val)
    try:
        return pd.to_datetime(val)
    except Exception:
        return pd.NaT


def parse_amount(val):
    """Parse numeric amount, handle empty/None."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val = str(val).strip().replace(",", "").replace(" ", "")
    if val == "" or val == "-":
        return 0.0
    try:
        return float(val)
    except Exception:
        return 0.0


def normalize_account(val):
    """Normalize account type string to 1账户/2账户/3账户."""
    if pd.isna(val):
        return "未知"
    val = str(val).strip()
    if "1账户" in val or "开票" in val:
        return "1账户"
    elif "2账户" in val or "现金" in val:
        return "2账户"
    elif "3账户" in val or "出口" in val:
        return "3账户"
    return "未知"


def normalize_customer_name(val):
    """Clean and standardize customer name."""
    if pd.isna(val):
        return "未知客户"
    val = str(val).strip()
    val = re.sub(r"\s+", " ", val)
    val = re.sub(r"^[12账户]+\s*", "", val)
    return val.strip() if val.strip() else "未知客户"


def clean_product_name(val):
    """Clean product name."""
    if pd.isna(val):
        return "未知产品"
    val = str(val).strip()
    val = re.sub(r"\s+", " ", val)
    return val


REQUIRED_SALES_COLS = [
    "单据日期", "单据编号", "客户名称", "商品名称",
    "合计$", "苏姆合计",
]

REQUIRED_COLLECTION_COLS = [
    "日期", "客户名称", "美金金额", "苏姆金额",
]


class DataError(Exception):
    """Raised when data is missing required columns."""
    pass


def check_required_columns(df: pd.DataFrame, required_cols: list, data_type: str):
    """Check if required columns exist, raise DataError with clear message if not."""
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise DataError(
            f"{data_type}缺少必需列: {missing}\n"
            f"实际列名: {df.columns.tolist()}"
        )


def process_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    """Process raw sales data: clean columns, parse dates/amounts, standardize."""
    check_required_columns(df, REQUIRED_SALES_COLS, "销售数据")
    df = df.copy()

    # Parse dates
    df["日期"] = df["单据日期"].apply(parse_chinese_date)
    df["年份"] = df["日期"].dt.year
    df["月份"] = df["日期"].dt.month
    df["年月"] = df["日期"].dt.to_period("M")

    # Parse amounts
    df["合计$_clean"] = df["合计$"].apply(parse_amount)
    df["苏姆合计_clean"] = df["苏姆合计"].apply(parse_amount)
    df["箱数_clean"] = df["箱数"].apply(parse_amount)
    df["平方数_clean"] = df["平方数"].apply(parse_amount)
    df["单价$_clean"] = df["单价$"].apply(parse_amount)

    # Normalize account type
    df["账户"] = df["客户分类"].apply(normalize_account)

    # Standardize customer name (remove account prefix)
    df["客户名称_clean"] = df["客户名称"].apply(normalize_customer_name)

    # Keep raw customer name for accurate counting
    df["客户名称"] = df["客户名称"].astype(str).str.strip()

    # Product info
    df["商品名称_clean"] = df["商品名称"].apply(clean_product_name)

    # Drop rows where date is missing (can't analyze)
    df = df.dropna(subset=["日期"])

    return df


def process_collection_data(df: pd.DataFrame) -> pd.DataFrame:
    """Process raw collection/receipt data."""
    check_required_columns(df, REQUIRED_COLLECTION_COLS, "收款数据")
    df = df.copy()

    # Parse dates
    df["日期_clean"] = df["日期"].apply(parse_chinese_date)
    df["年份"] = df["日期_clean"].dt.year
    df["月份"] = df["日期_clean"].dt.month
    df["年月"] = df["日期_clean"].dt.to_period("M")

    # Parse amounts
    df["美金_clean"] = df["美金金额"].apply(parse_amount)
    df["苏姆_clean"] = df["苏姆金额"].apply(parse_amount)

    # Normalize account
    df["账户"] = df["账户类型"].apply(normalize_account)

    # Standardize customer name
    df["客户名称_clean"] = df["客户名称"].apply(normalize_customer_name)

    # Drop rows with no date
    df = df.dropna(subset=["日期_clean"])

    return df


def process_customer_master(df: pd.DataFrame) -> pd.DataFrame:
    """Process customer master data from contract_customers.xlsx.

    Keeps 客户类别 for downstream join, normalizes customer names
    to match the format in sales data (strip account prefix).
    """
    df = df.copy()

    # Rename columns if needed
    col_map = {}
    for col in df.columns:
        if "类别" in col:
            col_map[col] = "客户类别"
        elif "税号" in col:
            col_map[col] = "税号"
        elif "客户名称" in col or "客户" in col:
            col_map[col] = "客户名称"
        elif "状态" in col:
            col_map[col] = "状态"

    df = df.rename(columns=col_map)

    # Keep 客户名称, 客户类别 (and optionally 税号, 状态)
    keep = [c for c in ["客户类别", "税号", "客户名称", "状态"] if c in df.columns]
    df = df[keep].copy()

    # Standardize names: strip account prefixes so they match sales data
    if "客户名称" in df.columns:
        df["客户名称_std"] = df["客户名称"].apply(normalize_customer_name)
    else:
        df["客户名称_std"] = "未知客户"

    return df
