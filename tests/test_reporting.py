"""Automated test suite for Phase 11 Report Generation and Data Export Layer.

Covers:
- PDF research report generation (ReportLab)
- Responsive interactive HTML reports (Plotly standalone and CDN)
- Standardized analytical CSV datasets
- Qualitative insights and evidence CSV exports
- Caller DataFrame immutability and defensive copying
- Synthetic data disclosures and watermarking
- Edge case handling (empty input, short histories, special characters)
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import pypdf
import pytest

from stock_analyzer.analysis.insights import (
    InsightCategory,
    InsightSeverity,
    MarketInsight,
    StockInsightAnalyzer,
)
from stock_analyzer.data.exceptions import EmptyDataError, MissingColumnError
from stock_analyzer.reporting.data_export import (
    export_cleaned_data_csv,
    export_comprehensive_analysis_csv,
    export_insights_summary_csv,
)
from stock_analyzer.reporting.html_report import HTMLReportGenerator
from stock_analyzer.reporting.pdf_report import PDFReportGenerator
from stock_analyzer.reporting.report_generator import StockReportGenerator


@pytest.fixture
def sample_reporting_df() -> pd.DataFrame:
    """Fixture providing a deterministic 30-session OHLCV stock DataFrame."""
    dates = pd.date_range("2026-01-05", periods=30, freq="B").strftime("%Y-%m-%d")
    prices = [100.0 + i * 1.5 + (2.0 if i % 4 == 0 else -1.0) for i in range(30)]
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": [p - 0.5 for p in prices],
            "High": [p + 2.0 for p in prices],
            "Low": [p - 2.0 for p in prices],
            "Close": prices,
            "Volume": [1000000 + i * 25000 for i in range(30)],
        }
    )


@pytest.fixture
def short_reporting_df() -> pd.DataFrame:
    """Fixture providing a short 8-session DataFrame (insufficient for 20-day MAs)."""
    dates = pd.date_range("2026-01-05", periods=8, freq="B").strftime("%Y-%m-%d")
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": [100.0] * 8,
            "High": [105.0] * 8,
            "Low": [95.0] * 8,
            "Close": [102.0] * 8,
            "Volume": [500000] * 8,
        }
    )


@pytest.fixture
def synthetic_reporting_df() -> pd.DataFrame:
    """Fixture loading the sample stock dataset explicitly tagged as synthetic."""
    df = pd.read_csv("data/sample/sample_stock.csv")
    df.attrs["data_source"] = "synthetic"
    df.attrs["is_synthetic"] = True
    return df


# =============================================================================
# 1. PDF Report Generation Tests
# =============================================================================


class TestPDFReportGeneration:
    """Tests for multi-page PDF document generation using ReportLab."""

    def test_pdf_generation_succeeds_for_valid_input(self, sample_reporting_df, tmp_path):
        out_pdf = tmp_path / "valid_test_report.pdf"
        gen = PDFReportGenerator(sample_reporting_df, ticker="TEST", data_source="Unit Test")
        res_path = gen.generate(output_path=out_pdf)

        assert Path(res_path).exists()
        assert Path(res_path).stat().st_size > 10000  # Non-trivial PDF size

    def test_generated_file_is_valid_pdf_format(self, sample_reporting_df):
        gen = PDFReportGenerator(sample_reporting_df, ticker="AAPL", data_source="Live Market")
        pdf_bytes = gen.generate(output_path=None)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF-1.")
        assert b"%%EOF" in pdf_bytes[-1024:]  # Standard valid PDF termination

    def test_pdf_contains_required_sections_and_cover(self, sample_reporting_df):
        gen = PDFReportGenerator(sample_reporting_df, ticker="MSFT", author="Akash Das")
        pdf_bytes = gen.generate()

        # Check for textual markers embedded in the PDF byte stream
        assert b"Stock Market Data Analyzer" in pdf_bytes
        assert b"Akash Das" in pdf_bytes
        assert b"MSFT" in pdf_bytes

    def test_synthetic_data_warning_in_pdf(self, synthetic_reporting_df):
        gen = PDFReportGenerator(synthetic_reporting_df, ticker="SAMPLE", data_source="Synthetic Sample Dataset")
        pdf_bytes = gen.generate()

        assert gen.is_synthetic is True
        assert b"SYNTHETIC SAMPLE DATA ACTIVE" in pdf_bytes or b"SYNTHETIC" in pdf_bytes

    def test_pdf_dataset_profile_section_contains_metadata_and_boundaries(self, sample_reporting_df, tmp_path):
        out_pdf = tmp_path / "profile_test.pdf"
        gen = PDFReportGenerator(
            sample_reporting_df,
            ticker="NVDA",
            data_source="Live Market Feed",
            is_synthetic=False,
        )
        gen.generate(output_path=out_pdf)

        reader = pypdf.PdfReader(str(out_pdf))
        full_text = "".join(page.extract_text() or "" for page in reader.pages)

        assert "2. Dataset & Ingestion Profile" in full_text
        assert "NVDA" in full_text
        assert "Live Market Feed" in full_text
        assert "Observation Count" in full_text
        assert "Temporal Start Date" in full_text
        assert "Temporal End Date" in full_text
        assert "Data Ingestion Profile & Methodological Boundaries" in full_text

    def test_charts_embedded_correctly_in_pdf(self, sample_reporting_df, tmp_path):
        out_pdf = tmp_path / "chart_embedded.pdf"
        gen = PDFReportGenerator(sample_reporting_df, ticker="GOOG")
        gen.generate(output_path=out_pdf)

        assert out_pdf.exists()
        # A PDF with 4-5 high-res raster charts will easily exceed 100 KB
        assert out_pdf.stat().st_size > 100000

    def test_missing_optional_data_or_short_history_handled_gracefully(self, short_reporting_df, tmp_path):
        out_pdf = tmp_path / "short_history.pdf"
        # 8 rows < 20 days: moving averages and rolling vol will encounter warmup
        gen = PDFReportGenerator(short_reporting_df, ticker="SHORT")
        res_path = gen.generate(output_path=out_pdf)

        assert Path(res_path).exists()
        assert Path(res_path).stat().st_size > 5000

    def test_empty_dataframe_raises_empty_data_error(self):
        with pytest.raises(EmptyDataError, match="Cannot generate PDF report"):
            PDFReportGenerator(pd.DataFrame())

    def test_invalid_type_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected pandas DataFrame"):
            PDFReportGenerator("not_a_df")  # type: ignore

    def test_input_dataframe_immutability(self, sample_reporting_df):
        original = sample_reporting_df.copy(deep=True)
        original_attrs = sample_reporting_df.attrs.copy()

        gen = PDFReportGenerator(sample_reporting_df, ticker="IMMUTABLE")
        _ = gen.generate()

        pd.testing.assert_frame_equal(sample_reporting_df, original)
        assert sample_reporting_df.attrs == original_attrs


# =============================================================================
# 2. HTML Report Generation Tests
# =============================================================================


class TestHTMLReportGeneration:
    """Tests for responsive interactive HTML research reports using Plotly."""

    def test_html_generation_succeeds_for_valid_input(self, sample_reporting_df, tmp_path):
        out_html = tmp_path / "test_report.html"
        gen = HTMLReportGenerator(sample_reporting_df, ticker="TEST", data_source="Live Stream")
        res_path = gen.generate(output_path=out_html, embed_plotly_js=False)

        assert Path(res_path).exists()
        content = Path(res_path).read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "Quantitative Financial Analysis Report" in content

    def test_required_report_sections_present_in_html(self, sample_reporting_df):
        gen = HTMLReportGenerator(sample_reporting_df, ticker="AAPL")
        html_text = gen.generate(embed_plotly_js=False)
        if isinstance(html_text, bytes):
            html_text = html_text.decode("utf-8")

        # Anchors and section headers
        assert 'id="summary"' in html_text
        assert 'id="technical"' in html_text
        assert 'id="returns"' in html_text
        assert 'id="risk"' in html_text
        assert 'id="volume"' in html_text
        assert 'id="correlation"' in html_text
        assert 'id="insights"' in html_text
        assert 'id="disclaimers"' in html_text

    def test_html_escaping_prevents_unsafe_injection(self, sample_reporting_df):
        unsafe_ticker = "<script>alert('xss')</script>"
        gen = HTMLReportGenerator(sample_reporting_df, ticker=unsafe_ticker)
        html_text = gen.generate(embed_plotly_js=False)
        if isinstance(html_text, bytes):
            html_text = html_text.decode("utf-8")

        # Ensure raw payload script is not executed and is properly escaped
        assert "<script>alert" not in html_text.lower()
        assert "&lt;script&gt;alert" in html_text.lower()

    def test_synthetic_data_labels_present_in_html(self, synthetic_reporting_df):
        gen = HTMLReportGenerator(synthetic_reporting_df, ticker="SAMPLE", data_source="Synthetic Sample Dataset")
        html_text = gen.generate(embed_plotly_js=False)
        if isinstance(html_text, bytes):
            html_text = html_text.decode("utf-8")

        assert "SYNTHETIC SAMPLE DATA ACTIVE" in html_text
        assert "data/sample/sample_stock.csv" in html_text

    def test_plotly_chart_integration_divs_rendered(self, sample_reporting_df):
        gen = HTMLReportGenerator(sample_reporting_df, ticker="TSLA")
        html_text = gen.generate(embed_plotly_js=False)
        if isinstance(html_text, bytes):
            html_text = html_text.decode("utf-8")

        # Confirm Plotly chart divs are injected
        assert 'class="plotly-graph-div"' in html_text or 'class="chart-container"' in html_text
        assert "cdn.plot.ly" in html_text

    def test_cdn_vs_embedded_plotly_modes(self, sample_reporting_df):
        gen = HTMLReportGenerator(sample_reporting_df, ticker="AMZN")

        # Mode A: CDN
        cdn_html = gen.generate(embed_plotly_js=False)
        if isinstance(cdn_html, bytes):
            cdn_html = cdn_html.decode("utf-8")
        assert "cdn.plot.ly" in cdn_html
        assert len(cdn_html) < 500000  # Lightweight

        # Mode B: Embedded full offline
        offline_html = gen.generate(embed_plotly_js=True)
        if isinstance(offline_html, bytes):
            offline_html = offline_html.decode("utf-8")
        assert len(offline_html) > 4000000  # >4 MB due to full embedded Plotly bundle
        assert "Fully Offline" in offline_html

    def test_missing_or_short_data_handled_gracefully_in_html(self, short_reporting_df):
        gen = HTMLReportGenerator(short_reporting_df, ticker="SHORT")
        html_text = gen.generate(embed_plotly_js=False)
        if isinstance(html_text, bytes):
            html_text = html_text.decode("utf-8")

        assert "<!DOCTYPE html>" in html_text
        assert "SHORT" in html_text

    def test_empty_dataframe_raises_empty_data_error_in_html(self):
        with pytest.raises(EmptyDataError, match="Cannot generate HTML report"):
            HTMLReportGenerator(pd.DataFrame())

    def test_input_dataframe_immutability_in_html(self, sample_reporting_df):
        original = sample_reporting_df.copy(deep=True)
        gen = HTMLReportGenerator(sample_reporting_df, ticker="IMMUTABLE_HTML")
        _ = gen.generate()

        pd.testing.assert_frame_equal(sample_reporting_df, original)


# =============================================================================
# 3. CSV Data Export Tests
# =============================================================================


class TestCSVDataExports:
    """Tests for standardized CSV exports (OHLCV, comprehensive analytical, and insights summary)."""

    def test_export_cleaned_data_csv(self, sample_reporting_df, tmp_path):
        out_csv = tmp_path / "cleaned_export.csv"
        res_path = export_cleaned_data_csv(sample_reporting_df, output_path=out_csv)

        assert Path(res_path).exists()
        loaded = pd.read_csv(res_path)
        assert len(loaded) == len(sample_reporting_df)
        assert list(loaded.columns) == list(sample_reporting_df.columns)

    def test_export_comprehensive_analysis_csv_columns_and_metrics(self, sample_reporting_df, tmp_path):
        out_csv = tmp_path / "full_analysis.csv"
        res_path = export_comprehensive_analysis_csv(sample_reporting_df, ticker="NVDA", output_path=out_csv)

        assert Path(res_path).exists()
        loaded = pd.read_csv(res_path)

        # Confirm indicator and risk columns were calculated and attached
        expected_cols = [
            "Ticker", "Date", "Open", "High", "Low", "Close", "Volume",
            "SMA_20", "SMA_50", "EMA_20", "Daily_Return", "Cumulative_Return",
            "Drawdown", "Rolling_Vol_21", "Rolling_Vol_63"
        ]
        for col in expected_cols:
            assert col in loaded.columns, f"Missing expected column '{col}' in comprehensive CSV"

        assert loaded["Ticker"].iloc[0] == "NVDA"

    def test_export_comprehensive_csv_preserves_dates_and_numerics(self, sample_reporting_df):
        csv_bytes = export_comprehensive_analysis_csv(sample_reporting_df, ticker="AAPL")
        assert isinstance(csv_bytes, bytes)

        df_loaded = pd.read_csv(io.BytesIO(csv_bytes))
        assert len(df_loaded) == len(sample_reporting_df)
        # Check date format YYYY-MM-DD
        assert df_loaded["Date"].str.match(r"^\d{4}-\d{2}-\d{2}$").all()
        # Check non-empty returns
        assert not df_loaded["Daily_Return"].iloc[1:].isna().any()

    def test_export_insights_summary_csv_structure(self, tmp_path):
        insights = [
            MarketInsight(
                category=InsightCategory.PRICE_TREND,
                title="Bullish Trajectory",
                observation="Price gained 15% across evaluated period.",
                evidence={"gain_pct": 0.15},
                severity=InsightSeverity.POSITIVE,
                description="Test description.",
                limitations="Past performance is not predictive.",
            ),
            MarketInsight(
                category=InsightCategory.TRADING_VOLUME,
                title="Elevated Trading Volume",
                observation="Latest volume represents 2.1x baseline turnover.",
                evidence={"volume_ratio": 2.1},
                severity=InsightSeverity.WARNING,
                description="Volume comparison.",
                limitations="Exchange volume does not identify participant classes.",
            ),
        ]

        out_csv = tmp_path / "insights_export.csv"
        res_path = export_insights_summary_csv(insights, ticker="TEST", output_path=out_csv)

        assert Path(res_path).exists()
        df_ins = pd.read_csv(res_path)
        assert len(df_ins) == 2
        assert list(df_ins.columns) == [
            "Ticker",
            "Data_Source",
            "Is_Synthetic",
            "Category",
            "Title",
            "Severity",
            "Observation",
            "Supporting_Evidence",
            "Limitations",
        ]
        assert df_ins["Category"].iloc[0] == "Price Trend"
        assert df_ins["Severity"].iloc[0] == "positive"
        assert "gain_pct=0.15" in df_ins["Supporting_Evidence"].iloc[0]

    def test_synthetic_cleaned_csv_export_has_is_synthetic_column(self, synthetic_reporting_df, tmp_path):
        out_csv = tmp_path / "synthetic_cleaned.csv"
        res_path = export_cleaned_data_csv(synthetic_reporting_df, output_path=out_csv, is_synthetic=True)

        assert Path(res_path).exists()
        loaded = pd.read_csv(res_path)
        assert "Is_Synthetic" in loaded.columns
        assert loaded["Is_Synthetic"].all()
        # Verify base OHLCV columns and date values remain intact
        for col in ["Date", "Open", "High", "Low", "Close", "Volume"]:
            assert col in loaded.columns
        assert len(loaded) == len(synthetic_reporting_df)

    def test_synthetic_insights_csv_export_has_is_synthetic_column(self, tmp_path):
        insights = [
            MarketInsight(
                category=InsightCategory.PRICE_TREND,
                title="Synthetic Signal",
                observation="Synthetic observation for testing.",
                evidence={"test": 1},
                severity=InsightSeverity.INFO,
                description="Test description.",
                limitations="Synthetic data.",
            )
        ]
        out_csv = tmp_path / "synthetic_insights.csv"
        res_path = export_insights_summary_csv(
            insights,
            ticker="SAMPLE",
            data_source="Sample Dataset (Synthetic)",
            is_synthetic=True,
            output_path=out_csv,
        )
        loaded = pd.read_csv(res_path)
        assert "Is_Synthetic" in loaded.columns
        assert loaded["Is_Synthetic"].iloc[0] == True
        assert loaded["Data_Source"].iloc[0] == "Sample Dataset (Synthetic)"
        assert loaded["Ticker"].iloc[0] == "SAMPLE"

    def test_reopen_and_verify_all_three_csv_exports_with_synthetic_data(self, synthetic_reporting_df, tmp_path):
        """Reopen and verify all three CSV exports independently using pandas."""
        # 1. Cleaned CSV
        c_path = tmp_path / "reopen_cleaned.csv"
        export_cleaned_data_csv(synthetic_reporting_df, output_path=c_path, is_synthetic=True)
        df_c = pd.read_csv(c_path)
        assert len(df_c) == len(synthetic_reporting_df)
        assert "Is_Synthetic" in df_c.columns
        assert df_c["Is_Synthetic"].all()

        # 2. Comprehensive CSV
        f_path = tmp_path / "reopen_full.csv"
        export_comprehensive_analysis_csv(synthetic_reporting_df, ticker="SAMPLE", output_path=f_path, is_synthetic=True)
        df_f = pd.read_csv(f_path)
        assert len(df_f) == len(synthetic_reporting_df)
        assert "Is_Synthetic" in df_f.columns
        assert "Drawdown" in df_f.columns
        assert "Rolling_Vol_63" in df_f.columns

        # 3. Insights CSV
        i_path = tmp_path / "reopen_insights.csv"
        analyzer = StockInsightAnalyzer(synthetic_reporting_df, ticker="SAMPLE")
        insights = analyzer.generate_all_insights()
        export_insights_summary_csv(
            insights,
            ticker="SAMPLE",
            data_source="Sample Dataset (Synthetic)",
            is_synthetic=True,
            output_path=i_path,
        )
        df_i = pd.read_csv(i_path)
        assert len(df_i) > 0
        assert "Is_Synthetic" in df_i.columns
        assert df_i["Is_Synthetic"].all()
        assert (df_i["Data_Source"] == "Sample Dataset (Synthetic)").all()

    def test_synthetic_flag_retained_in_comprehensive_csv(self, synthetic_reporting_df):
        csv_bytes = export_comprehensive_analysis_csv(synthetic_reporting_df, ticker="SAMPLE", is_synthetic=True)
        df_loaded = pd.read_csv(io.BytesIO(csv_bytes))
        assert "Is_Synthetic" in df_loaded.columns
        assert df_loaded["Is_Synthetic"].all()

    def test_source_dataframes_remain_unmodified_after_csv_export(self, sample_reporting_df):
        original = sample_reporting_df.copy(deep=True)
        _ = export_comprehensive_analysis_csv(sample_reporting_df, ticker="SOURCE_TEST")
        pd.testing.assert_frame_equal(sample_reporting_df, original)

    def test_empty_dataframe_raises_empty_data_error_in_csv(self):
        with pytest.raises(EmptyDataError):
            export_cleaned_data_csv(pd.DataFrame())

        with pytest.raises(EmptyDataError):
            export_comprehensive_analysis_csv(pd.DataFrame())


# =============================================================================
# 4. StockReportGenerator Orchestrator Tests
# =============================================================================


class TestStockReportGeneratorOrchestration:
    """Tests for unified StockReportGenerator interface and batch archival workflow."""

    def test_report_generator_initialization_and_immutability(self, sample_reporting_df):
        original = sample_reporting_df.copy(deep=True)
        srg = StockReportGenerator(sample_reporting_df, ticker="AAPL", data_source="Yahoo")

        assert srg.ticker == "AAPL"
        assert srg.data_source == "Yahoo"
        pd.testing.assert_frame_equal(sample_reporting_df, original)

    def test_generate_all_reports_creates_all_artifacts(self, sample_reporting_df, tmp_path):
        srg = StockReportGenerator(sample_reporting_df, ticker="ORCH_TEST", data_source="Fixture")
        results = srg.generate_all_reports(output_dir=tmp_path, embed_plotly_js=False)

        assert "cleaned_csv" in results
        assert "pdf_report" in results
        assert "html_report" in results
        assert "comprehensive_csv" in results
        assert "insights_csv" in results

        for key, file_path in results.items():
            p = Path(file_path)
            assert p.exists(), f"Generated artifact '{key}' not found at {p}"
            assert p.stat().st_size > 500, f"Artifact '{key}' appears truncated ({p.stat().st_size} bytes)"

    def test_sanitize_filename_cleans_unsafe_characters(self, sample_reporting_df):
        srg = StockReportGenerator(sample_reporting_df, ticker="BRK/B:US")
        safe_name = srg._sanitize_filename("BRK/B:US?*<>|")
        assert "/" not in safe_name
        assert ":" not in safe_name
        assert "<" not in safe_name

    def test_empty_input_raises_empty_data_error(self):
        with pytest.raises(EmptyDataError):
            StockReportGenerator(pd.DataFrame())

    def test_missing_required_close_column_raises_missing_column_error(self):
        df_no_close = pd.DataFrame({"Date": ["2026-01-01"], "Open": [100.0]})
        with pytest.raises(MissingColumnError, match="DataFrame lacks required 'Close'"):
            StockReportGenerator(df_no_close)

    def test_synthetic_data_detection_from_source_or_ticker(self):
        dates = ["2026-01-01", "2026-01-02"]
        df_sample = pd.DataFrame(
            {
                "Date": dates,
                "Open": [100.0, 101.0],
                "High": [102.0, 103.0],
                "Low": [99.0, 100.0],
                "Close": [100.0, 102.0],
                "Volume": [1000, 1000],
            }
        )
        srg1 = StockReportGenerator(df_sample, ticker="SAMPLE")
        assert srg1.is_synthetic is True

        srg2 = StockReportGenerator(df_sample, ticker="TEST", data_source="Sample Dataset (Synthetic)")
        assert srg2.is_synthetic is True

        srg3 = StockReportGenerator(df_sample, ticker="AAPL", data_source="Live Yahoo Finance")
        assert srg3.is_synthetic is False


# =============================================================================
# 5. Report Selection Freshness & Context Isolation Tests
# =============================================================================


class TestReportSelectionFreshnessAndContextIsolation:
    """Tests guaranteeing that report generation reflects active context without stale artifact reuse.

    Verifies isolation across:
    - Distinct ticker symbols (AAPL vs GOOGL)
    - Distinct date ranges (short vs full observation window)
    - Synthetic sample data provenance
    - Uploaded custom CSV data provenance
    - Live Yahoo Finance market data provenance (mocked)
    - Coherence across all artifact types (PDF, HTML, Cleaned CSV, Comprehensive CSV, Insights CSV)
    """

    def test_freshness_across_different_ticker_symbols(self, sample_reporting_df, tmp_path):
        """Verify that switching ticker from AAPL to GOOGL produces distinct artifacts without stale state."""
        # 1. Generate for AAPL
        dir_aapl = tmp_path / "aapl_run"
        gen_aapl = StockReportGenerator(sample_reporting_df, ticker="AAPL", data_source="Live Market Feed")
        res_aapl = gen_aapl.generate_all_reports(output_dir=dir_aapl)

        # Inspect PDF
        pdf_reader_aapl = pypdf.PdfReader(res_aapl["pdf_report"])
        pdf_text_aapl = "".join(p.extract_text() or "" for p in pdf_reader_aapl.pages)
        assert "AAPL" in pdf_text_aapl
        assert "GOOGL" not in pdf_text_aapl

        # Inspect HTML
        html_text_aapl = Path(res_aapl["html_report"]).read_text(encoding="utf-8")
        assert "AAPL" in html_text_aapl
        assert "GOOGL" not in html_text_aapl

        # Inspect Comprehensive CSV
        df_comp_aapl = pd.read_csv(res_aapl["comprehensive_csv"])
        assert (df_comp_aapl["Ticker"] == "AAPL").all()

        # Inspect Insights CSV
        df_ins_aapl = pd.read_csv(res_aapl["insights_csv"])
        assert (df_ins_aapl["Ticker"] == "AAPL").all()

        # 2. Generate for GOOGL
        dir_googl = tmp_path / "googl_run"
        gen_googl = StockReportGenerator(sample_reporting_df, ticker="GOOGL", data_source="Live Market Feed")
        res_googl = gen_googl.generate_all_reports(output_dir=dir_googl)

        # Inspect PDF
        pdf_reader_googl = pypdf.PdfReader(res_googl["pdf_report"])
        pdf_text_googl = "".join(p.extract_text() or "" for p in pdf_reader_googl.pages)
        assert "GOOGL" in pdf_text_googl
        assert "AAPL" not in pdf_text_googl

        # Inspect HTML
        html_text_googl = Path(res_googl["html_report"]).read_text(encoding="utf-8")
        assert "GOOGL" in html_text_googl
        assert "AAPL" not in html_text_googl

        # Inspect Comprehensive CSV
        df_comp_googl = pd.read_csv(res_googl["comprehensive_csv"])
        assert (df_comp_googl["Ticker"] == "GOOGL").all()

        # Inspect Insights CSV
        df_ins_googl = pd.read_csv(res_googl["insights_csv"])
        assert (df_ins_googl["Ticker"] == "GOOGL").all()

    def test_freshness_across_different_date_ranges(self, sample_reporting_df, tmp_path):
        """Verify that slicing to different date ranges produces matching observation counts and dates."""
        # Slice A: 12 sessions
        df_range_a = sample_reporting_df.iloc[:12].copy(deep=True)
        gen_a = StockReportGenerator(df_range_a, ticker="TEST_RANGE_A", data_source="Historical Window A")
        res_a = gen_a.generate_all_reports(output_dir=tmp_path / "range_a")

        df_comp_a = pd.read_csv(res_a["comprehensive_csv"])
        assert len(df_comp_a) == 12
        assert df_comp_a["Date"].iloc[0] == sample_reporting_df["Date"].iloc[0]
        assert df_comp_a["Date"].iloc[-1] == sample_reporting_df["Date"].iloc[11]

        pdf_a = pypdf.PdfReader(res_a["pdf_report"])
        text_a = "".join(p.extract_text() or "" for p in pdf_a.pages)
        assert "12 sessions" in text_a

        # Slice B: 28 sessions
        df_range_b = sample_reporting_df.iloc[:28].copy(deep=True)
        gen_b = StockReportGenerator(df_range_b, ticker="TEST_RANGE_B", data_source="Historical Window B")
        res_b = gen_b.generate_all_reports(output_dir=tmp_path / "range_b")

        df_comp_b = pd.read_csv(res_b["comprehensive_csv"])
        assert len(df_comp_b) == 28
        assert df_comp_b["Date"].iloc[0] == sample_reporting_df["Date"].iloc[0]
        assert df_comp_b["Date"].iloc[-1] == sample_reporting_df["Date"].iloc[27]

        pdf_b = pypdf.PdfReader(res_b["pdf_report"])
        text_b = "".join(p.extract_text() or "" for p in pdf_b.pages)
        assert "28 sessions" in text_b

    def test_freshness_sample_synthetic_data_context(self, synthetic_reporting_df, tmp_path):
        """Verify report generation under synthetic sample stock dataset context."""
        gen = StockReportGenerator(
            synthetic_reporting_df,
            ticker="SAMPLE",
            data_source="Sample Dataset (Synthetic)",
            is_synthetic=True,
        )
        res = gen.generate_all_reports(output_dir=tmp_path / "synth_run")

        # 1. Cleaned CSV
        df_c = pd.read_csv(res["cleaned_csv"])
        assert "Is_Synthetic" in df_c.columns
        assert df_c["Is_Synthetic"].all()
        assert len(df_c) == len(synthetic_reporting_df)

        # 2. Comprehensive CSV
        df_comp = pd.read_csv(res["comprehensive_csv"])
        assert "Is_Synthetic" in df_comp.columns
        assert df_comp["Is_Synthetic"].all()

        # 3. Insights CSV
        df_ins = pd.read_csv(res["insights_csv"])
        assert "Is_Synthetic" in df_ins.columns
        assert df_ins["Is_Synthetic"].all()
        assert (df_ins["Data_Source"] == "Sample Dataset (Synthetic)").all()

        # 4. PDF Report
        reader = pypdf.PdfReader(res["pdf_report"])
        pdf_text = "".join(p.extract_text() or "" for p in reader.pages)
        assert "SYNTHETIC DATASET IDENTIFICATION" in pdf_text
        assert "YES (Synthetic Test Data)" in pdf_text

        # 5. HTML Report
        html_text = Path(res["html_report"]).read_text(encoding="utf-8")
        assert "SYNTHETIC SAMPLE DATA ACTIVE" in html_text

    def test_freshness_uploaded_csv_data_context(self, tmp_path):
        """Verify report generation under user-uploaded custom CSV context."""
        dates = pd.date_range("2025-06-01", periods=25, freq="B").strftime("%Y-%m-%d")
        df_upload = pd.DataFrame(
            {
                "Date": dates,
                "Open": [200.0 + i for i in range(25)],
                "High": [205.0 + i for i in range(25)],
                "Low": [198.0 + i for i in range(25)],
                "Close": [202.0 + i for i in range(25)],
                "Volume": [750000 + i * 10000 for i in range(25)],
            }
        )
        df_upload.attrs["data_source"] = "csv"
        df_upload.attrs["is_synthetic"] = False

        gen = StockReportGenerator(
            df_upload,
            ticker="PORTFOLIO",
            data_source="Uploaded CSV (portfolio_2025.csv)",
            is_synthetic=False,
        )
        res = gen.generate_all_reports(output_dir=tmp_path / "upload_run")

        # Cleaned CSV should NOT have Is_Synthetic=True
        df_c = pd.read_csv(res["cleaned_csv"])
        assert "Is_Synthetic" not in df_c.columns or not df_c["Is_Synthetic"].any()

        # Comprehensive CSV
        df_comp = pd.read_csv(res["comprehensive_csv"])
        assert (df_comp["Ticker"] == "PORTFOLIO").all()
        assert "Is_Synthetic" not in df_comp.columns or not df_comp["Is_Synthetic"].any()

        # Insights CSV
        df_ins = pd.read_csv(res["insights_csv"])
        assert (df_ins["Ticker"] == "PORTFOLIO").all()
        assert (df_ins["Data_Source"] == "Uploaded CSV (portfolio_2025.csv)").all()
        assert not df_ins["Is_Synthetic"].any()

        # PDF should NOT contain synthetic warning
        reader = pypdf.PdfReader(res["pdf_report"])
        pdf_text = "".join(p.extract_text() or "" for p in reader.pages)
        assert "PORTFOLIO" in pdf_text
        assert "NO (Live Market Data)" in pdf_text
        assert "SYNTHETIC DATASET IDENTIFICATION" not in pdf_text

    def test_freshness_live_yahoo_finance_mocked_context(self, sample_reporting_df, tmp_path, monkeypatch):
        """Verify report generation under Live Yahoo Finance context without external network calls."""
        # Use deterministic DataFrame to simulate Yahoo Finance live retrieval
        mock_df = sample_reporting_df.copy(deep=True)
        mock_df.attrs["data_source"] = "yahoo"
        mock_df.attrs["is_synthetic"] = False

        gen = StockReportGenerator(
            mock_df,
            ticker="TSLA",
            data_source="Live Yahoo Finance",
            is_synthetic=False,
        )
        res = gen.generate_all_reports(output_dir=tmp_path / "yahoo_run")

        # Verify all exports carry Live Yahoo Finance metadata and TSLA ticker
        df_comp = pd.read_csv(res["comprehensive_csv"])
        assert (df_comp["Ticker"] == "TSLA").all()

        df_ins = pd.read_csv(res["insights_csv"])
        assert (df_ins["Ticker"] == "TSLA").all()
        assert (df_ins["Data_Source"] == "Live Yahoo Finance").all()
        assert not df_ins["Is_Synthetic"].any()

        reader = pypdf.PdfReader(res["pdf_report"])
        pdf_text = "".join(p.extract_text() or "" for p in reader.pages)
        assert "TSLA" in pdf_text
        assert "Live Yahoo Finance" in pdf_text
        assert "NO (Live Market Data)" in pdf_text

        html_text = Path(res["html_report"]).read_text(encoding="utf-8")
        assert "TSLA" in html_text
        assert "Live Yahoo Finance" in html_text

    def test_all_export_formats_share_same_active_context(self, sample_reporting_df, tmp_path):
        """Verify cross-format coherence: PDF, HTML, and all 3 CSVs strictly agree on active parameters."""
        gen = StockReportGenerator(
            sample_reporting_df,
            ticker="COHERENT",
            data_source="Multi-Format Validation Feed",
            is_synthetic=False,
        )
        res = gen.generate_all_reports(output_dir=tmp_path / "coherent_run")

        # 1. Cleaned CSV
        df_c = pd.read_csv(res["cleaned_csv"])
        # 2. Comprehensive CSV
        df_comp = pd.read_csv(res["comprehensive_csv"])
        # 3. Insights CSV
        df_ins = pd.read_csv(res["insights_csv"])

        # Row counts match
        assert len(df_c) == len(sample_reporting_df)
        assert len(df_comp) == len(sample_reporting_df)

        # Date boundaries match
        assert df_c["Date"].iloc[0] == df_comp["Date"].iloc[0]
        assert df_c["Date"].iloc[-1] == df_comp["Date"].iloc[-1]

        # Ticker match across CSVs
        assert (df_comp["Ticker"] == "COHERENT").all()
        assert (df_ins["Ticker"] == "COHERENT").all()

        # PDF matches observation count and ticker
        reader = pypdf.PdfReader(res["pdf_report"])
        pdf_text = "".join(p.extract_text() or "" for p in reader.pages)
        assert "COHERENT" in pdf_text
        assert f"{len(sample_reporting_df):,} sessions" in pdf_text

        # HTML matches ticker and dates
        html_text = Path(res["html_report"]).read_text(encoding="utf-8")
        assert "COHERENT" in html_text
        assert str(df_c["Date"].iloc[0]) in html_text
        assert str(df_c["Date"].iloc[-1]) in html_text
