"""Return calculation module.

Responsibility:
    Calculate daily percentage returns and cumulative return trajectories
    over cleaned historical stock price series.

Architecture Boundaries (Phase 7):
    - Performance calculations: daily returns and cumulative growth.
    - NO automated trading signals or buy/sell execution logic.
    - NO Plotly interactive charts (Phase 8).
    - NO Streamlit dashboard functionality (Phase 9).
    - NO report generation (Phase 11).
"""

from typing import List, Optional
import numpy as np
import pandas as pd

from stock_analyzer.data.exceptions import (
    DataValidationError,
    EmptyDataError,
    MissingColumnError,
)

REQUIRED_PRICE_COLUMNS: List[str] = ["Close"]


class ReturnAnalyzer:
    """Computes daily percentage returns and cumulative performance profiles.

    Enforces input immutability, chronological sorting, and explicit missing-value handling.
    """

    def __init__(self, df: pd.DataFrame, price_column: str = "Close") -> None:
        """Initialize the return analyzer with a cleaned stock DataFrame.

        Args:
            df: Cleaned stock DataFrame adhering to standard schema.
            price_column: Price column used for return calculation. Defaults to 'Close'.

        Raises:
            TypeError: If df is not a pandas DataFrame.
            EmptyDataError: If df is empty.
            MissingColumnError: If df lacks the specified price column.
            DataValidationError: If the specified price column is not numeric.
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame for return analysis, received {type(df).__name__}."
            )
        if df.empty:
            raise EmptyDataError(
                "Cannot perform return calculations on an empty DataFrame."
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
                date_dt = pd.to_datetime(working_df["Date"])
                sort_indices = np.argsort(date_dt.values)
                working_df = working_df.iloc[sort_indices].reset_index(drop=True)
            except Exception:
                working_df = working_df.sort_values(by="Date", ascending=True).reset_index(drop=True)

        self.df = working_df
        self.price_column = price_column
        self.ticker = str(df.attrs.get("ticker", "STOCK")).upper()
        self.is_synthetic = bool(df.attrs.get("is_synthetic", False))

    def calculate_daily_returns(self) -> pd.Series:
        """Calculate daily percentage returns using the configured price column.

        Formula:
            Daily Return_t = (Price_t / Price_{t-1}) - 1

        Conventions & Boundary Rules:
            - The first observation (t=0) is preserved as NaN because no previous price exists.
            - Missing returns are NOT filled with zero (no silent zero-imputation).
            - Returns reflect discrete arithmetic percentage changes.

        Returns:
            A named pandas Series representing daily percentage returns.
        """
        prices = self.df[self.price_column]
        daily_returns = prices.pct_change()
        daily_returns.name = "Daily_Return"
        return daily_returns

    def calculate_cumulative_returns(self) -> pd.Series:
        """Calculate cumulative return series from daily percentage returns.

        Formula:
            Cumulative Growth_t = Product_{i=1}^t (1 + Daily Return_i)
            Cumulative Return_t = Cumulative Growth_t - 1

        Conventions & Boundary Rules:
            - Uses starting wealth convention W_0 = 1.0.
            - Preserves missing initial return behavior: since Daily Return at t=0 is NaN,
              Cumulative Return at t=0 is also NaN.
            - Does NOT confuse cumulative return with the cumulative sum (cumsum) of percentage returns.

        Returns:
            A named pandas Series representing cumulative returns.
        """
        daily_returns = self.calculate_daily_returns()
        # (1 + R).cumprod() - 1 preserves NaN at index 0 where daily return is NaN
        cum_returns = (1.0 + daily_returns).cumprod() - 1.0
        cum_returns.name = "Cumulative_Return"
        return cum_returns

    def calculate_cumulative_growth(self, initial_wealth: float = 1.0) -> pd.Series:
        """Calculate wealth trajectory of an initial investment.

        Formula:
            Wealth_t = initial_wealth * Product_{i=1}^t (1 + Daily Return_i)
            At t=0, Wealth_0 = initial_wealth.

        Args:
            initial_wealth: Starting capital amount. Defaults to 1.0.

        Returns:
            A named pandas Series representing wealth evolution over time.
        """
        daily_returns = self.calculate_daily_returns()
        # For wealth index, starting baseline at index 0 is initial_wealth
        growth_factors = 1.0 + daily_returns.fillna(0.0)
        wealth = initial_wealth * growth_factors.cumprod()
        wealth.name = "Cumulative_Growth"
        return wealth

    def add_return_metrics(self) -> pd.DataFrame:
        """Append daily and cumulative return series to a copy of the input DataFrame.

        Returns:
            New pandas DataFrame preserving all original columns plus:
                - `Daily_Return`: Daily percentage change.
                - `Cumulative_Return`: Cumulative compound return from baseline.
        """
        out = self.df.copy()
        out["Daily_Return"] = self.calculate_daily_returns()
        out["Cumulative_Return"] = self.calculate_cumulative_returns()
        return out


# =============================================================================
# Functional Convenience Wrappers
# =============================================================================


def calculate_daily_returns(
    df: pd.DataFrame, price_column: str = "Close"
) -> pd.Series:
    """Convenience function to compute daily percentage returns for a stock DataFrame."""
    analyzer = ReturnAnalyzer(df, price_column=price_column)
    return analyzer.calculate_daily_returns()


def calculate_cumulative_returns(
    df: pd.DataFrame, price_column: str = "Close"
) -> pd.Series:
    """Convenience function to compute cumulative compound returns for a stock DataFrame."""
    analyzer = ReturnAnalyzer(df, price_column=price_column)
    return analyzer.calculate_cumulative_returns()


def add_return_metrics(
    df: pd.DataFrame, price_column: str = "Close"
) -> pd.DataFrame:
    """Convenience function to return DataFrame with Daily_Return and Cumulative_Return appended."""
    analyzer = ReturnAnalyzer(df, price_column=price_column)
    return analyzer.add_return_metrics()
