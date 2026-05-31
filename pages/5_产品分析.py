# -*- coding: utf-8 -*-
"""产品分析页面 - Product Analysis."""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_pyecharts
from pyecharts import options as opts
from pyecharts.charts import Bar, Pie, Scatter, Line, HeatMap, Grid
from utils.helpers import check_data_loaded, get_filtered_sales
from utils.narrative_generator import generate_product_commentary

C = ["#4A90E2", "#50C878", "#FF6B6B", "#FFD93D", "#6BCB77",
     "#4D96FF", "#FF922B", "#CC5DE8", "#20C997", "#F06595"]


def _bar(x_data, y_data, name, color=C[0], rotate=0, label_fmt="${c}"):
    return (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis(
            name, [float(v) for v in y_data],
            itemstyle_opts=opts.ItemStyleOpts(color=color),
            label_opts=opts.LabelOpts(is_show=True, formatter=label_fmt,
                                     position="top", rotate=rotate),
        )
        .set_global_opts(
            tooltip_opts=opts.TooltipOpts(trigger="axis",
                                         formatter="{b}: ${c:,.0f}"),
            legend_opts=opts.LegendOpts(is_show=False),
            xaxis_opts=opts.AxisOpts(type_="category",
                                    axislabel_opts=opts.LabelOpts(rotate=rotate)),
            yaxis_opts=opts.AxisOpts(type_="value",
                                    splitline_opts=opts.SplitLineOpts(is_show=True)),
            datazoom_opts=opts.DataZoomOpts(),
        )
    )


def _bar_multi(x_data: list, series: list) -> Bar:
    """Multiple series bar chart."""
    chart = Bar().add_xaxis(x_data)
    colors = C[:len(series)]
    for i, (name, data) in enumerate(series):
        chart.add_yaxis(
            name,
            [float(v) for v in data],
            itemstyle_opts=opts.ItemStyleOpts(color=colors[i]),
            label_opts=opts.LabelOpts(is_show=False),
        )
    chart.set_global_opts(
        tooltip_opts=opts.TooltipOpts(trigger="axis",
                                     formatter="{b}: ${c:,.0f}"),
        legend_opts=opts.LegendOpts(is_show=True, pos_top="2%"),
        xaxis_opts=opts.AxisOpts(type_="category",
                                axislabel_opts=opts.LabelOpts(rotate=20)),
        yaxis_opts=opts.AxisOpts(type_="value",
                                splitline_opts=opts.SplitLineOpts(is_show=True)),
        datazoom_opts=opts.DataZoomOpts(),
    )
    return chart


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
        .add("", data_pairs, radius=radius or ["0%", "65%"],
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


def _scatter(x_data, y_data, name, color=C[5]):
    return (
        Scatter()
        .add_xaxis([float(v) for v in x_data])
        .add_yaxis(
            name, [float(v) for v in y_data],
            label_opts=opts.LabelOpts(is_show=True, formatter="${c}"),
        )
        .set_global_opts(
            tooltip_opts=opts.TooltipOpts(trigger="item",
                                         formatter="{a}<br/>${c}"),
            xaxis_opts=opts.AxisOpts(type_="value",
                                    splitline_opts=opts.SplitLineOpts(is_show=True)),
            yaxis_opts=opts.AxisOpts(type_="value",
                                    splitline_opts=opts.SplitLineOpts(is_show=True)),
        )
    )


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
                                         formatter="{b}<br/>{a}: ${c:,.0f}"),
            legend_opts=opts.LegendOpts(is_show=True),
            xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
            yaxis_opts=opts.AxisOpts(type_="value",
                                    splitline_opts=opts.SplitLineOpts(is_show=True)),
        )
    )


