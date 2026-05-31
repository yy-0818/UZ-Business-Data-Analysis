# -*- coding: utf-8 -*-
"""Global configuration for the Sales Receivable Analysis app."""

ACCOUNT_MAPPING = {
    "开票公账": "1账户",
    "1账户": "1账户",
    "现金美金": "2账户",
    "2账户": "2账户",
    "出口美金": "3账户",
    "3账户": "3账户",
}

# Default number of top records to show
TOP_N = 10

# Currency display format
CURRENCY_PRECISION = 2

# Date format
DATE_FORMAT = "%Y-%m-%d"

# Color palette for charts
CHART_COLORS = [
    "#4A90E2", "#50C878", "#FF6B6B", "#FFD93D",
    "#6BCB77", "#4D96FF", "#FF922B", "#CC5DE8",
    "#20C997", "#F06595", "#ADB5BD", "#6610F2",
]

# Warning thresholds
OVERDUE_DAYS_WARNING = 30
LOW_PAYMENT_RATE_WARNING = 0.5  # 50%
