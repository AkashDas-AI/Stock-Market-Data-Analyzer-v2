"""Unit and integration tests for Streamlit dashboard application modules.

Tests coverage:
    - Data ingestion and manager workflows (Sample, Live mocked, CSV upload)
    - Input validation (tickers, date ranges, missing files, corrupted CSVs)
    - KPI metric computations and edge cases (empty data, missing columns)
    - View tabs and Plotly chart rendering integration
    - Indicator selection behavior and parameter toggling
    - Dashboard main execution flow (success path, error path, synthetic warnings)
    - Immutability of returned DataFrames
"""

from datetime import date, timedelta
from io import BytesIO, StringIO
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.data_manager import (
    SAMPLE_CSV_PATH,
    fetch_cached_live_data,
    filter_date_range,
    get_and_clean_data,
    load_cached_sample_data,
    load_uploaded_csv,
)
from app.kpis import render_kpi_metrics
from app.sidebar import DashboardParameters
from app.views import render_dashboard_views
from stock_analyzer.data.exceptions import (
    DataFetchError,
    DataValidationError,
    EmptyDataError,
    InvalidDateRangeError,
    StockDataError,
)


@pytest.fixture
def sample_dashboard_df() -> pd.DataFrame:
    """Fixture providing clean standard 30-day stock data with synthetic flag."""
    dates = pd.date_range("2026-01-01", periods=30, freq="B").strftime("%Y-%m-%d").tolist()
    prices = [100.0 + i * 1.5 + (i % 3) * 0.5 for i in range(30)]
    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": [p - 0.5 for p in prices],
            "High": [p + 1.2 for p in prices],
            "Low": [p - 1.0 for p in prices],
            "Close": prices,
            "Volume": [10000 + i * 500 for i in range(30)],
        }
    )
    df.attrs["ticker"] = "TEST"
    df.attrs["is_synthetic"] = True
    return df


@pytest.fixture
def default_dashboard_params() -> DashboardParameters:
    """Fixture providing default dashboard parameter settings."""
    return DashboardParameters(
        source_type="Sample Dataset (Synthetic)",
        ticker="TEST",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 2, 15),
        uploaded_file=None,
        show_sma_20=True,
        show_sma_50=True,
        show_ema_20=True,
        show_candlestick_volume=True,
        rolling_vol_windows=[21, 63],
    )


# =============================================================================
# 1. Data Manager Ingestion & Validation Tests
# =============================================================================


