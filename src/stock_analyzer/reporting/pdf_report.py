"""PDF report generation module using ReportLab.

Generates professional, publication-quality financial research reports in PDF format,
integrating executive summaries, technical charts, returns and risk analysis,
trading volume evaluations, Phase 10 structured insights, and regulatory disclaimers.
"""

from __future__ import annotations

import datetime as dt
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import pandas as pd
import reportlab.rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Disable stream compression for deterministic output and byte inspectability
reportlab.rl_config.pageCompression = 0

from stock_analyzer.analysis.eda import ExploratoryDataAnalyzer
from stock_analyzer.analysis.indicators import TechnicalIndicators
from stock_analyzer.analysis.insights import InsightSummary, MarketInsight, StockInsightAnalyzer
from stock_analyzer.analysis.returns import ReturnAnalyzer
from stock_analyzer.analysis.risk import RiskAnalyzer
from stock_analyzer.data.exceptions import EmptyDataError, MissingColumnError
from stock_analyzer.visualization.static_charts import StaticChartGenerator


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas that accumulates total page count and adds running headers/footers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int) -> None:
        """Draw running header and footer on all pages."""
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#6B7280"))

        # Do not draw top header on cover page (Page 1)
        if self._pageNumber > 1:
            header_text = getattr(self, "report_header_title", "Stock Market Data Analyzer | Akash Das")
            self.drawString(40, 755, header_text)
            self.setStrokeColor(colors.HexColor("#E5E7EB"))
            self.setLineWidth(0.5)
            self.line(40, 748, 572, 748)

        # Bottom footer on all pages
        footer_left = "FOR INFORMATIONAL PURPOSES ONLY — Not Investment Advice"
        footer_right = f"Page {self._pageNumber} of {page_count}"
        self.drawString(40, 32, footer_left)
        self.drawRightString(572, 32, footer_right)
        self.setStrokeColor(colors.HexColor("#E5E7EB"))
        self.setLineWidth(0.5)
        self.line(40, 42, 572, 42)

        self.restoreState()


