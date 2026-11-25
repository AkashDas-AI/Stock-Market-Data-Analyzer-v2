"""Unit tests for return calculation and cumulative growth module."""

import numpy as np
import pandas as pd
import pytest

from stock_analyzer.analysis.returns import (
    ReturnAnalyzer,
    calculate_daily_returns,
    calculate_cumulative_returns,
    add_return_metrics,
)
from stock_analyzer.data.exceptions import (
    DataValidationError,
    EmptyDataError,
    MissingColumnError,
)


@pytest.fixture
def sample_known_returns_df() -> pd.DataFrame:
    """Fixture providing a deterministic 4-row price series with known return properties.

    Prices: 100.0, 110.0, 99.0, 108.90
    R_1 = (110 - 100) / 100 = +0.10 (+10.0%)
    R_2 = (99 - 110) / 110 = -0.10 (-10.0%)
    R_3 = (108.9 - 99) / 99 = +0.10 (+10.0%)
    Cum_1 = 1.10 - 1 = +0.10 (+10.0%)
    Cum_2 = 1.10 * 0.90 - 1 = 0.99 - 1 = -0.01 (-1.0%)
    Cum_3 = 0.99 * 1.10 - 1 = 1.089 - 1 = +0.089 (+8.9%)
    Notice: Sum of returns is 0.10 - 0.10 + 0.10 = 0.10 != 0.089 (compound return).
    """
    return pd.DataFrame(
        {
            "Date": ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"],
            "Open": [99.0, 109.0, 100.0, 105.0],
            "High": [102.0, 112.0, 102.0, 110.0],
            "Low": [98.0, 108.0, 98.0, 104.0],
            "Close": [100.0, 110.0, 99.0, 108.90],
            "Adj Close": [99.5, 109.5, 98.5, 108.40],
            "Volume": [10000, 12000, 11000, 13000],
        }
    )


class TestReturnAnalyzerValidation:
    """Tests input validation, type enforcement, and defensive copying."""

    def test_invalid_input_type_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected pandas DataFrame"):
            ReturnAnalyzer("not_a_df")  # type: ignore

    def test_empty_dataframe_raises_empty_data_error(self):
        with pytest.raises(EmptyDataError, match="Cannot perform return calculations on an empty DataFrame"):
            ReturnAnalyzer(pd.DataFrame())

    def test_missing_price_column_raises_missing_column_error(self, sample_known_returns_df):
        with pytest.raises(MissingColumnError, match="Specified price column 'NonExistent' not found"):
            ReturnAnalyzer(sample_known_returns_df, price_column="NonExistent")

    def test_non_numeric_price_column_raises_data_validation_error(self, sample_known_returns_df):
        df = sample_known_returns_df.copy()
        df["Close"] = ["100", "110", "99", "108.9"]  # string objects
        with pytest.raises(DataValidationError, match="must have numeric data type"):
            ReturnAnalyzer(df, price_column="Close")

    def test_input_dataframe_immutability(self, sample_known_returns_df):
        original = sample_known_returns_df.copy(deep=True)
        analyzer = ReturnAnalyzer(sample_known_returns_df)
        res = analyzer.add_return_metrics()

        pd.testing.assert_frame_equal(sample_known_returns_df, original)
        assert "Daily_Return" not in sample_known_returns_df.columns
        assert "Daily_Return" in res.columns


class TestDailyReturnsCalculation:
    """Tests daily return calculations, missing value behavior, and ordering."""

    def test_daily_returns_known_values(self, sample_known_returns_df):
        analyzer = ReturnAnalyzer(sample_known_returns_df)
        returns = analyzer.calculate_daily_returns()

        assert len(returns) == 4
        assert returns.name == "Daily_Return"

        # Observation 0 must be NaN (no previous day price)
        assert np.isnan(returns.iloc[0])

        # Observations 1, 2, 3
        assert returns.iloc[1] == pytest.approx(0.10)
        assert returns.iloc[2] == pytest.approx(-0.10)
        assert returns.iloc[3] == pytest.approx(0.10)

    def test_first_observation_is_nan_and_not_filled_with_zero(self, sample_known_returns_df):
        returns = calculate_daily_returns(sample_known_returns_df)
        assert pd.isna(returns.iloc[0])
        assert returns.iloc[0] != 0.0

    def test_chronological_ordering_enforcement(self, sample_known_returns_df):
        # Reverse the order of rows
        reversed_df = sample_known_returns_df.iloc[::-1].copy().reset_index(drop=True)
        analyzer = ReturnAnalyzer(reversed_df)
        returns = analyzer.calculate_daily_returns()

        # Returns should be computed on forward chronological sequence
        assert np.isnan(returns.iloc[0])
        assert returns.iloc[1] == pytest.approx(0.10)
        assert returns.iloc[2] == pytest.approx(-0.10)
        assert returns.iloc[3] == pytest.approx(0.10)

    def test_custom_price_column(self, sample_known_returns_df):
        analyzer = ReturnAnalyzer(sample_known_returns_df, price_column="Adj Close")
        adj_returns = analyzer.calculate_daily_returns()

        expected_1 = (109.5 - 99.5) / 99.5
        assert adj_returns.iloc[1] == pytest.approx(expected_1)


