# Module Reference & API Specification

**Project Author:** Akash Das  
**Package:** `stock_analyzer` (Core Engine) and `app` (Streamlit Web Application)  
**Language:** Python 3.11 with Complete Type Hints  

---

## 1. Package Structure

```text
src/
└── stock_analyzer/
    ├── __init__.py
    ├── data/
    │   ├── __init__.py
    │   ├── cleaner.py          # StockDataCleaner, CleaningResult, CleaningReport
    │   ├── exceptions.py       # Custom exception hierarchy
    │   ├── fetcher.py          # StockDataFetcher
    │   └── loader.py           # StockDataLoader
    ├── analysis/
    │   ├── __init__.py
    │   ├── eda.py              # ExploratoryDataAnalyzer
    │   ├── indicators.py       # TechnicalIndicators
    │   ├── insights.py         # StockInsightAnalyzer
    │   ├── returns.py          # ReturnAnalyzer
    │   └── risk.py             # RiskAnalyzer
    ├── visualization/
    │   ├── __init__.py
    │   ├── static_charts.py    # StaticChartGenerator
    │   └── interactive_charts.py # InteractiveChartGenerator
    ├── reporting/
    │   ├── __init__.py
    │   ├── data_export.py      # CSV export functions
    │   ├── html_report.py      # HTMLReportGenerator
    │   ├── pdf_report.py       # PDFReportGenerator
    │   └── report_generator.py # StockReportGenerator (Facade)
    └── utils/
        ├── __init__.py
        ├── config.py           # System constants & paths
        └── logger.py           # Logging configuration
app/
├── __init__.py
├── dashboard.py                # Main Streamlit bootstrap
├── sidebar.py                  # Dynamic UI parameters
├── data_manager.py             # Controller & caching
├── kpis.py                     # Financial KPI cards
└── views.py                    # 5-Tab workspace renderer
```

---

## 2. Core Package Specifications

### 2.1 `stock_analyzer.data`

#### `StockDataFetcher` (`fetcher.py`)
- **Constructor:** `StockDataFetcher(ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None)`
- **Methods:**
  - `fetch_data() -> pd.DataFrame`: Queries Yahoo Finance via `yfinance.download()`, normalizes column names, adjusts for inclusive end-date, and returns cleaned raw DataFrame.
  - `validate_parameters() -> bool`: Verifies ticker string and date format validity.

#### `StockDataLoader` (`loader.py`)
- **Constructor:** `StockDataLoader(file_path: Union[str, Path])`
- **Methods:**
  - `load_data() -> pd.DataFrame`: Reads CSV from disk, parses ISO 8601 timestamps, validates mandatory OHLCV columns, and returns base DataFrame.

#### `StockDataCleaner` (`cleaner.py`)
- **Constructor:** `StockDataCleaner(df: pd.DataFrame, duplicate_policy: Optional[str] = None, conflict_policy: str = "reject", drop_missing: bool = True)`
- **Methods:**
  - `clean() -> CleaningResult`: Executes complete cleaning pipeline: defensive copy, date sorting, deduplication under conflict policy, price invariant verification, positive price checks, and forward/backward filling of missing values. Returns `CleaningResult(data=DataFrame, report=CleaningReport)`.

---

### 2.2 `stock_analyzer.analysis`

#### `ExploratoryDataAnalyzer` (`eda.py`)
- **Constructor:** `ExploratoryDataAnalyzer(df: pd.DataFrame)`
- **Methods:**
  - `compute_summary_statistics() -> pd.DataFrame`: Calculates count, mean, sample std dev ($ddof=1$), min, 25%, median, 75%, max, IQR across numeric features.
  - `compute_correlations(method: str = "pearson") -> pd.DataFrame`: Returns pairwise Pearson correlation matrix.
  - `compute_price_and_volume_summary() -> Dict[str, Any]`: Computes daily spreads, range ratios, and price-volume correlations.

#### `TechnicalIndicators` (`indicators.py`)
- **Constructor:** `TechnicalIndicators(df: pd.DataFrame)`
- **Methods:**
  - `calculate_sma(window: int = 20) -> pd.Series`: Computes unweighted rolling moving average over $N$ sessions.
  - `calculate_ema(window: int = 20) -> pd.Series`: Computes exponential moving average with smoothing multiplier $\alpha = \frac{2}{N+1}$ and `adjust=False`.

#### `ReturnAnalyzer` (`returns.py`)
- **Constructor:** `ReturnAnalyzer(df: pd.DataFrame)`
- **Methods:**
  - `calculate_daily_returns() -> pd.Series`: Computes 1-day percentage price change. First observation is `NaN`.
  - `calculate_cumulative_returns() -> pd.Series`: Computes geometrically compounded wealth trajectory: $\prod(1 + R) - 1$.