class TestDataManagerWorkflows:
    """Tests for app/data_manager.py across all three ingestion sources."""

    def test_sample_dataset_loading_and_synthetic_tagging(self):
        df, err = get_and_clean_data(source_type="Sample Dataset (Synthetic)")

        assert err is None
        assert df is not None
        assert not df.empty
        assert df.attrs.get("is_synthetic") is True
        assert df.attrs.get("ticker") == "SAMPLE"
        assert all(col in df.columns for col in ["Date", "Open", "High", "Low", "Close", "Volume"])

    def test_sample_dataset_immutability(self):
        df1, _ = get_and_clean_data(source_type="Sample Dataset (Synthetic)")
        original_close = df1["Close"].iloc[0]

        # Mutate first DataFrame via .loc
        df1.loc[0, "Close"] = 999999.0

        # Retrieve second DataFrame
        df2, _ = get_and_clean_data(source_type="Sample Dataset (Synthetic)")
        assert df2["Close"].iloc[0] == original_close
        assert df2["Close"].iloc[0] != 999999.0

    @patch("app.data_manager.fetch_cached_live_data")
    def test_live_fetch_success_mocked(self, mock_fetch, sample_dashboard_df):
        mock_fetch.return_value = sample_dashboard_df.copy()

        df, err = get_and_clean_data(
            source_type="Live Yahoo Finance",
            ticker="MSFT",
            start_date=date(2025, 1, 1),
            end_date=date(2026, 1, 1),
        )

        assert err is None
        assert df is not None
        assert df.attrs["ticker"] == "MSFT"
        assert df.attrs["is_synthetic"] is False
        mock_fetch.assert_called_once_with("MSFT", "2025-01-01", "2026-01-02")

    @patch("app.data_manager.fetch_cached_live_data")
    def test_live_fetch_failure_handled_gracefully(self, mock_fetch):
        mock_fetch.side_effect = DataFetchError("Simulated remote network timeout.")

        df, err = get_and_clean_data(
            source_type="Live Yahoo Finance",
            ticker="FAIL",
            start_date=date(2025, 1, 1),
            end_date=date(2026, 1, 1),
        )

        assert df is None
        assert err is not None
        assert "Live Data Fetch Error" in err
        assert "Simulated remote network timeout" in err

    def test_live_fetch_empty_ticker_returns_error(self):
        df, err = get_and_clean_data(
            source_type="Live Yahoo Finance",
            ticker="",
            start_date=date(2025, 1, 1),
            end_date=date(2026, 1, 1),
        )
        assert df is None
        assert "valid stock ticker symbol" in err

    def test_live_fetch_invalid_date_range_returns_error(self):
        df, err = get_and_clean_data(
            source_type="Live Yahoo Finance",
            ticker="AAPL",
            start_date=date(2026, 1, 1),
            end_date=date(2025, 1, 1),  # start > end
        )
        assert df is None
        assert "must be strictly before end date" in err

    def test_live_fetch_missing_dates_returns_error(self):
        df, err = get_and_clean_data(
            source_type="Live Yahoo Finance",
            ticker="AAPL",
            start_date=None,
            end_date=None,
        )
        assert df is None
        assert "must both be specified" in err

    def test_csv_upload_valid_data(self, sample_dashboard_df):
        csv_buffer = BytesIO()
        sample_dashboard_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        df, err = get_and_clean_data(
            source_type="Upload CSV",
            ticker="MYSTOCK",
            uploaded_file=csv_buffer,
        )

        assert err is None
        assert df is not None
        assert df.attrs["ticker"] == "MYSTOCK"
        assert df.attrs["is_synthetic"] is False
        assert len(df) == len(sample_dashboard_df)

    def test_csv_upload_missing_required_columns(self):
        bad_df = pd.DataFrame({"Date": ["2026-01-01"], "Open": [100.0]})
        csv_buffer = StringIO()
        bad_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        df, err = get_and_clean_data(
            source_type="Upload CSV",
            uploaded_file=csv_buffer,
        )

        assert df is None
        assert err is not None
        assert "Data Validation Error" in err

    def test_csv_upload_none_file_returns_guidance(self):
        df, err = get_and_clean_data(source_type="Upload CSV", uploaded_file=None)
        assert df is None
        assert "Please upload a CSV file" in err

    def test_unrecognized_data_source_type_returns_error(self):
        df, err = get_and_clean_data(source_type="UnknownSource")
        assert df is None
        assert "Unrecognized data source" in err


# =============================================================================
# 2. Financial KPI Metric Component Tests
# =============================================================================


class TestKPIComponents:
    """Tests for app/kpis.py."""

    @patch("streamlit.metric")
    @patch("streamlit.columns")
    def test_render_kpi_metrics_with_valid_data(self, mock_columns, mock_metric, sample_dashboard_df):
        # Setup 6 mocked columns
        mock_cols = [MagicMock() for _ in range(6)]
        mock_columns.return_value = mock_cols

        render_kpi_metrics(sample_dashboard_df)

        mock_columns.assert_called_once_with(6)
        assert mock_metric.call_count == 6

    @patch("streamlit.warning")
    def test_render_kpi_metrics_empty_data_shows_warning(self, mock_warning):
        render_kpi_metrics(pd.DataFrame())
        mock_warning.assert_called_once_with("Insufficient data available to compute financial KPIs.")

    @patch("streamlit.warning")
    def test_render_kpi_metrics_missing_close_shows_warning(self, mock_warning):
        df_no_close = pd.DataFrame({"Date": ["2026-01-01"], "Open": [100.0]})
        render_kpi_metrics(df_no_close)
        mock_warning.assert_called_once_with("Insufficient data available to compute financial KPIs.")


