"""Unit tests for technical indicators and moving averages module."""

import numpy as np
import pandas as pd
import pytest

from stock_analyzer.analysis.indicators import (
    TechnicalIndicators,
    calculate_sma_20,
    calculate_sma_50,
    calculate_ema_20,
    calculate_moving_averages,
    add_moving_averages,
)
from stock_analyzer.data.exceptions import (
    DataValidationError,
    EmptyDataError,
    MissingColumnError,
)


def _generate_synthetic_stock_df(num_rows: int, start_price: float = 100.0, step: float = 1.0) -> pd.DataFrame:
    """Generate deterministic OHLCV DataFrame with specified number of rows."""
    dates = pd.date_range("2026-01-01", periods=num_rows, freq="B")
    prices = [start_price + i * step for i in range(num_rows)]
    return pd.DataFrame(
        {
            "Date": dates.strftime("%Y-%m-%d"),
            "Open": [p - 0.5 for p in prices],
            "High": [p + 1.0 for p in prices],
            "Low": [p - 1.0 for p in prices],
            "Close": prices,
            "Adj Close": [p - 0.2 for p in prices],
            "Volume": [100000 + i * 1000 for i in range(num_rows)],
        }
    )


class TestTechnicalIndicatorsValidation:
    """Tests input validation, type safety, and defensive copying."""

    def test_invalid_input_type_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected pandas DataFrame"):
            TechnicalIndicators("not_a_df")  # type: ignore

    def test_empty_dataframe_raises_empty_data_error(self):
        with pytest.raises(EmptyDataError, match="Cannot calculate technical indicators on an empty DataFrame"):
            TechnicalIndicators(pd.DataFrame())

    def test_missing_required_columns_raises_missing_column_error(self):
        df = pd.DataFrame({"Date": ["2026-01-01"], "Close": [100.0]})
        with pytest.raises(MissingColumnError, match="DataFrame lacks mandatory OHLCV columns"):
            TechnicalIndicators(df)

    def test_missing_specified_price_column_raises_missing_column_error(self):
        df = _generate_synthetic_stock_df(5)
        with pytest.raises(MissingColumnError, match="Specified price column 'NonExistent' not found"):
            TechnicalIndicators(df, price_column="NonExistent")

    def test_non_numeric_price_column_raises_data_validation_error(self):
        df = _generate_synthetic_stock_df(5)
        df["Close"] = ["100", "101", "102", "103", "104"]  # object dtype
        with pytest.raises(DataValidationError, match="must have numeric data type"):
            TechnicalIndicators(df, price_column="Close")

    def test_invalid_window_or_span_raises_value_error(self):
        df = _generate_synthetic_stock_df(25)
        ti = TechnicalIndicators(df)
        with pytest.raises(ValueError, match="Window must be a positive integer"):
            ti.calculate_sma(window=0)
        with pytest.raises(ValueError, match="Window must be a positive integer"):
            ti.calculate_sma(window=-5)
        with pytest.raises(ValueError, match="Span must be a positive integer"):
            ti.calculate_ema(span=0)

    def test_input_dataframe_immutability(self):
        df = _generate_synthetic_stock_df(30)
        original_copy = df.copy(deep=True)
        ti = TechnicalIndicators(df)
        result_df = ti.calculate_moving_averages()

        # Input DataFrame must not be mutated
        pd.testing.assert_frame_equal(df, original_copy)
        assert "SMA_20" not in df.columns
        assert "SMA_20" in result_df.columns


class TestChronologicalOrdering:
    """Tests chronological ordering enforcement before indicator calculations."""

    def test_unsorted_input_is_sorted_chronologically(self):
        df = _generate_synthetic_stock_df(25)
        # Reverse the DataFrame order
        reversed_df = df.iloc[::-1].copy().reset_index(drop=True)

        ti = TechnicalIndicators(reversed_df)
        # Internal df must be sorted chronologically
        assert list(ti.df["Close"]) == list(df["Close"])
        # The rolling calculation operates on chronological sequence
        sma20 = ti.calculate_sma_20()
        expected_at_19 = df["Close"].iloc[:20].mean()
        assert sma20.iloc[19] == pytest.approx(expected_at_19)


