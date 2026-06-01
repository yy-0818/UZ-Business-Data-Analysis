# -*- coding: utf-8 -*-
"""导出报表页面 - Export Reports."""

import streamlit as st
import pandas as pd
from datetime import datetime
from utils.helpers import (
    check_data_loaded, get_filtered_sales, get_filtered_collection,
    period_label as _period_label, apply_quick_filter,
    apply_previous_period_filter, comparison_period_label,
)
from utils.report_generator import build_pdf, build_markdown, build_html
from utils.report_aggregates import (
    raw_col, make_kpis, sales_tables, collection_tables,
)
from utils.report_cache import cached_sales_commentary


def _resolve_periods(quick: str):
    """Apply quick filter and comparison period on sidebar-filtered data."""
    base_df = get_filtered_sales()
    base_col = get_filtered_collection()

    if quick == "全部":
        df = base_df
        col_df = base_col
        df_prev = apply_previous_period_filter(base_df, "全部", date_col="日期")
        col_prev = apply_previous_period_filter(base_col, "全部", date_col="日期_clean")
        period = _period_label()
    else:
        df = apply_quick_filter(base_df, quick, date_col="日期")
        col_df = apply_quick_filter(base_col, quick, date_col="日期_clean")
        df_prev = apply_previous_period_filter(base_df, quick, date_col="日期")
        col_prev = apply_previous_period_filter(base_col, quick, date_col="日期_clean")
        period = quick

    has_comparison = (
        df_prev is not None and not df_prev.empty
    ) or (
        col_prev is not None and not col_prev.empty
    )
    return df, col_df, df_prev, col_prev, period, has_comparison


def render():
    check_data_loaded()
    st.title("📥 导出报表")

    period_sidebar = _period_label()

    if get_filtered_sales().empty:
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

    df, col_df, df_prev, col_prev, period, has_comparison = _resolve_periods(quick)

    if df.empty:
        st.warning(f"「{quick}」区间内无销售数据" if quick != "全部" else "当前筛选条件下无销售数据")
        return

    tab1, tab2, tab3 = st.tabs(["📊 综合分析报告", "📋 明细查询", "🔍 客户对账单"])

    with tab1:
        st.subheader("专业商业分析报告生成")

        st.markdown("""
        选择报告格式并点击生成，系统将自动汇总核心指标、AI分析批语及多维数据表格，
        生成可直接向客户展示的专业商业报告。
        """)

        if has_comparison:
            st.caption(f"对比基准：{comparison_period_label(quick)}")

        # ── KPI preview (aligned with report KPIs) ─────────────────────────
        kpis_preview = make_kpis(df, col_df, df_prev, col_prev)

        ncol = min(len(kpis_preview), 4)
        cols = st.columns(ncol)
        for i, (label, value, delta) in enumerate(kpis_preview[:ncol]):
            with cols[i]:
                st.metric(label, value, delta if delta else None)

        if len(kpis_preview) > ncol:
            cols2 = st.columns(len(kpis_preview) - ncol)
            for j, (label, value, delta) in enumerate(kpis_preview[ncol:]):
                with cols2[j]:
                    st.metric(label, value, delta if delta else None)

        # ── Commentary preview (cached) ────────────────────────────────────
        commentary = cached_sales_commentary(df, col_df, df_prev, period)
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

        unique_months = (
            df.groupby(["年份", "月份"]).ngroups
            if "年份" in df.columns and "月份" in df.columns
            else 1
        )
        is_single_month = unique_months == 1

        if generate:
            kpis = make_kpis(df, col_df, df_prev, col_prev)
            tables = sales_tables(df, is_single_month=is_single_month)
            tables += collection_tables(col_df)

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
                            period=period if quick != "全部" else period_sidebar,
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
                            period=period if quick != "全部" else period_sidebar,
                        )
                        st.success("Markdown 报告生成成功！")
                        st.download_button(
                            "⬇ 下载 Markdown 报告",
                            data=content.encode("utf-8"),
                            file_name=f"{filename_prefix}.md",
                            mime="text/markdown",
                            use_container_width=True,
                        )

                    else:
                        content = build_pdf(
                            title="销售分析报告",
                            kpis=kpis,
                            commentary=commentary,
                            tables=tables,
                            footer_note=footer,
                            period=period if quick != "全部" else period_sidebar,
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
        rc = raw_col(df)
        if search:
            results = df[
                df[rc].str.contains(search, case=False, na=False) |
                df["单据编号"].str.contains(search, case=False, na=False)
            ]
            st.markdown(f"找到 **{len(results)}** 条销售记录")
            st.dataframe(
                results.assign(
                    日期=lambda x: x["日期"].dt.strftime("%Y-%m-%d"),
                    合计=lambda x: x["合计$_clean"].apply(lambda v: f"${v:,.2f}"),
                )[["日期", "单据编号", rc, "商品名称_clean",
                   "合计", "箱数_clean", "账户"]]
                .rename(columns={"箱数_clean": "箱数"})
                .head(200),
                hide_index=True, use_container_width=True,
            )

            if not col_df.empty:
                col_raw = raw_col(col_df)
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
        rc = raw_col(df)
        sa = (
            df.groupby([rc, "账户"])
            .agg(销售美金=("合计$_clean", "sum"), 销售苏姆=("苏姆合计_clean", "sum"),
                 销售单数=("单据编号", "nunique"))
            .reset_index()
        )
        if not col_df.empty:
            col_raw = raw_col(col_df)
            ca = (
                col_df.groupby([col_raw, "账户"])
                .agg(收款美金=("美金_clean", "sum"), 收款苏姆=("苏姆_clean", "sum"))
                .reset_index()
            )
            rec = sa.merge(ca, left_on=[rc, "账户"], right_on=[col_raw, "账户"],
                          how="left").fillna(0)
            dup = (col_raw if col_raw != rc else rc) + "_x"
            if dup in rec.columns:
                rec = rec.drop(columns=[dup])
        else:
            rec = sa.copy()
            rec["收款美金"] = 0.0
            rec["收款苏姆"] = 0.0

        customers = [""] + sorted(rec[rc].unique().tolist())
        sel = st.selectbox("选择客户", customers, key="export_cust_stmt")

        if sel:
            cr = rec[rec[rc] == sel]
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
