# Stock Market Data Analyzer

An institutional-grade Python application for financial time-series ingestion, algorithmic data cleaning, exploratory statistics, technical indicator computation, risk metrics evaluation, interactive dashboard visualization, structured insight generation, and multi-format report publishing.

Author: Akash Das  
Repository: stock-market-data-analyzer  
License: MIT  

---

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Pandas 3.1.1](https://img.shields.io/badge/pandas-3.1.1-150458.svg)](https://pandas.pydata.org/)
[![NumPy 2.4.6](https://img.shields.io/badge/numpy-2.4.6-013243.svg)](https://numpy.org/)
[![Matplotlib 3.11.2](https://img.shields.io/badge/matplotlib-3.11.2-11557c.svg)](https://matplotlib.org/)
[![Seaborn 0.13.2](https://img.shields.io/badge/seaborn-0.13.2-4c72b0.svg)](https://seaborn.pydata.org/)
[![Plotly 7.1.0](https://img.shields.io/badge/plotly-7.1.0-3f4f75.svg)](https://plotly.com/)
[![Streamlit 1.67.0](https://img.shields.io/badge/streamlit-1.67.0-ff4b4b.svg)](https://streamlit.io/)
[![yfinance 1.8.0](https://img.shields.io/badge/yfinance-1.8.0-2b5b84.svg)](https://pypi.org/project/yfinance/)
[![ReportLab 5.1.2](https://img.shields.io/badge/reportlab-5.1.2-d35400.svg)](https://www.reportlab.com/)
[![Pytest 268 Passed](https://img.shields.io/badge/pytest-268%20passed-brightgreen.svg)](https://docs.pytest.org/)
[![License MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 1. Project Overview

The Stock Market Data Analyzer is an end-to-end quantitative financial analysis platform designed to solve common data-integrity, statistical rigor, and reporting challenges in equity research workflows.

Financial market datasets frequently suffer from non-synchronous reporting, missing records, price inversions, dividend adjustments, and split anomalies. Typical retail analysis tools either overlook these data anomalies or obscure the underlying mathematical transformations within opaque models.

This project implements an open, mathematically deterministic quantitative pipeline that enforces strict data-quality invariants, executes time-series transformations, calculates standard technical and risk metrics, visualizes patterns across static and interactive visual layers, automates structured qualitative insights, and compiles audit-ready publications in PDF, HTML, and CSV formats.

The application serves both technical developers looking for a modular, fully tested quantitative library and non-technical stakeholders requiring an intuitive, multi-asset Streamlit analytics console.

---

## 2. Key Features

- Market Data Ingestion: Automated retrieval of daily OHLCV equity bars from Yahoo Finance (via yfinance) across user-specified date ranges, alongside local CSV loading and an embedded offline development dataset.
- Invariant Data Cleaning: Multi-stage pipeline enforcing chronological ordering, missing-value imputation, duplicate removal, positive price constraints, and strict OHLC price boundary relationships (High >= max(Open, Close) and Low <= min(Open, Close)).
- Exploratory Data Analysis: Comprehensive descriptive statistics, price range distributions, interquartile spreads, and correlation matrices evaluating relationships between price and volume metrics.
- Technical Indicator Suite: Exact mathematical computation of 20-day Simple Moving Average (SMA 20), 50-day Simple Moving Average (SMA 50), and 20-day Exponential Moving Average (EMA 20) with dynamic crossover detection.
- Quantitative Returns and Risk: Daily percentage returns, compounded cumulative return trajectories, rolling volatility, annualized volatility based on the 252-session trading convention, and peak-to-trough Maximum Drawdown (MDD) tracking.
- Dual Visual Interfaces: Publication-quality static visual outputs generated through Matplotlib and Seaborn alongside fully interactive web charts generated through Plotly (candlesticks, indicator overlays, volume subplots, and return histograms).
- Interactive Streamlit Dashboard: Modular multi-asset web console organized into five functional tabs with real-time parameter controls, sidebar configuration, dynamic asset profiles, and download triggers.
- Structured Financial Interpretation: Automated heuristic classification engine translating calculated metrics into evidence-based financial observations across trend direction, volatility regimes, and volume turnover anomalies.
- Publication-Grade Report Engine: High-resolution vector PDF generator built with ReportLab SimpleDocTemplate and custom two-pass NumberedCanvas (running headers, dynamic page counters, embedded charts, and compliance notices).
- Interactive Dossier Publishing: Self-contained interactive HTML reports built with Plotly supporting both lightweight CDN-linked and standalone offline viewing modes.
- Standardized Machine-Readable Exports: Three structured CSV artifacts: Cleaned OHLCV data, Comprehensive Analytical data with all calculated indicators, and Structured Insights summaries.

---

## 3. Technology Stack

| Category | Technology | Version | Architectural Role |
| :--- | :--- | :--- | :--- |
| Runtime | Python | 3.11 | Core runtime environment and standard libraries |
| Data Processing | Pandas | 3.1.1 | Vectorized time-series manipulation, DataFrames, indexing |
| Numerical Mathematics | NumPy | 2.4.6 | Numerical arrays, mathematical formulas, log-linear transforms |
| Market Data Ingestion | yfinance | 1.8.0 | Historical daily OHLCV financial market data collection |
| Static Visualization | Matplotlib | 3.11.2 | Publication-quality static chart generation and buffer export |
| Statistical Visualization | Seaborn | 0.13.2 | Distribution plots, heatmaps, and statistical chart styling |
| Interactive Visualization | Plotly | 7.1.0 | Web-based interactive charts, hover tooltips, range sliders |
| Web Application | Streamlit | 1.67.0 | Reactive frontend interface, session state, control widgets |
| PDF Publishing | ReportLab | 5.1.2 | Vector PDF document compilation, flowables, NumberedCanvas |
| PDF Inspection | pypdf | 7.1.1 | PDF verification, page count validation, and metadata audits |
| Automated Testing | Pytest | 9.2.0 | Test runner, fixtures, unit tests, and integration coverage |
| Configuration | python-dotenv | 1.0.1 | Environment variable configuration and workspace settings |

---

## 4. Project Architecture

The codebase follows a modular 4-tier separation of concerns: Ingestion Layer, Core Analytics Engine, Visualization & Reporting Layer, and Presentation UI.

```text
Stock-Market-Data-Analyzer/
|-- .github/                      # Continuous integration workflows and issue templates
|-- .vscode/                      # Workspace editor settings and interpreter configuration
|-- app/                          # Streamlit web application components
|   |-- __init__.py
|   |-- dashboard.py              # Main dashboard entrypoint and page router
|   |-- sidebar.py                # Ingestion controls, ticker input, date ranges
|   |-- data_manager.py           # Session data orchestration and caching layer
|   |-- ui_components.py          # KPI metrics cards and reusable UI containers
|   |-- tab_price_analysis.py     # Tab 1: Interactive candlestick and indicator charts
|   |-- tab_returns_risk.py       # Tab 2: Daily returns, cumulative growth, MDD
|   |-- tab_data_table.py         # Tab 3: Paginated data tables and statistical summaries
|   |-- tab_insights.py           # Tab 4: Structured qualitative financial observations
|   `-- tab_reports.py            # Tab 5: PDF, HTML, and CSV report download manager
|-- data/
|   |-- raw/                      # Ingested raw market data (git-ignored)
|   |-- interim/                  # Intermediate validation stages (git-ignored)
|   |-- processed/                # Fully cleaned and validated datasets (git-ignored)
|   `-- sample/                   # Pre-packaged offline reference dataset
|       `-- sample_stock.csv      # Verified 75-session sample market data
|-- docs/                         # Technical documentation and architecture guides
|   |-- DATA_DICTIONARY.md        # Schemas, metric formulas, and CSV layouts
|   |-- DATA_FLOW_AND_PIPELINE.md # End-to-end data lifecycle documentation
|   |-- DEVELOPMENT_ROADMAP.md    # 12-phase permanent implementation roadmap
|   |-- DOCUMENTATION_INDEX.md    # Central documentation guide and index
|   |-- EXECUTION_AND_VALIDATION_LOG.md # Complete audit log of all 22 execution entries
|   |-- MODULE_REFERENCE.md       # Public API method signatures and class hierarchy
|   |-- PROJECT_ARCHITECTURE.md   # Architectural blueprint and design patterns
|   |-- SCREENSHOT_GUIDE.md       # Visual design guidelines and layout standards
|   |-- TESTING_GUIDE.md          # Pytest inventory and testing execution guide
|   `-- USER_GUIDE.md             # End-user operational manual
|-- images/                       # Repository screenshot directory
|   |-- dashboard/                # Application dashboard screenshots
|   `-- reports/                  # Publication and report layout screenshots
|-- notebooks/                    # Research and exploratory Jupyter notebooks
|   `-- exploratory_analysis.ipynb
|-- outputs/
|   |-- charts/                   # Exported static PNG and interactive HTML charts
|   `-- tables/                   # Exported summary tables and matrices
|-- reports/
|   `-- generated/                # Locally compiled PDF and HTML reports
|-- src/
|   `-- stock_analyzer/           # Core library package
|       |-- __init__.py
|       |-- data/                 # Ingestion, validation, and cleaning
|       |   |-- __init__.py
|       |   |-- fetcher.py        # Yahoo Finance market data client
|       |   |-- loader.py         # CSV ingestion and date parsing
|       |   `-- cleaner.py        # StockDataCleaner invariant pipeline
|       |-- analysis/             # Quantitative and statistical modules
|       |   |-- __init__.py
|       |   |-- eda.py            # Descriptive statistics and correlations
|       |   |-- indicators.py     # SMA 20, SMA 50, EMA 20 indicators
|       |   |-- returns.py        # Simple and compounded returns
|       |   |-- risk.py           # Annualized volatility and Drawdown
|       |   `-- insights.py       # StockInsightAnalyzer qualitative heuristics
|       |-- visualization/        # Graphical rendering modules
|       |   |-- __init__.py
|       |   |-- static_charts.py  # Matplotlib/Seaborn static figures
|       |   `-- interactive_charts.py # Plotly web graphics
|       |-- reporting/            # Multi-format publication engine
|       |   |-- __init__.py
|       |   |-- pdf_report.py     # ReportLab vector document generator
|       |   |-- html_report.py    # Plotly HTML publication builder
|       |   |-- csv_exporter.py   # Standardized CSV dataset exporter
|       |   `-- report_generator.py # StockReportGenerator coordinator
|       `-- utils/                # Configuration and common helpers
|           |-- __init__.py
|           |-- config.py         # Workspace path definitions
|           `-- validators.py     # Parameter validation functions
|-- tests/                        # Automated Pytest test suite (268 tests)
|   |-- __init__.py
|   |-- conftest.py               # Shared test fixtures and synthetic series
|   |-- test_cleaner.py           # Data cleaner validation and constraint tests
|   |-- test_dashboard.py         # Streamlit UI integration and mock tests
|   |-- test_eda.py               # Statistical calculation verification
|   |-- test_fetcher.py           # Market data fetcher and mock network tests
|   |-- test_indicators.py        # Moving average accuracy tests
|   |-- test_insights.py          # Heuristic insight rules and threshold tests
|   |-- test_integration.py       # End-to-end pipeline integration tests
|   |-- test_interactive_charts.py # Plotly visualization validation
|   |-- test_loader.py            # CSV loading and schema validation tests
|   |-- test_reporting.py         # PDF, HTML, and CSV generator tests
|   |-- test_returns.py           # Return calculation and compound growth tests
|   |-- test_risk.py              # Volatility and Maximum Drawdown tests
|   `-- test_static_charts.py     # Matplotlib figure output tests
|-- .env.example                  # Environment variable configuration template
|-- .gitignore                    # Git exclusion rules
|-- CONTRIBUTING.md               # Guidelines for prospective contributors
|-- LICENSE                       # MIT open-source license
|-- main.py                       # Command-line interface entry point
|-- pytest.ini                    # Pytest framework settings and test paths
`-- requirements.txt              # Pinned production dependencies
```

---

## 5. Installation and Setup

This application has been verified on Windows 10/11 using Python 3.11.

### Prerequisites

Ensure Python 3.11 is installed and accessible from your system terminal:

```cmd
python --version
```

### Installation Steps

1. Clone the repository to your local computer:
   ```cmd
   git clone https://github.com/your-username/stock-market-data-analyzer.git
   ```

2. Navigate into the project root directory:
   ```cmd
   cd stock-market-data-analyzer
   ```

3. Create an isolated Python virtual environment:
   ```cmd
   python -m venv .venv
   ```

4. Activate the virtual environment:
   - On Windows Command Prompt:
     ```cmd
     .venv\Scripts\activate.bat
     ```
   - On Windows PowerShell:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```

5. Install pinned project dependencies:
   ```cmd
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. Optional Configuration: Copy the environment template if custom settings are required:
   - On Windows Command Prompt:
     ```cmd
     copy .env.example .env
     ```
   - On Windows PowerShell:
     ```powershell
     Copy-Item .env.example .env
     ```

7. VS Code Configuration: If developing in Visual Studio Code, select the Python interpreter located at `.venv\Scripts\python.exe` to enable linting and test discovery.

---

## 6. Running the Application

### Launching the Dashboard

Launch the interactive web dashboard using the verified module command:

```cmd
python -m streamlit run app/dashboard.py
```

The application will start a local server and display the connection URLs:
- Local URL: http://localhost:8501
- Network URL: http://your-local-ip:8501

### Data Ingestion Modes

The sidebar provides three mutually exclusive data ingestion sources:

1. Sample Dataset (Synthetic):
   - Loads the pre-packaged offline sample dataset (`data/sample/sample_stock.csv`).
   - Requires zero network connectivity.
   - Ideal for instant testing, evaluation, and offline development.
   - All charts, metrics, and generated reports display amber callout banners noting synthetic provenance.

2. Live Yahoo Finance:
   - Queries live market data directly from Yahoo Finance via the `StockDataFetcher` module.
   - Enter any standard equity ticker symbol (such as AAPL, MSFT, GOOGL, NVDA, TSLA).
   - Configure custom Start Date and End Date boundaries using calendar pickers.
   - Automatically cleans and validates live market bars before passing them to the analytics layer.

3. Upload CSV:
   - Allows users to drag and drop custom historical equity CSV files.
   - Supported CSV schema requirements:
     - Date column (ISO 8601 `YYYY-MM-DD` format preferred).
     - Numeric price columns: `Open`, `High`, `Low`, `Close` (positive numbers).
     - Trading activity column: `Volume` (non-negative numbers).
     - Optional: `Adj Close`.

---

## 7. Analytical Methodology

All calculations in this project are governed by exact mathematical formulas and executed through vectorized Pandas and NumPy routines.

### Data Cleaning and Invariants

Every dataset passes through `StockDataCleaner` to enforce four fundamental financial invariants:
1. Chronological Sorting: The DataFrame is indexed by `Date` and sorted ascending.
2. Deduplication: Duplicate date records are resolved through timestamp sorting and deterministic retention.
3. Positivity: Price columns (`Open`, `High`, `Low`, `Close`) must be strictly positive ($P > 0$).
4. OHLC Boundaries: The session high must be greater than or equal to both open and close ($High \ge \max(Open, Close)$), and the session low must be less than or equal to both open and close ($Low \le \min(Open, Close)$).

### Technical Indicators

- Simple Moving Average (SMA): Computed as the unweighted arithmetic mean of closing prices over window $N$:
  $$SMA_t(N) = \frac{1}{N} \sum_{i=0}^{N-1} Close_{t-i}$$
  Windows evaluated: 20-day (short-term momentum) and 50-day (medium-term trend).
- Exponential Moving Average (EMA): Computed using an exponential smoothing factor $\alpha = \frac{2}{N + 1}$:
  $$EMA_t(N) = \alpha \cdot Close_t + (1 - \alpha) \cdot EMA_{t-1}(N)$$
  Window evaluated: 20-day responsive exponential baseline.

### Returns and Risk Modeling

- Daily Percentage Return ($R_t$):
  $$R_t = \frac{Close_t - Close_{t-1}}{Close_{t-1}}$$
- Compounded Cumulative Return ($CR_t$):
  $$CR_t = \prod_{i=1}^{t} (1 + R_i) - 1$$
- Annualized Volatility ($\sigma_{annual}$): Computed using the standard equity trading convention of 252 sessions per calendar year:
  $$\sigma_{annual} = \sigma_{daily} \times \sqrt{252}$$
- Maximum Drawdown (MDD): Measures the largest peak-to-trough decline before a new high is established:
  $$Drawdown_t = \frac{Close_t - \max_{\tau \le t}(Close_\tau)}{\max_{\tau \le t}(Close_\tau)}$$
  $$MDD = \min_t (Drawdown_t)$$

### Volume Turnover Interpretation

Trading volume analysis tracks 20-day moving averages of traded shares. In strict compliance with quantitative integrity standards, volume surges (trading volume $> 1.5\times$ 20-day baseline) are described solely as elevated market turnover. Because aggregate OHLCV data does not distinguish institutional orders from retail execution, the system strictly avoids unsupported participant attribution.

### Correlation Caveat

The exploratory analysis matrix evaluates Pearson correlation coefficients across prices, ranges, and turnover. High statistical correlation between indicators and price action represents shared underlying price components, not independent causal confirmation.

---

## 8. Reports and Downloads

The application provides a centralized reporting suite accessible via Tab 5 of the dashboard or programmatically through `StockReportGenerator`:

1. Multi-Page Vector PDF Report:
   - Institutional research report compiled using ReportLab.
   - Sizing: Multi-page document (10 to 11 pages; 11 pages for synthetic dataset configurations due to dedicated Section 2 synthetic disclosure banners).
   - Layout: Running header with asset symbol, dynamic two-pass `NumberedCanvas` footer ("Page X of Y"), Executive Summary, Dataset Profile, embedded high-resolution static charts (160 DPI), return distributions, drawdown tables, structured qualitative insights, and regulatory disclaimers.

2. Interactive HTML Report:
   - Responsive web report embedding dynamic Plotly visualizations.
   - Dual compilation modes: Lightweight CDN mode (~15-20 KB) loading Plotly.js from `cdn.plot.ly`, and Offline mode bundling full JavaScript assets for offline corporate environments.

3. Cleaned OHLCV CSV Export:
   - Normalized time-series containing validated market data.
   - Includes explicit `Is_Synthetic` column flag ensuring dataset provenance is retained when opened in external spreadsheet tools.

4. Comprehensive Analytical CSV Export:
   - Full time-series containing all computed indicators: SMA 20, SMA 50, EMA 20, Daily Returns, Cumulative Returns, Rolling Volatility (21-day and 63-day), High-Low Spread, and MDD.

5. Insights Summary CSV Export:
   - Structured tabular export of all automated qualitative findings, complete with category classifications, sentiment tags, and numerical evidence dictionaries.

---

## 9. Screenshots and Visual Interface

The application interface is structured for high contrast and visual clarity using a dark financial theme.

```text
[Dashboard Overview]
images/dashboard/dashboard_overview.png

[Interactive Candlestick and Technical Indicators]
images/dashboard/candlestick_chart.png

[Returns Distribution and Drawdown Analysis]
images/dashboard/returns_and_risk.png

[Structured Insights and Interpretation View]
images/dashboard/insights_view.png

[Multi-Format Report Download Manager]
images/reports/report_downloads.png
```

*Note: Visual image files will be added to the repository by the author during final portfolio presentation. The directory structure and relative link targets are pre-configured in `images/dashboard/` and `images/reports/`.*

---

## 10. Automated Testing

The codebase maintains a 100% test pass rate verified through Pytest. The test suite isolates external network dependencies through mocking, verifies data-cleaning invariants, validates indicator formulas against closed-form mathematical calculations, and inspects PDF compilation structures.

### Running the Test Suite

Execute the complete test suite from the project root:

```cmd
pytest -q
```

### Verified Test Inventory (268 Passing Tests)

```text
tests/test_cleaner.py .....................                              [ 7%]
tests/test_dashboard.py ........................................         [22%]
tests/test_eda.py ........................                               [31%]
tests/test_fetcher.py ..........                                         [35%]
tests/test_indicators.py ...................                             [42%]
tests/test_insights.py .................................                 [54%]
tests/test_integration.py .                                              [55%]
tests/test_interactive_charts.py ..................                      [61%]
tests/test_loader.py .........                                           [65%]
tests/test_reporting.py .........................................        [80%]
tests/test_returns.py ...............                                    [86%]
tests/test_risk.py ...................                                   [93%]
tests/test_static_charts.py ..................                           [100%]

======================= 268 passed in 95.50s (0:01:35) ========================
```

---

## 11. Limitations and Disclaimer

1. Educational and Analytical Purpose Only: This software is designed exclusively for educational, quantitative research, and portfolio demonstration purposes. It does not constitute financial, investment, tax, or legal advice.
2. External Market Data Reliance: Live market data is fetched through the third-party `yfinance` library. Data availability, rate limits, dividend adjustment methods, and historical depth are subject to external provider uptime and Yahoo Finance terms of service.
3. No Predictive Guarantees: Moving averages, volatility models, and historical drawdowns are backward-looking descriptive metrics. Past performance and historical statistical patterns are not predictive of future equity returns.
4. Participant Anonymity: Market turnover analysis cannot distinguish retail trader activity from institutional flow. All volume findings describe aggregate turnover without participant attribution.
5. Synthetic Sample Data: The bundled sample dataset (`data/sample/sample_stock.csv`) consists of synthetically generated equity prices intended solely for offline testing, code validation, and unit test execution.

---

## 12. Author and License

Author: Akash Das  
Project: Stock Market Data Analyzer  
License: This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for complete terms and conditions.