class TestSMA20Calculation:
    """Tests mathematical correctness and warm-up behavior of SMA 20."""

    def test_sma20_known_linear_sequence(self):
        # 30 observations where Close = 101, 102, ..., 130
        df = _generate_synthetic_stock_df(30, start_price=101.0, step=1.0)
        ti = TechnicalIndicators(df)
        sma20 = ti.calculate_sma_20()

        assert sma20.name == "SMA_20"
        assert len(sma20) == 30

        # First 19 observations (indices 0..18) must be NaN
        assert sma20.iloc[:19].isna().all()
        assert sma20.iloc[:19].isna().sum() == 19

        # Observation at index 19 (20th row): average of [101, 102, ..., 120] = 110.5
        expected_19 = sum(range(101, 121)) / 20.0
        assert expected_19 == 110.5
        assert sma20.iloc[19] == pytest.approx(110.5)

        # Observation at index 20 (21st row): average of [102, 103, ..., 121] = 111.5
        assert sma20.iloc[20] == pytest.approx(111.5)

        # Observation at index 29 (30th row): average of [111, 112, ..., 130] = 120.5
        assert sma20.iloc[29] == pytest.approx(120.5)


class TestSMA50Calculation:
    """Tests mathematical correctness and warm-up behavior of SMA 50."""

    def test_sma50_known_linear_sequence(self):
        # 60 observations where Close = 1, 2, ..., 60
        df = _generate_synthetic_stock_df(60, start_price=1.0, step=1.0)
        ti = TechnicalIndicators(df)
        sma50 = ti.calculate_sma_50()

        assert sma50.name == "SMA_50"
        assert len(sma50) == 60

        # First 49 observations (indices 0..48) must be NaN
        assert sma50.iloc[:49].isna().all()
        assert sma50.iloc[:49].isna().sum() == 49

        # Observation at index 49 (50th row): average of [1, 2, ..., 50] = 50 * 51 / (2 * 50) = 25.5
        assert sma50.iloc[49] == pytest.approx(25.5)

        # Observation at index 50: average of [2, 3, ..., 51] = 26.5
        assert sma50.iloc[50] == pytest.approx(26.5)


class TestEMA20Calculation:
    """Tests mathematical correctness and warm-up behavior of EMA 20."""

    def test_ema20_known_recursive_sequence(self):
        # 30 observations where Close = 10, 11, ..., 39
        df = _generate_synthetic_stock_df(30, start_price=10.0, step=1.0)
        ti = TechnicalIndicators(df)
        ema20 = ti.calculate_ema_20()

        assert ema20.name == "EMA_20"
        assert len(ema20) == 30

        # First 19 observations must be NaN
        assert ema20.iloc[:19].isna().all()
        assert ema20.iloc[:19].isna().sum() == 19

        # Independent manual calculation of EMA with span=20, adjust=False:
        # alpha = 2 / (20 + 1) = 2 / 21
        prices = list(df["Close"])
        alpha = 2.0 / 21.0
        manual_ema = [prices[0]]
        for p in prices[1:]:
            manual_ema.append(alpha * p + (1.0 - alpha) * manual_ema[-1])

        # At index 19 (20th row)
        assert ema20.iloc[19] == pytest.approx(manual_ema[19], rel=1e-10)
        # At index 20 (21st row)
        assert ema20.iloc[20] == pytest.approx(manual_ema[20], rel=1e-10)
        # At index 29 (30th row)
        assert ema20.iloc[29] == pytest.approx(manual_ema[29], rel=1e-10)


