# -*- coding: utf-8 -*-
"""Excel export utilities."""

import io
import pandas as pd
from datetime import datetime
import os


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    """Convert a DataFrame to Excel bytes using openpyxl."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output.read()


def export_sales_summary(sales_df: pd.DataFrame) -> bytes:
    """Export aggregated sales summary."""
    summary = (
        sales_df.groupby(["年份", "月份", "账户", "客户名称_clean"])
        .agg(
            销售单数=("单据编号", "nunique"),
            销售产品数=("商品名称_clean", "count"),
            美金总额=("合计$_clean", "sum"),
            苏姆总额=("苏姆合计_clean", "sum"),
            总箱数=("箱数_clean", "sum"),
            总平方数=("平方数_clean", "sum"),
        )
        .reset_index()
        .sort_values(["年份", "月份", "美金总额"], ascending=[True, True, False])
    )
    return dataframe_to_excel_bytes(summary, "销售汇总")


def export_collection_summary(collection_df: pd.DataFrame) -> bytes:
    """Export aggregated collection summary."""
    summary = (
        collection_df.groupby(["年份", "月份", "账户", "客户名称_clean"])
        .agg(
            收款笔数=("日期_clean", "count"),
            美金总额=("美金_clean", "sum"),
            苏姆总额=("苏姆_clean", "sum"),
        )
        .reset_index()
        .sort_values(["年份", "月份", "美金总额"], ascending=[True, True, False])
    )
    return dataframe_to_excel_bytes(summary, "收款汇总")


def export_customer_statement(
    sales_df: pd.DataFrame,
    collection_df: pd.DataFrame,
    customer_name: str,
    account: str,
) -> bytes:
    """Export customer statement with all sales and collections."""
    sales_cust = sales_df[
        (sales_df["客户名称_clean"] == customer_name) & (sales_df["账户"] == account)
    ][
        [
            "日期", "单据编号", "商品名称_clean", "色号", "规格型号",
            "箱数_clean", "平方数_clean", "单价$_clean", "合计$_clean",
        ]
    ].copy()
    sales_cust.columns = [
        "日期", "单据编号", "商品名称", "色号", "规格型号",
        "箱数", "平方数", "单价$", "合计$",
    ]
    sales_cust["类型"] = "销售"

    collection_cust = collection_df[
        (collection_df["客户名称_clean"] == customer_name)
        & (collection_df["账户"] == account)
    ][["日期_clean", "美金_clean", "苏姆_clean", "备注"]].copy()
    collection_cust.columns = ["日期", "美金金额", "苏姆金额", "备注"]
    collection_cust["类型"] = "收款"

    # Combine
    combined = pd.concat([sales_cust, collection_cust], ignore_index=True)
    combined = combined.sort_values("日期")
    combined["日期"] = combined["日期"].dt.strftime("%Y-%m-%d")

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        sales_cust_out = combined[combined["类型"] == "销售"]
        collection_out = combined[combined["类型"] == "收款"]
        sales_cust_out.to_excel(writer, sheet_name="销售明细", index=False)
        collection_out.to_excel(writer, sheet_name="收款明细", index=False)

    output.seek(0)
    return output.read()


def ensure_reports_dir(base_dir: str) -> str:
    """Ensure reports directory exists and return path."""
    reports_dir = os.path.join(base_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir
