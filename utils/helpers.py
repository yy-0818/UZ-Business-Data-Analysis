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


def _reference_dates(df: pd.DataFrame, date_col: str):
    """Latest date in *df* used to anchor quick presets."""
    dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
    if dates.empty:
        return None, None
    max_dt = dates.max()
    return max_dt, max_dt.to_period("M")


def _quick_period_bounds(label: str, max_dt, max_ym, *, previous: bool = False):
    """Return (start, end) for a quick preset; previous=True yields the comparison window."""
    if label == "本月":
        if previous:
            prev_ym = max_ym - 1
            return prev_ym.to_timestamp(), prev_ym.end_time
        return max_ym.to_timestamp(), max_dt

    if label == "上月":
        ym = max_ym - (2 if previous else 1)
        return ym.to_timestamp(), ym.end_time

    if label == "近三月":
        if previous:
            start_ym = max_ym - 5
            end_ym = max_ym - 3
            return start_ym.to_timestamp(), end_ym.end_time
        start_ym = max_ym - 2
        return start_ym.to_timestamp(), max_dt

    if label == "本年":
        if previous:
            prev_year = max_ym.year - 1
            start_ym = pd.Period(f"{prev_year}-01", freq="M")
            end_ym = pd.Period(f"{prev_year}-12", freq="M")
            return start_ym.to_timestamp(), end_ym.end_time
        start_ym = pd.Period(f"{max_ym.year}-01", freq="M")
        return start_ym.to_timestamp(), max_dt

    return None, None


def comparison_period_label(quick: str) -> str:
    """Human-readable label for the period compared against *quick*."""
    return {
        "本月": "上月",
        "上月": "前一月",
        "近三月": "前三月",
        "本年": "去年",
    }.get(quick, "上一周期")


def _filter_by_date_range(df: pd.DataFrame, date_col: str, start, end) -> pd.DataFrame:
    d = pd.to_datetime(df[date_col], errors="coerce")
    return df[(d >= start) & (d <= end)].copy()


def apply_quick_filter(
    df: pd.DataFrame,
    label: str,
    date_col: str = "日期",
) -> pd.DataFrame:
    """
    Apply a quick date preset based on the *data's own* date range.
    Dates are derived from the data's actual max date (not the system date),
    so '本月' means the last complete month in the data.
    """
    if label == "全部" or df.empty:
        return df.copy()

    if date_col not in df.columns:
        return df.copy()

    max_dt, max_ym = _reference_dates(df, date_col)
    if max_dt is None:
        return df.copy()

    start, end = _quick_period_bounds(label, max_dt, max_ym, previous=False)
    if start is None:
        return df.copy()

    return _filter_by_date_range(df, date_col, start, end)


def apply_previous_period_filter(
    df: pd.DataFrame,
    label: str,
    date_col: str = "日期",
) -> pd.DataFrame:
    """
    Return rows for the comparison period before *label*'s window.
    For '全部', uses the sidebar date range and the immediately preceding span of equal length.
    """
    if df.empty or date_col not in df.columns:
        return pd.DataFrame()

    if label == "全部":
        import streamlit as st
        date_filter = st.session_state.get("date_filter")
        if not date_filter:
            return pd.DataFrame()
        start, end = date_filter
        duration = end - start
        prev_end = start - pd.Timedelta(days=1)
        prev_start = prev_end - duration
        return _filter_by_date_range(df, date_col, prev_start, prev_end)

    max_dt, max_ym = _reference_dates(df, date_col)
    if max_dt is None:
        return pd.DataFrame()

    start, end = _quick_period_bounds(label, max_dt, max_ym, previous=True)
    if start is None:
        return pd.DataFrame()

    return _filter_by_date_range(df, date_col, start, end)
