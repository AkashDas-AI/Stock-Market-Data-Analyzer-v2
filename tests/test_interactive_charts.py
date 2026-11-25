"""Unit tests for interactive visualizations module (Plotly)."""

from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from stock_analyzer.data.exceptions import EmptyDataError, MissingColumnError
from stock_analyzer.visualization.interactive_charts import (
    InteractiveChartGenerator,
    create_candlestick_chart,
    create_moving_averages_chart,
    create_volume_chart,
    create_daily_returns_chart,
    create_daily_returns_distribution_chart,
    create_cumulative_returns_chart,
    create_drawdown_chart,
    create_rolling_volatility_chart,
    create_correlation_heatmap,
)


@pytest.fixture
def sample_interactive_df() -> pd.DataFrame:
    """Fixture providing a deterministic 30-row OHLCV stock dataset."""
    dates = pd.date_range("2026-01-05", periods=30, freq="B")
    prices = [100.0 + i * 1.2 + (2.0 if i % 3 == 0 else -1.0) for i in range(30)]
    return pd.DataFrame(
        {
            "Date": dates.strftime("%Y-%m-%d"),
            "Open": [p - 0.5 for p in prices],
            "High": [p + 2.0 for p in prices],
            "Low": [p - 2.0 for p in prices],
            "Close": prices,
            "Volume": [1000000 + i * 30000 for i in range(30)],
        }
    )


class TestInteractiveChartValidation:
    """Tests input validation and defensive copying for InteractiveChartGenerator."""

    def test_invalid_input_type_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected pandas DataFrame"):
            InteractiveChartGenerator("not_a_df")  # type: ignore

    def test_empty_dataframe_raises_empty_data_error(self):
        with pytest.raises(EmptyDataError, match="Cannot generate interactive charts from an empty DataFrame"):
            InteractiveChartGenerator(pd.DataFrame())

    def test_missing_required_base_columns_raises_missing_column_error(self):
        incomplete_df = pd.DataFrame({"Date": ["2026-01-01"], "Open": [100.0]})
        with pytest.raises(MissingColumnError, match="DataFrame lacks required columns"):
            InteractiveChartGenerator(incomplete_df)

    def test_input_dataframe_immutability(self, sample_interactive_df):
        original = sample_interactive_df.copy(deep=True)
        gen = InteractiveChartGenerator(sample_interactive_df, ticker="TEST")
        fig = gen.create_candlestick_chart()

        pd.testing.assert_frame_equal(sample_interactive_df, original)


