"""Unit tests for static visualizations module (Matplotlib & Seaborn)."""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")  # Headless test runner
import matplotlib.figure
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from stock_analyzer.data.exceptions import EmptyDataError, MissingColumnError
from stock_analyzer.visualization.static_charts import (
    StaticChartGenerator,
    plot_closing_price,
    plot_ohlc_bars,
    plot_moving_averages,
    plot_trading_volume,
    plot_daily_returns_time_series,
    plot_daily_returns_distribution,
    plot_cumulative_returns,
    plot_drawdown,
    plot_rolling_volatility,
    plot_correlation_heatmap,
)


@pytest.fixture
def sample_viz_df() -> pd.DataFrame:
    """Fixture providing a deterministic 25-row OHLCV stock dataset."""
    dates = pd.date_range("2026-01-05", periods=25, freq="B")
    prices = [100.0 + i * 1.5 + (2.0 if i % 2 == 0 else -1.0) for i in range(25)]
    return pd.DataFrame(
        {
            "Date": dates.strftime("%Y-%m-%d"),
            "Open": [p - 0.5 for p in prices],
            "High": [p + 2.0 for p in prices],
            "Low": [p - 2.0 for p in prices],
            "Close": prices,
            "Volume": [1000000 + i * 50000 for i in range(25)],
        }
    )


class TestStaticChartValidation:
    """Tests input validation, type enforcement, and defensive copying."""

    def test_invalid_input_type_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected pandas DataFrame"):
            StaticChartGenerator("not_a_df")  # type: ignore

    def test_empty_dataframe_raises_empty_data_error(self):
        with pytest.raises(EmptyDataError, match="Cannot generate charts from an empty DataFrame"):
            StaticChartGenerator(pd.DataFrame())

    def test_missing_required_base_columns_raises_missing_column_error(self):
        incomplete_df = pd.DataFrame({"Date": ["2026-01-01"], "Open": [100.0]})
        with pytest.raises(MissingColumnError, match="DataFrame lacks required columns"):
            StaticChartGenerator(incomplete_df)

    def test_input_dataframe_immutability(self, sample_viz_df):
        original = sample_viz_df.copy(deep=True)
        gen = StaticChartGenerator(sample_viz_df, ticker="TEST")
        fig = gen.plot_closing_price()
        plt.close(fig)

        pd.testing.assert_frame_equal(sample_viz_df, original)