# =============================================================================
# 3. View Tabs & Chart Integration Tests
# =============================================================================


class TestViewsAndChartIntegration:
    """Tests for app/views.py and interactive chart embedding."""

    @patch("streamlit.plotly_chart")
    @patch("streamlit.tabs")
    def test_render_dashboard_views_runs_without_exceptions(
        self, mock_tabs, mock_plotly, sample_dashboard_df, default_dashboard_params
    ):
        mock_tabs.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_dashboard_views(sample_dashboard_df, default_dashboard_params)

        mock_tabs.assert_called_once()
        # Verify plotly_chart was called for charts across the tabs
        # Tab 1: Candlestick, Moving Averages, Volume (3)
        # Tab 2: Daily Returns, Returns Distribution, Cumulative Returns, Drawdown, Rolling Vol (5)
        # Tab 3: Correlation Heatmap (1) -> Total: 9 Plotly charts rendered
        assert mock_plotly.call_count >= 8

    @patch("streamlit.plotly_chart")
    @patch("streamlit.tabs")
    def test_render_dashboard_views_indicator_toggles(
        self, mock_tabs, mock_plotly, sample_dashboard_df, default_dashboard_params
    ):
        mock_tabs.return_value = [MagicMock(), MagicMock(), MagicMock()]
        # Disable SMA 50 and EMA 20
        default_dashboard_params.show_sma_50 = False
        default_dashboard_params.show_ema_20 = False

        render_dashboard_views(sample_dashboard_df, default_dashboard_params)
        assert mock_plotly.called

    @patch("streamlit.plotly_chart")
    @patch("streamlit.tabs")
    def test_render_dashboard_views_insights_tab_rendering(
        self, mock_tabs, mock_plotly, sample_dashboard_df, default_dashboard_params
    ):
        # 5 tabs: Price, Risk, Data, Insights, Reports
        mock_tab_objs = [MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_tabs.return_value = mock_tab_objs

        render_dashboard_views(sample_dashboard_df, default_dashboard_params)

        # Confirm tabs was called with all 5 tab labels
        tab_labels = mock_tabs.call_args[0][0]
        assert len(tab_labels) == 5
        assert any("Insights" in label for label in tab_labels)
        assert any("Reports" in label for label in tab_labels)

    @patch("streamlit.plotly_chart")
    @patch("streamlit.tabs")
    def test_insights_refresh_on_ticker_change(
        self, mock_tabs, mock_plotly, sample_dashboard_df, default_dashboard_params
    ):
        mock_tabs.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()]

        # Initial call with AAPL
        default_dashboard_params.ticker = "AAPL"
        render_dashboard_views(sample_dashboard_df, default_dashboard_params)

        # Subsequent call with MSFT
        default_dashboard_params.ticker = "MSFT"
        render_dashboard_views(sample_dashboard_df, default_dashboard_params)
        assert mock_tabs.call_count == 2

    @patch("streamlit.download_button")
    @patch("streamlit.plotly_chart")
    @patch("streamlit.tabs")
    def test_render_dashboard_views_reports_tab_downloads(
        self, mock_tabs, mock_plotly, mock_download, sample_dashboard_df, default_dashboard_params
    ):
        mock_tab_objs = [MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_tabs.return_value = mock_tab_objs

        render_dashboard_views(sample_dashboard_df, default_dashboard_params)

        # Confirm download buttons were rendered (PDF, HTML, CSVs)
        assert mock_download.call_count >= 5


# =============================================================================
# 4. Dashboard Main Application Flow Tests
# =============================================================================


class TestDashboardMainFlow:
    """Tests for app/dashboard.py main() application entry point."""

    @patch("app.dashboard.render_dashboard_views")
    @patch("app.dashboard.render_kpi_metrics")
    @patch("app.dashboard.get_and_clean_data")
    @patch("app.dashboard.render_sidebar")
    @patch("streamlit.set_page_config")
    def test_main_success_flow(
        self,
        mock_config,
        mock_sidebar,
        mock_get_data,
        mock_kpis,
        mock_views,
        sample_dashboard_df,
        default_dashboard_params,
    ):
        from app.dashboard import main

        mock_sidebar.return_value = default_dashboard_params
        mock_get_data.return_value = (sample_dashboard_df, None)

        main()

        mock_config.assert_called_once()
        mock_sidebar.assert_called_once()
        mock_get_data.assert_called_once()
        mock_kpis.assert_called_once_with(sample_dashboard_df)
        mock_views.assert_called_once_with(sample_dashboard_df, default_dashboard_params)

    @patch("app.dashboard.render_dashboard_views")
    @patch("app.dashboard.render_kpi_metrics")
    @patch("app.dashboard.get_and_clean_data")
    @patch("app.dashboard.render_sidebar")
    @patch("streamlit.error")
    @patch("streamlit.set_page_config")
    def test_main_error_flow_displays_error_banner(
        self,
        mock_config,
        mock_error,
        mock_sidebar,
        mock_get_data,
        mock_kpis,
        mock_views,
        default_dashboard_params,
    ):
        from app.dashboard import main

        mock_sidebar.return_value = default_dashboard_params
        mock_get_data.return_value = (None, "Test Data Retrieval Failure")

        main()

        mock_error.assert_called_once_with("❌ Test Data Retrieval Failure")
        mock_kpis.assert_not_called()
        mock_views.assert_not_called()

    @patch("app.dashboard.render_dashboard_views")
    @patch("app.dashboard.render_kpi_metrics")
    @patch("app.dashboard.get_and_clean_data")
    @patch("app.dashboard.render_sidebar")
    @patch("streamlit.warning")
    @patch("streamlit.set_page_config")
    def test_main_synthetic_warning_displayed(
        self,
        mock_config,
        mock_warning,
        mock_sidebar,
        mock_get_data,
        mock_kpis,
        mock_views,
        sample_dashboard_df,
        default_dashboard_params,
    ):
        from app.dashboard import main

        sample_dashboard_df.attrs["is_synthetic"] = True
        mock_sidebar.return_value = default_dashboard_params
        mock_get_data.return_value = (sample_dashboard_df, None)

        main()

        # Verify warning called for synthetic data
        warning_calls = [call[0][0] for call in mock_warning.call_args_list]
        assert any("SYNTHETIC SAMPLE DATA ACTIVE" in call for call in warning_calls)

    @patch("app.dashboard.render_dashboard_views")
    @patch("app.dashboard.render_kpi_metrics")
    @patch("app.dashboard.get_and_clean_data")
    @patch("app.dashboard.render_sidebar")
    @patch("streamlit.markdown")
    @patch("streamlit.set_page_config")
    def test_main_header_styling_high_contrast(
        self,
        mock_config,
        mock_markdown,
        mock_sidebar,
        mock_get_data,
        mock_kpis,
        mock_views,
        sample_dashboard_df,
        default_dashboard_params,
    ):
        from app.dashboard import main

        mock_sidebar.return_value = default_dashboard_params
        mock_get_data.return_value = (sample_dashboard_df, None)

        main()

        markdown_calls = [call[0][0] for call in mock_markdown.call_args_list]
        css_call = [c for c in markdown_calls if "<style>" in c][0]
        # Verify bright white color #FFFFFF for .main-header
        assert "color: #FFFFFF;" in css_call
        assert ".main-header" in css_call
        # Verify headline text rendered
        assert any('<div class="main-header">📈 Stock Market Data Analyzer</div>' in c for c in markdown_calls)
        # Verify subtitle and author attribution rendered
        assert any("Akash Das" in c for c in markdown_calls)


# =============================================================================
# 5. Date-Range Boundary Verification & Normalization Tests
# =============================================================================


class TestDateBoundaryAndNormalization:
    """Deterministic tests for date-boundary inclusivity and timezone normalization."""

    @patch("app.data_manager.fetch_cached_live_data")
    def test_live_fetch_end_date_inclusivity(self, mock_fetch):
        # User selects start_date=2026-01-01 and end_date=2026-01-05
        # yfinance end_date is exclusive, so fetch_cached_live_data must be called with end_date + 1 day = 2026-01-06
        dates = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05", "2026-01-06"]
        dummy_df = pd.DataFrame(
            {
                "Date": dates,
                "Open": [100.0] * 6,
                "High": [105.0] * 6,
                "Low": [95.0] * 6,
                "Close": [102.0] * 6,
                "Volume": [1000] * 6,
            }
        )
        mock_fetch.return_value = dummy_df

        df, err = get_and_clean_data(
            source_type="Live Yahoo Finance",
            ticker="AAPL",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 5),
        )

        assert err is None
        assert df is not None
        # Assert fetcher called with inclusive offset (2026-01-06)
        mock_fetch.assert_called_once_with("AAPL", "2026-01-01", "2026-01-06")
        # Assert returned DataFrame includes observations up to exactly 2026-01-05 (end_date inclusive)
        assert str(df["Date"].dt.date.iloc[-1]) == "2026-01-05"
        assert len(df) == 5

    def test_sample_dataset_inclusive_date_filtering(self):
        # Filter sample dataset between 2026-01-05 and 2026-01-15
        df, err = get_and_clean_data(
            source_type="Sample Dataset (Synthetic)",
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 15),
        )

        assert err is None
        assert df is not None
        assert not df.empty
        # Verify inclusive boundaries: 2026-01-05 and 2026-01-15 must both be included
        assert str(df["Date"].dt.date.min()) == "2026-01-05"
        assert str(df["Date"].dt.date.max()) == "2026-01-15"

    def test_csv_upload_inclusive_date_filtering(self, sample_dashboard_df):
        csv_buffer = BytesIO()
        sample_dashboard_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        # sample_dashboard_df has business days starting 2026-01-01
        dates_in_fixture = sample_dashboard_df["Date"].tolist()
        s_date = dates_in_fixture[2]
        e_date = dates_in_fixture[8]

        df, err = get_and_clean_data(
            source_type="Upload CSV",
            uploaded_file=csv_buffer,
            start_date=s_date,
            end_date=e_date,
        )

        assert err is None
        assert df is not None
        assert str(df["Date"].dt.date.min()) == s_date
        assert str(df["Date"].dt.date.max()) == e_date
        assert len(df) == 7

    def test_equal_start_and_end_date_rejected(self):
        df, err = get_and_clean_data(
            source_type="Live Yahoo Finance",
            ticker="AAPL",
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 5),
        )
        assert df is None
        assert "must be strictly before end date" in err

    def test_inverted_date_range_rejected_before_fetching_or_filtering(self):
        # Must be rejected across all 3 source types
        for source in ["Live Yahoo Finance", "Sample Dataset (Synthetic)", "Upload CSV"]:
            df, err = get_and_clean_data(
                source_type=source,
                ticker="AAPL",
                start_date=date(2026, 2, 1),
                end_date=date(2026, 1, 1),
                uploaded_file=BytesIO(b"Date,Open,High,Low,Close,Volume\n2026-01-01,1,2,0.5,1.5,100"),
            )
            assert df is None
            assert "must be strictly before end date" in err

    def test_timezone_and_timestamp_normalization_no_shift(self):
        # Timestamps with non-midnight hours or UTC offsets
        df = pd.DataFrame(
            {
                "Date": ["2026-01-05 23:45:00", "2026-01-06 04:15:00", "2026-01-07 12:00:00"],
                "Close": [100.0, 101.0, 102.0],
            }
        )
        filtered = filter_date_range(df, start_date="2026-01-05", end_date="2026-01-06")
        assert len(filtered) == 2
        assert filtered["Close"].tolist() == [100.0, 101.0]