class TestCumulativeReturnsCalculation:
    """Tests cumulative compound return calculations against ground truth."""

    def test_cumulative_returns_known_values(self, sample_known_returns_df):
        analyzer = ReturnAnalyzer(sample_known_returns_df)
        cum_ret = analyzer.calculate_cumulative_returns()

        assert len(cum_ret) == 4
        assert cum_ret.name == "Cumulative_Return"

        # Observation 0 is NaN, preserving initial missing return behavior
        assert pd.isna(cum_ret.iloc[0])

        # Observations 1, 2, 3
        assert cum_ret.iloc[1] == pytest.approx(0.10)
        assert cum_ret.iloc[2] == pytest.approx(-0.01)
        assert cum_ret.iloc[3] == pytest.approx(0.089)

        # Distinguish compound cumulative return from cumulative sum of returns
        daily_ret = analyzer.calculate_daily_returns().dropna()
        cumsum_ret = daily_ret.cumsum().iloc[-1]
        assert cumsum_ret == pytest.approx(0.10)
        assert cum_ret.iloc[3] != pytest.approx(cumsum_ret)
        assert cum_ret.iloc[3] == pytest.approx(0.089)

    def test_cumulative_growth_wealth_index(self, sample_known_returns_df):
        analyzer = ReturnAnalyzer(sample_known_returns_df)
        wealth = analyzer.calculate_cumulative_growth(initial_wealth=1000.0)

        assert wealth.iloc[0] == pytest.approx(1000.0)
        assert wealth.iloc[1] == pytest.approx(1100.0)
        assert wealth.iloc[2] == pytest.approx(990.0)
        assert wealth.iloc[3] == pytest.approx(1089.0)


class TestEdgeCasesAndWrappers:
    """Tests edge cases (flat, rising, falling prices) and convenience functions."""

    def test_flat_prices(self):
        df = pd.DataFrame(
            {
                "Date": ["2026-01-05", "2026-01-06", "2026-01-07"],
                "Close": [100.0, 100.0, 100.0],
            }
        )
        analyzer = ReturnAnalyzer(df)
        daily = analyzer.calculate_daily_returns()
        cum = analyzer.calculate_cumulative_returns()

        assert pd.isna(daily.iloc[0])
        assert (daily.iloc[1:] == 0.0).all()
        assert pd.isna(cum.iloc[0])
        assert (cum.iloc[1:] == 0.0).all()

    def test_strictly_rising_prices(self):
        df = pd.DataFrame(
            {
                "Date": ["2026-01-05", "2026-01-06", "2026-01-07"],
                "Close": [100.0, 105.0, 110.25],
            }
        )
        analyzer = ReturnAnalyzer(df)
        daily = analyzer.calculate_daily_returns()
        cum = analyzer.calculate_cumulative_returns()

        assert (daily.iloc[1:] > 0.0).all()
        assert cum.iloc[1] == pytest.approx(0.05)
        assert cum.iloc[2] == pytest.approx(0.1025)

    def test_strictly_falling_prices(self):
        df = pd.DataFrame(
            {
                "Date": ["2026-01-05", "2026-01-06", "2026-01-07"],
                "Close": [100.0, 80.0, 60.0],
            }
        )
        analyzer = ReturnAnalyzer(df)
        daily = analyzer.calculate_daily_returns()
        cum = analyzer.calculate_cumulative_returns()

        assert (daily.iloc[1:] < 0.0).all()
        assert daily.iloc[1] == pytest.approx(-0.20)
        assert daily.iloc[2] == pytest.approx(-0.25)
        assert cum.iloc[1] == pytest.approx(-0.20)
        assert cum.iloc[2] == pytest.approx(-0.40)

    def test_add_return_metrics_wrapper(self, sample_known_returns_df):
        res = add_return_metrics(sample_known_returns_df)

        for col in ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]:
            assert col in res.columns
            assert list(res[col]) == list(sample_known_returns_df[col])

        assert "Daily_Return" in res.columns
        assert "Cumulative_Return" in res.columns
        assert pd.isna(res["Daily_Return"].iloc[0])
        assert res["Cumulative_Return"].iloc[3] == pytest.approx(0.089)
