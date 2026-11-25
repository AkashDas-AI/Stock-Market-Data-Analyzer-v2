"""Technical indicators and moving averages calculation module.

Responsibility:
    Calculate technical trend indicators including Simple Moving Average (SMA 20, SMA 50)
    and Exponential Moving Average (EMA 20) over cleaned stock-market time series.

Architecture Boundaries (Phase 6):
    - Trend indicator calculation only (SMA 20, SMA 50, EMA 20).
    - NO daily or cumulative returns, volatility, or drawdown modeling (Phase 7).
    - NO automated trading signals or buy/sell execution logic (Phase 6/7/10).
    - NO Plotly interactive charts (Phase 8).
    - NO Streamlit dashboard functionality (Phase 9).
    - NO report generation (Phase 11).
"""

from typing import List, Optional, Union
import numpy as np
import pandas as pd

from stock_analyzer.data.exceptions import (
    DataValidationError,
    EmptyDataError,
    MissingColumnError,
)

REQUIRED_COLUMNS: List[str] = ["Date", "Open", "High", "Low", "Close", "Volume"]


class TechnicalIndicators:
    """Calculates moving averages and technical trend indicators for stock time-series.

    Enforces input immutability, chronological ordering, and robust validation.
    Supports calculating SMA 20, SMA 50, and EMA 20 individually or collectively.
    """

    def __init__(self, df: pd.DataFrame, price_column: str = "Close") -> None:
        """Initialize the technical indicators calculator with a cleaned stock DataFrame.

        Args:
            df: Cleaned stock DataFrame adhering to standard schema (OHLCV).
            price_column: Price column used for calculations. Defaults to 'Close'.

        Raises:
            TypeError: If df is not a pandas DataFrame.
            EmptyDataError: If df is empty.
            MissingColumnError: If df lacks required columns or the specified price column.
            DataValidationError: If the specified price column is not numeric.
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame for technical indicators, received {type(df).__name__}."
            )
        if df.empty:
            raise EmptyDataError(
                "Cannot calculate technical indicators on an empty DataFrame."
            )

        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise MissingColumnError(
                f"DataFrame lacks mandatory OHLCV columns required for analysis: {missing_cols}."
            )

        if price_column not in df.columns:
            raise MissingColumnError(
                f"Specified price column '{price_column}' not found in DataFrame columns: {list(df.columns)}."
            )

        # Validate that price_column contains numeric data
        if not pd.api.types.is_numeric_dtype(df[price_column]):
            raise DataValidationError(
                f"Price column '{price_column}' must have numeric data type, found {df[price_column].dtype}."
            )

        # Defensive deep copy to preserve input immutability
        working_df = df.copy(deep=True)

        # Enforce chronological ordering ascending by Date if Date is present
        if "Date" in working_df.columns:
            try:
                # Sort chronologically without mutating original Date column data type
                date_dt = pd.to_datetime(working_df["Date"])
                sort_indices = np.argsort(date_dt.values)
                working_df = working_df.iloc[sort_indices].reset_index(drop=True)
            except Exception:
                working_df = working_df.sort_values(by="Date", ascending=True).reset_index(drop=True)

        self.df = working_df
        self.price_column = price_column
        self.ticker = str(df.attrs.get("ticker", "STOCK")).upper()
        self.is_synthetic = bool(df.attrs.get("is_synthetic", False))

    def calculate_sma(self, window: int, min_periods: Optional[int] = None) -> pd.Series:
        """Calculate Simple Moving Average (SMA) over a specified rolling window.

        Formula:
            SMA_{window, t} = (1 / window) * sum_{i=0}^{window-1} Price_{t-i}

        Args:
            window: Rolling window length (number of observations). Must be >= 1.
            min_periods: Minimum observations in window required to produce a value.
                         Defaults to `window` (warm-up observations are NaN).

        Returns:
            A named pandas Series representing the rolling SMA values.

        Raises:
            ValueError: If window is less than 1.
        """
        if not isinstance(window, int) or window < 1:
            raise ValueError(f"Window must be a positive integer >= 1, got {window}.")

        min_p = min_periods if min_periods is not None else window
        sma = self.df[self.price_column].rolling(window=window, min_periods=min_p).mean()
        sma.name = f"SMA_{window}"
        return sma

    def calculate_ema(
        self, span: int, adjust: bool = False, min_periods: Optional[int] = None
    ) -> pd.Series:
        """Calculate Exponential Moving Average (EMA) over a specified span.

        Calculation Convention:
            Uses recursive exponential weighting with smoothing multiplier:
                alpha = 2 / (span + 1)
                EMA_t = alpha * Price_t + (1 - alpha) * EMA_{t-1}

            When `adjust=False` and `min_periods=span`, initial observations before
            index (span - 1) are set to NaN to strictly reflect the warm-up period.
            No artificial price fabrication is used to initialize the indicator.

        Args:
            span: Decay span for EMA (equivalent to span in pandas EWM). Must be >= 1.
            adjust: Whether to calculate using recursive formulation (adjust=False, default)
                    or weighted sum of weights (adjust=True).
            min_periods: Minimum observations required before producing non-null output.
                         Defaults to `span`.

        Returns:
            A named pandas Series representing the EMA values.

        Raises:
            ValueError: If span is less than 1.
        """
        if not isinstance(span, int) or span < 1:
            raise ValueError(f"Span must be a positive integer >= 1, got {span}.")

        min_p = min_periods if min_periods is not None else span
        ema = (
            self.df[self.price_column]
            .ewm(span=span, adjust=adjust, min_periods=min_p)
            .mean()
        )
        ema.name = f"EMA_{span}"
        return ema

    def calculate_sma_20(self) -> pd.Series:
        """Calculate 20-observation Simple Moving Average (SMA 20).

        Window: 20 observations, min_periods=20.
        The first 19 observations contain NaN.
        """
        return self.calculate_sma(window=20, min_periods=20)

    def calculate_sma_50(self) -> pd.Series:
        """Calculate 50-observation Simple Moving Average (SMA 50).

        Window: 50 observations, min_periods=50.
        The first 49 observations contain NaN.
        """
        return self.calculate_sma(window=50, min_periods=50)

    def calculate_ema_20(self) -> pd.Series:
        """Calculate 20-period Exponential Moving Average (EMA 20).

        Span: 20 observations, adjust=False, min_periods=20.
        The first 19 observations contain NaN.
        """
        return self.calculate_ema(span=20, adjust=False, min_periods=20)

    def add_sma_20(self) -> pd.DataFrame:
        """Return a copy of the DataFrame with SMA_20 appended."""
        out = self.df.copy()
        out["SMA_20"] = self.calculate_sma_20()
        return out

    def add_sma_50(self) -> pd.DataFrame:
        """Return a copy of the DataFrame with SMA_50 appended."""
        out = self.df.copy()
        out["SMA_50"] = self.calculate_sma_50()
        return out

    def add_ema_20(self) -> pd.DataFrame:
        """Return a copy of the DataFrame with EMA_20 appended."""
        out = self.df.copy()
        out["EMA_20"] = self.calculate_ema_20()
        return out

    def calculate_moving_averages(self) -> pd.DataFrame:
        """Calculate and append all three moving averages (SMA_20, SMA_50, EMA_20).

        Returns:
            A new pandas DataFrame containing all original columns and observations,
            plus three new technical indicator columns:
                - `SMA_20`: 20-observation Simple Moving Average.
                - `SMA_50`: 50-observation Simple Moving Average.
                - `EMA_20`: 20-observation Exponential Moving Average.
        """
        out = self.df.copy()
        out["SMA_20"] = self.calculate_sma_20()
        out["SMA_50"] = self.calculate_sma_50()
        out["EMA_20"] = self.calculate_ema_20()
        return out


# =============================================================================
# Functional Convenience Wrappers
# =============================================================================


def calculate_sma_20(
    df: pd.DataFrame, price_column: str = "Close"
) -> pd.Series:
    """Convenience function to compute SMA 20 series for a stock DataFrame."""
    indicators = TechnicalIndicators(df, price_column=price_column)
    return indicators.calculate_sma_20()


def calculate_sma_50(
    df: pd.DataFrame, price_column: str = "Close"
) -> pd.Series:
    """Convenience function to compute SMA 50 series for a stock DataFrame."""
    indicators = TechnicalIndicators(df, price_column=price_column)
    return indicators.calculate_sma_50()


def calculate_ema_20(
    df: pd.DataFrame, price_column: str = "Close"
) -> pd.Series:
    """Convenience function to compute EMA 20 series for a stock DataFrame."""
    indicators = TechnicalIndicators(df, price_column=price_column)
    return indicators.calculate_ema_20()


def calculate_moving_averages(
    df: pd.DataFrame, price_column: str = "Close"
) -> pd.DataFrame:
    """Convenience function to compute and append SMA_20, SMA_50, and EMA_20.

    Args:
        df: Input cleaned stock DataFrame.
        price_column: Price column used for calculations (defaults to 'Close').

    Returns:
        DataFrame with original columns and 'SMA_20', 'SMA_50', and 'EMA_20' columns.
    """
    indicators = TechnicalIndicators(df, price_column=price_column)
    return indicators.calculate_moving_averages()


def add_moving_averages(
    df: pd.DataFrame, price_column: str = "Close"
) -> pd.DataFrame:
    """Alias for calculate_moving_averages returning DataFrame with indicator columns."""
    return calculate_moving_averages(df, price_column=price_column)
