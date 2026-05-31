# -*- coding: utf-8 -*-
"""Sales Receivable Analysis Application - Main Entry Point."""

import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from processors.data_processor import (
    process_sales_data, process_collection_data,
    process_customer_master, DataError,
)
from utils.validators import (
    validate_sales_data, validate_collection_data, validate_customer_master,
)
from utils.helpers import (
    get_filtered_sales, get_filtered_collection,
    check_data_loaded, period_label as _period_label,
)


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="销售应收分析系统",
    page_icon="📊",
    layout="wide"
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_file(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file, dtype=str, encoding="utf-8-sig")
    elif uploaded_file.name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file, dtype=str)
    raise ValueError(f"Unsupported: {uploaded_file.name}")


# ── Session state defaults ─────────────────────────────────────────────────────
SESSION_DEFAULTS = {
    "sales_processed": False,
    "collection_processed": False,
    "customer_df": None,
    "sales_df": None,
    "collection_df": None,
    "date_filter": None,
    "account_filter": "全部",
}
for k, v in SESSION_DEFAULTS.items():
    st.session_state.setdefault(k, v)


# ── Sidebar: status + filters only ───────────────────────────────────────────
with st.sidebar:
    st.title("数据筛选")

    # ── Filters ─────────────────────────────────────────────────────────────────
    if st.session_state.get("sales_processed"):
        st.markdown("**日期范围**")

        df = st.session_state["sales_df"]
        min_d = pd.to_datetime(df["日期"]).min()
        max_d = pd.to_datetime(df["日期"]).max()

        c1, c2 = st.columns(2)
        with c1:
            s = st.date_input("开始", min_value=min_d, max_value=max_d,
                              value=min_d, key="start_date",
                              label_visibility="collapsed")
        with c2:
            e = st.date_input("结束", min_value=min_d, max_value=max_d,
                              value=max_d, key="end_date",
                              label_visibility="collapsed")
        st.session_state["date_filter"] = (pd.Timestamp(s), pd.Timestamp(e))

        accounts = ["全部"] + sorted(df["账户"].dropna().unique().tolist())
        st.selectbox("账户", accounts, key="account_filter")

    # ── Data status ─────────────────────────────────────────────────────────
    def _ok(flag): return "✅" if flag else "⏳"
    def _status_label(flag): return "已加载" if flag else "未上传"

    sales_ok = st.session_state.get("sales_processed", False)
    col_ok = st.session_state.get("collection_processed", False)
    cust_ok = st.session_state.get("customer_df") is not None

    st.markdown("**数据状态**")
    c1, c2 = st.columns([1, 4])
    with c1: st.markdown(_ok(sales_ok))
    with c2: st.markdown(f"销售数据  `{_status_label(sales_ok)}`")
    with c1: st.markdown(_ok(col_ok))
    with c2: st.markdown(f"收款数据  `{_status_label(col_ok)}`")
    with c1: st.markdown(_ok(cust_ok))
    with c2: st.markdown(f"客户主数据  `{_status_label(cust_ok)}`")



    st.markdown("---")
    st.caption(f"v1.0  ·  {datetime.now().strftime('%Y-%m-%d')}")


# ── Main page: upload + KPIs ─────────────────────────────────────────────────
def main():
    if not st.session_state.get("sales_processed"):
        _render_upload()
        return

    # ── Upload section (collapsible) ─────────────────────────────────────────
    with st.expander("📁 数据管理（上传 / 重新处理）", expanded=False):
        sales_file = st.file_uploader(
            "销售数据 (CSV/XLSX)", type=["csv", "xlsx", "xls"],
            key="sales_uploader_main", label_visibility="collapsed"
        )
        collection_file = st.file_uploader(
            "收款数据 (CSV/XLSX)", type=["csv", "xlsx", "xls"],
            key="collection_uploader_main", label_visibility="collapsed"
        )
        customer_file = st.file_uploader(
            "客户主数据 (CSV/XLSX)", type=["csv", "xlsx", "xls"],
            key="customer_uploader_main", label_visibility="collapsed"
        )

        if st.button("🚀 处理数据", type="primary", use_container_width=True):
            if not sales_file:
                st.error("请上传销售数据")
            elif not collection_file:
                st.error("请上传收款数据")
            else:
                _process_files(sales_file, collection_file, customer_file)

    # ── KPIs ────────────────────────────────────────────────────────────────
    df = get_filtered_sales()
    col_df = get_filtered_collection()

    if df.empty:
        st.warning("当前筛选条件下无销售数据")
        return

    total_usd = df["合计$_clean"].sum()
    total_som = df["苏姆合计_clean"].sum()
    total_orders = df["单据编号"].nunique()
    raw_col = "客户名称" if "客户名称" in df.columns else "客户名称_clean"
    total_customers = df[raw_col].nunique()

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    with kpi_col1:
        st.metric("💰 销售美金", f"${total_usd:,.2f}")
    with kpi_col2:
        st.metric("💵 销售苏姆", f"₴{total_som:,.2f}")
    with kpi_col3:
        st.metric("📋 销售单数", f"{total_orders:,}")
    with kpi_col4:
        st.metric("🏢 客户数量", f"{total_customers}")

    period_str = _period_label()
    acc_str = st.session_state.get("account_filter", "全部")
    st.caption(f"ℹ️ 筛选条件：{period_str}  |  账户：{acc_str}")

    # ── Data preview ────────────────────────────────────────────────────────
    with st.expander("🔍 数据预览（销售）", expanded=True):
        preview_cols = ["日期", "单据编号", "客户名称_clean", "商品名称_clean",
                        "合计$_clean", "苏姆合计_clean", "账户"]
        preview_cols = [c for c in preview_cols if c in df.columns]
        st.dataframe(
            df[preview_cols]
            .head(50)
            .assign(日期=lambda x: x["日期"].dt.strftime("%Y-%m-%d")),
            hide_index=True,
            use_container_width=True,
        )
        st.caption(f"共 {len(df)} 条记录，展示前 50 条")

    if not col_df.empty:
        with st.expander("🔍 数据预览（收款）", expanded=False):
            pcols = ["日期_clean", "客户名称_clean", "美金_clean", "苏姆_clean", "账户"]
            pcols = [c for c in pcols if c in col_df.columns]
            st.dataframe(
                col_df[pcols].head(30).assign(
                    日期=lambda x: x["日期_clean"].dt.strftime("%Y-%m-%d")
                ),
                hide_index=True, use_container_width=True,
            )
            st.caption(f"共 {len(col_df)} 条收款记录，展示前 30 条")

    st.info("👈 请从左侧导航选择分析模块")


