# -*- coding: utf-8 -*-
"""导出报表页面 - Export Reports."""

import streamlit as st
import pandas as pd
from datetime import datetime
from utils.helpers import (
    check_data_loaded, get_filtered_sales, get_filtered_collection,
    period_label as _period_label, apply_quick_filter,
)
from utils.report_generator import build_pdf, build_markdown, build_html
from utils.narrative_generator import (
    generate_sales_commentary,
    generate_product_commentary,
)


def _raw_col(df):
    return "客户名称" if "客户名称" in df.columns else "客户名称_clean"


def _fmt_usd(v):
    return f"${v:,.2f}"


def _fmt_som(v):
    return f"₴{v:,.2f}"


def _make_kpis(df, col_df):
    """Build KPI list for the report."""
    total_usd = df["合计$_clean"].sum()
    total_orders = df["单据编号"].nunique()
    raw_col = _raw_col(df)
    total_customers = df[raw_col].nunique()
    kpis = [
        ("销售美金合计", _fmt_usd(total_usd), ""),
        ("销售单数", f"{total_orders:,}", ""),
        ("客户数量", f"{total_customers}", ""),
    ]
    if not col_df.empty:
        col_usd = col_df["美金_clean"].sum()
        col_som = col_df["苏姆_clean"].sum()
        kpis.append(("收款美金合计", _fmt_usd(col_usd), ""))
        kpis.append(("收款苏姆合计", _fmt_som(col_som), ""))
    return kpis


def _sales_tables(df, is_single_month=False):
    """Build table list for sales section."""
    tables = []
    raw_col = _raw_col(df)

    # Monthly (only if not single month)
    if not is_single_month:
        m = (
            df.groupby(["年份", "月份"])
            .agg(销售美金=("合计$_clean", "sum"), 销售苏姆=("苏姆合计_clean", "sum"),
                 单数=("单据编号", "nunique"))
            .reset_index()
        )
        m["年月"] = (m["年份"].astype(str) + "-" +
                     m["月份"].astype(str).str.zfill(2))
        m = m.sort_values(["年份", "月份"])
        tables.append(("月度销售汇总",
                      [[r["年月"], int(r["单数"]), _fmt_usd(r["销售美金"]), _fmt_som(r["销售苏姆"])]
                       for _, r in m.iterrows()],
                      ["年月", "单数", "销售美金 ($)", "销售苏姆 (₴)"]))

    # By account
    total_acc_usd = df["合计$_clean"].sum()
    acc = (
        df.groupby("账户")
        .agg(销售美金=("合计$_clean", "sum"), 销售苏姆=("苏姆合计_clean", "sum"),
             单数=("单据编号", "nunique"))
        .reset_index()
        .sort_values("销售美金", ascending=False)
    )
    acc["占比"] = (acc["销售美金"] / total_acc_usd * 100).round(2)
    tables.append(("按账户汇总",
                  [[r["账户"], _fmt_usd(r["销售美金"]), _fmt_som(r["销售苏姆"]),
                    int(r["单数"]), f"{r['占比']:.2f}%"]
                   for _, r in acc.iterrows()],
                  ["账户", "销售美金 ($)", "销售苏姆 (₴)", "单数", "占比 (%)"]))

    # By category
    if "类别" in df.columns:
        cat_total_usd = df["合计$_clean"].sum()
        cat = (
            df.groupby("类别")
            .agg(销售美金=("合计$_clean", "sum"), 箱数=("箱数_clean", "sum"))
            .reset_index()
            .sort_values("销售美金", ascending=False)
        )
        cat["占比"] = (cat["销售美金"] / cat_total_usd * 100).round(2)
        tables.append(("按产品类别汇总",
                      [[r["类别"], _fmt_usd(r["销售美金"]), int(r["箱数"]), f"{r['占比']:.2f}%"]
                       for _, r in cat.iterrows()],
                      ["类别", "销售美金 ($)", "销售箱数", "占比 (%)"]))

    # 客户类别总览
    if "客户类别" in df.columns:
        cat_total_usd = df["合计$_clean"].sum()
        bc = (
            df.groupby("客户类别")
            .agg(销售美金=("合计$_clean", "sum"), 销售苏姆=("苏姆合计_clean", "sum"),
                 销售单数=("单据编号", "nunique"), 销售数量=("单据编号", "count"))
            .reset_index()
            .sort_values("销售美金", ascending=False)
        )
        bc["占比"] = (bc["销售美金"] / cat_total_usd * 100).round(2)
        tables.append(("客户类别总览",
                      [[r["客户类别"], _fmt_usd(r["销售美金"]),
                        _fmt_som(r["销售苏姆"]), int(r["销售单数"]),
                        int(r["销售数量"]), f"{r['占比']:.2f}%"]
                       for _, r in bc.iterrows()],
                      ["客户类别", "销售美金 ($)", "销售苏姆 (₴)", "销售单数", "销售数量", "占比 (%)"]))

    # All customers
    total_usd = df["合计$_clean"].sum()
    cust = (
        df.groupby(raw_col)
        .agg(销售美金=("合计$_clean", "sum"), 单数=("单据编号", "nunique"))
        .reset_index()
        .sort_values("销售美金", ascending=False)
    )
    cust["占比"] = (cust["销售美金"] / total_usd * 100).round(2)
    tables.append(("客户销售排名",
                  [[r[raw_col], _fmt_usd(r["销售美金"]), f"{r['占比']:.2f}%", int(r["单数"])]
                   for _, r in cust.iterrows()],
                  ["客户名称", "销售美金 ($)", "占比 (%)", "单数"]))

    # Top products
    prod_total_usd = df["合计$_clean"].sum()
    prod = (
        df.groupby("商品名称_clean")
        .agg(销售美金=("合计$_clean", "sum"), 箱数=("箱数_clean", "sum"))
        .reset_index()
        .sort_values("销售美金", ascending=False)
        .head(10)
    )
    prod["占比"] = (prod["销售美金"] / prod_total_usd * 100).round(2)
    tables.append(("产品销售排名 TOP10",
                  [[r["商品名称_clean"], _fmt_usd(r["销售美金"]),
                    int(r["箱数"]), f"{r['占比']:.2f}%"]
                   for _, r in prod.iterrows()],
                  ["产品名称", "销售美金 ($)", "箱数", "占比 (%)"]))

    return tables