class TestDatasetLengthThresholds:
    """Tests indicator behavior across various dataset sizes."""

    def test_dataset_shorter_than_20_observations(self):
        # 10 rows: shorter than 20 observations
        df = _generate_synthetic_stock_df(10)
        ti = TechnicalIndicators(df)
        result = ti.calculate_moving_averages()

        # All indicators must be entirely NaN
        assert result["SMA_20"].isna().all()
        assert result["SMA_50"].isna().all()
        assert result["EMA_20"].isna().all()

    def test_dataset_between_20_and_49_observations(self):
        # 35 rows: enough for SMA20 and EMA20, but not enough for SMA50
        df = _generate_synthetic_stock_df(35)
        ti = TechnicalIndicators(df)
        result = ti.calculate_moving_averages()

        # SMA_20: exactly 19 NaNs, 16 valid values
        assert result["SMA_20"].iloc[:19].isna().all()
        assert result["SMA_20"].iloc[19:].notna().all()
        assert len(result["SMA_20"].dropna()) == 16

        # EMA_20: exactly 19 NaNs, 16 valid values
        assert result["EMA_20"].iloc[:19].isna().all()
        assert result["EMA_20"].iloc[19:].notna().all()
        assert len(result["EMA_20"].dropna()) == 16

        # SMA_50: entirely NaN (needs 50 observations)
        assert result["SMA_50"].isna().all()

    def test_dataset_with_at_least_50_observations(self):
        # 60 rows: all three indicators produce valid values
        df = _generate_synthetic_stock_df(60)
        ti = TechnicalIndicators(df)
        result = ti.calculate_moving_averages()

        # SMA_20: 19 NaNs, 41 non-null
        assert result["SMA_20"].iloc[:19].isna().all()
        assert len(result["SMA_20"].dropna()) == 41

        # EMA_20: 19 NaNs, 41 non-null
        assert result["EMA_20"].iloc[:19].isna().all()
        assert len(result["EMA_20"].dropna()) == 41

        # SMA_50: 49 NaNs, 11 non-null
        assert result["SMA_50"].iloc[:49].isna().all()
        assert len(result["SMA_50"].dropna()) == 11


class TestCustomPriceColumnAndColumnPreservation:
    """Tests custom price column selection and original column preservation."""

    def test_custom_price_column_adj_close(self):
        df = _generate_synthetic_stock_df(25)
        ti = TechnicalIndicators(df, price_column="Adj Close")
        sma20 = ti.calculate_sma_20()

        expected_adj_close_20 = df["Adj Close"].iloc[:20].mean()
        assert sma20.iloc[19] == pytest.approx(expected_adj_close_20)

    def test_preservation_of_all_original_columns(self):
        df = _generate_synthetic_stock_df(55)
        df["CustomMeta"] = "CustomValue"
        ti = TechnicalIndicators(df)
        result = ti.calculate_moving_averages()

        for col in ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume", "CustomMeta"]:
            assert col in result.columns
            assert list(result[col]) == list(df[col])

        assert "SMA_20" in result.columns
        assert "SMA_50" in result.columns
        assert "EMA_20" in result.columns


class TestConvenienceWrappers:
    """Tests module-level convenience functions and individual indicator addition methods."""

    def test_standalone_calculate_functions(self):
        df = _generate_synthetic_stock_df(55)
        sma20 = calculate_sma_20(df)
        sma50 = calculate_sma_50(df)
        ema20 = calculate_ema_20(df)

        assert isinstance(sma20, pd.Series)
        assert isinstance(sma50, pd.Series)
        assert isinstance(ema20, pd.Series)
        assert sma20.name == "SMA_20"
        assert sma50.name == "SMA_50"
        assert ema20.name == "EMA_20"

    def test_calculate_and_add_moving_averages(self):
        df = _generate_synthetic_stock_df(55)
        res1 = calculate_moving_averages(df)
        res2 = add_moving_averages(df)

        pd.testing.assert_frame_equal(res1, res2)
        assert {"SMA_20", "SMA_50", "EMA_20"}.issubset(res1.columns)

    def test_individual_add_methods(self):
        df = _generate_synthetic_stock_df(55)
        ti = TechnicalIndicators(df)

        d1 = ti.add_sma_20()
        assert "SMA_20" in d1.columns
        assert "SMA_50" not in d1.columns

        d2 = ti.add_sma_50()
        assert "SMA_50" in d2.columns
        assert "SMA_20" not in d2.columns

        d3 = ti.add_ema_20()
        assert "EMA_20" in d3.columns
        assert "SMA_20" not in d3.columns
