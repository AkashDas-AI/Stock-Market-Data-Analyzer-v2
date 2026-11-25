"""Integration tests verifying consistency across Yahoo Finance and CSV ingestion paths."""

from unittest.mock import patch
import pandas as pd
import pytest

from stock_analyzer.data.fetcher import fetch_stock_data
from stock_analyzer.data.loader import load_stock_csv
from stock_analyzer.data.loader import REQUIRED_COLUMNS


@patch("yfinance.download")
def test_consistent_schema_across_ingestion_paths(mock_download, tmp_path):
    """Verify that both Yahoo Finance and CSV ingestion produce identical normalized structures."""
    # 1. Setup mock Yahoo Finance response
    mock_dates = ["2026-01-05", "2026-01-06"]
    mock_download.return_value = pd.DataFrame(
        {
            "Open": [150.0, 151.0],
            "High": [155.0, 156.0],
            "Low": [149.0, 150.0],
            "Close": [154.0, 155.0],
            "Adj Close": [153.5, 154.5],
            "Volume": [1000000, 1200000],
        },
        index=pd.to_datetime(mock_dates),
    )

    # 2. Setup equivalent CSV file
    csv_file = tmp_path / "stock_data.csv"
    csv_file.write_text(
        "Date,Open,High,Low,Close,Adj Close,Volume\n"
        "2026-01-05,150.0,155.0,149.0,154.0,153.5,1000000\n"
        "2026-01-06,151.0,156.0,150.0,155.0,154.5,1200000\n",
        encoding="utf-8",
    )

    yf_df = fetch_stock_data("AAPL", start_date="2026-01-05", end_date="2026-01-07")
    csv_df = load_stock_csv(csv_file)

    # Assert column lists match exactly
    assert list(yf_df.columns) == list(csv_df.columns)
    for col in REQUIRED_COLUMNS:
        assert col in yf_df.columns
        assert col in csv_df.columns

    # Assert dtypes match
    assert yf_df["Date"].dtype == csv_df["Date"].dtype
    assert pd.api.types.is_datetime64_any_dtype(yf_df["Date"])
    assert pd.api.types.is_float_dtype(yf_df["Close"])
    assert pd.api.types.is_float_dtype(csv_df["Close"])

    # Assert shape and record counts match
    assert yf_df.shape == csv_df.shape

    # Assert sources are distinguishable
    assert yf_df.attrs["source"] == "Yahoo Finance"
    assert csv_df.attrs["source"] == "Local CSV"
    assert yf_df.attrs["is_synthetic"] is False
    assert csv_df.attrs["is_synthetic"] is False
