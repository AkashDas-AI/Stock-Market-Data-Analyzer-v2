"""Visual views and tab layout components for Streamlit dashboard.

Responsibility:
    Render interactive Plotly charts, summary tables, and data preview grids
    across clean modular dashboard tabs:
    - Price & Technical Analysis
    - Returns & Risk Analysis
    - Data Preview & Statistics
"""

import re
from typing import TYPE_CHECKING
import streamlit as st
import pandas as pd

from stock_analyzer.analysis.eda import ExploratoryDataAnalyzer
from stock_analyzer.analysis.insights import StockInsightAnalyzer
from stock_analyzer.reporting.report_generator import StockReportGenerator
from stock_analyzer.visualization.interactive_charts import InteractiveChartGenerator

if TYPE_CHECKING:
    from app.sidebar import DashboardParameters


def render_dashboard_views(df: pd.DataFrame, params: "DashboardParameters") -> None:
    """Render main dashboard tabs with embedded Plotly charts and data grids.

    Args:
        df: Cleaned stock DataFrame.
        params: DashboardParameters containing widget states and indicator toggles.
    """
    chart_gen = InteractiveChartGenerator(df, ticker=params.ticker)
    tabs = st.tabs(
        [
            "📊 Price & Technical Analysis",
            "📈 Returns & Risk Analysis",
            "🔍 Data Preview & Statistics",
            "💡 Insights & Interpretation",
            "📑 Reports & Downloads",
        ]
    )
    tab_price = tabs[0]
    tab_risk = tabs[1] if len(tabs) > 1 else tabs[0]
    tab_data = tabs[2] if len(tabs) > 2 else tabs[0]
    tab_insights = tabs[3] if len(tabs) > 3 else tabs[0]
    tab_reports = tabs[4] if len(tabs) > 4 else tabs[0]

    # =========================================================================
    # Tab 1: Price & Technical Analysis
    # =========================================================================
    with tab_price:
        st.subheader("1. Interactive OHLC Candlestick Chart")
        st.caption("Price action with hover tooltips, period selectors, and range slider.")
        fig_candle = chart_gen.create_candlestick_chart(
            include_volume=params.show_candlestick_volume
        )
        st.plotly_chart(fig_candle, use_container_width=True)

        st.subheader("2. Moving Average Trend Overlays")
        st.caption("Closing price with user-selected moving averages (SMA 20, SMA 50, EMA 20).")
        fig_ma = chart_gen.create_moving_averages_chart(
            show_sma_20=params.show_sma_20,
            show_sma_50=params.show_sma_50,
            show_ema_20=params.show_ema_20,
        )
        st.plotly_chart(fig_ma, use_container_width=True)

        if "Volume" in df.columns:
            st.subheader("3. Trading Volume History")
            st.caption("Daily trading volume color-coded by daily price direction (green = up, red = down).")
            fig_vol = chart_gen.create_volume_chart()
            st.plotly_chart(fig_vol, use_container_width=True)

    # =========================================================================
    # Tab 2: Returns & Risk Analysis
    # =========================================================================
    with tab_risk:
        st.subheader("1. Daily Percentage Returns")
        col_r1, col_r2 = st.columns([1, 1])
        with col_r1:
            st.markdown("**Daily Returns Time Series**")
            fig_ret = chart_gen.create_daily_returns_chart()
            st.plotly_chart(fig_ret, use_container_width=True)

        with col_r2:
            st.markdown("**Daily Returns Distribution**")
            fig_dist = chart_gen.create_daily_returns_distribution_chart(bins=30)
            st.plotly_chart(fig_dist, use_container_width=True)

        st.subheader("2. Cumulative Compound Growth")
        st.caption("Trajectory of capital compounding from baseline over the selected period.")
        fig_cum = chart_gen.create_cumulative_returns_chart()
        st.plotly_chart(fig_cum, use_container_width=True)

        st.subheader("3. Underwater Drawdown Curve")
        st.caption("Percentage decline from historical high-water mark with Maximum Drawdown point.")
        fig_dd = chart_gen.create_drawdown_chart()
        st.plotly_chart(fig_dd, use_container_width=True)

        st.subheader("4. Rolling Annualized Volatility")
        w_labels = ", ".join(f"{w}d" for w in params.rolling_vol_windows)
        st.caption(f"Sliding window volatility annualized to 252 trading sessions ({w_labels}).")
        fig_rvol = chart_gen.create_rolling_volatility_chart(
            windows=params.rolling_vol_windows
        )
        st.plotly_chart(fig_rvol, use_container_width=True)

    # =========================================================================
    # Tab 3: Data Preview & Statistics
    # =========================================================================
    with tab_data:
        st.subheader("1. Exploratory Summary Statistics")
        st.caption("Descriptive statistics across OHLCV columns.")
        eda_analyzer = ExploratoryDataAnalyzer(df, ticker=params.ticker)
        summary_stats = eda_analyzer.compute_summary_statistics()
        st.dataframe(summary_stats.round(4), use_container_width=True)

        st.subheader("2. Numerical Feature Correlation Matrix")
        st.caption("Pearson correlation heatmap between prices and trading volume.")
        fig_corr = chart_gen.create_correlation_heatmap()
        st.plotly_chart(fig_corr, use_container_width=True)

        st.subheader("3. Cleaned Dataset Records")
        st.caption("Preview of the most recent 100 cleaned observation records.")
        st.dataframe(df.tail(100), use_container_width=True)

        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Cleaned Dataset (CSV)",
            data=csv_bytes,
            file_name=f"{params.ticker}_cleaned_stock_data.csv",
            mime="text/csv",
            help="Download the verified, cleaned dataset in standard CSV format.",
        )

    # =========================================================================
    # Tab 4: Insights & Interpretation
    # =========================================================================
    with tab_insights:
        st.subheader("💡 Stock Market Insights & Analytical Interpretation")
        st.caption(
            "Empirical observations, momentum evaluation, historical risk characteristics, "
            "and data limitations derived deterministically from analytical models."
        )

        insight_analyzer = StockInsightAnalyzer(df, ticker=params.ticker)
        summary = insight_analyzer.generate_summary()

        # Synthetic sample data notice
        if summary.is_synthetic:
            st.warning(
                "⚠️ **SYNTHETIC SAMPLE DATA ACTIVE**: All insights displayed below are derived from offline "
                "synthetic observations (data/sample/sample_stock.csv) and are presented strictly for testing."
            )

        # 1. Executive Summary Cards (2x2 layout)
        st.markdown("### 1. Executive Summary")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("##### 🟢 Key Positive Observations")
            if summary.positive_observations:
                for obs in summary.positive_observations:
                    st.markdown(f"- {obs}")
            else:
                st.info("No distinctly positive historical signals identified for this period.")

            st.markdown("##### ⚠️ Risk & Volatility Observations")
            if summary.risk_observations:
                for obs in summary.risk_observations:
                    st.markdown(f"- {obs}")
            else:
                st.info("No elevated risk flags triggered for the active period.")

        with col_s2:
            st.markdown("##### 🔴 Key Cautionary / Negative Observations")
            if summary.negative_observations:
                for obs in summary.negative_observations:
                    st.markdown(f"- {obs}")
            else:
                st.info("No distinctly negative historical signals identified for this period.")

            st.markdown("##### ℹ️ Data Limitations & Disclaimers")
            if summary.data_limitations:
                for lim in summary.data_limitations:
                    st.markdown(f"- {lim}")
            else:
                st.info("Standard statistical limitations apply.")

        st.divider()

        # 2. Detailed Categorical Observations in Expanders
        st.markdown("### 2. Detailed Categorical Observations")

        # Group insights by category
        categories_dict: dict = {}
        for ins in summary.insights:
            categories_dict.setdefault(ins.category.value, []).append(ins)

        for cat_name, cat_insights in categories_dict.items():
            with st.expander(
                f"📌 {cat_name} ({len(cat_insights)} observations)",
                expanded=(cat_name in ["Price Trend", "Moving Averages"]),
            ):
                for item in cat_insights:
                    sev_icon = (
                        "🟢"
                        if item.severity.value == "positive"
                        else (
                            "🔴"
                            if item.severity.value == "negative"
                            else ("⚠️" if item.severity.value == "warning" else "ℹ️")
                        )
                    )
                    st.markdown(f"**{sev_icon} {item.title}**")
                    st.write(item.observation)
                    if item.evidence:
                        evidence_str = ", ".join(f"`{k}`: **{v}**" for k, v in item.evidence.items())
                        st.caption(f"📊 Supporting Evidence: {evidence_str}")
                    if item.limitations:
                        st.caption(f"⚠️ Limitation: {item.limitations}")
                    st.divider()

        # 3. Regulatory and Integrity Notice
        st.info(
            "🛡️ **Analytical Integrity Notice**: All generated insights are descriptive, historical, and deterministic. "
            "They explain past statistical relationships and do not constitute financial advice, investment recommendations, "
            "or price predictions."
        )

    # =========================================================================
    # Tab 5: Reports & Downloads
    # =========================================================================
    with tab_reports:
        st.subheader("📑 Quantitative Research Reports & Data Export Center")
        st.caption(
            "Export currently active analytical results, charts, risk profiles, and qualitative insights "
            "into downloadable PDF research reports, interactive HTML dossiers, and structured CSV datasets."
        )

        safe_sym = re.sub(r"[^\w\-]", "_", params.ticker or "STOCK")
        source_name = getattr(params, "source_type", getattr(params, "data_source", "Unknown"))
        is_synthetic = (
            source_name == "Sample Dataset (Synthetic)"
            or df.attrs.get("data_source") == "synthetic"
            or df.attrs.get("is_synthetic", False)
            or "synthetic" in str(source_name).lower()
            or safe_sym == "SAMPLE"
        )

        if is_synthetic:
            st.warning(
                "⚠️ **SYNTHETIC SAMPLE DATA ACTIVE**: Exported reports will be explicitly branded with "
                "synthetic data disclosures and must not be interpreted as real exchange data."
            )

        report_gen = StockReportGenerator(
            df,
            ticker=params.ticker,
            data_source=source_name,
            is_synthetic=is_synthetic,
        )

        # 1. Executive Research Reports
        st.markdown("### 1. Executive Research Reports")
        col_rep1, col_rep2 = st.columns(2)

        with col_rep1:
            st.markdown("#### 📄 Multi-Page PDF Research Report")
            st.caption(
                "Publication-quality PDF document featuring Cover Page, Executive Summary, "
                "Technical Charts, Returns Analysis, Risk Metrics, Volume Turnover, and Phase 10 Insights."
            )
            try:
                pdf_bytes = report_gen.generate_pdf_report()
                st.download_button(
                    label="⬇️ Download PDF Research Report",
                    data=pdf_bytes,
                    file_name=f"{safe_sym}_quantitative_analysis_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    help="Download the formal, printable multi-page PDF research report.",
                )
            except Exception as e:
                st.error(f"Failed to generate PDF report: {e}")

        with col_rep2:
            st.markdown("#### 🌐 Interactive HTML Dossier")
            st.caption(
                "Responsive standalone web report embedding interactive Plotly charts, "
                "dynamic tooltips, period selectors, and Phase 10 structured insights."
            )
            embed_offline = st.checkbox(
                "Bundle full offline Plotly JavaScript (~4.8MB)",
                value=False,
                key="embed_offline_html",
                help="If checked, creates a 100% self-contained offline file. If unchecked, uses lightweight CDN.",
            )
            try:
                html_bytes = report_gen.generate_html_report(embed_plotly_js=embed_offline)
                st.download_button(
                    label="⬇️ Download Interactive HTML Report",
                    data=html_bytes,
                    file_name=f"{safe_sym}_interactive_analysis_report.html",
                    mime="text/html",
                    use_container_width=True,
                    help="Download the standalone interactive HTML report.",
                )
            except Exception as e:
                st.error(f"Failed to generate HTML report: {e}")

        st.divider()

        # 2. Standardized Analytical Data Exports
        st.markdown("### 2. Standardized Analytical Data Exports")
        st.caption("Machine-readable CSV exports for spreadsheet analysis, custom Python pipelines, or BI dashboards.")

        col_csv1, col_csv2, col_csv3 = st.columns(3)

        with col_csv1:
            st.markdown("##### 📊 Full Analytical CSV")
            st.caption("OHLCV + SMA20 + SMA50 + EMA20 + Daily Return + Cumulative Return + Drawdown + Rolling Volatilities.")
            try:
                comp_csv_bytes = report_gen.export_comprehensive_csv()
                st.download_button(
                    label="⬇️ Download Analytical Dataset (CSV)",
                    data=comp_csv_bytes,
                    file_name=f"{safe_sym}_comprehensive_analysis.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"CSV export failed: {e}")

        with col_csv2:
            st.markdown("##### 💡 Insights & Evidence CSV")
            st.caption("Tabular export of all Phase 10 structured findings, severity classifications, and limitation notices.")
            try:
                insights_csv_bytes = report_gen.export_insights_csv()
                st.download_button(
                    label="⬇️ Download Insights Summary (CSV)",
                    data=insights_csv_bytes,
                    file_name=f"{safe_sym}_insights_summary.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Insights export failed: {e}")

        with col_csv3:
            st.markdown("##### 📁 Cleaned OHLCV CSV")
            st.caption("Chronologically sorted, validated base OHLCV records formatted for external modeling.")
            try:
                cleaned_csv_bytes = report_gen.export_cleaned_csv()
                st.download_button(
                    label="⬇️ Download Cleaned OHLCV (CSV)",
                    data=cleaned_csv_bytes,
                    file_name=f"{safe_sym}_cleaned_ohlcv.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Cleaned CSV export failed: {e}")

        st.divider()

        # 3. Local Batch Archive Generation
        st.markdown("### 3. Local Batch Archive Generation")
        st.caption("Generate and persist all 4 reporting artifacts simultaneously to the local `reports/generated/` folder.")
        if st.button("🚀 Generate & Save All Reports Locally", use_container_width=True):
            with st.spinner("Generating and archiving complete report suite..."):
                try:
                    saved_paths = report_gen.generate_all_reports(
                        output_dir="reports/generated", embed_plotly_js=embed_offline
                    )
                    st.success("✅ Complete reporting package generated successfully:")
                    for art_name, art_path in saved_paths.items():
                        st.write(f"- **{art_name}**: `{art_path}`")
                except Exception as e:
                    st.error(f"Batch generation error: {e}")

        # 4. Compliance & Regulatory Notice
        st.info(
            "🛡️ **Compliance & Analytical Integrity**: All generated reports reflect backward-looking historical calculations. "
            "They explain past statistical relationships and do not constitute financial advice, investment recommendations, "
            "or price predictions. Synthetic data is explicitly labeled across all exported documents."
        )
