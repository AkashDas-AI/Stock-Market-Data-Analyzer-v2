"""HTML report generation module using Plotly interactive charts.

Generates structured, responsive, interactive standalone HTML research reports
with modern financial typography, Plotly chart integration, executive summaries,
risk metrics, Phase 10 structured insights, and regulatory disclaimers.
"""

from __future__ import annotations

import datetime as dt
import html
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import plotly.offline as pyo

from stock_analyzer.analysis.indicators import TechnicalIndicators
from stock_analyzer.analysis.insights import InsightSummary, MarketInsight, StockInsightAnalyzer
from stock_analyzer.analysis.returns import ReturnAnalyzer
from stock_analyzer.analysis.risk import RiskAnalyzer
from stock_analyzer.data.exceptions import EmptyDataError, MissingColumnError
from stock_analyzer.visualization.interactive_charts import InteractiveChartGenerator


class HTMLReportGenerator:
    """Orchestrates comprehensive interactive HTML research report generation."""

    def __init__(
        self,
        df: pd.DataFrame,
        ticker: Optional[str] = "STOCK",
        data_source: Optional[str] = "Unknown",
        is_synthetic: Optional[bool] = None,
        author: str = "Akash Das",
    ) -> None:
        """Initialize HTML report generator with stock DataFrame and metadata.

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
            raise EmptyDataError("Cannot generate HTML report from an empty DataFrame.")
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

        # Initialize chart generator and insight analyzer
        self._chart_gen = InteractiveChartGenerator(self.df, ticker=self.ticker)
        self._insight_analyzer = StockInsightAnalyzer(self.df, ticker=self.ticker)
        self._summary: InsightSummary = self._insight_analyzer.generate_summary()

    def generate(
        self,
        output_path: Optional[Union[str, Path]] = None,
        embed_plotly_js: bool = False,
    ) -> Union[str, bytes]:
        """Generate comprehensive interactive HTML report.

        Args:
            output_path: Optional destination file path. If None, returns UTF-8 encoded bytes.
            embed_plotly_js: If True, bundles full Plotly JS offline (~4.8MB). If False, uses official CDN (~150KB).

        Returns:
            File path string if output_path is provided, or HTML bytes.
        """
        html_content = self._render_full_html(embed_plotly_js=embed_plotly_js)

        if output_path is not None:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(html_content, encoding="utf-8")
            return str(p)

        return html_content.encode("utf-8")

    def _render_full_html(self, embed_plotly_js: bool) -> str:
        """Compose all HTML sections into a complete, standalone document."""
        # Sanitize metadata for HTML
        safe_ticker = html.escape(self.ticker)
        safe_author = html.escape(self.author)
        safe_source = html.escape(self.data_source)
        gen_timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        first_date = str(self.df["Date"].iloc[0]) if "Date" in self.df.columns else "N/A"
        latest_date = str(self.df["Date"].iloc[-1]) if "Date" in self.df.columns else "N/A"
        n_obs = len(self.df)

        # Plotly script inclusion
        if embed_plotly_js:
            plotly_script_tag = f"<script type='text/javascript'>\n{pyo.get_plotlyjs()}\n</script>"
            cdn_badge = (
                '<span class="badge badge-offline">📦 Fully Offline (Embedded Plotly JS)</span>'
            )
            mode_comment = "<!-- Plotly Mode: Embedded Full Offline (100% self-contained) -->"
        else:
            plotly_script_tag = '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>'
            cdn_badge = (
                '<span class="badge badge-cdn">🌐 External CDN (Requires Internet for Charts)</span>'
            )
            mode_comment = "<!-- Plotly Mode: External CDN (requires internet to load charts) -->"

        # KPI Metrics
        latest_close = float(self.df["Close"].iloc[-1])
        first_close = float(self.df["Close"].iloc[0])
        cum_ret = ((latest_close / first_close) - 1.0) if first_close > 0 else 0.0

        rka = RiskAnalyzer(self.df)
        ann_vol = rka.calculate_annualized_volatility()
        mdd_info = rka.calculate_max_drawdown()

        # Render Charts to HTML Divs
        chart_candlestick = self._safe_chart_to_html(self._chart_gen.create_candlestick_chart)
        chart_ma = self._safe_chart_to_html(self._chart_gen.create_moving_averages_chart)
        chart_cum_ret = self._safe_chart_to_html(self._chart_gen.create_cumulative_returns_chart)
        chart_ret_dist = self._safe_chart_to_html(self._chart_gen.create_daily_returns_distribution_chart)
        chart_drawdown = self._safe_chart_to_html(self._chart_gen.create_drawdown_chart)
        chart_volatility = self._safe_chart_to_html(self._chart_gen.create_rolling_volatility_chart)
        chart_volume = self._safe_chart_to_html(self._chart_gen.create_volume_chart)
        chart_corr = self._safe_chart_to_html(self._chart_gen.create_correlation_heatmap)

        # Build Sections
        synthetic_banner = self._render_synthetic_banner() if self.is_synthetic else ""
        exec_summary_html = self._render_executive_summary()
        insights_html = self._render_insights_section()

        css_styles = self._get_css_styles()

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantitative Stock Analysis Report — {safe_ticker}</title>
    {mode_comment}
    {plotly_script_tag}
    <style>
        {css_styles}
    </style>
</head>
<body>
    <div class="nav-bar">
        <div class="nav-container">
            <span class="nav-brand">📈 Stock Market Data Analyzer</span>
            <div class="nav-links">
                <a href="#summary">Executive Summary</a>
                <a href="#technical">Technical</a>
                <a href="#returns">Returns</a>
                <a href="#risk">Risk</a>
                <a href="#volume">Volume</a>
                <a href="#correlation">Correlation</a>
                <a href="#insights">Insights</a>
                <a href="#disclaimers">Disclaimers</a>
            </div>
            {cdn_badge}
        </div>
    </div>

    <div class="container">
        <!-- Header -->
        <header class="report-header">
            <div class="header-content">
                <h1 class="report-title">Quantitative Financial Analysis Report</h1>
                <p class="report-subtitle">Comprehensive Market Intelligence & Empirical Statistical Evaluation</p>
                <div class="meta-grid">
                    <div class="meta-item"><span class="meta-label">Ticker Symbol</span><span class="meta-value">{safe_ticker}</span></div>
                    <div class="meta-item"><span class="meta-label">Author / Analyst</span><span class="meta-value">{safe_author}</span></div>
                    <div class="meta-item"><span class="meta-label">Analysis Period</span><span class="meta-value">{first_date} to {latest_date}</span></div>
                    <div class="meta-item"><span class="meta-label">Observation Count</span><span class="meta-value">{n_obs:,} Sessions</span></div>
                    <div class="meta-item"><span class="meta-label">Data Ingestion Source</span><span class="meta-value">{safe_source}</span></div>
                    <div class="meta-item"><span class="meta-label">Generated Timestamp</span><span class="meta-value">{gen_timestamp}</span></div>
                </div>
            </div>
        </header>

        {synthetic_banner}

        <!-- KPI Metric Cards -->
        <section class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">Latest Close Price</div>
                <div class="kpi-value">${latest_close:,.2f}</div>
                <div class="kpi-sub">Initial Close: ${first_close:,.2f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Cumulative Return</div>
                <div class="kpi-value {'val-pos' if cum_ret > 0 else 'val-neg'}">{cum_ret * 100:+.2f}%</div>
                <div class="kpi-sub">Geometric Compounded</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Annualized Volatility</div>
                <div class="kpi-value">{ann_vol * 100:.2f}%</div>
                <div class="kpi-sub">Scaled to 252 Sessions</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Maximum Drawdown</div>
                <div class="kpi-value val-neg">{mdd_info['max_drawdown'] * 100:.2f}%</div>
                <div class="kpi-sub">Peak: {mdd_info['peak_date']}</div>
            </div>
        </section>

        <!-- 1. Executive Summary -->
        <section id="summary" class="section-block">
            <h2 class="section-heading">1. Executive Summary</h2>
            <p class="section-desc">Key empirical observations categorized into positive performance signals, cautionary factors, and statistical limitations.</p>
            {exec_summary_html}
        </section>

        <!-- 2. Technical Analysis -->
        <section id="technical" class="section-block">
            <h2 class="section-heading">2. Price Action & Technical Moving Averages</h2>
            <p class="section-desc">Interactive candlestick OHLC price trajectory and moving average positioning (SMA 20, SMA 50, EMA 20).</p>
            <div class="chart-container">{chart_candlestick}</div>
            <div class="chart-container">{chart_ma}</div>
        </section>

        <!-- 3. Returns Analysis -->
        <section id="returns" class="section-block">
            <h2 class="section-heading">3. Financial Returns Analysis</h2>
            <p class="section-desc">Compounded cumulative growth wealth index and historical daily return distribution histogram with standard deviation markers.</p>
            <div class="chart-container">{chart_cum_ret}</div>
            <div class="chart-container">{chart_ret_dist}</div>
        </section>

        <!-- 4. Risk Analysis -->
        <section id="risk" class="section-block">
            <h2 class="section-heading">4. Risk & Volatility Analysis</h2>
            <p class="section-desc">Underwater drawdown profile and sliding window annualized volatility dynamics (21-day and 63-day regimes).</p>
            <div class="chart-container">{chart_drawdown}</div>
            <div class="chart-container">{chart_volatility}</div>
        </section>

        <!-- 5. Trading Volume Analysis -->
        <section id="volume" class="section-block">
            <h2 class="section-heading">5. Trading Volume & Turnover Analysis</h2>
            <p class="section-desc">Daily share turnover evaluated against the trailing 20-day moving average baseline without unsupported participant attribution.</p>
            <div class="chart-container">{chart_volume}</div>
        </section>

        <!-- 6. Feature Correlation Matrix -->
        <section id="correlation" class="section-block">
            <h2 class="section-heading">6. Numerical Feature Correlation Matrix</h2>
            <p class="section-desc">Pearson linear correlation matrix evaluating intra-dataset co-movement between raw price levels ('Close') and trading volume ('Volume').</p>
            <div class="callout callout-info">
                <strong>Methodology & Limitation Notice:</strong> Correlation is evaluated strictly within this single asset's historical observations 
                (not a cross-stock comparison). Raw price series are frequently non-stationary, meaning price-level correlation may reflect common temporal 
                trends rather than economic causation. Correlation does not imply causation, does not measure buying/selling pressure, and provides no lead-lag predictability.
            </div>
            <div class="chart-container">{chart_corr}</div>
        </section>

        <!-- 7. Structured Insights -->
        <section id="insights" class="section-block">
            <h2 class="section-heading">7. Structured Insights & Analytical Interpretation</h2>
            <p class="section-desc">Deterministic takeaways synthesized across momentum, returns, volatility, turnover, and numerical feature relationships.</p>
            {insights_html}
        </section>

        <!-- 8. Disclaimers -->
        <section id="disclaimers" class="section-block">
            <h2 class="section-heading">8. Methodology & Regulatory Disclaimers</h2>
            <div class="callout callout-disclaimer">
                <p><strong>1. Historical and Descriptive Scope:</strong> All analytical outputs in this report represent backward-looking historical calculations. Past price trajectories, moving average alignments, and realized volatilities do not predict or guarantee future performance, returns, or tail risks.</p>
                <p><strong>2. Mathematical Conventions:</strong> Annualized volatility is scaled using the square root of 252 trading sessions. Sample standard deviation applies Bessel's correction (ddof=1). Cumulative returns represent geometric compounded growth rather than simple arithmetic sums.</p>
                <p><strong>3. Non-Causation Boundaries:</strong> Feature correlation indicates contemporaneous linear association only and does not establish causation or order book direction.</p>
                <p><strong>4. Volume Attribution Boundaries:</strong> Exchange volume reflects total share turnover and does not categorize market participants (such as institutional vs retail) without tick-level order book data.</p>
                <p><strong>5. Regulatory Notice:</strong> This report is generated strictly for quantitative analysis, education, and research. It does NOT constitute financial advice, investment recommendations, or an endorsement to buy or sell securities.</p>
            </div>
        </section>

        <!-- Footer -->
        <footer class="report-footer">
            <p>Stock Market Data Analyzer | Author: Akash Das | Generated via Antigravity Quantitative Reporting Layer</p>
            <p class="footer-small">For Informational Purposes Only — Not for Commercial Redistribution</p>
        </footer>
    </div>
</body>
</html>"""

    def _safe_chart_to_html(self, chart_method: Any) -> str:
        """Execute interactive chart generator and convert Plotly Figure to HTML div string."""
        try:
            fig = chart_method()
            return fig.to_html(include_plotlyjs=False, full_html=False)
        except Exception as e:
            return f'<div class="chart-error">⚠️ Chart temporarily unavailable: {html.escape(str(e))}</div>'

    def _render_synthetic_banner(self) -> str:
        """Render prominent amber warning banner when analyzing synthetic sample data."""
        return """
        <div class="banner banner-warning">
            <div class="banner-icon">⚠️</div>
            <div class="banner-content">
                <strong>SYNTHETIC SAMPLE DATA ACTIVE:</strong> This report was generated using an offline synthetic 
                fixture (<code>data/sample/sample_stock.csv</code>). All prices, indicator levels, returns, and risk calculations 
                reflect synthetic observations for offline validation and must not be interpreted as real exchange data.
            </div>
        </div>
        """

    def _render_executive_summary(self) -> str:
        """Render 4-card responsive executive summary grid."""
        pos_list = "".join(f"<li>{html.escape(p)}</li>" for p in self._summary.positive_observations) or "<li>No distinctly positive signals identified.</li>"
        neg_list = "".join(f"<li>{html.escape(n)}</li>" for n in self._summary.negative_observations) or "<li>No distinctly negative signals identified.</li>"
        risk_list = "".join(f"<li>{html.escape(r)}</li>" for r in self._summary.risk_observations) or "<li>No elevated risk flags triggered.</li>"
        lim_list = "".join(f"<li>{html.escape(l)}</li>" for l in self._summary.data_limitations) or "<li>Standard statistical limitations apply.</li>"

        return f"""
        <div class="summary-grid">
            <div class="summary-card card-positive">
                <h3>🟢 Key Positive Observations</h3>
                <ul>{pos_list}</ul>
            </div>
            <div class="summary-card card-negative">
                <h3>🔴 Key Cautionary / Negative Signals</h3>
                <ul>{neg_list}</ul>
            </div>
            <div class="summary-card card-risk">
                <h3>⚠️ Risk & Volatility Observations</h3>
                <ul>{risk_list}</ul>
            </div>
            <div class="summary-card card-limitations">
                <h3>ℹ️ Data Limitations & Disclaimers</h3>
                <ul>{lim_list}</ul>
            </div>
        </div>
        """

    def _render_insights_section(self) -> str:
        """Render structured insight cards with severity color-coding and evidence badges."""
        cards: List[str] = []
        for ins in self._summary.insights:
            sev_class = f"sev-{ins.severity.value}"
            cat_name = html.escape(ins.category.value if hasattr(ins.category, "value") else str(ins.category))
            title = html.escape(ins.title)
            obs = html.escape(ins.observation)

            evidence_items = ""
            if ins.evidence:
                ev_spans = "".join(
                    f'<span class="ev-tag"><strong>{html.escape(k)}</strong>: {html.escape(str(v))}</span>'
                    for k, v in ins.evidence.items()
                )
                evidence_items = f'<div class="insight-evidence"><span class="ev-label">Supporting Evidence:</span> {ev_spans}</div>'

            lim_div = ""
            if ins.limitations:
                lim_div = f'<div class="insight-limitation"><strong>Limitation:</strong> {html.escape(ins.limitations)}</div>'

            card_html = f"""
            <div class="insight-card {sev_class}">
                <div class="insight-header">
                    <span class="insight-cat">{cat_name}</span>
                    <h4 class="insight-title">{title}</h4>
                    <span class="insight-badge {sev_class}">{ins.severity.value.upper()}</span>
                </div>
                <div class="insight-body">{obs}</div>
                {evidence_items}
                {lim_div}
            </div>
            """
            cards.append(card_html)

        return f'<div class="insights-container">{"".join(cards)}</div>'

    def _get_css_styles(self) -> str:
        """Return production-grade CSS styling for clean, responsive layout."""
        return """
        :root {
            --primary: #1E3A8A;
            --primary-light: #3B82F6;
            --secondary: #0F766E;
            --text-dark: #0F172A;
            --text-muted: #64748B;
            --bg-page: #F8FAFC;
            --bg-card: #FFFFFF;
            --border-color: #E2E8F0;
            --pos-color: #059669;
            --pos-bg: #F0FDF4;
            --neg-color: #DC2626;
            --neg-bg: #FEF2F2;
            --warn-color: #D97706;
            --warn-bg: #FFFBEB;
            --info-color: #2563EB;
            --info-bg: #EFF6FF;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-page);
            color: var(--text-dark);
            line-height: 1.5;
            padding-top: 56px;
        }
        .nav-bar {
            position: fixed; top: 0; left: 0; right: 0; height: 56px;
            background-color: #0F172A; color: #FFFFFF;
            z-index: 1000; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .nav-container {
            max-width: 1200px; margin: 0 auto; height: 100%;
            display: flex; align-items: center; justify-content: space-between; padding: 0 20px;
        }
        .nav-brand { font-weight: 700; font-size: 16px; color: #FFFFFF; }
        .nav-links a {
            color: #94A3B8; text-decoration: none; font-size: 13px; margin: 0 10px; font-weight: 500;
        }
        .nav-links a:hover { color: #FFFFFF; }
        .badge { padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 600; }
        .badge-cdn { background-color: #1E293B; color: #38BDF8; border: 1px solid #0284C7; }
        .badge-offline { background-color: #064E3B; color: #34D399; border: 1px solid #059669; }
        .container { max-width: 1200px; margin: 24px auto; padding: 0 20px 60px 20px; }
        
        .report-header {
            background-color: var(--bg-card); border-radius: 12px; padding: 32px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid var(--border-color); margin-bottom: 24px;
        }
        .report-title { font-size: 28px; font-weight: 800; color: var(--primary); margin-bottom: 6px; }
        .report-subtitle { font-size: 15px; color: var(--text-muted); margin-bottom: 24px; }
        .meta-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px; background-color: #F1F5F9; padding: 16px; border-radius: 8px;
        }
        .meta-item { display: flex; flex-direction: column; }
        .meta-label { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; }
        .meta-value { font-size: 14px; font-weight: 700; color: var(--text-dark); margin-top: 2px; }

        .banner {
            display: flex; align-items: center; padding: 14px 20px; border-radius: 8px; margin-bottom: 24px;
        }
        .banner-warning { background-color: var(--warn-bg); border: 1.5px solid var(--warn-color); color: #78350F; }
        .banner-icon { font-size: 24px; margin-right: 14px; }
        .banner-content { font-size: 13px; line-height: 1.5; }

        .kpi-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px; margin-bottom: 24px;
        }
        .kpi-card {
            background-color: var(--bg-card); padding: 20px; border-radius: 10px;
            border: 1px solid var(--border-color); box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }
        .kpi-title { font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; }
        .kpi-value { font-size: 26px; font-weight: 800; color: var(--text-dark); margin: 6px 0 2px 0; }
        .kpi-sub { font-size: 12px; color: var(--text-muted); }
        .val-pos { color: var(--pos-color) !important; }
        .val-neg { color: var(--neg-color) !important; }

        .section-block {
            background-color: var(--bg-card); border-radius: 12px; padding: 28px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid var(--border-color); margin-bottom: 28px;
        }
        .section-heading { font-size: 20px; font-weight: 700; color: var(--primary); margin-bottom: 6px; }
        .section-desc { font-size: 14px; color: var(--text-muted); margin-bottom: 20px; }

        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
        .summary-card { padding: 18px; border-radius: 8px; border: 1px solid var(--border-color); }
        .summary-card h3 { font-size: 14px; font-weight: 700; margin-bottom: 12px; }
        .summary-card ul { padding-left: 20px; font-size: 13px; line-height: 1.6; }
        .card-positive { background-color: var(--pos-bg); border-color: #A7F3D0; }
        .card-negative { background-color: var(--neg-bg); border-color: #FECACA; }
        .card-risk { background-color: var(--warn-bg); border-color: #FDE68A; }
        .card-limitations { background-color: #F8FAFC; border-color: var(--border-color); }

        .chart-container { margin-bottom: 24px; min-height: 380px; }
        .chart-error {
            background-color: #FEF2F2; color: #991B1B; padding: 20px; border-radius: 8px;
            text-align: center; font-size: 14px; border: 1px solid #FCA5A5;
        }

        .callout { padding: 16px 20px; border-radius: 8px; margin-bottom: 20px; font-size: 13px; line-height: 1.6; }
        .callout-info { background-color: var(--info-bg); border-left: 4px solid var(--info-color); color: #1E40AF; }
        .callout-disclaimer { background-color: #F1F5F9; border-left: 4px solid #64748B; color: #334155; }
        .callout-disclaimer p { margin-bottom: 10px; }

        .insights-container { display: flex; flex-direction: column; gap: 14px; }
        .insight-card {
            background-color: #FFFFFF; border: 1px solid var(--border-color);
            border-left: 4px solid #CBD5E1; border-radius: 8px; padding: 18px;
        }
        .insight-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; flex-wrap: wrap; gap: 8px; }
        .insight-cat { font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; }
        .insight-title { font-size: 15px; font-weight: 700; color: var(--text-dark); flex: 1; margin: 0 12px; }
        .insight-badge { font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px; }
        .sev-positive { border-left-color: var(--pos-color) !important; }
        .sev-positive.insight-badge { background-color: var(--pos-bg); color: var(--pos-color); border: 1px solid #A7F3D0; }
        .sev-negative { border-left-color: var(--neg-color) !important; }
        .sev-negative.insight-badge { background-color: var(--neg-bg); color: var(--neg-color); border: 1px solid #FECACA; }
        .sev-warning { border-left-color: var(--warn-color) !important; }
        .sev-warning.insight-badge { background-color: var(--warn-bg); color: var(--warn-color); border: 1px solid #FDE68A; }
        .sev-info { border-left-color: var(--info-color) !important; }
        .sev-info.insight-badge { background-color: var(--info-bg); color: var(--info-color); border: 1px solid #BFDBFE; }
        .insight-body { font-size: 13.5px; color: #334155; margin-bottom: 12px; line-height: 1.6; }
        .insight-evidence {
            font-size: 12px; color: #475569; background-color: #F8FAFC;
            padding: 8px 12px; border-radius: 6px; margin-bottom: 8px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
        }
        .ev-label { font-weight: 700; color: var(--text-muted); }
        .ev-tag { background: #E2E8F0; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
        .insight-limitation { font-size: 11.5px; color: #92400E; font-style: italic; }

        .report-footer {
            text-align: center; padding: 30px 0; color: var(--text-muted);
            font-size: 13px; border-top: 1px solid var(--border-color);
        }
        .footer-small { font-size: 11px; margin-top: 4px; color: #94A3B8; }
        """