class TestInteractiveChartExecutionAndExport:
    """Tests execution of all interactive Plotly functions and HTML export."""

    def test_create_candlestick_chart_with_volume(self, sample_interactive_df, tmp_path):
        gen = InteractiveChartGenerator(sample_interactive_df, ticker="TEST")
        out_html = tmp_path / "candle_vol.html"
        fig = gen.create_candlestick_chart(include_volume=True, output_path=out_html)

        assert isinstance(fig, go.Figure)
        # Should contain candlestick trace and bar trace
        trace_types = [t.type for t in fig.data]
        assert "candlestick" in trace_types
        assert "bar" in trace_types
        assert out_html.exists()
        assert out_html.stat().st_size > 500  # valid HTML content

    def test_create_candlestick_chart_without_volume(self, sample_interactive_df, tmp_path):
        gen = InteractiveChartGenerator(sample_interactive_df, ticker="TEST")
        out_html = tmp_path / "candle.html"
        fig = gen.create_candlestick_chart(include_volume=False, output_path=out_html)

        assert isinstance(fig, go.Figure)
        trace_types = [t.type for t in fig.data]
        assert "candlestick" in trace_types
        assert "bar" not in trace_types
        assert out_html.exists()

    def test_create_candlestick_missing_ohlc_columns_raises_error(self):
        df_no_hl = pd.DataFrame({"Date": ["2026-01-01"], "Close": [100.0]})
        gen = InteractiveChartGenerator(df_no_hl)
        with pytest.raises(MissingColumnError, match="Candlestick chart requires columns"):
            gen.create_candlestick_chart()

    def test_create_moving_averages_chart(self, sample_interactive_df, tmp_path):
        gen = InteractiveChartGenerator(sample_interactive_df, ticker="TEST")
        out_html = tmp_path / "ma.html"
        fig = gen.create_moving_averages_chart(output_path=out_html)

        assert isinstance(fig, go.Figure)
        trace_names = [t.name for t in fig.data]
        assert "Close Price" in trace_names
        # Should include SMA 20 (since len >= 20)
        assert "SMA 20" in trace_names
        assert out_html.exists()

    def test_create_volume_chart(self, sample_interactive_df, tmp_path):
        gen = InteractiveChartGenerator(sample_interactive_df, ticker="TEST")
        out_html = tmp_path / "vol.html"
        fig = gen.create_volume_chart(output_path=out_html)

        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "bar"
        assert out_html.exists()

    def test_create_daily_returns_chart(self, sample_interactive_df, tmp_path):
        gen = InteractiveChartGenerator(sample_interactive_df, ticker="TEST")
        out_html = tmp_path / "daily_ret.html"
        fig = gen.create_daily_returns_chart(output_path=out_html)

        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "bar"
        assert out_html.exists()

    def test_create_cumulative_returns_chart(self, sample_interactive_df, tmp_path):
        gen = InteractiveChartGenerator(sample_interactive_df, ticker="TEST")
        out_html = tmp_path / "cum_ret.html"
        fig = gen.create_cumulative_returns_chart(output_path=out_html)

        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "scatter"
        assert out_html.exists()

    def test_create_drawdown_chart(self, sample_interactive_df, tmp_path):
        gen = InteractiveChartGenerator(sample_interactive_df, ticker="TEST")
        out_html = tmp_path / "dd.html"
        fig = gen.create_drawdown_chart(output_path=out_html)

        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "scatter"
        assert out_html.exists()

    def test_create_rolling_volatility_chart(self, sample_interactive_df, tmp_path):
        gen = InteractiveChartGenerator(sample_interactive_df, ticker="TEST")
        out_html = tmp_path / "volatility.html"
        fig = gen.create_rolling_volatility_chart(window=10, output_path=out_html)

        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "scatter"
        assert out_html.exists()

    def test_create_rolling_volatility_chart_default_windows(self, sample_interactive_df, tmp_path):
        gen = InteractiveChartGenerator(sample_interactive_df, ticker="TEST")
        out_html = tmp_path / "volatility_multi.html"
        fig = gen.create_rolling_volatility_chart(output_path=out_html)

        assert isinstance(fig, go.Figure)
        # Expect 2 scatter traces for (21, 63)
        assert len(fig.data) == 2
        assert "21d" in fig.data[0].name
        assert "63d" in fig.data[1].name
        assert out_html.exists()

    def test_create_daily_returns_distribution_chart(self, sample_interactive_df, tmp_path):
        gen = InteractiveChartGenerator(sample_interactive_df, ticker="TEST")
        out_html = tmp_path / "returns_dist.html"
        fig = gen.create_daily_returns_distribution_chart(bins=15, output_path=out_html)

        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "histogram"
        assert out_html.exists()

    def test_create_moving_averages_chart_with_toggles(self, sample_interactive_df):
        gen = InteractiveChartGenerator(sample_interactive_df, ticker="TEST")
        # Only Close and SMA 20
        fig = gen.create_moving_averages_chart(show_sma_20=True, show_sma_50=False, show_ema_20=False)
        names = [trace.name for trace in fig.data]
        assert "Close Price" in names
        assert "SMA 20" in names
        assert "SMA 50" not in names
        assert "EMA 20" not in names

    def test_create_correlation_heatmap(self, sample_interactive_df, tmp_path):
        gen = InteractiveChartGenerator(sample_interactive_df, ticker="TEST")
        out_html = tmp_path / "heatmap.html"
        fig = gen.create_correlation_heatmap(output_path=out_html)

        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "heatmap"
        assert out_html.exists()


class TestInteractiveConvenienceWrappers:
    """Tests module-level convenience functions for interactive Plotly charts."""

    def test_all_interactive_wrappers_execute_successfully(self, sample_interactive_df, tmp_path):
        f1 = create_candlestick_chart(sample_interactive_df, output_path=tmp_path / "w1.html")
        f2 = create_moving_averages_chart(sample_interactive_df, output_path=tmp_path / "w2.html")
        f3 = create_volume_chart(sample_interactive_df, output_path=tmp_path / "w3.html")
        f4 = create_daily_returns_chart(sample_interactive_df, output_path=tmp_path / "w4.html")
        f4_dist = create_daily_returns_distribution_chart(sample_interactive_df, output_path=tmp_path / "w4_dist.html")
        f5 = create_cumulative_returns_chart(sample_interactive_df, output_path=tmp_path / "w5.html")
        f6 = create_drawdown_chart(sample_interactive_df, output_path=tmp_path / "w6.html")
        f7 = create_rolling_volatility_chart(sample_interactive_df, window=10, output_path=tmp_path / "w7.html")
        f8 = create_correlation_heatmap(sample_interactive_df, output_path=tmp_path / "w8.html")

        for f in (f1, f2, f3, f4, f4_dist, f5, f6, f7, f8):
            assert isinstance(f, go.Figure)