def _heatmap(df, x_col, y_col, val_col) -> HeatMap:
    """Build a pivot heatmap. Returns None if insufficient data."""
    if x_col not in df.columns or y_col not in df.columns:
        return None
    mask = (
        df[x_col].notna() & (df[x_col].astype(str).str.strip() != "") &
        df[y_col].notna() & (df[y_col].astype(str).str.strip() != "")
    )
    sub = df.loc[mask]
    if sub.empty:
        return None
    pivot = sub.groupby([x_col, y_col])[val_col].sum().reset_index()
    if pivot.empty:
        return None
    x_vals = sorted(pivot[x_col].unique())
    y_vals = sorted(pivot[y_col].unique())
    if len(x_vals) < 2 or len(y_vals) < 2:
        return None
    pivot["val"] = pivot[val_col].apply(float)
    rows = [[x_vals.index(r[x_col]), y_vals.index(r[y_col]), float(r["val"])]
            for r in pivot.to_dict(orient="records")]
    return (
        HeatMap()
        .add_xaxis(x_vals)
        .add_yaxis(
            "", y_vals, rows,
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(
            tooltip_opts=opts.TooltipOpts(trigger="item",
                                         formatter="{b} / {a}: ${c:,.0f}"),
            xaxis_opts=opts.AxisOpts(type_="category",
                                    splitarea_opts=opts.SplitAreaOpts(is_show=True),
                                    axislabel_opts=opts.LabelOpts(rotate=25)),
            yaxis_opts=opts.AxisOpts(type_="category",
                                    splitarea_opts=opts.SplitAreaOpts(is_show=True)),
            visualmap_opts=opts.VisualMapOpts(
                min_=float(pivot["val"].min()), max_=float(pivot["val"].max()),
                is_piecewise=False,
                is_calculable=True, orient="vertical", pos_right="2%",
                pos_top="center",
                range_color=["#D6E8F7", "#2E6DA4", "#1B3A5C"],
            ),
        )
    )


def render():
    check_data_loaded()
    st.title("📦 产品分析")

    df = get_filtered_sales()
    if df.empty:
        st.warning("当前筛选条件下无销售数据")
        return

    period = "当前筛选周期"
    commentary = generate_product_commentary(df, period_label=period)

    with st.expander("📝 AI 分析批语", expanded=True):
        st.markdown(f"<div style='padding:12px 16px; background:#F5F7FA;"
                    f" border-left:4px solid #4D96FF; border-radius:4px;"
                    f" font-size:14px; line-height:1.7; color:#34495E;'>{commentary}</div>",
                    unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📦 整体产品分析", "👤 单客户产品分析"])

    with tab1:
        top_n = st.slider("显示前N名SKU", 5, 50, 15, key="prod_top_n")

        st.subheader("SKU销售排名")
        bp = (
            df.groupby("商品名称_clean")
            .agg(
                销售美金=("合计$_clean", "sum"),
                销售苏姆=("苏姆合计_clean", "sum"),
                总箱数=("箱数_clean", "sum"),
                销售次数=("单据编号", "nunique"),
            )
            .reset_index()
            .sort_values("销售美金", ascending=False)
        )
        h = max(400, top_n * 32)
        st_pyecharts(
            _bar(list(bp.head(top_n).iloc[::-1]["商品名称_clean"]),
                 list(bp.head(top_n).iloc[::-1]["销售美金"]),
                 "销售美金 ($)", color=C[5], rotate=25, label_fmt="${c:,.0f}"),
            height=f"{h}px"
        )

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**箱数 vs 销售美金 散点图**")
            scat = _scatter(
                list(bp.head(top_n)["总箱数"]),
                list(bp.head(top_n)["销售美金"]),
                "销售美金 ($)"
            )
            st_pyecharts(scat, height="320px")
        with c2:
            st.markdown("**购买频次 vs 销售美金 散点图**")
            scat2 = _scatter(
                list(bp.head(top_n)["销售次数"]),
                list(bp.head(top_n)["销售美金"]),
                "销售美金 ($)", color=C[7]
            )
            st_pyecharts(scat2, height="320px")

        # Category
        st.subheader("按产品类别分析")
        bc = (
            df.groupby("类别")
            .agg(销售美金=("合计$_clean", "sum"), 总箱数=("箱数_clean", "sum"))
            .reset_index()
            .sort_values("销售美金", ascending=False)
        )
        if bc.empty or bc["类别"].isna().all():
            st.info("暂无产品类别数据")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st_pyecharts(_pie(_top_pie_data(bc, "类别", "销售美金"), radius=["15%", "65%"]), height="380px")
            with c2:
                st_pyecharts(
                    _bar(list(bc["类别"]), list(bc["销售美金"]),
                         "销售美金 ($)", color=C[0], rotate=20),
                    height="380px"
                )

        # Heatmap: 类别 × 账户
        if "账户" in df.columns:
            st.subheader("类别 × 账户 销售热力图")
            hm = _heatmap(df, "类别", "账户", "合计$_clean")
            if hm:
                st_pyecharts(hm, height="400px")
            else:
                st.info("数据不足以生成热力图")

        # Category stacked bar: top categories over time
        st.subheader("主要类别月度趋势")
        top_cats = bc.head(5)["类别"].tolist()
        mt = (
            df[df["类别"].isin(top_cats)]
            .groupby(["年份", "月份", "类别"])["合计$_clean"].sum()
            .reset_index()
        )
        mt["年月"] = (mt["年份"].astype(str) + "-" +
                    mt["月份"].astype(str).str.zfill(2))
        mt = mt.sort_values(["年份", "月份"])

        # Build stacked bar
        x_vals = sorted(mt["年月"].unique())
        series_data = []
        for cat in top_cats:
            vals = []
            for ym in x_vals:
                v = mt[(mt["年月"] == ym) & (mt["类别"] == cat)]["合计$_clean"].sum()
                vals.append(float(v))
            series_data.append((cat, vals))

        stacked = (
            Bar(init_opts=opts.InitOpts(width="100%", height="380px"))
            .add_xaxis(x_vals)
        )
        for i, (cat, vals) in enumerate(series_data):
            stacked.add_yaxis(
                cat,
                vals,
                stack="stack1",
                itemstyle_opts=opts.ItemStyleOpts(color=C[i]),
                label_opts=opts.LabelOpts(is_show=False),
            )
        stacked.set_global_opts(
            tooltip_opts=opts.TooltipOpts(trigger="axis",
                                         formatter="{b}<br/>{a}: ${c:,.0f}"),
            legend_opts=opts.LegendOpts(is_show=True, pos_top="2%"),
            xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False,
                                    axislabel_opts=opts.LabelOpts(rotate=15)),
            yaxis_opts=opts.AxisOpts(type_="value",
                                    splitline_opts=opts.SplitLineOpts(is_show=True)),
        )
        st_pyecharts(stacked, height="400px")

        # Price volatility
        st.subheader("单价波动分析")
        ps = (
            df.groupby("商品名称_clean")
            .agg(
                平均单价=("单价$_clean", "mean"),
                最低单价=("单价$_clean", "min"),
                最高单价=("单价$_clean", "max"),
                销售美金=("合计$_clean", "sum"),
            )
            .reset_index()
            .sort_values("销售美金", ascending=False)
        )
        ps["波动额"] = ps["最高单价"] - ps["最低单价"]
        ps["波动率"] = ps.apply(
            lambda r: r["波动额"] / r["最低单价"] * 100
            if r["最低单价"] > 0 else 0, axis=1)

        volatile = ps[ps["波动率"] > 10].sort_values("波动率", ascending=False)
        if not volatile.empty:
            st.markdown(f"**单价波动超过10%的产品：{len(volatile)} 个**")
            h2 = max(300, min(len(volatile), 20) * 32)
            st_pyecharts(
                _bar(list(volatile.head(20).iloc[::-1]["商品名称_clean"]),
                     list(volatile.head(20).iloc[::-1]["波动率"]),
                     "波动率 (%)", color=C[3], label_fmt="{c}%"),
                height=f"{h2}px"
            )

        # Color / Grade
        if "色号" in df.columns:
            st.subheader("色号分析")
            bcolor = (
                df[df["色号"].notna() & (df["色号"] != "")]
                .groupby("色号")["合计$_clean"].sum()
                .sort_values(ascending=False).head(15)
                .reset_index()
            )
            st_pyecharts(
                _bar(list(bcolor.iloc[::-1]["色号"]),
                     list(bcolor.iloc[::-1]["合计$_clean"]),
                     "销售美金 ($)", color=C[8]),
                height=max(300, len(bcolor) * 32)
            )

        st.subheader("等级分析")
        if "等级" in df.columns:
            bgrade = (
                df[df["等级"].notna() & (df["等级"] != "")]
                .groupby("等级")["合计$_clean"].sum()
                .sort_values(ascending=False).reset_index()
            )
            if not bgrade.empty:
                c1, c2 = st.columns(2)
                with c1:
                    st_pyecharts(_pie(_top_pie_data(bgrade, "等级", "合计$_clean")), height="320px")
                with c2:
                    st.dataframe(
                        bgrade.assign(
                            销售美金=lambda x: x["合计$_clean"].apply(
                                lambda v: f"${v:,.0f}")),
                        hide_index=True, use_container_width=True,
                    )

    with tab2:
        st.subheader("单客户产品分析")
        sel = st.selectbox(
            "选择客户",
            [""] + sorted(df["客户名称_clean"].unique().tolist()),
            key="prod_cust_sel"
        )
        if sel:
            cdf = df[df["客户名称_clean"] == sel]
            cp = (
                cdf.groupby("商品名称_clean")
                .agg(销售美金=("合计$_clean", "sum"),
                     累计箱数=("箱数_clean", "sum"),
                     购买次数=("单据编号", "nunique"))
                .reset_index()
                .sort_values("销售美金", ascending=False)
            )
            top15 = cp.head(15)
            h3 = max(300, len(top15) * 32)
            st_pyecharts(
                _bar(list(top15.iloc[::-1]["商品名称_clean"]),
                     list(top15.iloc[::-1]["销售美金"]),
                     "销售美金 ($)", color=C[9]),
                height=f"{h3}px"
            )

            c1, c2 = st.columns(2)
            with c1:
                scat_c = _scatter(
                    list(cp["购买次数"]),
                    list(cp["销售美金"]),
                    "销售美金 ($)", color=C[5]
                )
                st_pyecharts(scat_c, height="300px")
            with c2:
                st.dataframe(
                    cp.assign(
                        销售美金=lambda x: x["销售美金"].apply(lambda v: f"${v:,.0f}"),
                    ),
                    hide_index=True, use_container_width=True,
                )


render()