def _collection_tables(col_df):
    tables = []
    if col_df.empty:
        return tables
    rc = _raw_col(col_df)

    acc = (
        col_df.groupby("账户")
        .agg(收款美金=("美金_clean", "sum"), 收款苏姆=("苏姆_clean", "sum"),
             笔数=("日期_clean", "count"))
        .reset_index()
        .sort_values("收款美金", ascending=False)
    )
    tables.append(("按账户收款汇总",
                  [[r["账户"], _fmt_usd(r["收款美金"]), _fmt_som(r["收款苏姆"]), int(r["笔数"])]
                   for _, r in acc.iterrows()],
                  ["账户", "收款美金 ($)", "收款苏姆 (₴)", "笔数"]))

    total_col_usd = col_df["美金_clean"].sum()
    cust = (
        col_df.groupby(rc)
        .agg(收款美金=("美金_clean", "sum"), 收款苏姆=("苏姆_clean", "sum"),
             笔数=("日期_clean", "count"))
        .reset_index()
        .sort_values("收款美金", ascending=False)
    )
    cust["占比"] = (cust["收款美金"] / total_col_usd * 100).round(2)
    tables.append(("客户收款排名",
                  [[r[rc], _fmt_usd(r["收款美金"]), _fmt_som(r["收款苏姆"]),
                    int(r["笔数"]), f"{r['占比']:.2f}%"]
                   for _, r in cust.iterrows()],
                  ["客户名称", "收款美金 ($)", "收款苏姆 (₴)", "笔数", "占比 (%)"]))
    return tables


