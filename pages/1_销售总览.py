# -*- coding: utf-8 -*-
"""销售总览页面 - Sales Overview."""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_pyecharts
from pyecharts import options as opts
from pyecharts.charts import Line, Bar, Pie, Grid, HeatMap
from pyecharts.components import Table
from utils.helpers import check_data_loaded, get_filtered_sales, get_filtered_collection
from utils.narrative_generator import generate_sales_commentary


# ── Color palette ──────────────────────────────────────────────────────────────
C = ["#4A90E2", "#50C878", "#FF6B6B", "#FFD93D", "#6BCB77",
     "#4D96FF", "#FF922B", "#CC5DE8", "#20C997", "#F06595"]


def _base_tooltip() -> opts.TooltipOpts:
    return opts.TooltipOpts(trigger="axis", is_show=True,
                            trigger_on="mousemove|click",
                            formatter="{b}: ${c}")


def _base_legend(show: bool = True, pos: str = "top") -> opts.LegendOpts:
    kw = {"is_show": show}
    if pos == "left":
        kw["pos_left"] = "2%"
    elif pos == "top":
        kw["pos_top"] = "2%"
    elif pos == "right":
        kw["pos_right"] = "2%"
    elif pos == "bottom":
        kw["pos_bottom"] = "2%"
    return opts.LegendOpts(**kw)


