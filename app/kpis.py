"""Financial Key Performance Indicators (KPIs) component for Streamlit dashboard.

Responsibility:
    Render financial overview summary cards using existing analytical calculations
    from ReturnAnalyzer and RiskAnalyzer. Displays prices, period returns,
    annualized volatility, maximum drawdown, and sample observation counts.
"""

from typing import Optional
import numpy as np
import pandas as pd
import streamlit as st

from stock_analyzer.analysis.returns import ReturnAnalyzer
from stock_analyzer.analysis.risk import RiskAnalyzer


def render_kpi_metrics(df: pd.DataFrame) -> None:
    """Render financial KPI metric cards across a responsive multi-column layout.

    Args:
        df: Cleaned stock DataFrame containing 'Date', 'Close', and optional 'Volume'.
    """
    if df.empty or "Close" not in df.columns:
        st.warning("Insufficient data available to compute financial KPIs.")
        return

    valid_closes = df["Close"].dropna()
    if valid_closes.empty:
        st.warning("Price series contains no valid numerical observations.")
        return

    ticker = str(df.attrs.get("ticker", "STOCK")).upper()
    is_synthetic = bool(df.attrs.get("is_synthetic", False))

    first_close = float(valid_closes.iloc[0])
    latest_close = float(valid_closes.iloc[-1])

    first_date = str(df["Date"].iloc[0])[:10] if "Date" in df.columns else "N/A"
    latest_date = str(df["Date"].iloc[-1])[:10] if "Date" in df.columns else "N/A"

    # 1. Period percentage return
    period_return_pct = ((latest_close / first_close) - 1.0) * 100.0 if first_close > 0 else float("nan")

    # 2. Cumulative Compound Return via ReturnAnalyzer
    ret_analyzer = ReturnAnalyzer(df, price_column="Close")
    cum_returns = ret_analyzer.calculate_cumulative_returns().dropna()
    cum_return_pct = float(cum_returns.iloc[-1] * 100.0) if not cum_returns.empty else float("nan")

    # 3. Volatility & Maximum Drawdown via RiskAnalyzer
    risk_analyzer = RiskAnalyzer(df, price_column="Close")
    daily_vol = risk_analyzer.calculate_daily_volatility()
    daily_vol_pct = daily_vol * 100.0 if not np.isnan(daily_vol) else float("nan")

    ann_vol = risk_analyzer.calculate_annualized_volatility(annualization_factor=252)
    ann_vol_pct = ann_vol * 100.0 if not np.isnan(ann_vol) else float("nan")

    mdd_data = risk_analyzer.calculate_max_drawdown()
    mdd_pct = mdd_data.get("max_drawdown_pct", float("nan"))
    trough_date = mdd_data.get("trough_date") or "N/A"

    # Render Metric Cards Row
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric(
            label=f"Latest Close ({latest_date})",
            value=f"${latest_close:,.2f}",
            delta=f"{period_return_pct:+.2f}%" if not np.isnan(period_return_pct) else None,
            help="Most recent closing price in the dataset.",
        )

    with col2:
        st.metric(
            label=f"First Close ({first_date})",
            value=f"${first_close:,.2f}",
            help="Starting closing price of the selected observation period.",
        )

    with col3:
        val_str = f"{cum_return_pct:+.2f}%" if not np.isnan(cum_return_pct) else "N/A"
        st.metric(
            label="Cumulative Return",
            value=val_str,
            delta=f"{cum_return_pct:+.2f}%" if not np.isnan(cum_return_pct) else None,
            help="Total compound growth of initial capital over the period.",
        )

    with col4:
        vol_str = f"{ann_vol_pct:.2f}%" if not np.isnan(ann_vol_pct) else "N/A"
        st.metric(
            label="Annualized Volatility",
            value=vol_str,
            help=f"Annualized return standard deviation (252-day basis). Daily σ: {daily_vol_pct:.2f}%.",
        )

    with col5:
        mdd_str = f"{mdd_pct:.2f}%" if not np.isnan(mdd_pct) else "N/A"
        st.metric(
            label="Max Drawdown (MDD)",
            value=mdd_str,
            delta=f"{mdd_pct:.2f}%" if not np.isnan(mdd_pct) else None,
            delta_color="inverse",
            help=f"Peak-to-trough decline. Deepest trough recorded on {trough_date}.",
        )

    with col6:
        st.metric(
            label="Total Observations",
            value=f"{len(df):,} Days",
            help="Number of chronological trading sessions included in analysis.",
        )
