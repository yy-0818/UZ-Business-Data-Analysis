# -*- coding: utf-8 -*-
"""Shared utility helpers used across all pages."""

import pandas as pd


def period_label() -> str:
    """Return current date filter range as a human-readable string."""
    import streamlit as st
    if "date_filter" in st.session_state and st.session_state["date_filter"]:
        s, e = st.session_state["date_filter"]
        return f"{s.strftime('%Y-%m-%d')} 至 {e.strftime('%Y-%m-%d')}"
    return "全部时间"


def get_filtered_sales() -> pd.DataFrame:
    """Get sales data with active date and account filters applied."""
    import streamlit as st
    if "sales_df" not in st.session_state or st.session_state["sales_df"] is None:
        return pd.DataFrame()
    df = st.session_state["sales_df"].copy()
    if "date_filter" in st.session_state and st.session_state["date_filter"]:
        s, e = st.session_state["date_filter"]
        df = df[(df["日期"] >= s) & (df["日期"] <= e)]
    acc = st.session_state.get("account_filter", "全部")
    if acc != "全部":
        df = df[df["账户"] == acc]
    return df


def get_filtered_collection() -> pd.DataFrame:
    """Get collection data with active date and account filters applied."""
    import streamlit as st
    if "collection_df" not in st.session_state or st.session_state["collection_df"] is None:
        return pd.DataFrame()
    df = st.session_state["collection_df"].copy()
    if "date_filter" in st.session_state and st.session_state["date_filter"]:
        s, e = st.session_state["date_filter"]
        df = df[(df["日期_clean"] >= s) & (df["日期_clean"] <= e)]
    acc = st.session_state.get("account_filter", "全部")
    if acc != "全部":
        df = df[df["账户"] == acc]
    return df


def check_data_loaded():
    """Check if required data is loaded, show warning and stop if not."""
    import streamlit as st
    if not st.session_state.get("sales_processed"):
        st.warning("请先在左侧上传并处理数据文件")
        st.stop()


def apply_quick_filter(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """
    Apply a quick date preset based on the *data's own* date range.
    Dates are derived from the data's actual max date (not the system date),
    so '本月' means the last complete month in the data.
    """
    if label == "全部" or df.empty:
        return df.copy()

    dates = pd.to_datetime(df["日期"], errors="coerce").dropna()
    if dates.empty:
        return df.copy()

    max_dt = dates.max()          # latest date in the data
    max_ym = max_dt.to_period("M")  # e.g. 2025-12

    if label == "本月":
        # Current period: same month as the latest data point
        start = max_ym.to_timestamp()
        end = max_dt
    elif label == "上月":
        prev_ym = max_ym - 1      # previous calendar month
        start = prev_ym.to_timestamp()
        end = prev_ym.end_time
    elif label == "近三月":
        start_ym = max_ym - 2     # 3-month window ending at max month
        start = start_ym.to_timestamp()
        end = max_dt
    elif label == "本年":
        start_ym = pd.Period(f"{max_ym.year}-01", freq="M")
        start = start_ym.to_timestamp()
        end = max_dt
    else:
        return df.copy()

    return df[
        (pd.to_datetime(df["日期"], errors="coerce") >= start) &
        (pd.to_datetime(df["日期"], errors="coerce") <= end)
    ].copy()
