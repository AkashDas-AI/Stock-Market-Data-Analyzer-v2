"""Sidebar controls and user parameter configuration for Streamlit dashboard.

Responsibility:
    Render interactive sidebar controls including data-source selection,
    ticker symbol, date pickers, technical indicator toggles, and rolling volatility
    window selections.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, List, Optional

import streamlit as st


@dataclass
class DashboardParameters:
    """User-selected parameters captured from the sidebar interface."""

    source_type: str
    ticker: str
    start_date: Optional[date]
    end_date: Optional[date]
    uploaded_file: Optional[Any]
    show_sma_20: bool
    show_sma_50: bool
    show_ema_20: bool
    show_candlestick_volume: bool
    rolling_vol_windows: List[int]


def render_sidebar() -> DashboardParameters:
    """Render interactive sidebar navigation and control widgets.

    Returns:
        DashboardParameters dataclass populated with current widget states.
    """
    st.sidebar.title("⚙️ Dashboard Controls")
    st.sidebar.caption("Configure data source, indicators, and risk settings.")

    # 1. Data Ingestion Source
    st.sidebar.subheader("1. Data Ingestion Source")
    source_type = st.sidebar.radio(
        "Select Data Source:",
        options=[
            "Sample Dataset (Synthetic)",
            "Live Yahoo Finance",
            "Upload CSV",
        ],
        index=0,
        help="Choose between offline synthetic sample data, Yahoo Finance historical market data, or custom CSV file upload.",
    )

    ticker = "AAPL"
    start_date = None
    end_date = None
    uploaded_file = None

    if source_type == "Live Yahoo Finance":
        ticker_input = st.sidebar.text_input(
            "Stock Ticker Symbol",
            value="AAPL",
            max_chars=10,
            help="Enter valid ticker symbol (e.g. AAPL, MSFT, GOOGL, AMZN, TSLA, SPY).",
        )
        ticker = ticker_input.strip().upper() if ticker_input else "AAPL"

        # Default: 1 year of historical daily data
        today = date.today()
        one_year_ago = today - timedelta(days=365)

        col_d1, col_d2 = st.sidebar.columns(2)
        with col_d1:
            start_date = st.date_input("Start Date", value=one_year_ago)
        with col_d2:
            end_date = st.date_input("End Date", value=today)

    elif source_type == "Upload CSV":
        uploaded_file = st.sidebar.file_uploader(
            "Upload Historical Stock CSV",
            type=["csv"],
            help="Uploaded CSV must contain Date, Open, High, Low, Close, and Volume columns.",
        )
        alias = st.sidebar.text_input(
            "Dataset Label / Ticker Alias",
            value="CUSTOM",
            help="Ticker label associated with the uploaded dataset.",
        )
        ticker = alias.strip().upper() if alias else "CUSTOM"

        filter_csv_dates = st.sidebar.checkbox("Filter by Date Range", value=False)
        if filter_csv_dates:
            col_d1, col_d2 = st.sidebar.columns(2)
            today = date.today()
            with col_d1:
                start_date = st.date_input("Start Date", value=today - timedelta(days=365))
            with col_d2:
                end_date = st.date_input("End Date", value=today)

    elif source_type == "Sample Dataset (Synthetic)":
        ticker = "SAMPLE"
        st.sidebar.info(
            "ℹ️ Loading pre-packaged synthetic stock dataset (`data/sample/sample_stock.csv`). "
            "Exclusively intended for offline testing and validation."
        )
        filter_sample_dates = st.sidebar.checkbox("Filter Sample Date Range", value=False)
        if filter_sample_dates:
            col_d1, col_d2 = st.sidebar.columns(2)
            with col_d1:
                start_date = st.date_input("Start Date", value=date(2026, 1, 1))
            with col_d2:
                end_date = st.date_input("End Date", value=date(2026, 4, 17))

    # 2. Technical Indicators Overlay
    st.sidebar.subheader("2. Technical Indicators")
    show_sma_20 = st.sidebar.checkbox(
        "SMA 20 (20-Day Simple Moving Avg)",
        value=True,
        help="20-day equal-weighted moving average for short-term trend direction.",
    )
    show_sma_50 = st.sidebar.checkbox(
        "SMA 50 (50-Day Simple Moving Avg)",
        value=True,
        help="50-day equal-weighted moving average for intermediate-term trend direction.",
    )
    show_ema_20 = st.sidebar.checkbox(
        "EMA 20 (20-Day Exponential Avg)",
        value=True,
        help="20-day exponentially-weighted moving average with higher sensitivity to recent price changes.",
    )

    # 3. Chart Layout & Visibility Preferences
    st.sidebar.subheader("3. Chart & Risk Preferences")
    show_candlestick_volume = st.sidebar.checkbox(
        "Shared Volume Subplot in Candlestick",
        value=True,
        help="Embed trading volume bars in a shared-axis subplot directly beneath the candlestick chart.",
    )

    rolling_vol_windows = st.sidebar.multiselect(
        "Rolling Volatility Windows (Days)",
        options=[10, 21, 50, 63, 126, 252],
        default=[21, 63],
        help="Select lookback periods for annualized rolling volatility curves (e.g. 21d ≈ 1m, 63d ≈ 3m).",
    )
    if not rolling_vol_windows:
        rolling_vol_windows = [21, 63]

    st.sidebar.divider()
    st.sidebar.markdown(
        "<small style='color: #64748B;'>Stock Market Data Analyzer | Phase 9<br>Author: Akash Das</small>",
        unsafe_allow_html=True,
    )

    return DashboardParameters(
        source_type=source_type,
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        uploaded_file=uploaded_file,
        show_sma_20=show_sma_20,
        show_sma_50=show_sma_50,
        show_ema_20=show_ema_20,
        show_candlestick_volume=show_candlestick_volume,
        rolling_vol_windows=rolling_vol_windows,
    )