class PDFReportGenerator:
    """Orchestrates comprehensive multi-page PDF research report generation."""

    def __init__(
        self,
        df: pd.DataFrame,
        ticker: Optional[str] = "STOCK",
        data_source: Optional[str] = "Unknown",
        is_synthetic: Optional[bool] = None,
        author: str = "Akash Das",
    ) -> None:
        """Initialize PDF report generator with stock DataFrame and metadata.

        Args:
            df: Cleaned OHLCV stock market DataFrame.
            ticker: Ticker symbol or dataset identifier.
            data_source: Human-readable origin of data.
            is_synthetic: Explicit synthetic data flag. Inferred from df.attrs if None.
            author: Report author name.
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"Expected pandas DataFrame, got {type(df).__name__}.")
        if df.empty:
            raise EmptyDataError("Cannot generate PDF report from an empty DataFrame.")
        if "Close" not in df.columns:
            raise MissingColumnError("DataFrame lacks required 'Close' price column.")

        # Ensure input immutability
        self.df = df.copy(deep=True)
        self.ticker = (ticker or "STOCK").upper()
        self.data_source = data_source or "Unknown"
        self.author = author

        # Detect synthetic data
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

        # Initialize analytical modules
        self._chart_gen = StaticChartGenerator(self.df, ticker=self.ticker)
        self._insight_analyzer = StockInsightAnalyzer(self.df, ticker=self.ticker)
        self._summary: InsightSummary = self._insight_analyzer.generate_summary()

        # Build custom typography styles
        self._init_styles()

    def _init_styles(self) -> None:
        """Initialize custom ReportLab typography styles."""
        self.styles = getSampleStyleSheet()

        # Primary Colors
        self.c_primary = colors.HexColor("#1E3A8A")  # Deep Blue
        self.c_secondary = colors.HexColor("#0F766E")  # Teal
        self.c_text = colors.HexColor("#1F2937")  # Slate 800
        self.c_muted = colors.HexColor("#6B7280")  # Slate 500
        self.c_bg_light = colors.HexColor("#F9FAFB")  # Slate 50
        self.c_border = colors.HexColor("#E5E7EB")  # Slate 200

        self.styles.add(
            ParagraphStyle(
                "CoverTitle",
                fontName="Helvetica-Bold",
                fontSize=26,
                leading=32,
                textColor=self.c_primary,
                spaceAfter=6,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "CoverSubtitle",
                fontName="Helvetica",
                fontSize=13,
                leading=17,
                textColor=self.c_muted,
                spaceAfter=20,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "ReportHeading1",
                fontName="Helvetica-Bold",
                fontSize=15,
                leading=19,
                textColor=self.c_primary,
                spaceBefore=14,
                spaceAfter=8,
                keepWithNext=True,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "ReportHeading2",
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=15,
                textColor=self.c_secondary,
                spaceBefore=10,
                spaceAfter=6,
                keepWithNext=True,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "ReportBody",
                fontName="Helvetica",
                fontSize=9,
                leading=13,
                textColor=self.c_text,
                spaceAfter=6,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "ReportCaption",
                fontName="Helvetica-Oblique",
                fontSize=8,
                leading=11,
                textColor=self.c_muted,
                spaceAfter=6,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "TableHeader",
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=11,
                textColor=colors.white,
                alignment=1,  # Center
            )
        )
        self.styles.add(
            ParagraphStyle(
                "TableCell",
                fontName="Helvetica",
                fontSize=8.5,
                leading=11,
                textColor=self.c_text,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "TableCellBold",
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=11,
                textColor=self.c_text,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "WarningBoxText",
                fontName="Helvetica-Bold",
                fontSize=9,
                leading=13,
                textColor=colors.HexColor("#92400E"),
            )
        )

    def _figure_to_image(self, fig: plt.Figure, width: float = 500, height: float = 230) -> Image:
        """Render Matplotlib Figure to in-memory PNG buffer and return ReportLab Image flowable."""
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return Image(buf, width=width, height=height)

    def generate(self, output_path: Optional[Union[str, Path]] = None) -> Union[str, bytes]:
        """Generate the complete multi-page PDF report.

        Args:
            output_path: Destination path for the PDF file. If None, returns PDF bytes.

        Returns:
            File path string if output_path is provided, or raw PDF bytes.
        """
        pdf_buffer = io.BytesIO()
        target: Any = str(output_path) if output_path is not None else pdf_buffer
        doc = SimpleDocTemplate(
            target,
            pagesize=letter,
            leftMargin=40,
            rightMargin=40,
            topMargin=50,
            bottomMargin=50,
        )

        story: List[Any] = []

        # 1. Cover Page
        self._build_cover_page(story)
        story.append(PageBreak())

        # 2. Executive Summary
        self._build_executive_summary_section(story)
        story.append(Spacer(1, 10))

        # 3. Dataset Profile
        self._build_dataset_profile_section(story)
        story.append(PageBreak())

        # 4. Price & Technical Analysis
        self._build_technical_analysis_section(story)
        story.append(PageBreak())

        # 5. Returns Analysis
        self._build_returns_section(story)
        story.append(PageBreak())

        # 6. Risk & Volatility Analysis
        self._build_risk_section(story)
        story.append(PageBreak())

        # 7. Trading Volume & Turnover Analysis
        self._build_volume_section(story)
        story.append(Spacer(1, 15))

        # 8. Structured Insights & Interpretation
        self._build_insights_section(story)
        story.append(PageBreak())

        # 9. Methodology & Regulatory Disclaimers
        self._build_disclaimers_section(story)

        # Set canvas running header attribute
        def make_canvas(*args: Any, **kwargs: Any) -> NumberedCanvas:
            c = NumberedCanvas(*args, **kwargs)
            setattr(
                c,
                "report_header_title",
                f"Stock Market Data Analyzer | Akash Das — {self.ticker} Quantitative Report",
            )
            return c

        doc.build(story, canvasmaker=make_canvas)

        if output_path is not None:
            return str(output_path)

        return pdf_buffer.getvalue()

    # =========================================================================
    # Section Builders
    # =========================================================================

    def _build_cover_page(self, story: List[Any]) -> None:
        """Construct cover page flowables."""
        story.append(Spacer(1, 40))
        story.append(Paragraph("Stock Market Data Analyzer", self.styles["CoverTitle"]))
        story.append(
            Paragraph(
                "Comprehensive Quantitative Analysis & Market Intelligence Report",
                self.styles["CoverSubtitle"],
            )
        )
        story.append(HRFlowable(width="100%", thickness=2, color=self.c_primary, spaceAfter=25))

        # Metadata Card Table
        n_obs = len(self.df)
        first_date = str(self.df["Date"].iloc[0]) if "Date" in self.df.columns else "N/A"
        latest_date = str(self.df["Date"].iloc[-1]) if "Date" in self.df.columns else "N/A"
        gen_timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        meta_data = [
            [
                Paragraph("<b>Ticker / Asset:</b>", self.styles["TableCellBold"]),
                Paragraph(self.ticker, self.styles["TableCell"]),
                Paragraph("<b>Author / Analyst:</b>", self.styles["TableCellBold"]),
                Paragraph(self.author, self.styles["TableCell"]),
            ],
            [
                Paragraph("<b>Data Ingestion Source:</b>", self.styles["TableCellBold"]),
                Paragraph(self.data_source, self.styles["TableCell"]),
                Paragraph("<b>Generated Timestamp:</b>", self.styles["TableCellBold"]),
                Paragraph(gen_timestamp, self.styles["TableCell"]),
            ],
            [
                Paragraph("<b>Analysis Date Range:</b>", self.styles["TableCellBold"]),
                Paragraph(f"{first_date} to {latest_date}", self.styles["TableCell"]),
                Paragraph("<b>Total Observations:</b>", self.styles["TableCellBold"]),
                Paragraph(f"{n_obs:,} trading sessions", self.styles["TableCell"]),
            ],
        ]

        t_meta = Table(meta_data, colWidths=[120, 146, 120, 146])
        t_meta.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), self.c_bg_light),
                    ("BOX", (0, 0), (-1, -1), 1, self.c_border),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, self.c_border),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(t_meta)
        story.append(Spacer(1, 30))

        # Prominent Amber Warning Banner if Synthetic
        if self.is_synthetic:
            warning_data = [
                [
                    Paragraph(
                        "⚠️ <b>SYNTHETIC SAMPLE DATA ACTIVE</b><br/>"
                        "This report was generated using an offline synthetic dataset fixture (data/sample/sample_stock.csv). "
                        "All metrics, price indicators, returns, and risk calculations reflect synthetic test prices and "
                        "must not be interpreted as actual real-world market data.",
                        self.styles["WarningBoxText"],
                    )
                ]
            ]
            t_warn = Table(warning_data, colWidths=[532])
            t_warn.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
                        ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#F59E0B")),
                        ("TOPPADDING", (0, 0), (-1, -1), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                        ("LEFTPADDING", (0, 0), (-1, -1), 14),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                    ]
                )
            )
            story.append(t_warn)
            story.append(Spacer(1, 30))

        # Executive Note
        story.append(
            Paragraph(
                "<b>Notice of Research Scope:</b> This document provides automated, deterministic quantitative analysis "
                "synthesized from historical daily price and volume records. It contains backward-looking performance metrics, "
                "mathematical indicators, and statistical risk measures. It does not provide predictive price targets or investment recommendations.",
                self.styles["ReportCaption"],
            )
        )

    def _build_executive_summary_section(self, story: List[Any]) -> None:
        """Construct Executive Summary section flowables."""
        story.append(Paragraph("1. Executive Summary", self.styles["ReportHeading1"]))
        story.append(
            Paragraph(
                "Key empirical observations categorized into positive performance signals, cautionary risk factors, "
                "and statistical limitations extracted directly from underlying quantitative models.",
                self.styles["ReportBody"],
            )
        )

        # 4 Quadrants Summary
        col_w = 260
        pos_text = "<br/>".join(f"• {p}" for p in self._summary.positive_observations) or "• No distinctly positive signals identified."
        neg_text = "<br/>".join(f"• {n}" for n in self._summary.negative_observations) or "• No distinctly negative signals identified."
        risk_text = "<br/>".join(f"• {r}" for r in self._summary.risk_observations) or "• No elevated risk flags triggered."
        lim_text = "<br/>".join(f"• {l}" for l in self._summary.data_limitations) or "• Standard statistical limitations apply."

        quad_data = [
            [
                Paragraph("<b>🟢 Key Positive Observations</b>", self.styles["ReportHeading2"]),
                Paragraph("<b>🔴 Key Cautionary / Negative Signals</b>", self.styles["ReportHeading2"]),
            ],
            [
                Paragraph(pos_text, self.styles["TableCell"]),
                Paragraph(neg_text, self.styles["TableCell"]),
            ],
            [
                Paragraph("<b>⚠️ Risk & Volatility Observations</b>", self.styles["ReportHeading2"]),
                Paragraph("<b>ℹ️ Data Limitations & Disclaimers</b>", self.styles["ReportHeading2"]),
            ],
            [
                Paragraph(risk_text, self.styles["TableCell"]),
                Paragraph(lim_text, self.styles["TableCell"]),
            ],
        ]

        t_quad = Table(quad_data, colWidths=[col_w, col_w])
        t_quad.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0FDF4")),
                    ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#FEF2F2")),
                    ("BACKGROUND", (0, 2), (0, 3), colors.HexColor("#FFFBEB")),
                    ("BACKGROUND", (1, 2), (1, 3), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 1, self.c_border),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, self.c_border),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(t_quad)

    def _build_dataset_profile_section(self, story: List[Any]) -> None:
        """Construct Dataset Profile section flowables."""
        story.append(Paragraph("2. Dataset & Ingestion Profile", self.styles["ReportHeading1"]))
        story.append(
            Paragraph(
                "Comprehensive profile of ingested price records, temporal boundaries, dataset provenance, "
                "structural validity checks, and data limitations.",
                self.styles["ReportBody"],
            )
        )

        n_obs = len(self.df)
        first_close = float(self.df["Close"].iloc[0])
        latest_close = float(self.df["Close"].iloc[-1])
        min_close = float(self.df["Close"].min())
        max_close = float(self.df["Close"].max())

        # Determine temporal boundary dates
        if "Date" in self.df.columns and len(self.df) > 0:
            start_date = str(self.df["Date"].iloc[0])[:10]
            end_date = str(self.df["Date"].iloc[-1])[:10]
        elif hasattr(self.df.index, "__getitem__") and len(self.df) > 0:
            start_date = str(self.df.index[0])[:10]
            end_date = str(self.df.index[-1])[:10]
        else:
            start_date = "N/A"
            end_date = "N/A"

        synthetic_status = "YES (Synthetic Test Data)" if self.is_synthetic else "NO (Live Market Data)"

        table_data = [
            [
                Paragraph("<b>Parameter</b>", self.styles["TableHeader"]),
                Paragraph("<b>Value</b>", self.styles["TableHeader"]),
                Paragraph("<b>Parameter</b>", self.styles["TableHeader"]),
                Paragraph("<b>Value</b>", self.styles["TableHeader"]),
            ],
            [
                Paragraph("Ticker Identifier", self.styles["TableCellBold"]),
                Paragraph(self.ticker, self.styles["TableCell"]),
                Paragraph("Data Source", self.styles["TableCellBold"]),
                Paragraph(self.data_source, self.styles["TableCell"]),
            ],
            [
                Paragraph("Temporal Start Date", self.styles["TableCellBold"]),
                Paragraph(start_date, self.styles["TableCell"]),
                Paragraph("Temporal End Date", self.styles["TableCellBold"]),
                Paragraph(end_date, self.styles["TableCell"]),
            ],
            [
                Paragraph("Observation Count", self.styles["TableCellBold"]),
                Paragraph(f"{n_obs:,} sessions", self.styles["TableCell"]),
                Paragraph("Synthetic Dataset", self.styles["TableCellBold"]),
                Paragraph(synthetic_status, self.styles["TableCell"]),
            ],
            [
                Paragraph("Initial Close Price", self.styles["TableCellBold"]),
                Paragraph(f"${first_close:,.2f}", self.styles["TableCell"]),
                Paragraph("Latest Close Price", self.styles["TableCellBold"]),
                Paragraph(f"${latest_close:,.2f}", self.styles["TableCell"]),
            ],
            [
                Paragraph("Period Low (Close)", self.styles["TableCellBold"]),
                Paragraph(f"${min_close:,.2f}", self.styles["TableCell"]),
                Paragraph("Period High (Close)", self.styles["TableCellBold"]),
                Paragraph(f"${max_close:,.2f}", self.styles["TableCell"]),
            ],
        ]

        t_prof = Table(table_data, colWidths=[120, 146, 120, 146])
        t_prof.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), self.c_primary),
                    ("BOX", (0, 0), (-1, -1), 1, self.c_border),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, self.c_border),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.c_bg_light]),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(t_prof)

        # Ingestion Quality & Dataset Limitations
        if self.is_synthetic:
            quality_desc = "Synthetic price history generated exclusively for offline testing, architectural verification, and algorithm benchmarking."
            sufficiency_note = "Sample series depth is designated for pipeline validation without external internet dependencies."
        else:
            quality_desc = "Standard OHLCV data validation completed: chronological sorting, price coherence (High >= Low, High >= Open/Close, Low <= Open/Close), positive volume, zero null values."
            sufficiency_note = (
                f"Historical window contains {n_obs} sessions, offering sufficient observation depth for 20-day, 50-day moving averages and 21/63-session rolling volatility."
                if n_obs >= 63
                else f"Historical window contains {n_obs} sessions; metrics requiring longer windows (SMA 50, 63-day rolling volatility) will exhibit initial warm-up NaNs."
            )

        notes_data = [
            [
                Paragraph(
                    f"<b>Data Ingestion Profile & Methodological Boundaries:</b><br/>"
                    f"• <b>Dataset Quality:</b> {quality_desc}<br/>"
                    f"• <b>Observation Sufficiency:</b> {sufficiency_note}<br/>"
                    f"• <b>Volume Attribution Limitation:</b> Volume reflects aggregate exchange transactions and cannot identify participant categories without tick-level order book records.",
                    self.styles["TableCell"],
                )
            ]
        ]
        t_notes = Table(notes_data, colWidths=[532])
        t_notes.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), self.c_bg_light),
                    ("BOX", (0, 0), (-1, -1), 1, self.c_border),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(Spacer(1, 8))
        story.append(t_notes)

        if self.is_synthetic:
            synth_box_data = [
                [
                    Paragraph(
                        "<b>⚠️ SYNTHETIC DATASET IDENTIFICATION:</b> This report analyzes synthetic stock observations. "
                        "All moving averages, realized volatilities, returns, and drawdowns are calculated from synthetic data and must not be treated as real-world market executions.",
                        self.styles["WarningBoxText"],
                    )
                ]
            ]
            t_synth = Table(synth_box_data, colWidths=[532])
            t_synth.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
                        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#F59E0B")),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(Spacer(1, 6))
            story.append(t_synth)

    def _build_technical_analysis_section(self, story: List[Any]) -> None:
        """Construct Price & Technical Analysis section flowables."""
        story.append(Paragraph("3. Price & Technical Analysis", self.styles["ReportHeading1"]))
        story.append(
            Paragraph(
                "Historical closing prices evaluated against key trend-smoothing moving averages: "
                "20-day Simple Moving Average (SMA 20), 50-day Simple Moving Average (SMA 50), and 20-day Exponential Moving Average (EMA 20).",
                self.styles["ReportBody"],
            )
        )

        try:
            fig = self._chart_gen.plot_moving_averages()
            story.append(self._figure_to_image(fig, width=520, height=240))
        except Exception as e:
            story.append(
                Paragraph(f"<i>Technical chart unavailable: {e}</i>", self.styles["ReportCaption"])
            )

    def _build_returns_section(self, story: List[Any]) -> None:
        """Construct Financial Returns Analysis section flowables."""
        story.append(Paragraph("4. Financial Returns Analysis", self.styles["ReportHeading1"]))
        story.append(
            Paragraph(
                "Analysis of daily percentage returns, compounded cumulative growth (wealth index), "
                "and return distribution asymmetry.",
                self.styles["ReportBody"],
            )
        )

        try:
            ra = ReturnAnalyzer(self.df)
            daily_ret = ra.calculate_daily_returns().dropna()
            cum_ret = ra.calculate_cumulative_returns().iloc[-1] if len(self.df) > 1 else 0.0

            n_pos = int((daily_ret > 0).sum())
            n_neg = int((daily_ret < 0).sum())
            win_rate = (n_pos / len(daily_ret)) * 100 if len(daily_ret) > 0 else 0.0
            max_gain = float(daily_ret.max()) * 100 if len(daily_ret) > 0 else 0.0
            max_loss = float(daily_ret.min()) * 100 if len(daily_ret) > 0 else 0.0

            ret_table_data = [
                [
                    Paragraph("<b>Metric</b>", self.styles["TableHeader"]),
                    Paragraph("<b>Value</b>", self.styles["TableHeader"]),
                    Paragraph("<b>Metric</b>", self.styles["TableHeader"]),
                    Paragraph("<b>Value</b>", self.styles["TableHeader"]),
                ],
                [
                    Paragraph("Cumulative Compound Return", self.styles["TableCellBold"]),
                    Paragraph(f"{cum_ret * 100:+.2f}%", self.styles["TableCell"]),
                    Paragraph("Daily Win Rate (Up Days)", self.styles["TableCellBold"]),
                    Paragraph(f"{win_rate:.1f}% ({n_pos} up / {n_neg} down)", self.styles["TableCell"]),
                ],
                [
                    Paragraph("Best Single-Day Return", self.styles["TableCellBold"]),
                    Paragraph(f"{max_gain:+.2f}%", self.styles["TableCell"]),
                    Paragraph("Worst Single-Day Return", self.styles["TableCellBold"]),
                    Paragraph(f"{max_loss:+.2f}%", self.styles["TableCell"]),
                ],
            ]

            t_ret = Table(ret_table_data, colWidths=[130, 136, 130, 136])
            t_ret.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), self.c_secondary),
                        ("BOX", (0, 0), (-1, -1), 1, self.c_border),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, self.c_border),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.c_bg_light]),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(t_ret)
            story.append(Spacer(1, 10))

            fig_ret = self._chart_gen.plot_cumulative_returns()
            story.append(self._figure_to_image(fig_ret, width=520, height=210))
        except Exception as e:
            story.append(Paragraph(f"<i>Returns analysis unavailable: {e}</i>", self.styles["ReportCaption"]))

    def _build_risk_section(self, story: List[Any]) -> None:
        """Construct Risk and Volatility Analysis section flowables."""
        story.append(Paragraph("5. Risk & Volatility Analysis", self.styles["ReportHeading1"]))
        story.append(
            Paragraph(
                "Risk evaluation comprising daily standard deviation, annualized volatility (scaled to 252 trading sessions), "
                "multi-window rolling volatility (21d, 63d), and historical peak-to-trough underwater drawdown.",
                self.styles["ReportBody"],
            )
        )

        try:
            rka = RiskAnalyzer(self.df)
            daily_vol = rka.calculate_daily_volatility()
            ann_vol = rka.calculate_annualized_volatility()
            mdd_info = rka.calculate_max_drawdown()
            trough_date_str = mdd_info.get("trough_date", mdd_info.get("valley_date", "N/A"))

            risk_table_data = [
                [
                    Paragraph("<b>Risk Metric</b>", self.styles["TableHeader"]),
                    Paragraph("<b>Value</b>", self.styles["TableHeader"]),
                    Paragraph("<b>Risk Metric</b>", self.styles["TableHeader"]),
                    Paragraph("<b>Value</b>", self.styles["TableHeader"]),
                ],
                [
                    Paragraph("Daily Volatility (std dev)", self.styles["TableCellBold"]),
                    Paragraph(f"{daily_vol * 100:.2f}%", self.styles["TableCell"]),
                    Paragraph("Annualized Volatility (252d)", self.styles["TableCellBold"]),
                    Paragraph(f"{ann_vol * 100:.2f}%", self.styles["TableCell"]),
                ],
                [
                    Paragraph("Maximum Drawdown (MDD)", self.styles["TableCellBold"]),
                    Paragraph(f"{mdd_info['max_drawdown'] * 100:.2f}%", self.styles["TableCell"]),
                    Paragraph("MDD Peak / Trough Dates", self.styles["TableCellBold"]),
                    Paragraph(f"{mdd_info['peak_date']} → {trough_date_str}", self.styles["TableCell"]),
                ],
            ]

            t_risk = Table(risk_table_data, colWidths=[130, 136, 130, 136])
            t_risk.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7C2D12")),
                        ("BOX", (0, 0), (-1, -1), 1, self.c_border),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, self.c_border),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.c_bg_light]),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(t_risk)
            story.append(Spacer(1, 10))

            fig_dd = self._chart_gen.plot_drawdown()
            story.append(self._figure_to_image(fig_dd, width=520, height=200))
        except Exception as e:
            story.append(Paragraph(f"<i>Risk analysis unavailable: {e}</i>", self.styles["ReportCaption"]))

    def _build_volume_section(self, story: List[Any]) -> None:
        """Construct Trading Volume Analysis section flowables."""
        story.append(Paragraph("6. Trading Volume & Turnover Analysis", self.styles["ReportHeading1"]))
        story.append(
            Paragraph(
                "Evaluation of daily share turnover against the trailing 20-day moving average baseline. "
                "Adheres strictly to empirical volume turnover observation without unsupported participant attribution.",
                self.styles["ReportBody"],
            )
        )

        try:
            if "Volume" in self.df.columns and len(self.df) >= 5:
                vol_series = pd.to_numeric(self.df["Volume"], errors="coerce").dropna()
                latest_vol = float(vol_series.iloc[-1])
                window = min(20, len(vol_series))
                baseline_vol = float(vol_series.iloc[-window:].mean())
                vol_ratio = latest_vol / baseline_vol if baseline_vol > 0 else 1.0

                vol_table_data = [
                    [
                        Paragraph("<b>Volume Metric</b>", self.styles["TableHeader"]),
                        Paragraph("<b>Value</b>", self.styles["TableHeader"]),
                        Paragraph("<b>Volume Metric</b>", self.styles["TableHeader"]),
                        Paragraph("<b>Value</b>", self.styles["TableHeader"]),
                    ],
                    [
                        Paragraph("Latest Session Volume", self.styles["TableCellBold"]),
                        Paragraph(f"{latest_vol:,.0f} shares", self.styles["TableCell"]),
                        Paragraph(f"Trailing {window}-Day Baseline", self.styles["TableCellBold"]),
                        Paragraph(f"{baseline_vol:,.0f} shares", self.styles["TableCell"]),
                    ],
                    [
                        Paragraph("Volume Ratio vs Baseline", self.styles["TableCellBold"]),
                        Paragraph(f"{vol_ratio:.2f}x", self.styles["TableCell"]),
                        Paragraph("Activity Classification", self.styles["TableCellBold"]),
                        Paragraph(
                            "Elevated Trading Volume" if vol_ratio >= 1.5 else ("Reduced Trading Volume" if vol_ratio <= 0.5 else "Typical Trading Volume"),
                            self.styles["TableCell"],
                        ),
                    ],
                ]

                t_vol = Table(vol_table_data, colWidths=[130, 136, 130, 136])
                t_vol.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), self.c_secondary),
                            ("BOX", (0, 0), (-1, -1), 1, self.c_border),
                            ("INNERGRID", (0, 0), (-1, -1), 0.5, self.c_border),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.c_bg_light]),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                            ("LEFTPADDING", (0, 0), (-1, -1), 8),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ]
                    )
                )
                story.append(t_vol)
                story.append(Spacer(1, 10))

                fig_vol = self._chart_gen.plot_trading_volume()
                story.append(self._figure_to_image(fig_vol, width=520, height=190))
        except Exception as e:
            story.append(Paragraph(f"<i>Volume analysis unavailable: {e}</i>", self.styles["ReportCaption"]))

    def _build_insights_section(self, story: List[Any]) -> None:
        """Construct Structured Insights & Interpretation section flowables."""
        story.append(Paragraph("7. Structured Insights & Interpretation", self.styles["ReportHeading1"]))
        story.append(
            Paragraph(
                "Deterministic qualitative findings synthesized across technical momentum, returns distribution, "
                "risk regimes, volume turnover, and single-asset price-volume correlations.",
                self.styles["ReportBody"],
            )
        )

        insights = self._summary.insights
        for ins in insights:
            sev_color = "#059669" if ins.severity.value == "positive" else ("#DC2626" if ins.severity.value == "negative" else ("#D97706" if ins.severity.value == "warning" else "#2563EB"))
            cat_name = ins.category.value if hasattr(ins.category, "value") else str(ins.category)

            item_data = [
                [
                    Paragraph(f"<b>{cat_name.upper()}: {ins.title}</b>", ParagraphStyle("InsTitle", parent=self.styles["TableCellBold"], textColor=colors.HexColor(sev_color))),
                ],
                [
                    Paragraph(ins.observation, self.styles["ReportBody"]),
                ],
            ]

            if ins.evidence:
                ev_str = " | ".join(f"<b>{k}</b>: {v}" for k, v in ins.evidence.items())
                item_data.append([Paragraph(f"<i>Supporting Evidence:</i> {ev_str}", self.styles["ReportCaption"])])

            if ins.limitations:
                item_data.append([Paragraph(f"<b>Limitation:</b> {ins.limitations}", ParagraphStyle("InsLim", parent=self.styles["ReportCaption"], textColor=colors.HexColor("#78350F")))])

            t_ins = Table(item_data, colWidths=[532])
            t_ins.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), self.c_bg_light),
                        ("BOX", (0, 0), (-1, -1), 0.75, self.c_border),
                        ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor(sev_color)),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(KeepTogether([t_ins, Spacer(1, 6)]))

    def _build_disclaimers_section(self, story: List[Any]) -> None:
        """Construct Methodology & Regulatory Disclaimers section flowables."""
        story.append(Paragraph("8. Methodology & Regulatory Disclaimers", self.styles["ReportHeading1"]))

        disclaimer_text = (
            "<b>1. Historical and Descriptive Scope:</b> All computations and qualitative interpretations in this report "
            "are strictly historical, mathematical, and descriptive. Past price trajectory, moving average positioning, "
            "and realized volatility do not guarantee or predict future performance, returns, or downside risk.<br/><br/>"
            "<b>2. Mathematical Conventions:</b> Annualized volatility is scaled using the square root of 252 trading sessions. "
            "Sample standard deviation uses Bessel's correction (ddof=1). Cumulative returns represent geometric compounded growth "
            "rather than simple arithmetic sums.<br/><br/>"
            "<b>3. Correlation Limitations:</b> Empirical correlation is evaluated between raw closing prices ('Close') and "
            "trading volume ('Volume') within this single asset's historical series. Raw price levels frequently exhibit non-stationary "
            "trends, meaning observed correlations may reflect common temporal trends rather than causal economic relationships. "
            "Correlation does not establish causation, cannot infer buyer-initiated or seller-initiated pressure, and does not evaluate "
            "cross-stock diversification.<br/><br/>"
            "<b>4. Volume Interpretation:</b> Exchange volume measures total share turnover and does not categorize market participants "
            "(such as institutional vs retail investors). Without tick-level order book data, volume cannot distinguish between "
            "aggressive buying and aggressive selling.<br/><br/>"
            "<b>5. Regulatory Notice:</b> This automated document is generated for research, educational, and quantitative exploration "
            "purposes only. It does not constitute investment advice, financial planning, a solicitation, or an endorsement to buy or "
            "sell any security."
        )

        t_disc = Table([[Paragraph(disclaimer_text, self.styles["ReportBody"])]], colWidths=[532])
        t_disc.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), self.c_bg_light),
                    ("BOX", (0, 0), (-1, -1), 1, self.c_border),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )
        story.append(t_disc)
