# -*- coding: utf-8 -*-
"""Auto-generated business analysis commentary."""

from typing import Optional
import pandas as pd


def _pct_change(current: float, previous: float) -> Optional[float]:
    if previous and previous != 0:
        return (current - previous) / abs(previous)
    return None


def _concentration_desc(share: float) -> str:
    """Describe customer/product concentration level."""
    if share >= 0.6:
        return "集中度较高"
    if share >= 0.35:
        return "集中度适中"
    return "分布较为分散"


def _period_prefix(period_label: str) -> str:
    if period_label and period_label not in ("全部", "当前筛选周期"):
        return f"本报告期（{period_label}）"
    return "本报告期"


def _sales_fx(total_usd: float, total_som: float) -> Optional[float]:
    """Som per USD implied from sales (same underlying amount, two currencies)."""
    if total_usd > 0 and total_som > 0:
        return total_som / total_usd
    return None


def _collection_rates(
    col_usd: float, col_som: float, total_usd: float, total_som: float,
) -> dict[str, float]:
    """Collection rates: sales USD/Som are the same total via FX; payments split by channel."""
    rates: dict[str, float] = {}
    fx = _sales_fx(total_usd, total_som)
    if total_usd > 0 and fx:
        # 苏姆收款折算为美金后与美金收款相加，再除以销售美金（唯一销售口径）
        col_equiv_usd = col_usd + col_som / fx
        rates["combined"] = col_equiv_usd / total_usd
        rates["usd_channel"] = col_usd / total_usd
        rates["som_channel"] = col_som / total_som if total_som > 0 else 0.0
    elif total_usd > 0:
        rates["combined"] = col_usd / total_usd
        rates["usd_channel"] = rates["combined"]
    elif total_som > 0:
        rates["combined"] = col_som / total_som
        rates["som_channel"] = rates["combined"]
    else:
        rates["combined"] = 0.0
    return rates


def _collection_rate_comment(rate: float) -> str:
    if rate >= 0.8:
        return "回款进度良好，资金周转效率较高。"
    if rate >= 0.5:
        return "回款进度正常，建议持续跟进未结清客户。"
    return "回款覆盖率偏低，建议加强应收账款管理与催收力度。"


