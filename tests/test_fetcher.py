"""Unit tests for Yahoo Finance stock data fetcher module."""

from unittest.mock import patch
import pandas as pd
import pytest

from stock_analyzer.data.fetcher import StockDataFetcher, fetch_stock_data
from stock_analyzer.data.exceptions import (
    DataFetchError,
    EmptyDataError,
    InvalidDateRangeError,
)


def _create_mock_single_level_df(dates, ticker="AAPL"):
    """Helper to create a standard single-level DataFrame mimicking yfinance."""
    n = len(dates)
    return pd.DataFrame(
        {
            "Open": [150.0 + i for i in range(n)],
            "High": [155.0 + i for i in range(n)],
            "Low": [149.0 + i for i in range(n)],
            "Close": [154.0 + i for i in range(n)],
            "Adj Close": [153.5 + i for i in range(n)],
            "Volume": [1000000 + i * 100000 for i in range(n)],
        },
        index=pd.to_datetime(dates),
    )


def _create_mock_multiindex_df(dates, ticker="AAPL"):
    """Helper to create a MultiIndex DataFrame (Price, Ticker) mimicking yfinance download."""
    cols = pd.MultiIndex.from_tuples(
        [
            ("Open", ticker),
            ("High", ticker),
            ("Low", ticker),
            ("Close", ticker),
            ("Adj Close", ticker),
            ("Volume", ticker),
        ]
    )
    data = [
        [150.0, 155.0, 149.0, 154.0, 153.5, 1000000],
        [151.0, 156.0, 150.0, 155.0, 154.5, 1200000],
        [152.0, 157.0, 151.0, 156.0, 155.5, 1100000],
    ]
    return pd.DataFrame(data, index=pd.to_datetime(dates), columns=cols)


class TestStockDataFetcher:
    """Tests for StockDataFetcher class."""

    def test_init_valid_ticker(self):
        fetcher = StockDataFetcher("aapl")
        assert fetcher.ticker == "AAPL"

    def test_init_invalid_ticker(self):
        with pytest.raises(ValueError, match="non-empty string"):
            StockDataFetcher("")
        with pytest.raises(ValueError, match="non-empty string"):
            StockDataFetcher("   ")

    @patch("yfinance.download")
    def test_successful_fetch_single_level(self, mock_download):
        mock_dates = ["2026-01-05", "2026-01-06", "2026-01-07"]
        mock_download.return_value = _create_mock_single_level_df(mock_dates, "AAPL")

        fetcher = StockDataFetcher("AAPL")
        df = fetcher.fetch_history(start_date="2026-01-05", end_date="2026-01-08")

        mock_download.assert_called_once()
        assert not df.empty
        assert len(df) == 3
        assert list(df.columns) == ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        assert df["Date"].iloc[0] == pd.Timestamp("2026-01-05")
        assert df.attrs["ticker"] == "AAPL"
        assert df.attrs["source"] == "Yahoo Finance"
        assert df.attrs["is_synthetic"] is False

    @patch("yfinance.download")
    def test_multiindex_response_handling(self, mock_download):
        mock_dates = ["2026-01-05", "2026-01-06", "2026-01-07"]
        mock_download.return_value = _create_mock_multiindex_df(mock_dates, "MSFT")

        fetcher = StockDataFetcher("MSFT")
        df = fetcher.fetch_history(start_date="2026-01-05", end_date="2026-01-08")

        assert not df.empty
        assert len(df) == 3
        assert not isinstance(df.columns, pd.MultiIndex)
        assert "Close" in df.columns
        assert "Volume" in df.columns
        assert df["Close"].iloc[0] == 154.0

    @patch("yfinance.download")
    def test_empty_response_raises_error(self, mock_download):
        mock_download.return_value = pd.DataFrame()

        fetcher = StockDataFetcher("INVALID")
        with pytest.raises(EmptyDataError, match="No market data found for ticker 'INVALID'"):
            fetcher.fetch_history(start_date="2026-01-01", end_date="2026-01-10")

    @patch("yfinance.download")
    def test_failed_download_network_error(self, mock_download):
        mock_download.side_effect = RuntimeError("Connection timeout")

        fetcher = StockDataFetcher("AAPL")
        with pytest.raises(DataFetchError, match="Failed to fetch market data"):
            fetcher.fetch_history(start_date="2026-01-01", end_date="2026-01-10")

    def test_invalid_date_range_start_after_end(self):
        fetcher = StockDataFetcher("AAPL")
        with pytest.raises(InvalidDateRangeError, match="must be strictly before"):
            fetcher.fetch_history(start_date="2026-01-10", end_date="2026-01-05")

    def test_invalid_date_range_same_day(self):
        fetcher = StockDataFetcher("AAPL")
        with pytest.raises(InvalidDateRangeError, match="must be strictly before"):
            fetcher.fetch_history(start_date="2026-01-10", end_date="2026-01-10")

    def test_unparseable_dates(self):
        fetcher = StockDataFetcher("AAPL")
        with pytest.raises(InvalidDateRangeError, match="Invalid start_date"):
            fetcher.fetch_history(start_date="not-a-date", end_date="2026-01-10")

    @patch("yfinance.download")
    def test_convenience_function(self, mock_download):
        mock_dates = ["2026-01-05", "2026-01-06"]
        mock_download.return_value = _create_mock_single_level_df(mock_dates, "GOOGL")

        df = fetch_stock_data("GOOGL", start_date="2026-01-05", end_date="2026-01-07")
        assert len(df) == 2
        assert df.attrs["ticker"] == "GOOGL"
