# User Guide: Stock Market Data Analyzer

**Project Author:** Akash Das  
**Application Type:** Interactive Quantitative Financial Analytics Dashboard & Reporting Platform  
**Technology Stack:** Python 3.11, Streamlit, Plotly, Pandas, NumPy, ReportLab  

---

## 1. Introduction

The **Stock Market Data Analyzer** is a quantitative financial analysis and reporting application. It enables quantitative researchers, financial analysts, and retail investors to:
- Ingest real-world historical equity data from Yahoo Finance or custom CSV files.
- Inspect cleaned, validated OHLCV time-series with automatic financial invariant enforcement.
- Analyze trend-smoothing indicators: 20-day Simple Moving Average (SMA 20), 50-day Simple Moving Average (SMA 50), and 20-day Exponential Moving Average (EMA 20).
- Evaluate market risk through annualized realized volatility, rolling volatility bands, and peak-to-trough Maximum Drawdown (MDD).
- Review automated heuristic market insights categorized by price trend, volatility, risk, volume turnover, and correlation.
- Generate and download publication-quality multi-page PDF reports (10–11 pages; 11 pages for synthetic dataset configurations), interactive Plotly HTML reports, and standardized analytical CSV files.

---

## 2. Installation & Quick Start

### 2.1 Prerequisites
- **Operating System:** Windows 10/11, macOS, or Linux.
- **Python Version:** Python 3.11 (recommended).
- **Environment:** Dedicated Python virtual environment (`.venv`).

### 2.2 Activating Virtual Environment
Before launching the application, activate the local environment from the project root:

**On Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**On macOS/Linux:**
```bash
source .venv/bin/activate
```

### 2.3 Starting the Dashboard
Launch the Streamlit web application:
```bash
streamlit run app/dashboard.py
```
Upon startup, Streamlit opens the dashboard automatically in your default browser at:  
`http://localhost:8501`

---

## 3. Sidebar Controls & Data Selection

The left-hand sidebar contains all interactive configuration controls:

### 3.1 Data Ingestion Source
Choose between three data modes:
1. **Sample Dataset (Synthetic):**
   - Loads the pre-packaged 75-session dataset from `data/sample/sample_stock.csv`.
   - Requires zero internet connectivity; ideal for offline demonstrations and testing.
   - Automatically activates amber synthetic warning badges across charts, tables, and reports.
2. **Live Yahoo Finance:**
   - Fetches live daily market records directly from Yahoo Finance via `yfinance`.
   - **Stock Ticker Symbol:** Enter any valid US ticker (e.g., `AAPL`, `MSFT`, `GOOGL`, `SPY`, `NVDA`, `TSLA`). Case-insensitive.
   - **Date Range Pickers:** Select Start Date and End Date. End date boundary is inclusive.
3. **Upload CSV:**
   - Upload your own historical CSV file.
   - **Required Columns:** Must contain `Date`, `Open`, `High`, `Low`, `Close`, and `Volume`.
   - Date formats supported: `YYYY-MM-DD` or ISO 8601 timestamps.

### 3.2 Technical Indicator Toggles
- **SMA 20:** Enable/disable 20-day Simple Moving Average overlay (Cyan line).
- **SMA 50:** Enable/disable 50-day Simple Moving Average overlay (Amber line).
- **EMA 20:** Enable/disable 20-day Exponential Moving Average overlay (Magenta line).

### 3.3 Chart & Risk Preferences
- **Shared Volume Subplot:** When enabled, embeds a synchronized trading volume bar chart beneath the candlestick chart.
- **Rolling Volatility Windows:** Multi-select input for sliding lookback periods (default: 21 days and 63 days).

---

## 4. Executive Financial KPIs

Directly above the tabbed workspace, six high-level financial KPI cards summarize the active dataset:

| KPI Card | Description | Mathematical Basis |
| :--- | :--- | :--- |
| **Latest Close** | Final closing price in the selected period. | $\text{Close}_{T}$ |
| **First Close** | First recorded closing price in the selected period. | $\text{Close}_{0}$ |
| **Cumulative Return** | Total percentage capital growth over the period. | $\prod_{t=1}^T (1 + R_t) - 1$ |
| **Annualized Volatility** | Realized volatility scaled to an annual calendar. | $\sigma_{\text{daily}} \times \sqrt{252}$ |
| **Max Drawdown (MDD)** | Deepest peak-to-trough capital decline. | $\min(\text{Drawdown}_t)$ |
| **Total Observations** | Total number of valid trading sessions evaluated. | Count of rows $T$ |

---

## 5. Dashboard Tab Navigation

### Tab 1: Price & Technical Analysis
- **Interactive OHLC Candlestick Chart:** Displays daily price action with green/red candlestick bodies and wicks.
- **Synchronized Volume Bars:** Colored according to daily price direction (green for up days, red for down days).
- **Interactive Tools:** Period selector buttons (1m, 3m, 6m, YTD, 1y, All), interactive range slider, crosshair hover tooltips, and box zooming.

### Tab 2: Returns & Risk Analysis
- **Daily Returns Distribution:** Interactive bar chart displaying daily percentage returns. Includes horizontal reference lines for mean return and $\pm 2\sigma$ statistical threshold bands.
- **Cumulative Return vs. Underwater Drawdown:** Dual-panel synchronized visualization displaying total compounded wealth trajectory on top and peak-to-trough capital drawdown below.
- **Rolling Volatility Comparison:** Multi-line plot tracking short-term (21-session) vs. quarterly (63-session) annualized rolling volatility.

### Tab 3: Insights & Interpretation
- **Executive Synthesis:** Quadrant summary outlining key positive signals, cautionary risks, volatility flags, and data limitations.
- **Categorized Finding Cards:** Structured cards displaying Title, Severity badge (Positive, Warning, Danger, Info), Observation text, Supporting Evidence metrics, and Methodological Boundaries.

### Tab 4: Data Preview & Statistics
- **Descriptive Statistics Table:** Summary metrics across Open, High, Low, Close, and Volume (Count, Mean, Std Dev $ddof=1$, Min, 25%, Median, 75%, Max, IQR).
- **Price-Volume Dynamics:** High-Low spread analysis, range ratios, and linear correlation coefficients.
- **Correlation Heatmap:** Annotated Pearson correlation matrix across all numeric features.
- **Paginated Data Table:** Interactive viewer for raw and cleaned records.

### Tab 5: Reports & Downloads
Generate and download five distinct reporting artifacts:
1. **Executive PDF Report:** Comprehensive multi-page vector document (10–11 pages; 11 pages for synthetic dataset configurations) with embedded charts, KPI tables, dataset profiles, and compliance footers.
2. **Interactive HTML Report:** Responsive web document with embedded Plotly charts and navigation.
3. **Cleaned OHLCV CSV:** Standardized price and volume records formatted for external analysis.
4. **Comprehensive Analytical CSV:** Enriched dataset containing all OHLCV bars plus SMA 20, SMA 50, EMA 20, Daily Return, Cumulative Return, Drawdown, and Rolling Volatilities.
5. **Insights Summary CSV:** Structured tabular export of all qualitative findings, severity classifications, and statistical limits.

---

## 6. Troubleshooting & FAQ

### Q: Why do I see an amber banner saying "SYNTHETIC SAMPLE DATA ACTIVE"?
**A:** This indicates that the dashboard is running on the pre-packaged synthetic test dataset (`data/sample/sample_stock.csv`). All metrics reflect synthetic demonstration data. To analyze real securities, switch the sidebar source to **Live Yahoo Finance**.

### Q: Why do moving averages display `NaN` on the first few rows?
**A:** Moving averages require a historical warmup window ($N$ trading sessions). For example, a 50-day SMA requires 50 historical observations before producing its first valid value. The first 49 rows are legitimately `NaN`.

### Q: Can I run this offline without internet access?
**A:** Yes. The application is fully functional offline when using **Sample Dataset (Synthetic)** or **Upload CSV**. Live Yahoo Finance requires an active internet connection.