# =============================================================================
# 6. Application Startup & Smoke Verification Tests
# =============================================================================


class TestApplicationStartupAndSmoke:
    """Reliable smoke verification tests confirming end-to-end component readiness."""

    def test_application_modules_import_cleanly(self):
        import app.dashboard as dash
        import app.data_manager as dm
        import app.kpis as kpi
        import app.sidebar as sb
        import app.views as vw

        assert callable(dash.main)
        assert callable(dm.get_and_clean_data)
        assert callable(dm.filter_date_range)
        assert callable(kpi.render_kpi_metrics)
        assert callable(sb.render_sidebar)
        assert callable(vw.render_dashboard_views)

    @patch("streamlit.plotly_chart")
    @patch("streamlit.tabs")
    @patch("streamlit.metric")
    @patch("streamlit.columns")
    def test_sample_dataset_full_render_smoke_test(
        self, mock_cols, mock_metric, mock_tabs, mock_plotly, default_dashboard_params
    ):
        mock_cols.side_effect = lambda spec: [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
        mock_tabs.return_value = [MagicMock(), MagicMock(), MagicMock()]

        # 1. Ingest sample data
        df, err = get_and_clean_data(source_type="Sample Dataset (Synthetic)")
        assert err is None
        assert df is not None

        # 2. Render KPIs
        render_kpi_metrics(df)
        assert mock_metric.call_count == 6

        # 3. Render Views
        render_dashboard_views(df, default_dashboard_params)
        assert mock_plotly.call_count >= 8

    @patch("streamlit.plotly_chart")
    @patch("streamlit.tabs")
    @patch("streamlit.metric")
    @patch("streamlit.columns")
    def test_csv_upload_full_render_smoke_test(
        self, mock_cols, mock_metric, mock_tabs, mock_plotly, sample_dashboard_df, default_dashboard_params
    ):
        mock_cols.side_effect = lambda spec: [MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))]
        mock_tabs.return_value = [MagicMock(), MagicMock(), MagicMock()]

        csv_buf = BytesIO()
        sample_dashboard_df.to_csv(csv_buf, index=False)
        csv_buf.seek(0)

        df, err = get_and_clean_data(
            source_type="Upload CSV",
            uploaded_file=csv_buf,
            ticker="CUSTOM",
        )
        assert err is None
        assert df is not None

        render_kpi_metrics(df)
        render_dashboard_views(df, default_dashboard_params)
        assert mock_plotly.called

    @patch("app.data_manager.fetch_cached_live_data")
    def test_live_fetch_controlled_failure_smoke_test(self, mock_fetch):
        mock_fetch.side_effect = DataFetchError("Controlled API failure simulation.")

        df, err = get_and_clean_data(
            source_type="Live Yahoo Finance",
            ticker="FAIL",
            start_date=date(2025, 1, 1),
            end_date=date(2026, 1, 1),
        )

        assert df is None
        assert err is not None
        assert "Controlled API failure simulation" in err