#### `RiskAnalyzer` (`risk.py`)
- **Constructor:** `RiskAnalyzer(df: pd.DataFrame)`
- **Methods:**
  - `calculate_annualized_volatility(annualization_factor: int = 252) -> float`: Computes sample standard deviation ($ddof=1$) scaled by $\sqrt{252}$.
  - `calculate_rolling_volatility(window: int = 21, annualization_factor: int = 252) -> pd.Series`: Computes sliding-window annualized volatility.
  - `calculate_drawdown_series() -> pd.Series`: Computes rolling percentage decline from running peak.
  - `calculate_max_drawdown() -> Dict[str, Any]`: Returns maximum drawdown depth, peak date, trough date, and duration.

#### `StockInsightAnalyzer` (`insights.py`)
- **Constructor:** `StockInsightAnalyzer(df: pd.DataFrame, ticker: Optional[str] = "STOCK")`
- **Methods:**
  - `generate_all_insights() -> List[MarketInsight]`: Generates structured findings across Price Trend, Volatility, Risk, Volume, and Correlation.
  - `generate_summary() -> InsightSummary`: Categorizes findings into positive observations, negative observations, risk alerts, and data limitations.

---

### 2.3 `stock_analyzer.visualization`

#### `StaticChartGenerator` (`static_charts.py`)
- **Constructor:** `StaticChartGenerator(df: pd.DataFrame, ticker: Optional[str] = "STOCK")`
- **Methods:**
  - `plot_moving_averages(...) -> plt.Figure`: Generates 300 DPI Matplotlib plot of Close vs SMA 20, SMA 50, EMA 20.
  - `plot_daily_returns(...) -> plt.Figure`: Generates bar chart of daily returns with $\pm 2\sigma$ threshold lines.
  - `plot_cumulative_returns(...) -> plt.Figure`: Dual-panel plot of cumulative growth and underwater drawdowns.
  - `plot_rolling_volatility(...) -> plt.Figure`: Multi-line plot of 21-day and 63-day rolling volatility.

#### `InteractiveChartGenerator` (`interactive_charts.py`)
- **Constructor:** `InteractiveChartGenerator(df: pd.DataFrame, ticker: Optional[str] = "STOCK")`
- **Methods:**
  - `plot_candlestick_with_volume(...) -> go.Figure`: Interactive Plotly candlestick with shared volume subplot, range sliders, and period buttons.
  - `plot_daily_returns_distribution(...) -> go.Figure`: Interactive daily returns bar chart.
  - `plot_cumulative_and_drawdown(...) -> go.Figure`: Dual-panel interactive wealth growth vs drawdown.
  - `plot_rolling_volatility(...) -> go.Figure`: Interactive multi-window rolling volatility comparison.

---

### 2.4 `stock_analyzer.reporting`

#### `PDFReportGenerator` (`pdf_report.py`)
- **Constructor:** `PDFReportGenerator(df: pd.DataFrame, ticker: str, data_source: str, is_synthetic: bool, author: str)`
- **Methods:**
  - `generate(output_path: Optional[Union[str, Path]]) -> Union[str, bytes]`: Builds complete multi-page vector PDF report (10–11 pages; 11 pages for synthetic dataset configurations) using ReportLab `SimpleDocTemplate` and two-pass `NumberedCanvas`.

#### `HTMLReportGenerator` (`html_report.py`)
- **Constructor:** `HTMLReportGenerator(df: pd.DataFrame, ticker: str, data_source: str, is_synthetic: bool, author: str)`
- **Methods:**
  - `generate(output_path: Optional[Union[str, Path]], embed_plotly_js: bool) -> Union[str, bytes]`: Generates standalone responsive HTML report with CDN or full offline embedded bundle modes.

#### `StockReportGenerator` (`report_generator.py`)
- **Constructor:** `StockReportGenerator(df: pd.DataFrame, ticker: str, data_source: str, is_synthetic: bool, author: str)`
- **Methods:**
  - `generate_all_reports(output_dir: str) -> Dict[str, str]`: Coordinates simultaneous generation of PDF, HTML, Cleaned CSV, Comprehensive CSV, and Insights CSV.
  - `export_cleaned_csv() -> bytes`: Exports base OHLCV with `Is_Synthetic` indicator.
  - `export_comprehensive_csv() -> bytes`: Exports 16-column analytical dataset.
  - `export_insights_csv() -> bytes`: Exports 9-column qualitative findings summary.

---

### 2.5 `app` (Streamlit Subsystem)

- **`dashboard.py`**: Configures Streamlit page wide layout, injects high-contrast custom CSS, orchestrates controllers.
- **`sidebar.py`**: Manages user input widgets and returns typed `DashboardParameters` dataclass.
- **`data_manager.py`**: Mediates between UI parameters and data fetching. Applies `@st.cache_data`.
- **`kpis.py`**: Renders 6 executive metric cards with clean color-coded percentage badges.
- **`views.py`**: Implements the 5-tab reactive interface and report download controls.