def _smooth_line(x_data: list, y_data: list, name: str,
                  color: str = C[0]) -> Line:
    return (
        Line()
        .add_xaxis(x_data)
        .add_yaxis(
            name,
            [float(v) for v in y_data],
            is_smooth=True,
            linestyle_opts=opts.LineStyleOpts(color=color, width=3),
            itemstyle_opts=opts.ItemStyleOpts(color=color),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_series_opts(
            areastyle_opts=opts.AreaStyleOpts(opacity=0.08, color=color),
        )
        .set_global_opts(
            tooltip_opts=_base_tooltip(),
            legend_opts=_base_legend(),
            xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
            yaxis_opts=opts.AxisOpts(type_="value", splitline_opts=opts.SplitLineOpts(is_show=True)),
        )
    )


def _bar(x_data: list, y_data: list, name: str,
         color: str = C[1], rotate: int = 0,
         label_fmt: str = "${c}") -> Bar:
    return (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis(
            name,
            [float(v) for v in y_data],
            itemstyle_opts=opts.ItemStyleOpts(color=color),
            label_opts=opts.LabelOpts(is_show=True, formatter=label_fmt,
                                     position="top", rotate=rotate),
        )
        .set_global_opts(
            tooltip_opts=_base_tooltip(),
            legend_opts=_base_legend(show=False),
            xaxis_opts=opts.AxisOpts(type_="category",
                                    axislabel_opts=opts.LabelOpts(rotate=rotate)),
            yaxis_opts=opts.AxisOpts(type_="value",
                                    splitline_opts=opts.SplitLineOpts(is_show=True)),
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


def _pie(data_pairs: list, radius: list = None) -> Pie:
    return (
        Pie()
        .add(
            series_name="",
            data_pair=data_pairs,
            radius=radius or ["0%", "65%"],
            label_opts=opts.LabelOpts(is_show=True, formatter="{b}: {d}%"),
        )
        .set_global_opts(
            tooltip_opts=opts.TooltipOpts(trigger="item",
                                         formatter="{b}: ${c} ({d}%)"),
            legend_opts=_base_legend(pos="left", show=False),
        )
        .set_series_opts(
            itemstyle_opts=opts.ItemStyleOpts(
                border_color="#fff", border_width=1
            )
        )
    )


def _composite_trend(ym_data: list, usd_data: list, box_data: list,
                      order_data: list) -> Grid:
    """Overlay smooth line + grouped bars on the same x-axis."""
    line = (
        Line()
        .add_xaxis(ym_data)
        .add_yaxis(
            "销售美金 ($)",
            [float(v) for v in usd_data],
            is_smooth=True,
            linestyle_opts=opts.LineStyleOpts(color=C[0], width=3),
            itemstyle_opts=opts.ItemStyleOpts(color=C[0]),
            label_opts=opts.LabelOpts(is_show=False),
            z=2,
        )
        .add_yaxis(
            "销售单数",
            [float(v) for v in order_data],
            linestyle_opts=opts.LineStyleOpts(color=C[3], width=2, type_="dashed"),
            itemstyle_opts=opts.ItemStyleOpts(color=C[3]),
            label_opts=opts.LabelOpts(is_show=False),
            z=1,
        )
        .set_global_opts(
            legend_opts=_base_legend(pos="top"),
            xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
            yaxis_opts=opts.AxisOpts(type_="value",
                                    splitline_opts=opts.SplitLineOpts(is_show=True)),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                formatter="{b}<br/><span style='color:#4A90E2'>●</span> 销售美金: ${c0:,.0f}<br/><span style='color:#FFD93D'>●</span> 销售单数: {c1}",
            ),
        )
    )

    bar_chart = (
        Bar()
        .add_xaxis(ym_data)
        .add_yaxis(
            "销售箱数",
            [float(v) for v in box_data],
            itemstyle_opts=opts.ItemStyleOpts(color=C[1], opacity=0.7),
            label_opts=opts.LabelOpts(is_show=False),
            bar_width="40%",
        )
        .set_global_opts(
            legend_opts=_base_legend(pos="top"),
            xaxis_opts=opts.AxisOpts(type_="category", boundary_gap=False),
            yaxis_opts=opts.AxisOpts(type_="value"),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                formatter="{b}<br/><span style='color:#50C878'>■</span> 销售箱数: {c}",
            ),
        )
    )

    grid = Grid(init_opts=opts.InitOpts(width="100%", height="420px"))
    grid.add(
        line,
        grid_opts=opts.GridOpts(pos_left="8%", pos_right="2%", pos_top="15%", pos_bottom="15%"),
    )
    grid.add(
        bar_chart,
        grid_opts=opts.GridOpts(pos_left="8%", pos_right="2%", pos_top="60%", pos_bottom="5%"),
    )
    return grid


def _heatmap_pivot(data: pd.DataFrame, x_col: str, y_col: str,
                   val_col: str) -> HeatMap:
    """Build a pivot heatmap. Returns None if there is no valid data."""
    if x_col not in data.columns or y_col not in data.columns:
        return None
    mask = (
        data[x_col].notna() & (data[x_col].astype(str).str.strip() != "") &
        data[y_col].notna() & (data[y_col].astype(str).str.strip() != "")
    )
    sub = data.loc[mask]
    if sub.empty:
        return None
    pivot = sub.groupby([x_col, y_col])[val_col].sum().reset_index()
    if pivot.empty:
        return None
    x_vals = sorted(pivot[x_col].unique())
    y_vals = sorted(pivot[y_col].unique())
    pivot["val"] = pivot[val_col].apply(lambda x: float(x))
    rows = pivot[[x_col, y_col, "val"]].values.tolist()
    return (
        HeatMap()
        .add_xaxis(x_vals)
        .add_yaxis(
            "",
            y_vals,
            [[x_vals.index(r[0]), y_vals.index(r[1]), r[2]] for r in rows],
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(
            tooltip_opts=opts.TooltipOpts(
                trigger="item",
                formatter="{b} / {a}: ${c:,.0f}",
            ),
            xaxis_opts=opts.AxisOpts(type_="category", splitarea_opts=opts.SplitAreaOpts(is_show=True),
                                    axislabel_opts=opts.LabelOpts(rotate=30)),
            yaxis_opts=opts.AxisOpts(type_="category", splitarea_opts=opts.SplitAreaOpts(is_show=True)),
            visualmap_opts=opts.VisualMapOpts(
                min_=float(pivot["val"].min()), max_=float(pivot["val"].max()),
                is_piecewise=False,
                is_calculable=True, orient="vertical", pos_right="2%", pos_top="center",
                range_color=["#D6E8F7", "#2E6DA4", "#1B3A5C"],
            ),
        )
    )


def render():
    check_data_loaded()
    st.title("📈 销售总览")

    df = get_filtered_sales()
    if df.empty:
        st.warning("当前筛选条件下无销售数据")
        return

    period = "当前筛选周期"
    col_df = get_filtered_collection()
    commentary = generate_sales_commentary(df, period_label=period, col_df=col_df)

    with st.expander("📝 AI 分析批语", expanded=True):
        st.markdown(commentary)

    tab1, tab2, tab3 = st.tabs(
        ["📊 趋势分析", "🏷️ 分类分析", "🏆 TOP排名"]
    )

    # ── Prepare monthly data ─────────────────────────────────────────────────
    monthly = (
        df.groupby(["年份", "月份"])
        .agg(销售美金=("合计$_clean", "sum"),
             销售苏姆=("苏姆合计_clean", "sum"),
             销售单数=("单据编号", "nunique"),
             销售箱数=("箱数_clean", "sum"))
        .reset_index()
    )
    monthly["年月"] = (monthly["年份"].astype(str) + "-" +
                      monthly["月份"].astype(str).str.zfill(2))
    monthly = monthly.sort_values(["年份", "月份"])

    with tab1:
        st.subheader("月度销售趋势（平滑折线 + 柱状叠加）")

        grid_chart = _composite_trend(
            list(monthly["年月"]),
            list(monthly["销售美金"]),
            list(monthly["销售箱数"]),
            list(monthly["销售单数"]),
        )
        st_pyecharts(grid_chart, height="440px")

        # Side-by-side detail
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**销售美金趋势**")
            line_usd = _smooth_line(list(monthly["年月"]), list(monthly["销售美金"]),
                                    "销售美金 ($)", color=C[0])
            st_pyecharts(line_usd, height="300px")
        with c2:
            st.markdown("**销售苏姆趋势**")
            line_som = _smooth_line(list(monthly["年月"]), list(monthly["销售苏姆"]),
                                    "销售苏姆 (₴)", color=C[2])
            st_pyecharts(line_som, height="300px")

        st.subheader("月度汇总表")
        st.dataframe(
            monthly[["年月", "销售单数", "销售箱数", "销售美金", "销售苏姆"]]
            .assign(销售美金=lambda x: x["销售美金"].apply(lambda v: f"${v:,.2f}")),
            hide_index=True, use_container_width=True,
        )

    with tab2:
        st.subheader("按账户类型")
        by_acc = (
            df.groupby("账户")
            .agg(销售美金=("合计$_clean", "sum"), 销售苏姆=("苏姆合计_clean", "sum"),
                 销售单数=("单据编号", "nunique"))
            .reset_index()
        )
        c1, c2 = st.columns(2)
        with c1:
            st_pyecharts(_pie(_top_pie_data(by_acc, "账户", "销售美金")), height="350px")
        with c2:
            st_pyecharts(
                _bar(list(by_acc["账户"]), list(by_acc["销售美金"]),
                     "销售美金 ($)", color=C[0]),
                height="350px"
            )

        st.subheader("按产品类别")
        by_cat = (
            df.groupby("类别")
            .agg(销售美金=("合计$_clean", "sum"), 销售苏姆=("苏姆合计_clean", "sum"))
            .reset_index()
            .sort_values("销售美金", ascending=False)
        )
        if by_cat.empty or by_cat["类别"].isna().all():
            st.info("暂无产品类别数据")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st_pyecharts(_pie(_top_pie_data(by_cat, "类别", "销售美金"), radius=["20%", "65%"]), height="350px")
            with c2:
                st_pyecharts(
                    _bar(list(by_cat.head(10)["类别"]),
                         list(by_cat.head(10)["销售美金"]),
                         "销售美金 ($)", color=C[4], rotate=20),
                    height="350px"
                )

        # Heatmap: 类别 × 账户
        st.subheader("类别 × 账户 热力图")
        hm = _heatmap_pivot(df, "类别", "账户", "合计$_clean")
        if hm:
            st_pyecharts(hm, height="400px")
        else:
            st.info("数据不足以生成热力图")

        st.subheader("按产品等级")
        by_grade = (
            df.groupby("等级")
            .agg(销售美金=("合计$_clean", "sum"))
            .reset_index()
            .sort_values("销售美金", ascending=False)
        )
        if not by_grade.empty and by_grade["等级"].notna().any():
            c1, c2 = st.columns(2)
            with c1:
                st_pyecharts(_pie(_top_pie_data(by_grade, "等级", "销售美金")), height="300px")
            with c2:
                st.dataframe(
                    by_grade.assign(销售美金=lambda x: x["销售美金"].apply(lambda v: f"${v:,.2f}")),
                    hide_index=True, use_container_width=True,
                )
        else:
            st.info("暂无等级数据")

    with tab3:
        top_n = st.slider("显示前N名", 5, 50, 10, key="top_n_sales")

        st.subheader("客户TOP排名")
        by_cust = (
            df.groupby("客户名称_clean")
            .agg(销售美金=("合计$_clean", "sum"), 销售苏姆=("苏姆合计_clean", "sum"),
                 销售单数=("单据编号", "nunique"))
            .reset_index()
            .sort_values("销售美金", ascending=False)
        )
        h = max(400, top_n * 32)
        st_pyecharts(
            _bar(list(by_cust.head(top_n).iloc[::-1]["客户名称_clean"]),
                 list(by_cust.head(top_n).iloc[::-1]["销售美金"]),
                 "销售美金 ($)", color=C[5], rotate=25, label_fmt="${c:,.2f}"),
            height=f"{h}px"
        )
        st.dataframe(
            by_cust.head(20).assign(
                销售美金=lambda x: x["销售美金"].apply(lambda v: f"${v:,.2f}")),
            hide_index=True, use_container_width=True,
        )

        st.subheader("产品TOP排名")
        by_prod = (
            df.groupby("商品名称_clean")
            .agg(销售美金=("合计$_clean", "sum"), 销售箱数=("箱数_clean", "sum"))
            .reset_index()
            .sort_values("销售美金", ascending=False)
        )
        st_pyecharts(
            _bar(list(by_prod.head(top_n).iloc[::-1]["商品名称_clean"]),
                 list(by_prod.head(top_n).iloc[::-1]["销售美金"]),
                 "销售美金 ($)", color=C[6], rotate=25, label_fmt="${c:,.2f}"),
            height=f"{h}px"
        )
        st.dataframe(
            by_prod.head(20).assign(
                销售美金=lambda x: x["销售美金"].apply(lambda v: f"${v:,.2f}")),
            hide_index=True, use_container_width=True,
        )

render()
