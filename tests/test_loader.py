"""Unit tests for CSV stock data loader module."""

import pytest
import pandas as pd
from pathlib import Path

from stock_analyzer.data.loader import (
    StockDataLoader,
    load_stock_csv,
    load_sample_stock_data,
    REQUIRED_COLUMNS,
)
from stock_analyzer.data.exceptions import (
    DataLoadingError,
    EmptyDataError,
    MissingColumnError,
    InvalidDateError,
)
from stock_analyzer.utils.config import SAMPLE_STOCK_CSV


class TestStockDataLoader:
    """Tests for StockDataLoader class."""

    def test_init_invalid_path(self):
        with pytest.raises(ValueError, match="File path must be provided"):
            StockDataLoader("")

    def test_file_not_found(self):
        loader = StockDataLoader("non_existent_file.csv")
        with pytest.raises(DataLoadingError, match="File not found"):
            loader.load_csv()

    def test_empty_csv_file(self, tmp_path):
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("", encoding="utf-8")

        loader = StockDataLoader(empty_file)
        with pytest.raises(EmptyDataError):
            loader.load_csv()

    def test_successful_csv_load(self, tmp_path):
        csv_file = tmp_path / "valid.csv"
        content = (
            "Date,Open,High,Low,Close,Adj Close,Volume\n"
            "2026-01-05,150.0,155.0,149.0,154.0,153.5,1000000\n"
            "2026-01-06,151.0,156.0,150.0,155.0,154.5,1200000\n"
        )
        csv_file.write_text(content, encoding="utf-8")

        loader = StockDataLoader(csv_file)
        df = loader.load_csv()

        assert not df.empty
        assert len(df) == 2
        for col in REQUIRED_COLUMNS:
            assert col in df.columns
        assert "Adj Close" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["Date"])
        assert df["Close"].iloc[0] == 154.0
        assert df.attrs["is_synthetic"] is False
        assert df.attrs["source"] == "Local CSV"

    def test_column_name_variations(self, tmp_path):
        csv_file = tmp_path / "variations.csv"
        content = (
            "date,OPEN,High,low,CLOSE,adj_close,vol\n"
            "2026-01-05,150.0,155.0,149.0,154.0,153.5,1000000\n"
        )
        csv_file.write_text(content, encoding="utf-8")

        loader = StockDataLoader(csv_file)
        df = loader.load_csv()

        assert list(df.columns) == ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
        assert df["Date"].iloc[0] == pd.Timestamp("2026-01-05")

    def test_missing_required_columns(self, tmp_path):
        csv_file = tmp_path / "missing_cols.csv"
        content = (
            "Date,Open,High,Low\n"
            "2026-01-05,150.0,155.0,149.0\n"
        )
        csv_file.write_text(content, encoding="utf-8")

        loader = StockDataLoader(csv_file)
        with pytest.raises(MissingColumnError, match="missing mandatory columns"):
            loader.load_csv()

    def test_invalid_date_values(self, tmp_path):
        csv_file = tmp_path / "bad_date.csv"
        content = (
            "Date,Open,High,Low,Close,Volume\n"
            "not-a-valid-date,150.0,155.0,149.0,154.0,1000000\n"
        )
        csv_file.write_text(content, encoding="utf-8")

        loader = StockDataLoader(csv_file)
        with pytest.raises(InvalidDateError, match="invalid date values"):
            loader.load_csv()

    def test_load_sample_dataset(self):
        assert SAMPLE_STOCK_CSV.exists()
        df = StockDataLoader.load_sample()

        assert not df.empty
        assert len(df) == 75
        for col in REQUIRED_COLUMNS:
            assert col in df.columns
        assert df.attrs["is_synthetic"] is True
        assert "Synthetic" in df.attrs["source"]

    def test_convenience_functions(self, tmp_path):
        csv_file = tmp_path / "conv.csv"
        content = (
            "Date,Open,High,Low,Close,Volume\n"
            "2026-01-05,150.0,155.0,149.0,154.0,1000000\n"
        )
        csv_file.write_text(content, encoding="utf-8")

        df1 = load_stock_csv(csv_file)
        assert len(df1) == 1

        df_sample = load_sample_stock_data()
        assert len(df_sample) == 75
        assert df_sample.attrs["is_synthetic"] is True
