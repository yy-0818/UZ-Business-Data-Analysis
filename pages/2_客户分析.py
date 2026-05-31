# -*- coding: utf-8 -*-
"""客户分析页面 - Customer Analysis."""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_pyecharts
from pyecharts import options as opts
from pyecharts.charts import Line, Bar, Pie, Scatter, Grid
from utils.helpers import check_data_loaded, get_filtered_sales, get_filtered_collection

C = ["#4A90E2", "#50C878", "#FF6B6B", "#FFD93D", "#6BCB77",
     "#4D96FF", "#FF922B", "#CC5DE8", "#20C997", "#F06595"]


def _smooth_line(x_data, y_data, name, color=C[0]):
    return (
        Line()
        .add_xaxis(x_data)
        .add_yaxis(
            name, [float(v) for v in y_data],
            is_smooth=True,
            linestyle_opts=opts.LineStyleOpts(color=color, width=3),
            itemstyle_opts=opts.ItemStyleOpts(color=color),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_series_opts(
            areastyle_opts=opts.AreaStyleOpts(opacity=0.08, color=color),
        )
        .set_global_opts(
            tooltip_opts=opts.TooltipOpts(trigger="axis",
                                         formatter="{b}<br/>{a}: ${c}"),
            legend_opts=opts.LegendOpts(is_show=True),
            xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
            yaxis_opts=opts.AxisOpts(type_="value",
                                    splitline_opts=opts.SplitLineOpts(is_show=True)),
        )
    )


def _bar_h(x_data, y_data, name, color=C[0], label_fmt="${c}"):
    return (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis(
            name, [float(v) for v in y_data],
            itemstyle_opts=opts.ItemStyleOpts(color=color),
            label_opts=opts.LabelOpts(is_show=True, formatter=label_fmt,
                                     position="top", rotate=0),
        )
        .set_global_opts(
            tooltip_opts=opts.TooltipOpts(trigger="axis",
                                         formatter="{b}: ${c}"),
            legend_opts=opts.LegendOpts(is_show=False),
            xaxis_opts=opts.AxisOpts(type_="category",
                                    axislabel_opts=opts.LabelOpts(rotate=25)),
            yaxis_opts=opts.AxisOpts(type_="value",
                                    splitline_opts=opts.SplitLineOpts(is_show=True)),
            datazoom_opts=opts.DataZoomOpts(),
        )
    )


def _top_pie_data(df_grouped, label_col, value_col, n=8):
    """Return top-n pairs + group rest as 其他."""
    top = df_grouped.sort_values(value_col, ascending=False).head(n)
    rest = df_grouped.sort_values(value_col, ascending=False).iloc[n:]
    pairs = [[row[label_col], float(row[value_col])]
             for row in top.to_dict(orient="records")]
    if not rest.empty:
        rest_sum = float(rest[value_col].sum())
        if rest_sum > 0:
            pairs.append(["其他", rest_sum])
    return pairs


def _pie(data_pairs, radius=None):
    return (
        Pie()
        .add("", data_pair=data_pairs, radius=radius or ["0%", "65%"],
             label_opts=opts.LabelOpts(is_show=True, formatter="{b}: {d}%"))
        .set_global_opts(
            tooltip_opts=opts.TooltipOpts(trigger="item",
                                         formatter="{b}: ${c} ({d}%)"),
            legend_opts=opts.LegendOpts(is_show=True, pos_left="2%"),
        )
        .set_series_opts(
            itemstyle_opts=opts.ItemStyleOpts(border_color="#fff", border_width=1)
        )
    )


def _scatter(x_data, y_data, name, color=C[0]):
    return (
        Scatter()
        .add_xaxis([float(v) for v in x_data])
        .add_yaxis(
            name, [float(v) for v in y_data],
            label_opts=opts.LabelOpts(is_show=True, formatter="${c}"),
        )
        .set_global_opts(
            tooltip_opts=opts.TooltipOpts(trigger="item",
                                         formatter="{a}<br/>{c}"),
            xaxis_opts=opts.AxisOpts(type_="value", name="X",
                                    splitline_opts=opts.SplitLineOpts(is_show=True)),
            yaxis_opts=opts.AxisOpts(type_="value", name="Y ($)",
                                    splitline_opts=opts.SplitLineOpts(is_show=True)),
        )
    )


def render():
    check_data_loaded()
    st.title("👥 客户分析")

    sales_df = get_filtered_sales()
    col_df = get_filtered_collection()

    if sales_df.empty:
        st.warning("当前筛选条件下无销售数据")
        return

    # Use raw 客户名称 for display, 客户类别 for category grouping
    raw_name_col = "客户名称" if "客户名称" in sales_df.columns else "客户名称_clean"
    has_category = (
        "客户类别" in sales_df.columns
        and not sales_df["客户类别"].isna().all()
        and (sales_df["客户类别"] != "未分类").any()
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 类别总览", "👤 客户画像", "📈 单客户趋势", "🛒 常购产品"]
    )

    # ── Tab 1: 类别总览 ──────────────────────────────────────────────────────
    with tab1:
        if has_category:
            # Category summary
            by_cat = (
                sales_df.groupby("客户类别")
                .agg(
                    销售美金=("合计$_clean", "sum"),
                    销售苏姆=("苏姆合计_clean", "sum"),
                    客户数=("客户名称", pd.Series.nunique),
                    销售单数=("单据编号", "nunique"),
                )
                .reset_index()
                .sort_values("销售美金", ascending=False)
            )

            c1, c2 = st.columns(2)
            with c1:
                st_pyecharts(
                    _pie(_top_pie_data(by_cat, "客户类别", "销售美金")),
                    height="380px"
                )
            with c2:
                st.markdown("**类别销售排名**")
                st.dataframe(
                    by_cat.assign(
                        销售美金=lambda x: x["销售美金"].apply(lambda v: f"${v:,.0f}"),
                    ),
                    hide_index=True, use_container_width=True,
                )

            # Per-category monthly trend
            st.subheader("各类别月度趋势")
            top_cats = by_cat["客户类别"].head(5).tolist()
            monthly_cat = (
                sales_df[sales_df["客户类别"].isin(top_cats)]
                .groupby(["年份", "月份", "客户类别"])["合计$_clean"].sum()
                .reset_index()
            )
            monthly_cat["年月"] = (
                monthly_cat["年份"].astype(str) + "-" +
                monthly_cat["月份"].astype(str).str.zfill(2)
            )
            monthly_cat = monthly_cat.sort_values(["年份", "月份"])

            # Build stacked bar (all series in one Bar for stacking)
            if not monthly_cat.empty:
                ym_list = sorted(monthly_cat["年月"].unique())
                cat_colors = {cat: C[i % len(C)] for i, cat in enumerate(top_cats)}

                bar_chart = Bar()
                for i, cat in enumerate(top_cats):
                    y_vals = []
                    for ym in ym_list:
                        row = monthly_cat[(monthly_cat["年月"] == ym) & (monthly_cat["客户类别"] == cat)]
                        y_vals.append(float(row["合计$_clean"].sum()) if not row.empty else 0.0)
                    bar_chart.add_yaxis(
                        cat, y_vals,
                        stack=f"stack_1",
                        itemstyle_opts=opts.ItemStyleOpts(color=cat_colors[cat]),
                        label_opts=opts.LabelOpts(is_show=False),
                    )
                bar_chart.set_global_opts(
                    legend_opts=opts.LegendOpts(is_show=True, pos_top="2%"),
                    xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
                    yaxis_opts=opts.AxisOpts(type_="value",
                                            splitline_opts=opts.SplitLineOpts(is_show=True)),
                    tooltip_opts=opts.TooltipOpts(trigger="axis",
                                                 formatter="{b}<br/>{a}: ${c:,.0f}"),
                )
                st_pyecharts(bar_chart, height="420px")

            # Per-category detail table
            st.subheader("类别明细")
            st.dataframe(
                by_cat.assign(
                    销售美金=lambda x: x["销售美金"].apply(lambda v: f"${v:,.0f}"),
                    销售苏姆=lambda x: x["销售苏姆"].apply(lambda v: f"₴{v:,.0f}"),
                    销售单数=lambda x: x["销售单数"].apply(lambda v: f"{int(v):,}"),
                    客户数=lambda x: x["客户数"].apply(lambda v: f"{int(v)}"),
                ),
                hide_index=True, use_container_width=True,
            )
        else:
            st.info("请上传客户主数据（contract_customers.xlsx）以查看类别分析")

    # ── Tab 2: 客户画像 ──────────────────────────────────────────────────────
    with tab2:
        # Per-customer summary grouped by category
        cs = (
            sales_df.groupby(raw_name_col)
            .agg(
                销售美金=("合计$_clean", "sum"),
                销售苏姆=("苏姆合计_clean", "sum"),
                销售单数=("单据编号", "nunique"),
                账户类型=("账户", lambda x: ", ".join(sorted(x.unique()))),
                总箱数=("箱数_clean", "sum"),
                客户类别=("客户类别", "first"),
            )
            .reset_index()
            .sort_values("销售美金", ascending=False)
        )
        if has_category:
            cs["客户类别"] = cs["客户类别"].fillna("未分类")

        if not col_df.empty:
            col_name_col = "客户名称" if "客户名称" in col_df.columns else "客户名称_clean"
            col_by = col_df.groupby(col_name_col)["美金_clean"].sum().reset_index()
            col_by.columns = [raw_name_col, "收款美金"]
            cs = cs.merge(col_by, on=raw_name_col, how="left")
            cs["收款美金"] = cs["收款美金"].fillna(0)

        st.subheader("客户销售贡献分布")
        c1, c2 = st.columns(2)
        with c1:
            st_pyecharts(_pie(_top_pie_data(cs, raw_name_col, "销售美金")), height="380px")
        with c2:
            display_cols = [raw_name_col, "销售美金", "收款美金", "销售单数"]
            if has_category:
                display_cols.insert(1, "客户类别")
            st.markdown("**客户销售排名 TOP15**")
            st.dataframe(
                cs.head(15).assign(
                    销售美金=lambda x: x["销售美金"].apply(lambda v: f"${float(v):,.0f}"),
                    收款美金=lambda x: x["收款美金"].apply(
                        lambda v: f"${float(v):,.0f}" if pd.notna(v) else "$—"),
                )[display_cols],
                hide_index=True, use_container_width=True,
            )

        st.subheader("客户完整列表")
        all_cols = [raw_name_col, "销售美金", "收款美金", "销售单数", "账户类型"]
        if has_category:
            all_cols.insert(1, "客户类别")
        st.dataframe(
            cs.assign(
                销售美金=lambda x: x["销售美金"].apply(lambda v: f"${float(v):,.2f}"),
                收款美金=lambda x: x["收款美金"].apply(
                    lambda v: f"${float(v):,.2f}" if pd.notna(v) else "$—"),
            )[all_cols],
            hide_index=True, use_container_width=True,
        )

    # ── Tab 3: 单客户趋势 ───────────────────────────────────────────────────
    with tab3:
        st.subheader("选择客户查看月度趋势")
        customers = [""] + sorted(sales_df[raw_name_col].unique().tolist())
        sel = st.selectbox("客户", customers, key="trend_cust")

        if sel:
            cust_s = (
                sales_df[sales_df[raw_name_col] == sel]
                .groupby(["年份", "月份"])
                .agg(销售美金=("合计$_clean", "sum"),
                     销售单数=("单据编号", "nunique"))
                .reset_index()
            )
            cust_s["年月"] = (cust_s["年份"].astype(str) + "-" +
                             cust_s["月份"].astype(str).str.zfill(2))
            cust_s = cust_s.sort_values(["年份", "月份"])

            line_c = (
                Line()
                .add_xaxis(list(cust_s["年月"]))
                .add_yaxis(
                    "销售美金 ($)",
                    [float(v) for v in cust_s["销售美金"]],
                    is_smooth=True,
                    linestyle_opts=opts.LineStyleOpts(color=C[0], width=3),
                    itemstyle_opts=opts.ItemStyleOpts(color=C[0]),
                    label_opts=opts.LabelOpts(is_show=False),
                )
                .set_global_opts(
                    tooltip_opts=opts.TooltipOpts(trigger="axis",
                                                 formatter="{b}<br/><span style='color:#4A90E2'>●</span> 销售美金: ${c:,.0f}"),
                    legend_opts=opts.LegendOpts(is_show=True),
                    xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
                    yaxis_opts=opts.AxisOpts(type_="value",
                                            splitline_opts=opts.SplitLineOpts(is_show=True)),
                )
            )
            bar_c = (
                Bar()
                .add_xaxis(list(cust_s["年月"]))
                .add_yaxis(
                    "销售单数",
                    [float(v) for v in cust_s["销售单数"]],
                    itemstyle_opts=opts.ItemStyleOpts(color=C[1], opacity=0.6),
                    label_opts=opts.LabelOpts(is_show=False),
                )
                .set_global_opts(
                    tooltip_opts=opts.TooltipOpts(trigger="axis",
                                                 formatter="{b}<br/><span style='color:#50C878'>■</span> 单数: {c}"),
                    legend_opts=opts.LegendOpts(is_show=True),
                    xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
                    yaxis_opts=opts.AxisOpts(type_="value"),
                )
            )
            grid = Grid(init_opts=opts.InitOpts(width="100%", height="380px"))
            grid.add(line_c,
                     grid_opts=opts.GridOpts(pos_left="8%", pos_right="8%",
                                            pos_top="15%", pos_bottom="15%"))
            grid.add(bar_c,
                     grid_opts=opts.GridOpts(pos_left="8%", pos_right="8%",
                                            pos_top="60%", pos_bottom="5%"))
            st_pyecharts(grid, height="400px")

            # scatter
            cust_detail = sales_df[sales_df[raw_name_col] == sel]
            if "单价$_clean" in cust_detail.columns and not cust_detail.empty:
                scat_data = cust_detail.dropna(subset=["单价$_clean", "箱数_clean"])
                if not scat_data.empty:
                    st.markdown("**单价 vs 箱数 散点图**")
                    scat = _scatter(
                        list(scat_data["箱数_clean"]),
                        list(scat_data["合计$_clean"]),
                        "订单金额", color=C[5]
                    )
                    st_pyecharts(scat, height="320px")

            # collection trend
            col_name_col = "客户名称" if "客户名称" in col_df.columns else "客户名称_clean"
            if not col_df.empty and sel in col_df[col_name_col].values:
                col_sel = (
                    col_df[col_df[col_name_col] == sel]
                    .groupby(["年份", "月份"])["美金_clean"].sum().reset_index()
                )
                col_sel["年月"] = (col_sel["年份"].astype(str) + "-" +
                                  col_sel["月份"].astype(str).str.zfill(2))
                col_sel = col_sel.sort_values(["年份", "月份"])
                if not col_sel.empty:
                    st.markdown("**收款趋势**")
                    line_col = _smooth_line(
                        list(col_sel["年月"]),
                        list(col_sel["美金_clean"]),
                        "收款美金 ($)", color=C[1]
                    )
                    st_pyecharts(line_col, height="280px")

    # ── Tab 4: 常购产品 ──────────────────────────────────────────────────────
    with tab4:
        st.subheader("常购产品分析")
        customers_prod = [""] + sorted(sales_df[raw_name_col].unique().tolist())
        sel2 = st.selectbox("选择客户", customers_prod, key="prod_cust")
        if sel2:
            cp = (
                sales_df[sales_df[raw_name_col] == sel2]
                .groupby("商品名称_clean")
                .agg(销售美金=("合计$_clean", "sum"),
                     累计箱数=("箱数_clean", "sum"),
                     购买次数=("单据编号", "nunique"))
                .reset_index()
                .sort_values("销售美金", ascending=False)
            )
            top15 = cp.head(15)
            h = max(300, len(top15) * 32)
            st_pyecharts(
                _bar_h(list(top15.iloc[::-1]["商品名称_clean"]),
                       list(top15.iloc[::-1]["销售美金"]),
                       "销售美金 ($)", color=C[7]),
                height=f"{h}px"
            )
            st.dataframe(
                cp.assign(
                    销售美金=lambda x: x["销售美金"].apply(lambda v: f"${v:,.0f}"),
                ),
                hide_index=True, use_container_width=True,
            )


render()