# =============================================================================
# 7. Live Yahoo Finance Fetcher Integration & Regression Tests
# =============================================================================


def _mock_yfinance_df(dates: list[str]) -> pd.DataFrame:
    """Helper creating standard single-level OHLCV DataFrame mimicking yfinance."""
    n = len(dates)
    return pd.DataFrame(
        {
            "Open": [150.0 + i for i in range(n)],
            "High": [155.0 + i for i in range(n)],
            "Low": [149.0 + i for i in range(n)],
            "Close": [154.0 + i for i in range(n)],
            "Adj Close": [153.5 + i for i in range(n)],
            "Volume": [1000000 + i * 10000 for i in range(n)],
        },
        index=pd.to_datetime(dates),
    )


class TestLiveYahooFinanceFetcherRegression:
    """Targeted regression tests verifying live Yahoo Finance fetcher integration."""

    @patch("yfinance.download")
    def test_stock_data_fetcher_initialization_with_ticker(self, mock_download):
        fetch_cached_live_data.clear()
        dates = ["2026-01-05", "2026-01-06"]
        mock_download.return_value = _mock_yfinance_df(dates)

        df = fetch_cached_live_data("AAPL", "2026-01-05", "2026-01-07")
        assert df is not None
        assert not df.empty
        mock_download.assert_called_once()
        call_kwargs = mock_download.call_args[1]
        assert call_kwargs["tickers"] == "AAPL"
        assert call_kwargs["start"] == "2026-01-05"
        assert call_kwargs["end"] == "2026-01-07"

    @patch("yfinance.download")
    def test_live_fetch_end_to_end_success_produces_cleaned_dataframe(self, mock_download):
        fetch_cached_live_data.clear()
        dates = ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"]
        mock_download.return_value = _mock_yfinance_df(dates)

        df, err = get_and_clean_data(
            source_type="Live Yahoo Finance",
            ticker="AAPL",
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 9),
        )

        assert err is None
        assert df is not None
        assert len(df) == 5
        assert df.attrs["ticker"] == "AAPL"
        assert df.attrs["is_synthetic"] is False
        assert "cleaning_report" in df.attrs

        # Verify inclusive end-date offset (+1 day: 2026-01-10) passed to yfinance
        mock_download.assert_called_once()
        call_kwargs = mock_download.call_args[1]
        assert call_kwargs["tickers"] == "AAPL"
        assert call_kwargs["start"] == "2026-01-05"
        assert call_kwargs["end"] == "2026-01-10"

        # Verify observations in cleaned DataFrame are bounded up to 2026-01-09
        assert str(df["Date"].dt.date.iloc[-1]) == "2026-01-09"

    @patch("yfinance.download")
    def test_live_fetch_empty_response_handled_gracefully(self, mock_download):
        fetch_cached_live_data.clear()
        mock_download.return_value = pd.DataFrame()

        df, err = get_and_clean_data(
            source_type="Live Yahoo Finance",
            ticker="UNKNOWN_TICKER",
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 9),
        )

        assert df is None
        assert err is not None
        assert "No market data returned" in err or "No market data found" in err

    @patch("yfinance.download")
    def test_live_fetch_network_error_handled_gracefully(self, mock_download):
        fetch_cached_live_data.clear()
        mock_download.side_effect = Exception("HTTP 503: Service Unavailable")

        df, err = get_and_clean_data(
            source_type="Live Yahoo Finance",
            ticker="AAPL",
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 9),
        )

        assert df is None
        assert err is not None
        assert "Live Data Fetch Error" in err
        assert "HTTP 503" in err

    @patch("yfinance.download")
    def test_live_fetch_does_not_silently_fallback_to_sample_data(self, mock_download):
        fetch_cached_live_data.clear()
        mock_download.side_effect = DataFetchError("Simulated remote failure.")

        df, err = get_and_clean_data(
            source_type="Live Yahoo Finance",
            ticker="AAPL",
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 9),
        )

        assert df is None
        assert err is not None
        assert "SAMPLE" not in str(err)

    def test_sample_dataset_workflow_unaffected(self):
        df, err = get_and_clean_data(source_type="Sample Dataset (Synthetic)")
        assert err is None
        assert df is not None
        assert df.attrs["is_synthetic"] is True
        assert df.attrs["ticker"] == "SAMPLE"
        assert len(df) == 75

    def test_csv_upload_workflow_unaffected(self, sample_dashboard_df):
        csv_buf = BytesIO()
        sample_dashboard_df.to_csv(csv_buf, index=False)
        csv_buf.seek(0)

        df, err = get_and_clean_data(
            source_type="Upload CSV",
            uploaded_file=csv_buf,
            ticker="CUSTOM",
        )
        assert err is None
        assert df is not None
        assert df.attrs["is_synthetic"] is False
        assert df.attrs["ticker"] == "CUSTOM"
        assert len(df) == len(sample_dashboard_df)

