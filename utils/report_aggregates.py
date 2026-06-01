# -*- coding: utf-8 -*-
"""Shared aggregations for export reports (KPIs, tables, preview metrics)."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from utils.narrative_generator import _pct_change, _collection_rates


def raw_col(df: pd.DataFrame) -> str:
    return "客户名称" if "客户名称" in df.columns else "客户名称_clean"


def fmt_usd(v: float) -> str:
    return f"${v:,.2f}"


def fmt_som(v: float) -> str:
    return f"₴{v:,.2f}"


def fmt_delta(current: float, previous: Optional[float]) -> str:
    """Format KPI change for report cards (+5.1% / -3.2%)."""
    if previous is None:
        return ""
    pct = _pct_change(current, previous)
    if pct is None:
        return ""
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1%}"


def fmt_delta_count(current: int, previous: Optional[int]) -> str:
    if previous is None:
        return ""
    delta = current - previous
    if delta == 0:
        return "0"
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:,}"


def sales_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"total_usd": 0.0, "total_som": 0.0, "total_orders": 0, "total_customers": 0}
    rc = raw_col(df)
    return {
        "total_usd": float(df["合计$_clean"].sum()),
        "total_som": float(df["苏姆合计_clean"].sum()),
        "total_orders": int(df["单据编号"].nunique()),
        "total_customers": int(df[rc].nunique()),
    }


def collection_metrics(col_df: pd.DataFrame) -> dict:
    if col_df.empty:
        return {"col_usd": 0.0, "col_som": 0.0, "combined_rate": None}
    col_usd = float(col_df["美金_clean"].sum())
    col_som = float(col_df["苏姆_clean"].sum())
    return {
        "col_usd": col_usd,
        "col_som": col_som,
        "combined_rate": None,
    }


def combined_collection_rate(
    col_df: pd.DataFrame,
    sales_df: pd.DataFrame,
) -> Optional[float]:
    if col_df.empty or sales_df.empty:
        return None
    sm = sales_metrics(sales_df)
    cm = collection_metrics(col_df)
    rates = _collection_rates(cm["col_usd"], cm["col_som"], sm["total_usd"], sm["total_som"])
    return rates.get("combined")


def _rows_from_df(frame: pd.DataFrame, builders) -> list:
    """Build table rows via itertuples (faster than iterrows)."""
    return [builders(r) for r in frame.itertuples(index=False)]


def make_kpis(
    df: pd.DataFrame,
    col_df: pd.DataFrame,
    df_prev: Optional[pd.DataFrame] = None,
    col_prev: Optional[pd.DataFrame] = None,
) -> list[tuple[str, str, str]]:
    """Build KPI list for the report; third column is period-over-period change."""
    cur = sales_metrics(df)
    prev = sales_metrics(df_prev) if df_prev is not None and not df_prev.empty else None
    prev_usd = prev["total_usd"] if prev else None
    prev_orders = prev["total_orders"] if prev else None
    prev_customers = prev["total_customers"] if prev else None

    kpis = [
        ("销售美金合计", fmt_usd(cur["total_usd"]), fmt_delta(cur["total_usd"], prev_usd)),
        ("销售单数", f"{cur['total_orders']:,}", fmt_delta_count(cur["total_orders"], prev_orders)),
        ("客户数量", f"{cur['total_customers']}", fmt_delta_count(cur["total_customers"], prev_customers)),
    ]

    if not col_df.empty:
        cm = collection_metrics(col_df)
        prev_cm = (
            collection_metrics(col_prev)
            if col_prev is not None and not col_prev.empty
            else None
        )
        prev_col_usd = prev_cm["col_usd"] if prev_cm else None
        prev_col_som = prev_cm["col_som"] if prev_cm else None

        rate = combined_collection_rate(col_df, df)
        prev_rate = (
            combined_collection_rate(col_prev, df_prev)
            if col_prev is not None and not col_prev.empty
            and df_prev is not None and not df_prev.empty
            else None
        )
        rate_delta = ""
        if rate is not None and prev_rate is not None:
            pts = (rate - prev_rate) * 100
            sign = "+" if pts > 0 else ""
            rate_delta = f"{sign}{pts:.1f}pp"

        kpis.append(("收款美金合计", fmt_usd(cm["col_usd"]), fmt_delta(cm["col_usd"], prev_col_usd)))
        kpis.append(("收款苏姆合计", fmt_som(cm["col_som"]), fmt_delta(cm["col_som"], prev_col_som)))
        if rate is not None:
            kpis.append(("综合回款率", f"{rate:.1%}", rate_delta))

    return kpis


def sales_tables(df: pd.DataFrame, is_single_month: bool = False) -> list:
    """Build table list for sales section."""
    tables = []
    rc = raw_col(df)

    if not is_single_month:
        m = (
            df.groupby(["年份", "月份"])
            .agg(
                销售美金=("合计$_clean", "sum"),
                销售苏姆=("苏姆合计_clean", "sum"),
                单数=("单据编号", "nunique"),
            )
            .reset_index()
        )
        m["年月"] = m["年份"].astype(str) + "-" + m["月份"].astype(str).str.zfill(2)
        m = m.sort_values(["年份", "月份"])
        tables.append((
            "月度销售汇总",
            _rows_from_df(
                m,
                lambda r: [r.年月, int(r.单数), fmt_usd(r.销售美金), fmt_som(r.销售苏姆)],
            ),
            ["年月", "单数", "销售美金 ($)", "销售苏姆 (₴)"],
        ))

    total_acc_usd = df["合计$_clean"].sum()
    acc = (
        df.groupby("账户")
        .agg(
            销售美金=("合计$_clean", "sum"),
            销售苏姆=("苏姆合计_clean", "sum"),
            单数=("单据编号", "nunique"),
        )
        .reset_index()
        .sort_values("销售美金", ascending=False)
    )
    acc["占比"] = (acc["销售美金"] / total_acc_usd * 100).round(2)
    tables.append((
        "按账户汇总",
        _rows_from_df(
            acc,
            lambda r: [
                r.账户, fmt_usd(r.销售美金), fmt_som(r.销售苏姆),
                int(r.单数), f"{r.占比:.2f}%",
            ],
        ),
        ["账户", "销售美金 ($)", "销售苏姆 (₴)", "单数", "占比 (%)"],
    ))

    if "类别" in df.columns:
        cat_total_usd = df["合计$_clean"].sum()
        cat = (
            df.groupby("类别")
            .agg(销售美金=("合计$_clean", "sum"), 箱数=("箱数_clean", "sum"))
            .reset_index()
            .sort_values("销售美金", ascending=False)
        )
        cat["占比"] = (cat["销售美金"] / cat_total_usd * 100).round(2)
        tables.append((
            "按产品类别汇总",
            _rows_from_df(
                cat,
                lambda r: [r.类别, fmt_usd(r.销售美金), int(r.箱数), f"{r.占比:.2f}%"],
            ),
            ["类别", "销售美金 ($)", "销售箱数", "占比 (%)"],
        ))

    if "客户类别" in df.columns:
        cat_total_usd = df["合计$_clean"].sum()
        bc = (
            df.groupby("客户类别")
            .agg(
                销售美金=("合计$_clean", "sum"),
                销售苏姆=("苏姆合计_clean", "sum"),
                销售单数=("单据编号", "nunique"),
                销售数量=("单据编号", "count"),
            )
            .reset_index()
            .sort_values("销售美金", ascending=False)
        )
        bc["占比"] = (bc["销售美金"] / cat_total_usd * 100).round(2)
        tables.append((
            "客户类别总览",
            _rows_from_df(
                bc,
                lambda r: [
                    r.客户类别, fmt_usd(r.销售美金), fmt_som(r.销售苏姆),
                    int(r.销售单数), int(r.销售数量), f"{r.占比:.2f}%",
                ],
            ),
            ["客户类别", "销售美金 ($)", "销售苏姆 (₴)", "销售单数", "销售数量", "占比 (%)"],
        ))

    total_usd = df["合计$_clean"].sum()
    cust = (
        df.groupby(rc)
        .agg(销售美金=("合计$_clean", "sum"), 单数=("单据编号", "nunique"))
        .reset_index()
        .sort_values("销售美金", ascending=False)
    )
    cust["占比"] = (cust["销售美金"] / total_usd * 100).round(2)
    tables.append((
        "客户销售排名",
        [
            [row[rc], fmt_usd(row["销售美金"]), f"{row['占比']:.2f}%", int(row["单数"])]
            for _, row in cust.iterrows()
        ],
        ["客户名称", "销售美金 ($)", "占比 (%)", "单数"],
    ))

    prod_total_usd = df["合计$_clean"].sum()
    prod = (
        df.groupby("商品名称_clean")
        .agg(销售美金=("合计$_clean", "sum"), 箱数=("箱数_clean", "sum"))
        .reset_index()
        .sort_values("销售美金", ascending=False)
        .head(10)
    )
    prod["占比"] = (prod["销售美金"] / prod_total_usd * 100).round(2)
    tables.append((
        "产品销售排名 TOP10",
        _rows_from_df(
            prod,
            lambda r: [
                r.商品名称_clean, fmt_usd(r.销售美金),
                int(r.箱数), f"{r.占比:.2f}%",
            ],
        ),
        ["产品名称", "销售美金 ($)", "箱数", "占比 (%)"],
    ))

    return tables


def collection_tables(col_df: pd.DataFrame) -> list:
    tables = []
    if col_df.empty:
        return tables
    rc = raw_col(col_df)

    acc = (
        col_df.groupby("账户")
        .agg(
            收款美金=("美金_clean", "sum"),
            收款苏姆=("苏姆_clean", "sum"),
            笔数=("日期_clean", "count"),
        )
        .reset_index()
        .sort_values("收款美金", ascending=False)
    )
    tables.append((
        "按账户收款汇总",
        _rows_from_df(
            acc,
            lambda r: [r.账户, fmt_usd(r.收款美金), fmt_som(r.收款苏姆), int(r.笔数)],
        ),
        ["账户", "收款美金 ($)", "收款苏姆 (₴)", "笔数"],
    ))

    total_col_usd = col_df["美金_clean"].sum()
    total_col_som = col_df["苏姆_clean"].sum()
    cust = (
        col_df.groupby(rc)
        .agg(
            收款美金=("美金_clean", "sum"),
            收款苏姆=("苏姆_clean", "sum"),
            笔数=("日期_clean", "count"),
        )
        .reset_index()
    )
    cust["美金占比"] = (
        (cust["收款美金"] / total_col_usd * 100).round(2) if total_col_usd > 0 else 0
    )
    cust["苏姆占比"] = (
        (cust["收款苏姆"] / total_col_som * 100).round(2) if total_col_som > 0 else 0
    )
    cust = cust.sort_values(["收款美金", "收款苏姆"], ascending=[False, False])
    tables.append((
        "客户收款排名",
        [
            [
                row[rc], fmt_usd(row["收款美金"]), fmt_som(row["收款苏姆"]),
                int(row["笔数"]), f"{row['美金占比']:.2f}%", f"{row['苏姆占比']:.2f}%",
            ]
            for _, row in cust.iterrows()
        ],
        ["客户名称", "收款美金 ($)", "收款苏姆 (₴)", "笔数", "美金占比 (%)", "苏姆占比 (%)"],
    ))
    return tables