class TestStaticChartExecutionAndExport:
    """Tests execution of all 10 static visualization functions and PNG exports."""

    def test_plot_closing_price(self, sample_viz_df, tmp_path):
        gen = StaticChartGenerator(sample_viz_df, ticker="TEST")
        out_file = tmp_path / "close.png"
        fig = gen.plot_closing_price(output_path=out_file)

        assert isinstance(fig, matplotlib.figure.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)

    def test_plot_ohlc_bars(self, sample_viz_df, tmp_path):
        gen = StaticChartGenerator(sample_viz_df, ticker="TEST")
        out_file = tmp_path / "ohlc.png"
        fig = gen.plot_ohlc_bars(max_bars=20, output_path=out_file)

        assert isinstance(fig, matplotlib.figure.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)

    def test_plot_ohlc_bars_missing_columns_raises_error(self):
        df_no_hl = pd.DataFrame({"Date": ["2026-01-01"], "Close": [100.0]})
        gen = StaticChartGenerator(df_no_hl)
        with pytest.raises(MissingColumnError, match="Candlestick chart requires columns"):
            gen.plot_ohlc_bars()

    def test_plot_moving_averages(self, sample_viz_df, tmp_path):
        gen = StaticChartGenerator(sample_viz_df, ticker="TEST")
        out_file = tmp_path / "ma.png"
        fig = gen.plot_moving_averages(output_path=out_file)

        assert isinstance(fig, matplotlib.figure.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)

    def test_plot_trading_volume(self, sample_viz_df, tmp_path):
        gen = StaticChartGenerator(sample_viz_df, ticker="TEST")
        out_file = tmp_path / "vol.png"
        fig = gen.plot_trading_volume(output_path=out_file)

        assert isinstance(fig, matplotlib.figure.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)

    def test_plot_daily_returns_time_series(self, sample_viz_df, tmp_path):
        gen = StaticChartGenerator(sample_viz_df, ticker="TEST")
        out_file = tmp_path / "ret_ts.png"
        fig = gen.plot_daily_returns_time_series(output_path=out_file)

        assert isinstance(fig, matplotlib.figure.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)

    def test_plot_daily_returns_distribution(self, sample_viz_df, tmp_path):
        gen = StaticChartGenerator(sample_viz_df, ticker="TEST")
        out_file = tmp_path / "ret_dist.png"
        fig = gen.plot_daily_returns_distribution(bins=15, output_path=out_file)

        assert isinstance(fig, matplotlib.figure.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)

    def test_plot_cumulative_returns(self, sample_viz_df, tmp_path):
        gen = StaticChartGenerator(sample_viz_df, ticker="TEST")
        out_file = tmp_path / "cum_ret.png"
        fig = gen.plot_cumulative_returns(output_path=out_file)

        assert isinstance(fig, matplotlib.figure.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)

    def test_plot_drawdown(self, sample_viz_df, tmp_path):
        gen = StaticChartGenerator(sample_viz_df, ticker="TEST")
        out_file = tmp_path / "drawdown.png"
        fig = gen.plot_drawdown(output_path=out_file)

        assert isinstance(fig, matplotlib.figure.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)

    def test_plot_rolling_volatility(self, sample_viz_df, tmp_path):
        gen = StaticChartGenerator(sample_viz_df, ticker="TEST")
        out_file = tmp_path / "roll_vol.png"
        fig = gen.plot_rolling_volatility(window=10, output_path=out_file)

        assert isinstance(fig, matplotlib.figure.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)

    def test_plot_rolling_volatility_default_windows(self, sample_viz_df, tmp_path):
        gen = StaticChartGenerator(sample_viz_df, ticker="TEST")
        out_file = tmp_path / "roll_vol_multi.png"
        fig = gen.plot_rolling_volatility(output_path=out_file)

        assert isinstance(fig, matplotlib.figure.Figure)
        ax = fig.axes[0]
        # Expect at least 2 lines for 21d and 63d rolling vol curves
        lines = [line for line in ax.get_lines() if "Rolling" in (line.get_label() or "")]
        assert len(lines) == 2
        assert out_file.exists()
        plt.close(fig)

    def test_plot_correlation_heatmap(self, sample_viz_df, tmp_path):
        gen = StaticChartGenerator(sample_viz_df, ticker="TEST")
        out_file = tmp_path / "heatmap.png"
        fig = gen.plot_correlation_heatmap(output_path=out_file)

        assert isinstance(fig, matplotlib.figure.Figure)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        plt.close(fig)

    def test_synthetic_tag_in_title(self, sample_viz_df):
        sample_viz_df.attrs["is_synthetic"] = True
        gen = StaticChartGenerator(sample_viz_df, ticker="SYNTH")
        ctx = gen._get_title_context()
        assert "[SYNTHETIC DATA]" in ctx


class TestStaticConvenienceWrappers:
    """Tests module-level convenience functions for static charts."""

    def test_all_static_wrappers_execute_successfully(self, sample_viz_df, tmp_path):
        f1 = plot_closing_price(sample_viz_df, output_path=tmp_path / "w1.png")
        f2 = plot_ohlc_bars(sample_viz_df, output_path=tmp_path / "w2.png")
        f3 = plot_moving_averages(sample_viz_df, output_path=tmp_path / "w3.png")
        f4 = plot_trading_volume(sample_viz_df, output_path=tmp_path / "w4.png")
        f5 = plot_daily_returns_time_series(sample_viz_df, output_path=tmp_path / "w5.png")
        f6 = plot_daily_returns_distribution(sample_viz_df, output_path=tmp_path / "w6.png")
        f7 = plot_cumulative_returns(sample_viz_df, output_path=tmp_path / "w7.png")
        f8 = plot_drawdown(sample_viz_df, output_path=tmp_path / "w8.png")
        f9 = plot_rolling_volatility(sample_viz_df, window=10, output_path=tmp_path / "w9.png")
        f10 = plot_correlation_heatmap(sample_viz_df, output_path=tmp_path / "w10.png")

        for f in (f1, f2, f3, f4, f5, f6, f7, f8, f9, f10):
            assert isinstance(f, matplotlib.figure.Figure)
            plt.close(f)
