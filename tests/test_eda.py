"""Unit tests for the Exploratory Data Analysis (EDA) module."""

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Enforce headless backend for deterministic headless testing
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from stock_analyzer.analysis.eda import (
    ExploratoryDataAnalyzer,
    generate_summary_statistics,
    compute_correlation_matrix,
    generate_eda_summary,
    plot_price_distribution,
    plot_volume_distribution,
    plot_ohlc_distributions,
    plot_correlation_heatmap,
    plot_high_low_spread,
)
from stock_analyzer.data.exceptions import (
    DataValidationError,
    EmptyDataError,
    MissingColumnError,
)


@pytest.fixture
def sample_known_df() -> pd.DataFrame:
    """Fixture providing a deterministic 5-row OHLCV dataset with known mathematical properties."""
    return pd.DataFrame(
        {
            "Date": ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"],
            "Open": [100.0, 102.0, 104.0, 106.0, 108.0],
            "High": [105.0, 107.0, 109.0, 111.0, 113.0],
            "Low": [95.0, 97.0, 99.0, 101.0, 103.0],
            "Close": [102.0, 104.0, 106.0, 108.0, 110.0],
            "Adj Close": [101.0, 103.0, 105.0, 107.0, 109.0],
            "Volume": [1000, 2000, 3000, 4000, 5000],
        }
    )


class TestExploratoryDataAnalyzerValidation:
    """Tests input validation and defensive copying for ExploratoryDataAnalyzer."""

    def test_invalid_input_type_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected pandas DataFrame"):
            ExploratoryDataAnalyzer("not_a_df")  # type: ignore

    def test_empty_dataframe_raises_empty_data_error(self):
        empty_df = pd.DataFrame()
        with pytest.raises(EmptyDataError, match="Cannot perform exploratory data analysis on an empty DataFrame"):
            ExploratoryDataAnalyzer(empty_df)

    def test_missing_required_columns_raises_missing_column_error(self):
        incomplete_df = pd.DataFrame(
            {
                "Date": ["2026-01-05"],
                "Open": [100.0],
                "Close": [105.0],
            }
        )
        with pytest.raises(MissingColumnError, match="DataFrame lacks mandatory OHLCV columns"):
            ExploratoryDataAnalyzer(incomplete_df)

    def test_input_immutability(self, sample_known_df):
        original_copy = sample_known_df.copy(deep=True)
        analyzer = ExploratoryDataAnalyzer(sample_known_df, ticker="TEST")

        # Mutate analyzer internal DataFrame copy
        analyzer.df.loc[0, "Close"] = 999.0

        # Verify original DataFrame remained unchanged
        pd.testing.assert_frame_equal(sample_known_df, original_copy)
        assert sample_known_df.loc[0, "Close"] == 102.0


class TestSummaryStatistics:
    """Tests descriptive statistical calculations."""

    def test_summary_statistics_metrics_and_dimensions(self, sample_known_df):
        analyzer = ExploratoryDataAnalyzer(sample_known_df, ticker="TEST")
        stats = analyzer.compute_summary_statistics()

        expected_metrics = ["count", "mean", "std", "min", "25%", "50%", "75%", "max", "iqr"]
        for metric in expected_metrics:
            assert metric in stats.index

        expected_cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
        for col in expected_cols:
            assert col in stats.columns

    def test_summary_statistics_known_values(self, sample_known_df):
        analyzer = ExploratoryDataAnalyzer(sample_known_df, ticker="TEST")
        stats = analyzer.compute_summary_statistics()

        # Known calculations for Close: [102, 104, 106, 108, 110]
        # count: 5
        # mean: 106.0
        # median (50%): 106.0
        # min: 102.0
        # max: 110.0
        # 25%: 104.0
        # 75%: 108.0
        # iqr: 108.0 - 104.0 = 4.0
        # std: np.std([102, 104, 106, 108, 110], ddof=1) = sqrt(40 / 4) = sqrt(10) ~= 3.16227766
        assert stats.loc["count", "Close"] == 5.0
        assert stats.loc["mean", "Close"] == pytest.approx(106.0)
        assert stats.loc["50%", "Close"] == pytest.approx(106.0)
        assert stats.loc["min", "Close"] == pytest.approx(102.0)
        assert stats.loc["max", "Close"] == pytest.approx(110.0)
        assert stats.loc["25%", "Close"] == pytest.approx(104.0)
        assert stats.loc["75%", "Close"] == pytest.approx(108.0)
        assert stats.loc["iqr", "Close"] == pytest.approx(4.0)
        assert stats.loc["std", "Close"] == pytest.approx(np.sqrt(10.0))

    def test_custom_percentiles(self, sample_known_df):
        analyzer = ExploratoryDataAnalyzer(sample_known_df)
        stats = analyzer.compute_summary_statistics(percentiles=[0.10, 0.90])

        assert "10%" in stats.index
        assert "90%" in stats.index
        assert stats.loc["10%", "Close"] == pytest.approx(102.8)
        assert stats.loc["90%", "Close"] == pytest.approx(109.2)

    def test_invalid_percentile_raises_value_error(self, sample_known_df):
        analyzer = ExploratoryDataAnalyzer(sample_known_df)
        with pytest.raises(ValueError, match="Percentile values must be between 0.0 and 1.0"):
            analyzer.compute_summary_statistics(percentiles=[1.5])

        with pytest.raises(ValueError, match="Percentile values must be between 0.0 and 1.0"):
            analyzer.compute_summary_statistics(percentiles=[-0.1])

    def test_missing_values_in_optional_column(self, sample_known_df):
        df_with_nan = sample_known_df.copy()
        df_with_nan.loc[0, "Adj Close"] = np.nan
        analyzer = ExploratoryDataAnalyzer(df_with_nan)
        stats = analyzer.compute_summary_statistics()

        assert stats.loc["count", "Adj Close"] == 4.0
        assert stats.loc["count", "Close"] == 5.0


