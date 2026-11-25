"""Yahoo Finance market data retrieval module.

Responsibility:
    Fetch historical stock price data and metadata from Yahoo Finance,
    handling column normalization, MultiIndex flattening, and comprehensive
    error handling.

Data Provider Terms & Limitations:
    Market data from Yahoo Finance is subject to Yahoo's Terms of Service and rate limits.
    Data is provided for informational and analytical purposes, with potential latency or
    gaps in historical intraday records.

Date Range Behavior:
    In Yahoo Finance, the `end_date` parameter is EXCLUSIVE.
    For example, to retrieve data through 2026-01-10, `end_date` should be set to 2026-01-11.
"""

from datetime import date, datetime
from typing import Optional, Union, List
import pandas as pd
import yfinance as yf

from stock_analyzer.data.exceptions import (
    DataFetchError,
    TickerNotFoundError,
    EmptyDataError,
    InvalidDateRangeError,
)

# Standard market data columns
MANDATORY_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]
STANDARD_COLUMNS_WITH_ADJ = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]


class StockDataFetcher:
    """Fetcher for historical stock market data via Yahoo Finance."""

    def __init__(self, ticker: str) -> None:
        """Initialize fetcher with target ticker symbol.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'SPY').

        Raises:
            ValueError: If ticker is not a valid non-empty string.
        """
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("Ticker symbol must be a non-empty string.")
        self.ticker = ticker.strip().upper()

    def fetch_history(
        self,
        start_date: Optional[Union[str, date, datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[str, date, datetime, pd.Timestamp]] = None,
        period: Optional[str] = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data from Yahoo Finance.

        Args:
            start_date: Inclusive start date (string 'YYYY-MM-DD' or date object).
            end_date: Exclusive end date (string 'YYYY-MM-DD' or date object).
            period: Duration string (e.g. '1y', '5y') if start/end dates are not provided.
            interval: Bar frequency interval (default '1d').

        Returns:
            Normalized pandas DataFrame containing ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            and optionally 'Adj Close', sorted chronologically by Date.

        Raises:
            InvalidDateRangeError: If start date is on or after end date, or invalid.
            EmptyDataError: If the query returns zero observations.
            DataFetchError: If network, API, or parser errors occur.
        """
        start_str, end_str = self._validate_and_format_dates(start_date, end_date)

        # Default period if neither start/end nor period specified
        if not start_str and not end_str and not period:
            period = "1y"

        try:
            raw_df = yf.download(
                tickers=self.ticker,
                start=start_str,
                end=end_str,
                period=period if not start_str else None,
                interval=interval,
                auto_adjust=False,
                progress=False,
            )
        except Exception as exc:
            raise DataFetchError(
                f"Failed to fetch market data for ticker '{self.ticker}' from Yahoo Finance: {exc}"
            ) from exc

        if raw_df is None or raw_df.empty:
            raise EmptyDataError(
                f"No market data found for ticker '{self.ticker}'. "
                "The ticker symbol may be invalid, delisted, or have no trading data in the requested range."
            )

        normalized_df = self._normalize_dataframe(raw_df)
        if normalized_df.empty:
            raise EmptyDataError(
                f"Market data for ticker '{self.ticker}' contained zero valid rows after normalization."
            )

        # Attach source metadata
        normalized_df.attrs["ticker"] = self.ticker
        normalized_df.attrs["source"] = "Yahoo Finance"
        normalized_df.attrs["is_synthetic"] = False
        normalized_df.attrs["interval"] = interval

        return normalized_df

    def _validate_and_format_dates(
        self,
        start_date: Optional[Union[str, date, datetime, pd.Timestamp]],
        end_date: Optional[Union[str, date, datetime, pd.Timestamp]],
    ) -> tuple[Optional[str], Optional[str]]:
        """Validate date inputs and convert to ISO-8601 strings."""
        start_ts = None
        end_ts = None

        if start_date is not None:
            try:
                start_ts = pd.to_datetime(start_date)
            except Exception as e:
                raise InvalidDateRangeError(f"Invalid start_date '{start_date}': {e}") from e

        if end_date is not None:
            try:
                end_ts = pd.to_datetime(end_date)
            except Exception as e:
                raise InvalidDateRangeError(f"Invalid end_date '{end_date}': {e}") from e

        if start_ts is not None and end_ts is not None:
            if start_ts >= end_ts:
                raise InvalidDateRangeError(
                    f"Start date ({start_ts.strftime('%Y-%m-%d')}) must be strictly before "
                    f"end date ({end_ts.strftime('%Y-%m-%d')}). Note that Yahoo Finance end dates are exclusive."
                )

        start_str = start_ts.strftime("%Y-%m-%d") if start_ts is not None else None
        end_str = end_ts.strftime("%Y-%m-%d") if end_ts is not None else None

        return start_str, end_str

    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize yfinance DataFrame into standard schema.

        Handles:
            - MultiIndex columns (flattening to target ticker)
            - DatetimeIndex conversion to 'Date' column
            - Timezone removal (naive UTC date/timestamp)
            - Column renaming (canonical casing)
            - Chronological sorting
        """
        working_df = df.copy()

        # Handle MultiIndex columns
        if isinstance(working_df.columns, pd.MultiIndex):
            working_df = self._flatten_multiindex_columns(working_df)

        # Normalize column names: strip whitespace and match case
        col_map = {}
        for col in working_df.columns:
            cleaned = str(col).strip()
            lower_col = cleaned.lower()
            if lower_col == "open":
                col_map[col] = "Open"
            elif lower_col == "high":
                col_map[col] = "High"
            elif lower_col == "low":
                col_map[col] = "Low"
            elif lower_col == "close":
                col_map[col] = "Close"
            elif lower_col in ("adj close", "adj_close", "adjusted close", "adjclose"):
                col_map[col] = "Adj Close"
            elif lower_col in ("volume", "vol"):
                col_map[col] = "Volume"
            elif lower_col in ("date", "datetime", "timestamp"):
                col_map[col] = "Date"

        working_df = working_df.rename(columns=col_map)

        # Ensure Date column is present (from index if not already a column)
        if "Date" not in working_df.columns:
            if isinstance(working_df.index, pd.DatetimeIndex) or working_df.index.name in ("Date", "Datetime"):
                working_df = working_df.reset_index()
                # Rename the index column if needed
                if "index" in working_df.columns:
                    working_df = working_df.rename(columns={"index": "Date"})
                elif "Datetime" in working_df.columns:
                    working_df = working_df.rename(columns={"Datetime": "Date"})
            else:
                working_df = working_df.reset_index()
                first_col = working_df.columns[0]
                working_df = working_df.rename(columns={first_col: "Date"})

        # Format Date column to timezone-naive datetime
        working_df["Date"] = pd.to_datetime(working_df["Date"])
        if hasattr(working_df["Date"].dt, "tz") and working_df["Date"].dt.tz is not None:
            working_df["Date"] = working_df["Date"].dt.tz_localize(None)

        # Select only standard market columns
        available_cols = []
        for col in ["Date", "Open", "High", "Low", "Close"]:
            if col in working_df.columns:
                available_cols.append(col)
        if "Adj Close" in working_df.columns:
            available_cols.append("Adj Close")
        if "Volume" in working_df.columns:
            available_cols.append("Volume")

        working_df = working_df[available_cols]

        # Convert numeric columns
        numeric_cols = [c for c in available_cols if c != "Date"]
        for c in numeric_cols:
            working_df[c] = pd.to_numeric(working_df[c], errors="coerce")

        # Sort chronologically and reset index
        working_df = working_df.sort_values(by="Date", ascending=True).reset_index(drop=True)

        return working_df

    def _flatten_multiindex_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Flatten MultiIndex columns safely targeting this fetcher's ticker."""
        # Check if ticker is in level 1 (common: (Metric, Ticker))
        if self.ticker in df.columns.get_level_values(1):
            return df.xs(self.ticker, axis=1, level=1)

        # Check if ticker is in level 0 (common: (Ticker, Metric))
        if self.ticker in df.columns.get_level_values(0):
            return df.xs(self.ticker, axis=1, level=0)

        # Case-insensitive match on level 1 or 0
        for lvl in (1, 0):
            vals_upper = [str(v).upper() for v in df.columns.get_level_values(lvl)]
            if self.ticker in vals_upper:
                idx = vals_upper.index(self.ticker)
                actual_val = df.columns.get_level_values(lvl)[idx]
                return df.xs(actual_val, axis=1, level=lvl)

        # If MultiIndex has 2 levels but ticker isn't explicitly in the names,
        # drop level 1 if level 0 contains standard metric names
        lvl0_lower = [str(c).lower() for c in df.columns.get_level_values(0)]
        if any(m in lvl0_lower for m in ("open", "close", "high", "low", "volume")):
            df_copy = df.copy()
            df_copy.columns = df_copy.columns.get_level_values(0)
            return df_copy

        return df


def fetch_stock_data(
    ticker: str,
    start_date: Optional[Union[str, date, datetime, pd.Timestamp]] = None,
    end_date: Optional[Union[str, date, datetime, pd.Timestamp]] = None,
    period: Optional[str] = None,
    interval: str = "1d",
) -> pd.DataFrame:
    """Convenience function to fetch historical stock data.

    Args:
        ticker: Stock ticker symbol (e.g. 'AAPL', 'MSFT').
        start_date: Start date (inclusive).
        end_date: End date (exclusive).
        period: Alternative period string (e.g. '1y').
        interval: Bar interval (default '1d').

    Returns:
        Normalized DataFrame with OHLCV data.
    """
    fetcher = StockDataFetcher(ticker)
    return fetcher.fetch_history(
        start_date=start_date,
        end_date=end_date,
        period=period,
        interval=interval,
    )
