"""Data export utilities for analytical CSV generation.

Provides structured, clean exports of OHLCV data, computed technical indicators,
financial returns, risk metrics, and qualitative insights into standardized CSV files.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from stock_analyzer.analysis.indicators import TechnicalIndicators
from stock_analyzer.analysis.insights import MarketInsight
from stock_analyzer.analysis.returns import ReturnAnalyzer
from stock_analyzer.analysis.risk import RiskAnalyzer
from stock_analyzer.data.exceptions import EmptyDataError, MissingColumnError


def export_cleaned_data_csv(
    df: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
    is_synthetic: Optional[bool] = None,
) -> Union[str, bytes]:
    """Export cleaned base OHLCV dataset to CSV format.

    Args:
        df: Cleaned stock market DataFrame.
        output_path: Optional destination file path. If None, returns UTF-8 encoded bytes.
        is_synthetic: Optional flag indicating synthetic data origin. Inferred from df.attrs if omitted.

    Returns:
        String path to saved file if output_path is provided, or CSV bytes.

    Raises:
        TypeError: If df is not a pandas DataFrame.
        EmptyDataError: If df is empty.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Expected pandas DataFrame, got {type(df).__name__}.")
    if df.empty:
        raise EmptyDataError("Cannot export empty DataFrame.")

    synthetic_flag = (
        is_synthetic
        if is_synthetic is not None
        else (df.attrs.get("data_source") == "synthetic" or df.attrs.get("is_synthetic", False))
    )

    export_df = df.copy(deep=True)
    if "Date" in export_df.columns:
        export_df["Date"] = pd.to_datetime(export_df["Date"]).dt.strftime("%Y-%m-%d")

    # If dataset has synthetic origin, attach explicit Is_Synthetic column so file is self-describing
    if synthetic_flag:
        export_df["Is_Synthetic"] = True

    csv_str = export_df.to_csv(index=False)

    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(csv_str, encoding="utf-8")
        return str(p)

    return csv_str.encode("utf-8")


def export_comprehensive_analysis_csv(
    df: pd.DataFrame,
    ticker: Optional[str] = "STOCK",
    output_path: Optional[Union[str, Path]] = None,
    is_synthetic: Optional[bool] = None,
) -> Union[str, bytes]:
    """Export fully enriched analytical dataset containing OHLCV, indicators, returns, and risk metrics.

    Args:
        df: Base cleaned stock DataFrame with OHLCV data.
        ticker: Ticker symbol identifier.
        output_path: Optional destination file path. If None, returns UTF-8 encoded bytes.
        is_synthetic: Optional flag indicating synthetic data origin. Inferred from df.attrs if omitted.

    Returns:
        String path to saved file if output_path is provided, or CSV bytes.

    Raises:
        TypeError: If df is not a pandas DataFrame.
        EmptyDataError: If df is empty.
        MissingColumnError: If required price or date columns are missing.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Expected pandas DataFrame, got {type(df).__name__}.")
    if df.empty:
        raise EmptyDataError("Cannot export empty DataFrame.")
    if "Close" not in df.columns:
        raise MissingColumnError("DataFrame lacks required 'Close' price column.")

    synthetic_flag = (
        is_synthetic
        if is_synthetic is not None
        else (df.attrs.get("data_source") == "synthetic" or df.attrs.get("is_synthetic", False))
    )

    working_df = df.copy(deep=True)
    if "Date" in working_df.columns:
        working_df["Date"] = pd.to_datetime(working_df["Date"]).dt.strftime("%Y-%m-%d")

    # 1. Technical Indicators
    try:
        ti = TechnicalIndicators(working_df)
        working_df["SMA_20"] = ti.calculate_sma(20).round(4)
        working_df["SMA_50"] = ti.calculate_sma(50).round(4)
        working_df["EMA_20"] = ti.calculate_ema(20).round(4)
    except Exception:
        pass

    # 2. Returns
    try:
        ra = ReturnAnalyzer(working_df)
        working_df["Daily_Return"] = ra.calculate_daily_returns().round(6)
        working_df["Cumulative_Return"] = ra.calculate_cumulative_returns().round(6)
    except Exception:
        pass

    # 3. Risk and Drawdown
    try:
        rka = RiskAnalyzer(working_df)
        working_df["Drawdown"] = rka.calculate_drawdown_series().round(6)
        working_df["Rolling_Vol_21"] = rka.calculate_rolling_volatility(window=21).round(6)
        working_df["Rolling_Vol_63"] = rka.calculate_rolling_volatility(window=63).round(6)
    except Exception:
        pass

    # Attach ticker identifier and synthetic flag column
    if "Ticker" not in working_df.columns:
        working_df.insert(0, "Ticker", ticker or "STOCK")
    if synthetic_flag:
        working_df["Is_Synthetic"] = True

    csv_str = working_df.to_csv(index=False)

    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(csv_str, encoding="utf-8")
        return str(p)

    return csv_str.encode("utf-8")


def export_insights_summary_csv(
    insights: List[MarketInsight],
    ticker: Optional[str] = "STOCK",
    data_source: Optional[str] = "Unknown",
    is_synthetic: Optional[bool] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> Union[str, bytes]:
    """Export qualitative insights collection to structured CSV format.

    Args:
        insights: List of MarketInsight objects.
        ticker: Ticker symbol identifier.
        data_source: Provenance / data source description.
        is_synthetic: Explicit flag indicating whether dataset is synthetic.
        output_path: Optional destination file path. If None, returns UTF-8 encoded bytes.

    Returns:
        String path to saved file if output_path is provided, or CSV bytes.
    """
    synthetic_flag = (
        is_synthetic
        if is_synthetic is not None
        else ("synthetic" in str(data_source).lower() or (ticker and ticker.upper() == "SAMPLE"))
    )

    rows: List[Dict[str, Any]] = []
    for item in insights:
        evidence_str = (
            "; ".join(f"{k}={v}" for k, v in item.evidence.items()) if item.evidence else ""
        )
        rows.append(
            {
                "Ticker": ticker or "STOCK",
                "Data_Source": data_source or "Unknown",
                "Is_Synthetic": bool(synthetic_flag),
                "Category": item.category.value if hasattr(item.category, "value") else str(item.category),
                "Title": item.title,
                "Severity": item.severity.value if hasattr(item.severity, "value") else str(item.severity),
                "Observation": item.observation,
                "Supporting_Evidence": evidence_str,
                "Limitations": item.limitations or "",
            }
        )

    if not rows:
        export_df = pd.DataFrame(
            columns=[
                "Ticker",
                "Data_Source",
                "Is_Synthetic",
                "Category",
                "Title",
                "Severity",
                "Observation",
                "Supporting_Evidence",
                "Limitations",
            ]
        )
    else:
        export_df = pd.DataFrame(rows)

    csv_str = export_df.to_csv(index=False)

    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(csv_str, encoding="utf-8")
        return str(p)

    return csv_str.encode("utf-8")
