# -*- coding: utf-8 -*-
"""Auto-generated business analysis commentary."""

from typing import Optional
import pandas as pd


def _pct_change(current: float, previous: float) -> Optional[float]:
    if previous and previous != 0:
        return (current - previous) / abs(previous)
    return None


def generate_sales_commentary(
    df: pd.DataFrame,
    df_prev: Optional[pd.DataFrame] = None,
    period_label: str = "",
) -> str:
    """Generate a natural-language sales analysis commentary (no markdown syntax)."""
    if df.empty:
        return "当前筛选条件下无销售数据，无法生成分析。"

    total_usd = df["合计$_clean"].sum()
    total_som = df["苏姆合计_clean"].sum()
    total_orders = df["单据编号"].nunique()
    raw_col = "客户名称" if "客户名称" in df.columns else "客户名称_clean"
    total_customers = df[raw_col].nunique()

    lines = []
    lines.append(f"在{period_label}内，共实现销售收入 ${total_usd:,.2f}，"
                 f"苏姆 {total_som:,.2f}，完成订单 {total_orders} 笔，客户数 {total_customers} 家。")

    if df_prev is not None and not df_prev.empty:
        prev_usd = df_prev["合计$_clean"].sum()
        prev_orders = df_prev["单据编号"].nunique()
        pct = _pct_change(total_usd, prev_usd)
        if pct is not None:
            trend = "增长" if pct > 0 else "下降"
            lines.append(f"与上一周期相比，销售收入{trend} ${abs(total_usd - prev_usd):,.2f}"
                         f"（{pct:+.1%}），"
                         f"订单量{trend.replace('增长','增加').replace('下降','减少')} "
                         f"{abs(total_orders - prev_orders)} 笔。")

    top_cust = df.groupby(raw_col)["合计$_clean"].sum().sort_values(ascending=False).head(3)
    if not top_cust.empty:
        names = "、".join(top_cust.index.tolist())
        lines.append(f"销售贡献前三名的客户分别是：{names}。")

    by_acc = df.groupby("账户")["合计$_clean"].sum().sort_values(ascending=False)
    if len(by_acc) > 1:
        top_acc = by_acc.index[0]
        top_acc_share = by_acc.iloc[0] / total_usd
        lines.append(f"从账户维度看，{top_acc}贡献了总收入的 {top_acc_share:.1%}，"
                     f"是当前最主要的销售来源。")

    if "类别" in df.columns:
        by_cat = df.groupby("类别")["合计$_clean"].sum().sort_values(ascending=False)
        if not by_cat.empty:
            cat1 = by_cat.index[0]
            cat1_val = by_cat.iloc[0]
            line = f"产品类别方面，{cat1} 销售额最高（${cat1_val:,.2f}）。"
            if len(by_cat) > 1:
                cat2 = by_cat.index[1]
                cat2_val = by_cat.iloc[1]
                line += f" 其次为 {cat2}（${cat2_val:,.2f}）。"
            lines.append(line)

    return " ".join(lines)


def generate_product_commentary(
    df: pd.DataFrame,
    period_label: str = "",
) -> str:
    """Generate a product analysis commentary (no markdown syntax)."""
    if df.empty:
        return "当前筛选条件下无销售数据。"

    top_prod = df.groupby("商品名称_clean")["合计$_clean"].sum().sort_values(ascending=False).head(3)
    total_usd = df["合计$_clean"].sum()

    lines = []
    lines.append(f"在{period_label}内，共涉及 SKU {df['商品名称_clean'].nunique()} 个，"
                 f"总销售 ${total_usd:,.2f}。")

    if not top_prod.empty:
        p1 = top_prod.index[0]
        p1_val = top_prod.iloc[0]
        lines.append(f"最畅销产品为 {p1}（${p1_val:,.2f}），"
                     f"占总销售的 {p1_val / total_usd:.1%}。")
        if len(top_prod) > 1:
            p2 = top_prod.index[1]
            p2_val = top_prod.iloc[1]
            lines.append(f"其次为 {p2}（${p2_val:,.2f}）。")
        if len(top_prod) > 2:
            p3 = top_prod.index[2]
            p3_val = top_prod.iloc[2]
            lines.append(f"第三为 {p3}（${p3_val:,.2f}）。")

    if "类别" in df.columns:
        by_cat = df.groupby("类别")["合计$_clean"].sum().sort_values(ascending=False)
        if not by_cat.empty:
            cat1 = by_cat.index[0]
            cat1_val = by_cat.iloc[0]
            lines.append(f"从类别看，{cat1} 贡献最高（${cat1_val:,.2f}），"
                         f"占总额的 {cat1_val / total_usd:.1%}。")

    if "等级" in df.columns:
        by_grade = df.groupby("等级")["合计$_clean"].sum().sort_values(ascending=False)
        if not by_grade.empty and by_grade.index[0] not in ["", None]:
            g1 = by_grade.index[0]
            g1_val = by_grade.iloc[0]
            lines.append(f"等级方面，{g1} 为主打等级（${g1_val:,.2f}）。")

    return " ".join(lines)