class TestPriceAndVolumeSummary:
    """Tests price range, spread, and volume exploration logic."""

    def test_price_and_volume_summary_values(self, sample_known_df):
        sample_known_df.attrs["is_synthetic"] = True
        analyzer = ExploratoryDataAnalyzer(sample_known_df, ticker="TEST")
        summary = analyzer.compute_price_and_volume_summary()

        assert summary["ticker"] == "TEST"
        assert summary["is_synthetic"] is True
        assert summary["total_observations"] == 5
        assert summary["date_range"]["start"] == "2026-01-05"
        assert summary["date_range"]["end"] == "2026-01-09"

        # Price extremes
        # Highs: [105, 107, 109, 111, 113] -> max: 113 on 2026-01-09
        # Lows: [95, 97, 99, 101, 103] -> min: 95 on 2026-01-05
        assert summary["price_extremes"]["period_high"] == pytest.approx(113.0)
        assert summary["price_extremes"]["period_high_date"] == "2026-01-09"
        assert summary["price_extremes"]["period_low"] == pytest.approx(95.0)
        assert summary["price_extremes"]["period_low_date"] == "2026-01-05"
        assert summary["price_extremes"]["total_range"] == pytest.approx(18.0)
        assert summary["price_extremes"]["range_ratio"] == pytest.approx(113.0 / 95.0)

        # Daily spread: High - Low = 10.0 for every single day
        assert summary["daily_spread"]["min_spread"] == pytest.approx(10.0)
        assert summary["daily_spread"]["max_spread"] == pytest.approx(10.0)
        assert summary["daily_spread"]["mean_spread"] == pytest.approx(10.0)
        assert summary["daily_spread"]["median_spread"] == pytest.approx(10.0)
        assert summary["daily_spread"]["std_spread"] == pytest.approx(0.0)

        # Volume summary: [1000, 2000, 3000, 4000, 5000]
        assert summary["volume_summary"]["min_volume"] == pytest.approx(1000.0)
        assert summary["volume_summary"]["min_volume_date"] == "2026-01-05"
        assert summary["volume_summary"]["max_volume"] == pytest.approx(5000.0)
        assert summary["volume_summary"]["max_volume_date"] == "2026-01-09"
        assert summary["volume_summary"]["mean_volume"] == pytest.approx(3000.0)
        assert summary["volume_summary"]["total_volume"] == pytest.approx(15000.0)

        # Price-volume correlation: Close and Volume are both strictly increasing linearly -> corr == 1.0
        assert summary["price_volume_relationship"]["pearson_correlation"] == pytest.approx(1.0)


