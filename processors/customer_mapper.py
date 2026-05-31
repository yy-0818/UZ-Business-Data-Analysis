# -*- coding: utf-8 -*-
"""Customer name mapping and normalization."""

import pandas as pd
import re


def build_customer_mapping(customer_master: pd.DataFrame) -> dict:
    """
    Build a mapping from sub-account customer names to standardized names.
    E.g. '1账户 ZPT', '2账户 ZPT' -> 'ZPT'
         '1账户 E2客户 CORONA' -> 'CORONA'
    """
    mapping = {}

    if customer_master is None or customer_master.empty:
        return mapping

    if "客户名称" not in customer_master.columns:
        return mapping

    for _, row in customer_master.iterrows():
        raw_name = str(row["客户名称"]).strip()
        standardized = standardize_name(raw_name)
        mapping[raw_name] = standardized

        # Also map versions with account prefix stripped
        cleaned = re.sub(r"^[12账户]+\s*", "", raw_name)
        if cleaned and cleaned != raw_name:
            mapping[cleaned] = standardize_name(cleaned)

    return mapping


def standardize_name(name: str) -> str:
    """Standardize a customer name by removing prefixes and cleaning whitespace."""
    if not name:
        return "未知客户"
    name = str(name).strip()
    name = re.sub(r"\s+", " ", name)
    # Remove account prefix
    name = re.sub(r"^[12账户]+\s*", "", name)
    return name.strip() if name.strip() else "未知客户"


def apply_customer_mapping(df: pd.DataFrame, mapping: dict, col: str = "客户名称_clean") -> pd.Series:
    """Apply customer name mapping to a dataframe column."""
    return df[col].map(lambda x: mapping.get(x, x))
