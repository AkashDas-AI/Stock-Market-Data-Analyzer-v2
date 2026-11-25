"""Public report generation orchestrator.

Provides the unified StockReportGenerator interface to export stock market
analysis into professional PDF reports, interactive HTML dossiers, and analytical CSV datasets.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

from stock_analyzer.analysis.insights import MarketInsight, StockInsightAnalyzer
from stock_analyzer.data.exceptions import EmptyDataError, MissingColumnError
from stock_analyzer.reporting.data_export import (
    export_cleaned_data_csv,
    export_comprehensive_analysis_csv,
    export_insights_summary_csv,
)
from stock_analyzer.reporting.html_report import HTMLReportGenerator
from stock_analyzer.reporting.pdf_report import PDFReportGenerator


class StockReportGenerator:
    """Unified reporting engine for generating PDF, HTML, and CSV export packages."""

    def __init__(
        self,
        df: pd.DataFrame,
        ticker: Optional[str] = "STOCK",
        data_source: Optional[str] = "Unknown",
        is_synthetic: Optional[bool] = None,
        author: str = "Akash Das",
    ) -> None:
        """Initialize reporting engine with cleaned stock DataFrame.

        Args:
            df: Cleaned OHLCV stock market DataFrame.
            ticker: Ticker symbol or dataset identifier.
            data_source: Ingestion source description (e.g. 'Live Yahoo Finance').
            is_synthetic: Explicit synthetic data indicator.
            author: Report author name.

        Raises:
            TypeError: If df is not a pandas DataFrame.
            EmptyDataError: If df is empty.
            MissingColumnError: If df lacks required columns.
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"Expected pandas DataFrame, got {type(df).__name__}.")
        if df.empty:
            raise EmptyDataError("Cannot generate reports from an empty DataFrame.")
        if "Close" not in df.columns:
            raise MissingColumnError("DataFrame lacks required 'Close' price column.")

        # Ensure caller immutability
        self.df = df.copy(deep=True)
        self.ticker = (ticker or "STOCK").upper()
        self.data_source = data_source or "Unknown"
        self.author = author

        if is_synthetic is not None:
            self.is_synthetic = is_synthetic
        else:
            self.is_synthetic = (
                self.df.attrs.get("data_source") == "synthetic"
                or self.df.attrs.get("is_synthetic", False)
                or "synthetic" in str(self.data_source).lower()
                or self.ticker == "SAMPLE"
            )

        if self.is_synthetic:
            self.df.attrs["is_synthetic"] = True

        # Initialize sub-generators
        self._pdf_generator = PDFReportGenerator(
            self.df,
            ticker=self.ticker,
            data_source=self.data_source,
            is_synthetic=self.is_synthetic,
            author=self.author,
        )
        self._html_generator = HTMLReportGenerator(
            self.df,
            ticker=self.ticker,
            data_source=self.data_source,
            is_synthetic=self.is_synthetic,
            author=self.author,
        )
        self._insight_analyzer = StockInsightAnalyzer(self.df, ticker=self.ticker)

    def _sanitize_filename(self, name: str) -> str:
        """Ensure filenames contain only safe alphanumeric and underscore characters."""
        return re.sub(r"[^\w\-]", "_", name)

    def generate_pdf_report(
        self, output_path: Optional[Union[str, Path]] = None
    ) -> Union[str, bytes]:
        """Generate professional multi-page research report in PDF format.

        Args:
            output_path: Optional file path. If None, returns PDF bytes.

        Returns:
            File path string if output_path is provided, or PDF bytes.
        """
        return self._pdf_generator.generate(output_path=output_path)

    def generate_html_report(
        self,
        output_path: Optional[Union[str, Path]] = None,
        embed_plotly_js: bool = False,
    ) -> Union[str, bytes]:
        """Generate interactive research report in standalone HTML format.

        Args:
            output_path: Optional file path. If None, returns HTML bytes.
            embed_plotly_js: If True, bundles full offline Plotly JS. If False, uses CDN.

        Returns:
            File path string if output_path is provided, or HTML bytes.
        """
        return self._html_generator.generate(
            output_path=output_path, embed_plotly_js=embed_plotly_js
        )

    def export_cleaned_csv(
        self, output_path: Optional[Union[str, Path]] = None
    ) -> Union[str, bytes]:
        """Export cleaned base OHLCV dataset to CSV format.

        Args:
            output_path: Optional file path. If None, returns CSV bytes.

        Returns:
            File path string if output_path is provided, or CSV bytes.
        """
        return export_cleaned_data_csv(
            self.df, output_path=output_path, is_synthetic=self.is_synthetic
        )

    def export_comprehensive_csv(
        self, output_path: Optional[Union[str, Path]] = None
    ) -> Union[str, bytes]:
        """Export enriched analytical dataset (OHLCV + indicators + returns + risk metrics).

        Args:
            output_path: Optional file path. If None, returns CSV bytes.

        Returns:
            File path string if output_path is provided, or CSV bytes.
        """
        return export_comprehensive_analysis_csv(
            self.df,
            ticker=self.ticker,
            output_path=output_path,
            is_synthetic=self.is_synthetic,
        )

    def export_insights_csv(
        self, output_path: Optional[Union[str, Path]] = None
    ) -> Union[str, bytes]:
        """Export qualitative insights collection to structured CSV format.

        Args:
            output_path: Optional file path. If None, returns CSV bytes.

        Returns:
            File path string if output_path is provided, or CSV bytes.
        """
        insights = self._insight_analyzer.generate_all_insights()
        return export_insights_summary_csv(
            insights,
            ticker=self.ticker,
            data_source=self.data_source,
            is_synthetic=self.is_synthetic,
            output_path=output_path,
        )

    def generate_all_reports(
        self,
        output_dir: Union[str, Path] = "reports/generated",
        embed_plotly_js: bool = False,
    ) -> Dict[str, str]:
        """Generate complete suite of reports and CSV exports in destination directory.

        Args:
            output_dir: Directory where reports will be saved.
            embed_plotly_js: If True, HTML report embeds full offline Plotly JS.

        Returns:
            Dictionary mapping artifact type to generated file path string.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        date_str = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_sym = self._sanitize_filename(self.ticker)

        pdf_path = out_path / f"{safe_sym}_analysis_report_{date_str}.pdf"
        html_path = out_path / f"{safe_sym}_interactive_report_{date_str}.html"
        cleaned_csv_path = out_path / f"{safe_sym}_cleaned_ohlcv_{date_str}.csv"
        full_csv_path = out_path / f"{safe_sym}_comprehensive_analysis_{date_str}.csv"
        insights_csv_path = out_path / f"{safe_sym}_insights_summary_{date_str}.csv"

        self.generate_pdf_report(output_path=pdf_path)
        self.generate_html_report(output_path=html_path, embed_plotly_js=embed_plotly_js)
        self.export_cleaned_csv(output_path=cleaned_csv_path)
        self.export_comprehensive_csv(output_path=full_csv_path)
        self.export_insights_csv(output_path=insights_csv_path)

        return {
            "pdf_report": str(pdf_path),
            "html_report": str(html_path),
            "cleaned_csv": str(cleaned_csv_path),
            "comprehensive_csv": str(full_csv_path),
            "insights_csv": str(insights_csv_path),
        }