def _process_files(sales_file, collection_file, customer_file):
    """Run all data processing steps in sequence."""
    with st.spinner("处理销售数据..."):
        try:
            raw = load_file(sales_file)
            processed = process_sales_data(raw)
        except DataError as e:
            st.error(str(e))
            return
        except Exception as e:
            st.error(f"销售数据处理出错: {e}")
            return
        else:
            st.session_state["sales_df"] = processed
            st.session_state["sales_processed"] = True
            st.success(f"销售数据: {len(processed)} 条 ✅")

    with st.spinner("处理收款数据..."):
        try:
            raw = load_file(collection_file)
            processed = process_collection_data(raw)
        except DataError as e:
            st.error(str(e))
            return
        except Exception as e:
            st.error(f"收款数据处理出错: {e}")
            return
        else:
            st.session_state["collection_df"] = processed
            st.session_state["collection_processed"] = True
            st.success(f"收款数据: {len(processed)} 条 ✅")

    with st.spinner("处理客户主数据..."):
        try:
            if customer_file:
                raw = load_file(customer_file)
                vr = validate_customer_master(raw)
                if vr.is_valid:
                    processed = process_customer_master(raw)
                    st.session_state["customer_df"] = processed
                    st.success(f"客户主数据: {len(processed)} 条 ✅")
                else:
                    st.session_state["customer_df"] = pd.DataFrame()
                    st.warning("客户主数据校验未通过，已跳过")
            else:
                st.session_state["customer_df"] = pd.DataFrame()
        except Exception as e:
            st.session_state["customer_df"] = pd.DataFrame()
            st.warning(f"客户主数据处理出错: {e}")

    with st.spinner("处理客户类别映射..."):
        try:
            sales_df = st.session_state["sales_df"]
            cust_df = st.session_state.get("customer_df")
            if cust_df is not None and not cust_df.empty and "客户名称_std" in cust_df.columns:
                cat_df = cust_df[["客户名称_std", "客户类别"]].drop_duplicates("客户名称_std")
                sales_df = sales_df.merge(cat_df, left_on="客户名称_clean",
                                          right_on="客户名称_std", how="left")
                sales_df["客户类别"] = sales_df["客户类别"].fillna("未分类")
                st.session_state["sales_df"] = sales_df
            st.success("数据处理完成 ✅")
        except Exception as e:
            st.warning(f"客户类别映射出错: {e}")

    st.rerun()


def _render_upload():
    """Render the welcome/upload screen when no data is loaded."""
    st.markdown("""
    <div style="text-align:center; padding: 40px 0 20px;">
      <h2 style="color:#1B3A5C;">欢迎使用销售分析系统</h2>
      <p style="color:#7F8C8D; font-size:15px; margin-top:10px;">
        上传数据文件，系统将自动处理并生成多维度商业分析
      </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("📁 **步骤一**\n\n上传销售数据（CSV/XLSX）")
    with c2:
        st.info("📥 **步骤二**\n\n上传收款数据（CSV/XLSX）")
    with c3:
        st.info("🔧 **步骤三**\n\n点击「处理数据」开始分析")

    st.markdown("---")

    sales_file = st.file_uploader(
        "上传销售数据 (CSV/XLSX)",
        type=["csv", "xlsx", "xls"], key="sales_uploader_welcome",
        label_visibility="collapsed"
    )
    collection_file = st.file_uploader(
        "上传收款数据 (CSV/XLSX)",
        type=["csv", "xlsx", "xls"], key="collection_uploader_welcome",
        label_visibility="collapsed"
    )
    customer_file = st.file_uploader(
        "上传客户主数据 (CSV/XLSX)（可选）",
        type=["csv", "xlsx", "xls"], key="customer_uploader_welcome",
        label_visibility="collapsed"
    )

    if st.button("🚀 开始处理数据", type="primary", use_container_width=True):
        if not sales_file:
            st.error("请上传销售数据")
        elif not collection_file:
            st.error("请上传收款数据")
        else:
            _process_files(sales_file, collection_file, customer_file)

    st.markdown("---")
    st.markdown("""
    ### 所需文件说明

    | 文件 | 格式 | 说明 |
    |------|------|------|
    | 销售数据 | CSV / XLSX | 包含日期、单据编号、客户名称、商品、金额等字段 |
    | 收款数据 | CSV / XLSX | 包含收款日期、客户名称、收款金额等字段 |
    | 客户主数据 | CSV / XLSX | 可选，用于客户名称标准化映射 |
    """)


main()
