"""Main interactive Streamlit dashboard application for Stock Market Data Analyzer.

Author: Akash Das
Phase: 9 of 12 — Streamlit Dashboard Integration

Responsibility:
    Entry point for the web application. Integrates sidebar controls,
    data ingestion pipelines (Yahoo Finance, CSV upload, sample data),
    financial KPI metric cards, and interactive Plotly visualization tabs.
"""

import sys
from pathlib import Path

# Ensure 'src' is in python path for module imports when launched via streamlit run
src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import streamlit as st

from app.data_manager import get_and_clean_data
from app.kpis import render_kpi_metrics
from app.sidebar import render_sidebar
from app.views import render_dashboard_views


def main() -> None:
    """Streamlit application entry point."""
    st.set_page_config(
        page_title="Stock Market Data Analyzer",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom styling
    st.markdown(
        """
        <style>
            .main-header {
                font-size: 2.125rem;
                font-weight: 700;
                color: #FFFFFF;
                line-height: 1.25;
                margin-top: 0rem;
                margin-bottom: 0.35rem;
                letter-spacing: -0.015em;
            }
            .sub-header {
                font-size: 1rem;
                font-weight: 400;
                color: #94A3B8;
                line-height: 1.5;
                margin-bottom: 1.25rem;
            }
            .sub-header strong {
                color: #E2E8F0;
                font-weight: 600;
            }
            @media (max-width: 768px) {
                .main-header {
                    font-size: 1.75rem;
                }
                .sub-header {
                    font-size: 0.9rem;
                }
            }
            div[data-testid="stMetricValue"] {
                font-size: 1.55rem;
                font-weight: 700;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="main-header">📈 Stock Market Data Analyzer</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Interactive Quantitative Financial Analysis & Technical Indicators Dashboard | '
        'Author: <strong>Akash Das</strong></div>',
        unsafe_allow_html=True,
    )

    # 1. Sidebar parameter capture
    params = render_sidebar()

    # 2. Data ingestion and cleaning pipeline
    with st.spinner(f"Ingesting and cleaning data for {params.ticker} from {params.source_type}..."):
        df, error_msg = get_and_clean_data(
            source_type=params.source_type,
            ticker=params.ticker,
            start_date=params.start_date,
            end_date=params.end_date,
            uploaded_file=params.uploaded_file,
        )

    # 3. Validation and error handling
    if error_msg is not None:
        st.error(f"❌ {error_msg}")
        st.info("💡 Adjust your sidebar settings or upload a valid stock CSV file to continue.")
        return

    if df is None or df.empty:
        st.warning("⚠️ No data available for the selected configuration. Please verify sidebar parameters.")
        return

    # 4. Clear synthetic data labelling
    is_synthetic = bool(df.attrs.get("is_synthetic", False))
    if is_synthetic:
        st.warning(
            "⚠️ **SYNTHETIC SAMPLE DATA ACTIVE**: The loaded dataset contains synthetic stock prices from "
            "`data/sample/sample_stock.csv`. All indicators, returns, and volatility figures reflect synthetic "
            "observations for offline testing and must not be interpreted as real market prices."
        )

    # 5. Financial KPIs Overview
    st.subheader(f"Financial Overview — {params.ticker}")
    render_kpi_metrics(df)

    st.divider()

    # 6. Interactive Visualization Views
    render_dashboard_views(df, params)

    # 7. Regulatory & Educational Footer
    st.divider()
    st.markdown(
        """
        <div style='text-align: center; color: #94A3B8; font-size: 0.85rem; padding: 1rem 0;'>
            Stock Market Data Analyzer (Phase 9) • Built with Streamlit & Plotly • Author: Akash Das<br>
            <em>Historical market data retrieved via yfinance is for analytical and educational purposes only.
            Does not constitute financial advice or investment recommendations. Offline note: Sample dataset and CSV ingestion
            operate completely offline; in-dashboard charts render via Streamlit's local bundled assets, while standalone HTML exports
            load Plotly.js dynamically from an external CDN (cdn.plot.ly).</em>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
