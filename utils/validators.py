# -*- coding: utf-8 -*-
"""Data validation utilities."""

import pandas as pd


REQUIRED_SALES_COLS = [
    "单据日期", "单据编号", "客户名称", "商品名称",
    "合计$", "苏姆合计",
]

REQUIRED_COLLECTION_COLS = [
    "日期", "客户名称", "美金金额", "苏姆金额",
]

REQUIRED_CUSTOMER_COLS = [
    "客户名称",
]


class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.is_valid = True

    def add_error(self, msg):
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg):
        self.warnings.append(msg)


def validate_sales_data(df: pd.DataFrame) -> ValidationResult:
    """Validate sales data DataFrame."""
    result = ValidationResult()

    # Check required columns
    missing = [c for c in REQUIRED_SALES_COLS if c not in df.columns]
    if missing:
        result.add_error(f"销售数据缺少必要字段: {missing}")

    # Check date parseable
    date_col = "单据日期"
    if date_col in df.columns:
        null_dates = df[date_col].isna().sum()
        if null_dates > 0:
            result.add_warning(f"销售数据有 {null_dates} 行日期无法解析")

    # Check amount fields
    for col in ["合计$", "苏姆合计"]:
        if col in df.columns:
            non_numeric = pd.to_numeric(df[col], errors="coerce").isna().sum()
            if non_numeric > 0:
                result.add_warning(f"销售数据 '{col}' 列有 {non_numeric} 个非数值项")

    return result


def validate_collection_data(df: pd.DataFrame) -> ValidationResult:
    """Validate collection data DataFrame."""
    result = ValidationResult()

    missing = [c for c in REQUIRED_COLLECTION_COLS if c not in df.columns]
    if missing:
        result.add_error(f"收款数据缺少必要字段: {missing}")

    date_col = "日期"
    if date_col in df.columns:
        null_dates = df[date_col].isna().sum()
        if null_dates > 0:
            result.add_warning(f"收款数据有 {null_dates} 行日期无法解析")

    return result


def validate_customer_master(df: pd.DataFrame) -> ValidationResult:
    """Validate customer master data."""
    result = ValidationResult()

    missing = [c for c in REQUIRED_CUSTOMER_COLS if c not in df.columns]
    if missing:
        result.add_error(f"客户主数据缺少必要字段: {missing}")

    return result