def render():
    check_data_loaded()
    st.title("📥 导出报表")

    df = get_filtered_sales()
    col_df = get_filtered_collection()
    period = _period_label()

    if df.empty:
        st.warning("当前筛选条件下无销售数据")
        return

    # ── Quick date range selector ──────────────────────────────────────────
    st.caption("快速选择报告周期（覆盖侧边栏筛选）")
    qc1, qc2 = st.columns([1, 3])
    with qc1:
        quick = st.selectbox(
            "报告周期",
            options=["全部", "本月", "上月", "近三月", "本年"],
            index=0,
            label_visibility="collapsed",
        )
    if quick != "全部":
        df = apply_quick_filter(df, quick)
        col_df = apply_quick_filter(col_df, quick)
        if df.empty:
            st.warning(f"「{quick}」区间内无销售数据")
            return

    period = quick if quick != "全部" else _period_label()

    tab1, tab2, tab3 = st.tabs(["📊 综合分析报告", "📋 明细查询", "🔍 客户对账单"])

    with tab1:
        st.subheader("专业商业分析报告生成")

        st.markdown("""
        选择报告格式并点击生成，系统将自动汇总核心指标、AI分析批语及多维数据表格，
        生成可直接向客户展示的专业商业报告。
        """)

        # ── KPI preview ──────────────────────────────────────────────────
        total_usd = df["合计$_clean"].sum()
        total_orders = df["单据编号"].nunique()
        raw_col = _raw_col(df)
        total_customers = df[raw_col].nunique()

        kc1, kc2, kc3, kc4 = st.columns(4)
        with kc1:
            st.metric("销售美金", f"${total_usd:,.2f}")
        with kc2:
            st.metric("销售单数", f"{total_orders:,}")
        with kc3:
            st.metric("客户数量", f"{total_customers}")
        with kc4:
            if not col_df.empty:
                col_som = col_df["苏姆_clean"].sum()
                st.metric("收款苏姆", f"₴{col_som:,.2f}")
            else:
                st.metric("收款苏姆", "无数据")

        # ── Commentary preview ─────────────────────────────────────────────
        commentary = generate_sales_commentary(df, period_label=period)
        with st.expander("📝 分析批语预览", expanded=True):
            st.markdown(commentary)

        # ── Report type selector ───────────────────────────────────────────
        report_type = st.selectbox(
            "报告格式",
            ["HTML 报告（推荐，可直接浏览器打开）",
             "Markdown 报告（可复制到文档）",
             "PDF 报告（适合打印/发送邮件）"],
        )

        col_gen, col_dl = st.columns([1, 2])
        with col_gen:
            generate = st.button("🚀 生成报告", type="primary", use_container_width=True)

        # Determine if single month
        unique_months = df.groupby(["年份", "月份"]).ngroups if "年份" in df.columns and "月份" in df.columns else 1
        is_single_month = unique_months == 1

        if generate:
            kpis = _make_kpis(df, col_df)
            tables = _sales_tables(df, is_single_month=is_single_month)
            tables += _collection_tables(col_df)

            footer = "销售分析系统"
            filename_prefix = f"销售分析报告_{datetime.now().strftime('%Y%m%d_%H%M')}"

            with st.spinner("正在生成报告..."):
                try:
                    if "HTML" in report_type:
                        content = build_html(
                            title="销售分析报告",
                            kpis=kpis,
                            commentary=commentary,
                            tables=tables,
                            footer_note=footer,
                            period=period,
                        )
                        st.success("HTML 报告生成成功！")
                        st.download_button(
                            "⬇ 下载 HTML 报告",
                            data=content.encode("utf-8"),
                            file_name=f"{filename_prefix}.html",
                            mime="text/html",
                            use_container_width=True,
                        )
                        st.markdown("💡 **提示：** HTML 报告可直接在浏览器中打开，支持打印为 PDF（Ctrl/Cmd+P）")

                    elif "Markdown" in report_type:
                        content = build_markdown(
                            title="销售分析报告",
                            kpis=kpis,
                            commentary=commentary,
                            tables=tables,
                            footer_note=footer,
                            period=period,
                        )
                        st.success("Markdown 报告生成成功！")
                        st.download_button(
                            "⬇ 下载 Markdown 报告",
                            data=content.encode("utf-8"),
                            file_name=f"{filename_prefix}.md",
                            mime="text/markdown",
                            use_container_width=True,
                        )

                    else:  # PDF
                        content = build_pdf(
                            title="销售分析报告",
                            kpis=kpis,
                            commentary=commentary,
                            tables=tables,
                            footer_note=footer,
                            period=period,
                        )
                        st.success("PDF 报告生成成功！")
                        st.download_button(
                            "⬇ 下载 PDF 报告",
                            data=content,
                            file_name=f"{filename_prefix}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                except Exception as e:
                    st.error(f"报告生成失败: {e}")

        # ── Sheet-by-sheet Excel export ───────────────────────────────────
        st.markdown("---")
        st.subheader("Excel 分Sheet导出")
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            if st.button("导出月度销售汇总", use_container_width=True):
                from utils.excel_exporter import export_sales_summary
                try:
                    data = export_sales_summary(df)
                    st.success("导出成功！")
                    st.download_button(
                        "⬇ 下载销售汇总",
                        data=data,
                        file_name=f"销售汇总_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"导出失败: {e}")

        with col_e2:
            if not col_df.empty:
                if st.button("导出收款汇总", use_container_width=True):
                    from utils.excel_exporter import export_collection_summary
                    try:
                        data = export_collection_summary(col_df)
                        st.success("导出成功！")
                        st.download_button(
                            "⬇ 下载收款汇总",
                            data=data,
                            file_name=f"收款汇总_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.error(f"导出失败: {e}")

    with tab2:
        st.subheader("销售/收款明细查询")

        search = st.text_input("搜索客户名称或单据编号", key="export_search")
        raw_col = _raw_col(df)
        if search:
            results = df[
                df[raw_col].str.contains(search, case=False, na=False) |
                df["单据编号"].str.contains(search, case=False, na=False)
            ]
            st.markdown(f"找到 **{len(results)}** 条销售记录")
            st.dataframe(
                results.assign(
                    日期=lambda x: x["日期"].dt.strftime("%Y-%m-%d"),
                    合计=lambda x: x["合计$_clean"].apply(lambda v: f"${v:,.2f}"),
                )[["日期", "单据编号", raw_col, "商品名称_clean",
                   "合计", "箱数_clean", "账户"]]
                .rename(columns={"箱数_clean": "箱数"})
                .head(200),
                hide_index=True, use_container_width=True,
            )

            if not col_df.empty:
                col_raw = _raw_col(col_df)
                cres = col_df[
                    col_df[col_raw].str.contains(search, case=False, na=False)
                ]
                if not cres.empty:
                    st.markdown(f"找到 **{len(cres)}** 条收款记录")
                    st.dataframe(
                        cres.assign(
                            日期=lambda x: x["日期_clean"].dt.strftime("%Y-%m-%d"),
                            美金=lambda x: x["美金_clean"].apply(lambda v: f"${v:,.2f}"),
                        )[["日期", col_raw, "美金", "苏姆_clean", "备注", "账户"]]
                        .rename(columns={"苏姆_clean": "苏姆"})
                        .head(200),
                        hide_index=True, use_container_width=True,
                    )

    with tab3:
        st.subheader("客户销售汇总")
        raw_col = _raw_col(df)
        sa = (
            df.groupby([raw_col, "账户"])
            .agg(销售美金=("合计$_clean", "sum"), 销售苏姆=("苏姆合计_clean", "sum"),
                 销售单数=("单据编号", "nunique"))
            .reset_index()
        )
        if not col_df.empty:
            col_raw = _raw_col(col_df)
            ca = (
                col_df.groupby([col_raw, "账户"])
                .agg(收款美金=("美金_clean", "sum"), 收款苏姆=("苏姆_clean", "sum"))
                .reset_index()
            )
            rec = sa.merge(ca, left_on=[raw_col, "账户"], right_on=[col_raw, "账户"],
                          how="left").fillna(0)
            # When both sides have same column name, pandas suffixes with _x/_y
            dup = (col_raw if col_raw != raw_col else raw_col) + "_x"
            if dup in rec.columns:
                rec = rec.drop(columns=[dup])
        else:
            rec = sa.copy()
            rec["收款美金"] = 0.0
            rec["收款苏姆"] = 0.0

        customers = [""] + sorted(rec[raw_col].unique().tolist())
        sel = st.selectbox("选择客户", customers, key="export_cust_stmt")

        if sel:
            cr = rec[rec[raw_col] == sel]
            st.dataframe(
                cr.assign(
                    销售美金=lambda x: x["销售美金"].apply(lambda v: f"${v:,.2f}"),
                    销售苏姆=lambda x: x["销售苏姆"].apply(lambda v: f"₴{v:,.2f}"),
                    收款美金=lambda x: x["收款美金"].apply(lambda v: f"${v:,.2f}"),
                    收款苏姆=lambda x: x["收款苏姆"].apply(lambda v: f"₴{v:,.2f}"),
                ),
                hide_index=True, use_container_width=True,
            )

            for _, row in cr.iterrows():
                acc = row["账户"]
                if st.button(f"导出 {sel} ({acc}) 明细", key=f"stmt_{sel}_{acc}"):
                    from utils.excel_exporter import export_customer_statement
                    try:
                        data = export_customer_statement(
                            df, col_df if not col_df.empty else pd.DataFrame(),
                            sel, acc,
                        )
                        st.success("导出成功！")
                        st.download_button(
                            f"⬇ 下载 {sel}_{acc}.xlsx",
                            data=data,
                            file_name=f"{sel}_{acc}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_{sel}_{acc}",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.error(f"导出失败: {e}")


render()