def generate_sales_commentary(
    df: pd.DataFrame,
    df_prev: Optional[pd.DataFrame] = None,
    period_label: str = "",
    col_df: Optional[pd.DataFrame] = None,
) -> str:
    """Generate a professional multi-paragraph sales analysis commentary."""
    if df.empty:
        return "当前筛选条件下无销售数据，无法生成分析。"

    total_usd = df["合计$_clean"].sum()
    total_som = df["苏姆合计_clean"].sum()
    total_orders = df["单据编号"].nunique()
    raw_col = "客户名称" if "客户名称" in df.columns else "客户名称_clean"
    total_customers = df[raw_col].nunique()
    avg_order_usd = total_usd / total_orders if total_orders else 0
    avg_cust_usd = total_usd / total_customers if total_customers else 0

    prefix = _period_prefix(period_label)
    paragraphs = []

    # ── 1. 经营概况 ──────────────────────────────────────────────────────────
    overview = (
        f"{prefix}，公司共实现销售收入 **${total_usd:,.2f}**（苏姆 {total_som:,.2f}），"
        f"完成销售订单 **{total_orders:,}** 笔，服务活跃客户 **{total_customers}** 家。"
        f"单均订单金额约 **${avg_order_usd:,.2f}**，"
        f"户均销售贡献约 **${avg_cust_usd:,.2f}**。"
    )
    if total_usd > 0 and total_som > 0:
        overview += (
            f" 销售金额的美金与苏姆为同一数据按汇率 **{total_som / total_usd:,.2f}** 苏姆/美金换算，"
            f"差异来自客户付款币种不同。"
        )
    paragraphs.append(overview)

    # ── 2. 同比/环比 ─────────────────────────────────────────────────────────
    if df_prev is not None and not df_prev.empty:
        prev_usd = df_prev["合计$_clean"].sum()
        prev_orders = df_prev["单据编号"].nunique()
        prev_customers = df_prev[raw_col].nunique()
        pct = _pct_change(total_usd, prev_usd)
        if pct is not None:
            trend = "增长" if pct > 0 else "下降"
            order_delta = total_orders - prev_orders
            cust_delta = total_customers - prev_customers
            paragraphs.append(
                f"与上一对比周期相比，销售收入{trend} **${abs(total_usd - prev_usd):,.2f}**（{pct:+.1%}），"
                f"订单量{'增加' if order_delta >= 0 else '减少'} **{abs(order_delta)}** 笔，"
                f"活跃客户数{'增加' if cust_delta >= 0 else '减少'} **{abs(cust_delta)}** 家。"
                f"{'整体经营呈扩张态势，需关注产能与回款配套。' if pct > 0.05 else ''}"
                f"{'经营规模有所收缩，建议重点复盘核心客户与主力品类。' if pct < -0.05 else ''}"
            )

    # ── 3. 客户结构 ──────────────────────────────────────────────────────────
    by_cust = df.groupby(raw_col)["合计$_clean"].sum().sort_values(ascending=False)
    if not by_cust.empty and total_usd > 0:
        top3 = by_cust.head(3)
        cr3 = top3.sum() / total_usd
        top1_name, top1_val = top3.index[0], top3.iloc[0]
        top1_share = top1_val / total_usd
        cust_parts = [
            f"{name}（${val:,.2f}，{val / total_usd:.1%}）"
            for name, val in top3.items()
        ]
        cust_line = (
            f"客户结构方面，销售贡献前三位分别为：{'、'.join(cust_parts)}。"
            f"前三名合计占比 **{cr3:.1%}**，{_concentration_desc(cr3)}；"
            f"最大单一客户 **{top1_name}** 贡献 **{top1_share:.1%}**。"
        )
        if top1_share >= 0.25:
            cust_line += " 建议持续关注头部客户依存度，并同步拓展中腰部客户。"
        paragraphs.append(cust_line)

    # ── 4. 账户维度 ──────────────────────────────────────────────────────────
    if "账户" in df.columns:
        by_acc = df.groupby("账户").agg(
            销售美金=("合计$_clean", "sum"),
            销售苏姆=("苏姆合计_clean", "sum"),
            单数=("单据编号", "nunique"),
        ).sort_values("销售美金", ascending=False)
        if len(by_acc) >= 1 and total_usd > 0:
            acc_parts = []
            for acc_name, row in by_acc.head(3).iterrows():
                usd_share = row["销售美金"] / total_usd
                som_share = row["销售苏姆"] / total_som if total_som > 0 else 0
                acc_parts.append(
                    f"{acc_name}（美金 {usd_share:.1%}、苏姆 {som_share:.1%}，{int(row['单数'])} 单）"
                )
            acc_line = f"按账户划分，{'；'.join(acc_parts)}。"
            if len(by_acc) > 1:
                top_acc = by_acc.index[0]
                top_share = by_acc.iloc[0]["销售美金"] / total_usd
                acc_line += (
                    f" **{top_acc}** 为当前主力账户，美金销售占比 **{top_share:.1%}**。"
                )
            paragraphs.append(acc_line)

    # ── 5. 产品结构 ──────────────────────────────────────────────────────────
    if "类别" in df.columns:
        by_cat = df.groupby("类别").agg(
            销售美金=("合计$_clean", "sum"),
            箱数=("箱数_clean", "sum"),
        ).sort_values("销售美金", ascending=False)
        if not by_cat.empty and total_usd > 0:
            cat_parts = []
            for cat_name, row in by_cat.head(3).iterrows():
                cat_parts.append(
                    f"{cat_name}（${row['销售美金']:,.2f}，{row['销售美金'] / total_usd:.1%}，"
                    f"{int(row['箱数']):,} 箱）"
                )
            cat_line = f"产品类别方面，销售前三类为：{'、'.join(cat_parts)}。"
            top_cat_share = by_cat.iloc[0]["销售美金"] / total_usd
            if top_cat_share >= 0.4:
                cat_line += " 品类结构偏集中，可评估是否需要丰富产品组合以分散风险。"
            else:
                cat_line += " 品类分布相对均衡，有利于稳定整体销售基本盘。"
            paragraphs.append(cat_line)

    # ── 6. 收款与回款（有收款数据时）──────────────────────────────────────────
    if col_df is not None and not col_df.empty:
        col_usd = col_df["美金_clean"].sum()
        col_som = col_df["苏姆_clean"].sum()
        col_count = len(col_df)
        col_rc = "客户名称" if "客户名称" in col_df.columns else "客户名称_clean"
        col_customers = col_df[col_rc].nunique()

        rates = _collection_rates(col_usd, col_som, total_usd, total_som)
        fx = _sales_fx(total_usd, total_som)
        col_line = (
            f"回款方面，本期共确认收款 **${col_usd:,.2f}**（苏姆 {col_som:,.2f}），"
            f"涉及收款记录 **{col_count}** 笔、**{col_customers}** 家客户。"
        )
        if fx and total_usd > 0:
            col_equiv_usd = col_usd + col_som / fx
            col_line += (
                f" 按销售汇率折算后，收款合计约 **${col_equiv_usd:,.2f}**（美金收款 + 苏姆收款折算），"
                f"综合回款率 **{rates['combined']:.1%}**（= 销售美金口径）。"
            )
            if "usd_channel" in rates and "som_channel" in rates:
                col_line += (
                    f" 其中美金渠道 **{rates['usd_channel']:.1%}**、"
                    f"苏姆渠道 **{rates['som_channel']:.1%}**（两渠道相加为综合回款，"
                    f"因销售美金/苏姆为同一金额的双币种表示）。"
                )
            col_line += " " + _collection_rate_comment(rates["combined"])
        elif rates:
            col_line += f" 综合回款率 **{rates['combined']:.1%}**。"
            col_line += " " + _collection_rate_comment(rates["combined"])

        # 按账户：同样以销售美金为唯一分母，苏姆收款先折算
        if "账户" in df.columns and "账户" in col_df.columns:
            acc_notes = []
            for acc in sorted(df["账户"].dropna().unique()):
                s_acc = df[df["账户"] == acc]
                c_acc = col_df[col_df["账户"] == acc]
                s_usd = s_acc["合计$_clean"].sum()
                s_som = s_acc["苏姆合计_clean"].sum()
                c_usd = c_acc["美金_clean"].sum()
                c_som = c_acc["苏姆_clean"].sum()
                acc_fx = _sales_fx(s_usd, s_som)
                if s_usd > 0 and acc_fx:
                    acc_rate = (c_usd + c_som / acc_fx) / s_usd
                    acc_notes.append(f"{acc}综合回款 **{acc_rate:.1%}**")
                elif s_usd > 0:
                    acc_notes.append(f"{acc}综合回款 **{c_usd / s_usd:.1%}**")
                elif s_som > 0:
                    acc_notes.append(f"{acc}综合回款 **{c_som / s_som:.1%}**")
            if acc_notes:
                col_line += " 分账户：" + "；".join(acc_notes) + "。"

        if col_usd > 0:
            by_usd = col_df.groupby(col_rc)["美金_clean"].sum()
            top_usd = by_usd[by_usd > 0].sort_values(ascending=False).head(3)
            if not top_usd.empty:
                payer_parts = [
                    f"{name}（${val:,.2f}，{val / col_usd:.1%}）"
                    for name, val in top_usd.items()
                ]
                col_line += f" 美金收款贡献前三客户：{'、'.join(payer_parts)}。"
        if col_som > 0:
            by_som = col_df.groupby(col_rc)["苏姆_clean"].sum()
            top_som = by_som[by_som > 0].sort_values(ascending=False).head(3)
            if not top_som.empty:
                som_parts = [
                    f"{name}（{val:,.2f}，{val / col_som:.1%}）"
                    for name, val in top_som.items()
                ]
                col_line += f" 苏姆收款贡献前三客户：{'、'.join(som_parts)}。"
        paragraphs.append(col_line)

    # ── 7. 综合建议 ──────────────────────────────────────────────────────────
    closing = "综合以上数据，建议持续关注头部客户维护、主力品类供应保障及回款节奏管控，确保销售增长与现金流健康同步。"
    paragraphs.append(closing)

    return "\n\n".join(paragraphs)


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