class TestCorrelationAnalysis:
    """Tests Pearson correlation calculations and error handling."""

    def test_correlation_matrix_dimensions_and_labels(self, sample_known_df):
        analyzer = ExploratoryDataAnalyzer(sample_known_df)
        corr = analyzer.compute_correlations(method="pearson")

        expected_cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
        assert list(corr.columns) == expected_cols
        assert list(corr.index) == expected_cols

    def test_correlation_symmetry_and_diagonal(self, sample_known_df):
        analyzer = ExploratoryDataAnalyzer(sample_known_df)
        corr = analyzer.compute_correlations(method="pearson")

        # Diagonal must be 1.0
        for col in corr.columns:
            assert corr.loc[col, col] == pytest.approx(1.0)

        # Symmetry: corr[i, j] == corr[j, i]
        for col1 in corr.columns:
            for col2 in corr.columns:
                assert corr.loc[col1, col2] == pytest.approx(corr.loc[col2, col1])

    def test_perfect_linear_correlation(self, sample_known_df):
        analyzer = ExploratoryDataAnalyzer(sample_known_df)
        corr = analyzer.compute_correlations(method="pearson")

        # In sample_known_df, Open, High, Low, Close, Adj Close, and Volume all increase by a constant step each day
        # Hence Pearson correlation between any pair is exactly 1.0
        assert corr.loc["Open", "Close"] == pytest.approx(1.0)
        assert corr.loc["High", "Low"] == pytest.approx(1.0)
        assert corr.loc["Close", "Volume"] == pytest.approx(1.0)

    def test_unsupported_correlation_method_raises_value_error(self, sample_known_df):
        analyzer = ExploratoryDataAnalyzer(sample_known_df)
        with pytest.raises(ValueError, match="Unsupported correlation method"):
            analyzer.compute_correlations(method="invalid_method")


class TestExploratoryVisualizations:
    """Tests static exploratory visualization functions."""

    def test_plot_price_distribution(self, sample_known_df, tmp_path):
        analyzer = ExploratoryDataAnalyzer(sample_known_df, ticker="TEST")
        out_file = tmp_path / "price_dist.png"

        fig = analyzer.plot_price_distribution(column="Close", bins=10, output_path=out_file)
        assert isinstance(fig, plt.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)

    def test_plot_price_distribution_invalid_column_raises_key_error(self, sample_known_df):
        analyzer = ExploratoryDataAnalyzer(sample_known_df)
        with pytest.raises(KeyError, match="not found in DataFrame columns"):
            analyzer.plot_price_distribution(column="NonExistent")

    def test_plot_volume_distribution(self, sample_known_df, tmp_path):
        analyzer = ExploratoryDataAnalyzer(sample_known_df, ticker="TEST")
        out_file = tmp_path / "vol_dist.png"

        fig = analyzer.plot_volume_distribution(bins=10, output_path=out_file)
        assert isinstance(fig, plt.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)

    def test_plot_ohlc_distributions(self, sample_known_df, tmp_path):
        analyzer = ExploratoryDataAnalyzer(sample_known_df, ticker="TEST")
        out_file = tmp_path / "ohlc_boxplot.png"

        fig = analyzer.plot_ohlc_distributions(output_path=out_file)
        assert isinstance(fig, plt.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)

    def test_plot_correlation_heatmap(self, sample_known_df, tmp_path):
        analyzer = ExploratoryDataAnalyzer(sample_known_df, ticker="TEST")
        out_file = tmp_path / "corr_heatmap.png"

        fig = analyzer.plot_correlation_heatmap(output_path=out_file, annot=True)
        assert isinstance(fig, plt.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)

    def test_plot_high_low_spread(self, sample_known_df, tmp_path):
        analyzer = ExploratoryDataAnalyzer(sample_known_df, ticker="TEST")
        out_file = tmp_path / "hl_spread.png"

        fig = analyzer.plot_high_low_spread(output_path=out_file)
        assert isinstance(fig, plt.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)


class TestConvenienceWrappers:
    """Tests module-level convenience functions."""

    def test_generate_summary_statistics_wrapper(self, sample_known_df):
        stats = generate_summary_statistics(sample_known_df)
        assert isinstance(stats, pd.DataFrame)
        assert "mean" in stats.index
        assert stats.loc["mean", "Close"] == pytest.approx(106.0)

    def test_compute_correlation_matrix_wrapper(self, sample_known_df):
        corr = compute_correlation_matrix(sample_known_df)
        assert isinstance(corr, pd.DataFrame)
        assert corr.loc["Open", "Close"] == pytest.approx(1.0)

    def test_generate_eda_summary_wrapper(self, sample_known_df):
        summary = generate_eda_summary(sample_known_df, ticker="TEST")
        assert isinstance(summary, dict)
        assert summary["ticker"] == "TEST"
        assert "price_extremes" in summary

    def test_plot_wrappers_execute_without_error(self, sample_known_df, tmp_path):
        f1 = plot_price_distribution(sample_known_df, output_path=tmp_path / "p.png")
        f2 = plot_volume_distribution(sample_known_df, output_path=tmp_path / "v.png")
        f3 = plot_ohlc_distributions(sample_known_df, output_path=tmp_path / "o.png")
        f4 = plot_correlation_heatmap(sample_known_df, output_path=tmp_path / "c.png")
        f5 = plot_high_low_spread(sample_known_df, output_path=tmp_path / "s.png")

        for f in (f1, f2, f3, f4, f5):
            assert isinstance(f, plt.Figure)
            plt.close(f)
