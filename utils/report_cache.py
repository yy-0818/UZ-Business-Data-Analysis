# -*- coding: utf-8 -*-
"""Cached report narrative generation (Streamlit)."""

from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from utils.narrative_generator import generate_sales_commentary


@st.cache_data(show_spinner=False)
def cached_sales_commentary(
    df: pd.DataFrame,
    col_df: pd.DataFrame,
    df_prev: pd.DataFrame,
    period_label: str,
) -> str:
    """Cache analysis commentary keyed on filtered dataframe contents."""
    prev = df_prev if df_prev is not None and not df_prev.empty else None
    col = col_df if col_df is not None and not col_df.empty else None
    return generate_sales_commentary(
        df,
        df_prev=prev,
        period_label=period_label,
        col_df=col,
    )
