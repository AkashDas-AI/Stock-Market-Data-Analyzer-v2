# Project Architecture: Stock Market Data Analyzer

**Project Author:** Akash Das  
**Architecture Version:** Phase 2 Scaffold  

## 1. High-Level Modular Design
The project is built around a clear separation of concerns, ensuring each package owns a single responsibility:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Streamlit Web App (app/)                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                  Stock Analyzer Core (src/stock_analyzer)              │
│                                                                        │
│   ┌─────────────────┐  ┌───────────────────┐  ┌────────────────────┐   │
│   │      Data       │  │     Analysis      │  │   Visualization    │   │
│   │ (fetch, load,   │─►│ (eda, indicators, │─►│ (static &          │   │
│   │  clean)         │  │  returns, risk,   │  │  interactive)      │   │
│   │                 │  │  insights)        │  │                    │   │
│   └─────────────────┘  └───────────────────┘  └────────────────────┘   │
│                                    │                                   │
│                        ┌───────────▼───────────┐                       │
│                        │       Reporting       │                       │
│                        │   (report_generator)  │                       │
│                        └───────────────────────┘                       │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Subsystem Responsibilities

### 2.1 Data Subsystem (`src/stock_analyzer/data/`)
- `fetcher.py`: Manages network requests to Yahoo Finance via `yfinance` with parameter validation.
- `loader.py`: Handles local file reads for synthetic datasets and user-supplied CSV files.
- `cleaner.py`: Enforces data integrity (OHLC bounds, deduplication, datetime index ordering).

### 2.2 Analysis Subsystem (`src/stock_analyzer/analysis/`)
- `eda.py`: Computes statistical summaries and correlation structures.
- `indicators.py`: Calculates technical trend indicators (SMA 20, SMA 50, EMA 20).
- `returns.py`: Computes daily percentage returns and cumulative performance.
- `risk.py`: Computes annualized standard deviation and maximum drawdown metrics.
- `insights.py`: Translates numerical outputs into plain-language bullet points.

### 2.3 Visualization Subsystem (`src/stock_analyzer/visualization/`)
- `static_charts.py`: Generates Matplotlib and Seaborn figures for reports and offline export.
- `interactive_charts.py`: Generates interactive Plotly candlestick and overlay charts for the web app.

### 2.4 Reporting Subsystem (`src/stock_analyzer/reporting/`)
- `report_generator.py`: Assembles metrics, figures, and interpretation into formatted reports.

### 2.5 Utilities & Configuration (`src/stock_analyzer/utils/`)
- `config.py`: Central repository paths, default asset tickers, and analysis parameters.
- `validators.py`: Input assertions for DataFrame schemas and price constraints.

---

## 3. Data Ingestion Architecture & Usage Guide (Phase 3)

### 3.1 Yahoo Finance Ingestion (`fetcher.py`)
- **Primary Class**: `StockDataFetcher(ticker: str)`
- **Convenience Function**: `fetch_stock_data(ticker, start_date, end_date, interval="1d", period=None)`
- **Key Behavior**:
  - `auto_adjust=False` is set explicitly, preserving unadjusted OHLC prices and maintaining `Adj Close` as a distinct series.
  - **MultiIndex Normalization**: Safely handles multi-level column indexes produced by `yfinance`, flattening to the target ticker without risk of cross-ticker column bleeding.
  - **Date Normalization**: Resets index to extract `Date` as a first-class column, removes timezones, and converts to standard `datetime64[ns]`.
- **Date-Range Semantics**:
  - The `end_date` parameter in Yahoo Finance is **exclusive** (data returned is strictly $< \text{end\_date}$).
  - *Example*: To analyze trading days through `2026-01-10`, specify `end_date="2026-01-11"`.
- **Provider Limitations & Terms**:
  - Availability is subject to Yahoo Finance Terms of Service, server rate limits, and network latency. Data is intended for informational/analytical use.
- **Error Conditions**:
  - `ValueError`: Empty or whitespace-only ticker.
  - `InvalidDateRangeError`: Start date $\ge$ end date, or invalid date string.
  - `EmptyDataError`: Ticker delisted, invalid symbol, or no market transactions in the window.
  - `DataFetchError`: Network connectivity failure or API response format change.

### 3.2 CSV Ingestion (`loader.py`)
- **Primary Class**: `StockDataLoader(file_path: Union[str, Path])`
- **Convenience Functions**: `load_stock_csv(path)`, `load_sample_stock_data()`
- **Expected CSV Format**:
  - Mandatory columns: `Date`, `Open`, `High`, `Low`, `Close`, `Volume`.
  - Optional column: `Adj Close`.
  - Flexible column aliases supported: `date`/`datetime`/`timestamp`, `OPEN`/`open`, `adj_close`/`adjusted close`, `vol`/`volume`.
- **Integrity & Boundary Rules**:
  - Does NOT silently impute missing values, drop duplicate rows, or alter source values (cleaning belongs strictly to Phase 4).
  - Never silently substitutes fallback or synthetic data if a user-supplied CSV fails.
- **Error Conditions**:
  - `DataLoadingError`: File does not exist or cannot be read.
  - `EmptyDataError`: File is completely empty (0 bytes or 0 data rows).
  - `MissingColumnError`: File lacks one or more required OHLCV columns.
  - `InvalidDateError`: Date strings cannot be parsed into valid timestamps.

### 3.3 Synthetic Development Sample vs Real Market Data
- **Real Market Data**: Fetched from Yahoo Finance or loaded from user CSVs; marked with `df.attrs["is_synthetic"] = False`.
- **Synthetic Sample** (`data/sample/sample_stock.csv`):
  - Fixed 75-observation deterministic dataset created in Phase 2.
  - Marked with `df.attrs["is_synthetic"] = True` and explicit source description.
  - Serves exclusively as an offline development baseline, unit testing fixture, and fallback when network access is unavailable.
  - Must never be represented as actual historical market observations.

---

## 4. Data Cleaning Pipeline & Validation Protocols (Phase 4)

### 4.1 Cleaning Workflow
The `StockDataCleaner` in `src/stock_analyzer/data/cleaner.py` enforces a deterministic 8-step pipeline:
1. **Defensive Copying**: Creates an isolated deep copy of the raw DataFrame so the input series remains immutable.
2. **Mandatory Schema Assertion**: Validates that all 6 required fields (`Date`, `Open`, `High`, `Low`, `Close`, `Volume`) are present.
3. **Date Normalization**: Parses dates into `datetime64[ns]`, localizes/strips timezones to naive UTC, and removes rows with unparseable timestamps.
4. **Duplicate Record Resolution (Exact vs Conflicting)**:
   - **Exact Duplicates**: Rows sharing the exact same timestamp and identical values across all features are safely deduplicated (retaining one instance) and counted under `exact_duplicates_count`.
   - **Conflicting Duplicates**: Rows sharing the same timestamp but possessing differing price or volume values.
   - **Safe Default (`conflict_policy='reject'`)**: Automatically rejects conflicting records by raising `DataValidationError`, preventing silent corruption of time-series continuity.
   - **Explicit Resolution Policies**:
     - `keep_last`: Deterministically preserves the latest duplicate record, logging the resolution.
     - `keep_first`: Deterministically preserves the initial duplicate record, logging the resolution.
     - `retain`: Retains all conflicting records for manual inspection while marking `is_valid=False` and recording warnings.
5. **Numeric Typing & Missing Value Strategy**:
   - Converts price and volume fields to numeric types.
   - Detects and tallies missing values on a per-column basis.
   - Removes rows missing mandatory OHLCV values (no blind interpolation or synthetic price filling).
   - Keeps optional `Adj Close` missing values separate: rows are retained, and informational warnings are logged.
6. **Price & Volume Boundary Checks**: Enforces strictly positive prices ($P > 0$) and non-negative volume ($V \ge 0$).
7. **OHLC Internal Consistency**:
   $$\text{High} \ge \max(\text{Open}, \text{Close}), \quad \text{Low} \le \min(\text{Open}, \text{Close}), \quad \text{High} \ge \text{Low}$$
   Removes rows violating internal price logic and logs specific counts.
8. **Chronological Ordering**: Sorts observations ascending by `Date` and resets the DataFrame index.

### 4.2 Cleaning Report Architecture
The pipeline returns a `CleaningResult(data, report)` containing a structured `CleaningReport` with:
- `original_row_count` and `final_row_count`.
- `missing_values_by_column` (mapping each column to its missing count).
- `exact_duplicates_count` (identical rows across all fields).
- `conflicting_duplicates_count` (differing values on same timestamp).
- `duplicate_dates_count` (aggregate duplicates resolved/tracked).
- `conflict_policy` (effective policy applied: `'reject'`, `'retain'`, `'keep_last'`, or `'keep_first'`).
- `invalid_records_count` (OHLC boundary violations).
- `records_removed` (total dropped rows) and `removal_reasons` breakdown.
- `warnings` (detailed human-readable explanations).
- `is_valid` boolean flag.

### 4.3 Data Layer Storage Responsibilities
- `data/raw/`: Read-only storage for original datasets acquired via Yahoo Finance or uploaded by users. Never altered.
- `data/interim/`: Scratch space for intermediate transformations when multi-step processing is needed.
- `data/processed/`: Verified, schema-enforced, and chronologically sorted datasets ready for downstream analysis (EDA, indicators, returns, risk). Exported via `save_processed_data()`.

---

## 5. Exploratory Data Analysis Architecture (Phase 5)

### 5.1 Analytical Scope & Boundaries
The Exploratory Data Analysis module (`src/stock_analyzer/analysis/eda.py`) provides statistical profiling, distribution analysis, and correlation evaluation for cleaned stock datasets.
In accordance with the 12-phase permanent roadmap, Phase 5 enforces strict descriptive boundaries:
- **Scope Included**: Descriptive statistics, quartiles, IQR, custom percentiles, intraday price spread dynamics, volume dispersion, Pearson correlation matrices, and static Matplotlib/Seaborn exploratory figures.
- **Strict Scope Exclusions**:
  - No moving averages or technical indicators (Phase 6).
  - No daily or cumulative returns, volatility, or drawdown modeling (Phase 7).
  - No interactive Plotly visualization components (Phase 8).
  - No Streamlit UI dashboard features (Phase 9).
  - No automated investment advice or ML predictions (Phases 10–12).

### 5.2 Core Components & API Structure
- **Primary Class**: `ExploratoryDataAnalyzer(df: pd.DataFrame, ticker: Optional[str] = None)`
  - Enforces DataFrame schema validation (`Date`, `Open`, `High`, `Low`, `Close`, `Volume`).
  - Creates a defensive deep copy of the raw DataFrame ensuring caller immutability.
  - Automatically identifies and handles numeric features, including optional `Adj Close`.
  - Tags and transparently highlights synthetic development datasets (`is_synthetic` flag).
- **Core Methods**:
  - `compute_summary_statistics(percentiles=None) -> pd.DataFrame`: Calculates count, mean, sample standard deviation ($ddof=1$), minimum, 25% (Q1), 50% (median, Q2), 75% (Q3), maximum, Interquartile Range ($IQR = Q3 - Q1$), and arbitrary percentiles.
  - `compute_price_and_volume_summary() -> Dict[str, Any]`: Computes intraday high-low spreads ($High - Low$), percentage spread relative to close ($Spread / Close \times 100$), period extremes (historical high/low dates and values, overall range ratio), volume metrics, and linear price-volume correlation.
  - `compute_correlations(method="pearson") -> pd.DataFrame`: Computes symmetric, labelled correlation matrices across numeric features with pairwise-complete observation handling.
- **Exploratory Visualizations** (Matplotlib & Seaborn):
  - `plot_price_distribution(column="Close", bins=30, output_path=None)`: Histogram with KDE and mean/median reference lines.
  - `plot_volume_distribution(bins=30, output_path=None)`: Volume histogram with KDE and central tendency indicators.
  - `plot_ohlc_distributions(output_path=None)`: Comparative boxplots across Open, High, Low, Close, and Adj Close to evaluate dispersion and outliers.
  - `plot_correlation_heatmap(output_path=None, annot=True)`: Annotated heatmap displaying Pearson correlation coefficients.
  - `plot_high_low_spread(output_path=None)`: Dual-panel figure showing daily spread time-series trajectory and spread frequency distribution.
- **Convenience Functions**: Module-level functional wrappers (`generate_summary_statistics`, `compute_correlation_matrix`, `generate_eda_summary`, `plot_price_distribution`, etc.) for direct script execution.

### 5.3 Correlation Methodology & Interpretive Limitations
- Evaluates linear association between numerical OHLCV series.
- While price variables (`Open`, `High`, `Low`, `Close`) display strong co-movement ($r > 0.95$), the analyzer and documentation explicitly reinforce that **correlation does not imply causation**.
- Handles missing observations transparently on a pairwise basis.

### 5.4 Visualization Output Routing
- All exploratory visualizations route to `outputs/charts/` when saved.
- Chart titles explicitly display ticker identity, date intervals, and prominent `[SYNTHETIC DATA]` disclaimers when operating on sample datasets.

---

## 6. Technical Indicators Architecture (Phase 6)

### 6.1 Moving Average Formulas and Calculation Conventions
The `TechnicalIndicators` engine in `src/stock_analyzer/analysis/indicators.py` provides deterministic implementations of foundational trend-following averages:

1. **Simple Moving Average (SMA 20)**:
   $$\text{SMA}_{20, t} = \frac{1}{20} \sum_{i=0}^{19} P_{t-i}$$
   - Window: 20 observations, `min_periods=20`.
   - Equal weight ($5\%$) assigned to each price in the lookback window.
   - Warm-up period: Observations 0 through 18 contain `NaN`. Observation index 19 (the 20th row) yields the first valid value.

2. **Simple Moving Average (SMA 50)**:
   $$\text{SMA}_{50, t} = \frac{1}{50} \sum_{i=0}^{49} P_{t-i}$$
   - Window: 50 observations, `min_periods=50`.
   - Equal weight ($2\%$) assigned to each price in the lookback window.
   - Warm-up period: Observations 0 through 48 contain `NaN`. Observation index 49 (the 50th row) yields the first valid value.

3. **Exponential Moving Average (EMA 20)**:
   $$\alpha = \frac{2}{\text{span} + 1} = \frac{2}{21} \approx 0.095238$$
   $$\text{EMA}_{20, t} = \alpha P_t + (1 - \alpha) \text{EMA}_{20, t-1}$$
   - Calculated via Pandas EWM: `span=20, adjust=False, min_periods=20`.
   - Applies recursive exponential decay weighting, making it significantly more sensitive to recent price action than SMA 20.
   - Warm-up period: Observations 0 through 18 contain `NaN`. No artificial backfill or fabricated prices are used for initialization.

### 6.2 Data Integrity, Immutability & Chronological Sorting
- **Defensive Immutability**: The input DataFrame is never modified. An isolated deep copy is created upon instantiation.
- **Chronological Sequencing**: Checks for `"Date"` column presence and enforces strict ascending chronological order prior to rolling calculations, preserving original column data types.
- **Price Column Selection**: Defaults to `"Close"`, with full support for user-specified numeric price columns (e.g. `"Adj Close"`). Non-numeric price series are rejected with `DataValidationError`.
- **Output Structure**: Appends `SMA_20`, `SMA_50`, and `EMA_20` as new columns while strictly preserving all original data fields and observation metadata.

### 6.3 Test Suite Warning Diagnostics and Upstream Deprecation Handling
During the Phase 5 test run, 12 warnings were recorded:
- **Root Cause**: Seaborn 0.13.2 internally invokes Matplotlib's `ax.bxp(**boxplot_kws)` with the keyword argument `vert=True`. Matplotlib 3.11.2 deprecated `vert` in favor of `orientation={'vertical', 'horizontal'}`. Additionally, Seaborn's matrix heatmap module invokes `self.cmap.set_bad(bad)`, which Matplotlib marked with `PendingDeprecationWarning` in favor of `cmap.with_extremes(bad=...)`.
- **Resolution**: Configured precise warning filters in `pytest.ini` targeting the specific internal Seaborn/Matplotlib deprecation notices (`matplotlib.MatplotlibDeprecationWarning` and `PendingDeprecationWarning`), eliminating test noise while maintaining strict warning detection for project-owned code.

### 6.4 Architectural Boundaries
- Strictly restricted to technical indicator calculation.
- Does NOT implement trading signals, crossover buy/sell rules, return/volatility modeling (Phase 7), interactive Plotly figures (Phase 8), or Streamlit dashboard components (Phase 9).

---

## 7. Performance & Risk Analytics Architecture (Phase 7)

### 7.1 Daily Returns Calculation & Conventions
The `ReturnAnalyzer` in `src/stock_analyzer/analysis/returns.py` computes discrete percentage returns:
$$R_t = \frac{P_t - P_{t-1}}{P_{t-1}} = \frac{P_t}{P_{t-1}} - 1$$
- **Missing Value Convention**: The initial return at $t=0$ is strictly preserved as `NaN` because no preceding price observation exists. Missing returns are never imputed with zero.
- **Price Validation**: Requires strictly numeric price inputs ($P > 0$) and asserts forward chronological ordering ascending by date.
- **Output Column**: Appended as `Daily_Return` in `add_return_metrics()`.

### 7.2 Cumulative Compound Returns & Wealth Trajectory
- **Compound Multiplicative Growth**:
  $$\text{Wealth}_t = \prod_{i=1}^t (1 + R_i), \quad \text{Cumulative Return}_t = \text{Wealth}_t - 1$$
- **Distinction from Cumulative Sum**: Realized compound growth is multiplicative. Summing daily percentage returns produces arithmetic distortions and is mathematically invalid for multi-period compounding.
- **Initial Observation**: Preserves missing return behavior at $t=0$ as `NaN` (or wealth baseline $W_0 = 1.0$ in wealth index representations).
- **Output Column**: Appended as `Cumulative_Return` in `add_return_metrics()`.

### 7.3 Volatility Profiling, Annualization & Rolling Volatility
The `RiskAnalyzer` in `src/stock_analyzer/analysis/risk.py` measures dispersion of returns:
- **Sample Standard Deviation**:
  $$\sigma_{\text{daily}} = \sqrt{\frac{1}{N - 1} \sum_{t=1}^N (R_t - \bar{R})^2} \quad (\text{ddof}=1)$$
- **Annualization Formula**:
  $$\sigma_{\text{annual}} = \sigma_{\text{daily}} \times \sqrt{\text{annualization\_factor}}$$
  - Default scaling factor: $N = 252$ trading days per year for equity markets (configurable, e.g. 365 for crypto/continuous markets).
  - Assumes returns are independently and identically distributed (i.i.d.) over time.
- **Rolling Annualized Volatility**:
  $$\sigma_{\text{rolling}, t} = \text{std}(R_{t-w+1:t}, \text{ddof}=1) \times \sqrt{\text{annualization\_factor}}$$
  Implemented centrally in `RiskAnalyzer.calculate_rolling_volatility(window=w)`. Lookback warm-up periods (indices $0$ to $w-1$) contain `NaN`. Shared directly by both static and interactive visualization engines (defaulting to 21-day and 63-day lookback windows).
- **Sample Size Safeguards**: If valid non-null returns $N \le \text{ddof}$, volatility returns `np.nan` rather than raising uncaught zero-division errors.

### 7.4 Drawdown Series & Maximum Drawdown (MDD)
- **High-Water Mark (HWM)**:
  $$\text{HWM}_t = \max_{0 \le s \le t} \text{Wealth}_s$$
- **Drawdown Series**:
  $$\text{Drawdown}_t = \frac{\text{Wealth}_t}{\text{HWM}_t} - 1.0$$
  Bounded as $\text{Drawdown}_t \le 0.0$ at all times ($0.0$ indicates an all-time high).
- **Maximum Drawdown (MDD)**:
  $$\text{MDD} = \min_{t} \text{Drawdown}_t$$
  Returns exact peak and trough dates:
  $$t_{\text{trough}} = \text{argmin}_t \text{Drawdown}_t, \quad t_{\text{peak}} = \text{argmax}_{0 \le s \le t_{\text{trough}}} \text{Wealth}_s$$
- Supported data inputs: Accepts either a `pd.DataFrame` (with price column) or a `pd.Series` (returns or prices with optional date series).

### 7.5 Architectural Boundaries
- Performance profiling and risk metrics only.
- Does NOT implement automated investment recommendations, trading signals, Plotly interactive candlestick plots (Phase 8), or Streamlit UI components (Phase 9).

---

## 8. Data Visualization Architecture (Phase 8)

### 8.1 Dual-Engine Architecture (Static & Interactive)
The visualization layer (`src/stock_analyzer/visualization/`) provides a dual-engine architecture separating publication-grade static figures from web-ready interactive figures:
- **Static Engine (`static_charts.py`)**: Built on Matplotlib and Seaborn. Produces high-resolution raster images (PNG, 300 DPI) suitable for analytical reports, documentation, and archival.
- **Interactive Engine (`interactive_charts.py`)**: Built on Plotly (`plotly.graph_objects` and `plotly.subplots`). Produces dynamic figures with hover tooltips, range sliders, multi-period selectors, and standalone HTML export capability.

### 8.2 Comprehensive Chart Catalog
The visualization subpackage implements 10 static charts and 8 interactive chart types:

| Category | Chart Type | Static Engine (`static_charts.py`) | Interactive Engine (`interactive_charts.py`) |
| :--- | :--- | :--- | :--- |
| **Price & OHLC** | Closing Price Series | `plot_closing_price()` | `create_moving_averages_chart()` |
| **Price & OHLC** | OHLC Candlestick | `plot_ohlc_bars()` | `create_candlestick_chart()` |
| **Trend Indicators** | Moving Average Comparison | `plot_moving_averages()` | `create_moving_averages_chart()` |
| **Market Activity** | Trading Volume | `plot_trading_volume()` | `create_volume_chart()` |
| **Performance** | Daily Returns Time Series | `plot_daily_returns_time_series()` | `create_daily_returns_chart()` |
| **Performance** | Daily Returns Distribution | `plot_daily_returns_distribution()` | — |
| **Performance** | Cumulative Growth Trajectory | `plot_cumulative_returns()` | `create_cumulative_returns_chart()` |
| **Risk & Volatility** | Underwater Drawdown | `plot_drawdown()` | `create_drawdown_chart()` |
| **Risk & Volatility** | Rolling Annualized Volatility | `plot_rolling_volatility()` | `create_rolling_volatility_chart()` |
| **Correlation** | Feature Correlation Heatmap | `plot_correlation_heatmap()` | `create_correlation_heatmap()` |

### 8.3 Integration with Analytical Layers
Visualization modules directly reuse calculation pipelines from earlier phases:
- `analysis.eda.ExploratoryDataAnalyzer`: for feature correlation structures.
- `analysis.indicators.TechnicalIndicators`: for automated calculation of `SMA_20`, `SMA_50`, and `EMA_20` when missing from input DataFrames.
- `analysis.returns.ReturnAnalyzer`: for computing daily percentage changes and compound cumulative returns.
- `analysis.risk.RiskAnalyzer`: for drawdown series, MDD peak/trough identification, and rolling annualized volatility.
Financial formulas are never duplicated within visualization functions.

### 8.4 Chart Organization & Export Formats
- Target Directory: `outputs/charts/`
- **Static Export**: PNG at 300 DPI with tight bounding boxes (`bbox_inches="tight"`).
- **Interactive Export**: Standalone full HTML loading Plotly JavaScript dynamically via external CDN (`include_plotlyjs="cdn"`). This achieves minimal file footprint (~15–20 KB per figure) and operates independently of the Python runtime or Streamlit sessions, while requiring network access in the client browser to load the Plotly JS engine from `cdn.plot.ly` (does not embed the library inline for offline rendering).
- **Naming Convention**: Ticker symbol prefix + descriptive chart identifier (e.g. `AAPL_candlestick_interactive.html`, `AAPL_drawdown.png`).

### 8.5 Architectural Boundaries
- Strictly limited to charting functions and standalone export.
- Does NOT implement Streamlit UI pages or widget controls (Phase 9).
- Does NOT generate automated insight narratives (Phase 10) or PDF/HTML reports (Phase 11).

---

## 9. Streamlit Dashboard Architecture (Phase 9)

### 9.1 Modular Application Layout
The dashboard layer is organized under `app/` with clean separation of concerns:
- **`app/dashboard.py`**: Web application entry point. Configures page layout, styling, application header, error handling, synthetic data warning alerts, and coordinates component workflows.
- **`app/sidebar.py`**: User configuration sidebar. Captures data source choice, ticker symbol, date boundaries, file uploads, technical indicator toggles (SMA 20, SMA 50, EMA 20), shared volume toggles, and rolling volatility window multiselect. Encapsulated in the `DashboardParameters` dataclass.
- **`app/data_manager.py`**: Ingestion and caching layer. Manages live Yahoo Finance retrieval (`@st.cache_data(ttl=300)`), CSV uploads, and cached sample dataset loading (`load_cached_sample_data`). Executes automated cleaning and validation via `StockDataCleaner`. Enforces deep copy immutability and attaches metadata attributes (`ticker`, `is_synthetic`, `cleaning_report`).
- **`app/kpis.py`**: Overview metric cards. Displays latest close price with period delta, period start price, cumulative compound return, annualized volatility, maximum drawdown with trough date, and active trading session counts across a 6-column layout.
- **`app/views.py`**: Tabulated analytical views embedding interactive Plotly visualizations:
  1. **Price & Technical Analysis**: Candlestick with volume subplot, moving averages overlay with dynamic indicator toggling, and trading volume history.
  2. **Returns & Risk Analysis**: Daily returns time series, daily returns distribution histogram with mean and $\pm 1\sigma$ markers, cumulative compound growth curve, underwater drawdown plot, and rolling annualized volatility across user-selected windows.
  3. **Data Preview & Statistics**: Summary statistics table (`compute_summary_statistics()`), Pearson correlation heatmap, cleaned data table preview, and downloadable CSV export.

### 9.2 Data Ingestion Options & Validation
1. **Live Yahoo Finance**: Validates ticker presence and chronological date boundaries (`start_date < end_date`). Gracefully catches `DataFetchError` without crashing or silently falling back to synthetic data.
2. **CSV Upload**: Verifies mandatory OHLCV schema, catches missing columns or parsing errors, and preserves uploaded records without synthetic fabrication.
3. **Sample Dataset (Synthetic)**: Loads `data/sample/sample_stock.csv` with explicit amber warning banner (`⚠️ SYNTHETIC SAMPLE DATA ACTIVE`) to prevent misinterpreting offline testing data as live market prices.

### 9.3 Launching the Application
Execute the following command from the repository root:
```bash
streamlit run app/dashboard.py
```

### 9.4 Architectural Boundaries
- Strictly restricted to dashboard visualization, user controls, and interactive analysis.
- Does NOT implement automated textual investment recommendations or pattern detection (Phase 10).
- Does NOT generate automated downloadable PDF/HTML summary reports (Phase 11).

---

## 10. Insights and Interpretation Architecture (Phase 10)

### 10.1 Primary Engine & Design Philosophy
Phase 10 introduces the dedicated interpretation layer in `src/stock_analyzer/analysis/insights.py`, centered on `StockInsightAnalyzer`.
- **Purpose**: Transform quantitative indicators, returns, and risk calculations into clear, deterministic, evidence-grounded observations.
- **Strict Boundary**: Purely descriptive and analytical. Never generates investment advice (buy/sell/hold), target price forecasts, or black-box predictive scores.

### 10.2 Structured Output Schema
Outputs are encapsulated in typed dataclasses:
- **`MarketInsight`**:
  - `category`: `InsightCategory` (Price Trend, Moving Averages, Returns Analysis, Risk & Volatility, Trading Volume, Correlation).
  - `title`: Short imperative headline (e.g. *Price vs SMA 20: Trading Above 1-Month Trend*).
  - `observation`: Human-readable narrative detailing the historical finding.
  - `evidence`: Dictionary of exact numerical parameters supporting the observation.
  - `severity`: `InsightSeverity` (`positive`, `negative`, `warning`, `info`, `neutral`).
  - `description`: Analytical methodology description.
  - `limitations`: Explicit statement of statistical or lookback constraints.
- **`InsightSummary`**: Comprehensive synthesis holding `positive_observations`, `negative_observations`, `risk_observations`, `data_limitations`, and complete `insights` collection.
- **`InsightThresholds`**: Configurable parameter class documenting all analytical benchmarks.

### 10.3 Insight Categories & Evaluated Metrics
1. **Price Trend Insights**:
   - Compares initial and latest closing prices over the observation window.
   - Evaluates absolute change ($\Delta P$), percentage change ($\Delta P / P_0$), and directional momentum.
2. **Moving Average Insights**:
   - Price positioning relative to SMA 20, SMA 50, and EMA 20.
   - Dual moving average relationship ($SMA_{20}$ vs $SMA_{50}$).
   - Handles warm-up NaN periods and truncations gracefully without fabrication.
   - Strict disclaimer: moving averages reflect historical smoothing and do not forecast trend endurance.
3. **Returns Analysis Insights**:
   - Compounded cumulative return $(1 + R_{cum}) = \prod (1 + R_t) - 1.0$ (never additive sums).
   - Session asymmetry and win/loss rates.
   - Single-day extremes (best session gain and worst session loss with exact dates).
4. **Risk & Volatility Insights**:
   - Realized annualized volatility ($\sigma_{annual} = \sigma_{daily} \times \sqrt{252}$).
   - Maximum Drawdown (MDD) with high-water-mark peak date and trough date.
   - Rolling volatility trends (21-day sliding window expanding vs compressing).
5. **Trading Volume Insights**:
   - Compares latest trading volume against a 20-day trailing baseline average.
   - Detects volume surges ($\ge 1.5\times$) or liquidity dry-ups ($\le 0.5\times$).
   - Explains that exchange volume indicates turnover but not buy/sell order imbalance.
6. **Correlation Insights**:
   - Intra-dataset feature linear co-movement (e.g. price vs volume).
   - Enforces the universal rule: *correlation measures co-dependence only and does not establish causation*.
7. **Overall Executive Summary**:
   - Synthesizes key positives, key negatives, risk characteristics, and data limitations directly from underlying insight evaluations without arbitrary numerical scores.

### 10.4 Interpretation Rules & Configured Thresholds
| Parameter | Default Value | Analytical Rationale |
| :--- | :---: | :--- |
| `volatility_low_threshold` | 0.15 (15%) | Subdued price dispersion typical of broad defensive/benchmark indices. |
| `volatility_high_threshold` | 0.30 (30%) | Elevated dispersion typical of high-beta or high-growth individual equities. |
| `drawdown_correction_threshold` | -0.10 (-10%) | Standard market correction boundary. |
| `drawdown_bear_threshold` | -0.20 (-20%) | Formal market bear territory threshold. |
| `volume_baseline_window` | 20 days | Approximately one calendar month of trading activity baseline. |
| `volume_surge_multiplier` | 1.5x | Significant trading turnover expansion indicating heightened market interest. |
| `volume_dryup_multiplier` | 0.5x | Subdued trading activity indicating reduced market participation. |
| `correlation_strong_threshold` | 0.70 | Standard statistical cutoff for strong linear co-dependence. |
| `correlation_moderate_threshold` | 0.40 | Cutoff for moderate linear co-dependence. |

### 10.5 Dashboard Integration
- Tab 4 added to `app/views.py`: **`💡 Insights & Interpretation`**.
- Displays an executive 2x2 grid (Key Positives, Key Negatives, Risk Characteristics, Data Limitations) followed by categorized expandable insight cards with supporting evidence badges and limitation captions.
- Retains high-contrast styling matching the dark dashboard theme.
- Dynamically updates whenever ticker, dates, or data sources change.

### 10.6 Architectural Boundaries
- Strictly limited to quantitative interpretation and insight synthesis.
- Report generation and analytical exports are encapsulated in Phase 11.
- Does NOT provide buy/sell signals, target price projections, or predictive machine learning models.

### 10.7 Analytical Audit & Statistical Methodology Refinement
Following the Phase 10 compliance audit, two analytical interpretations were refined to maintain strict methodological fidelity:
1. **Trading Volume Interpretation**:
   - Eliminated all unsupported institutional attribution ("institutional turnover surges", "institutional trading activity", "institutional participation").
   - Standard exchange OHLCV data reflects aggregate share turnover but does not identify participant classes (e.g. institutional vs retail) or order flow direction (buyer-initiated vs seller-initiated).
   - Replaced with evidence-based descriptions: "Elevated Trading Volume", "Higher-than-average trading activity", "Reduced Trading Volume", and "Increased market turnover", preserving the 20-day baseline window and 1.5x / 0.5x thresholds.
2. **Correlation Methodology & Limitations**:
   - **Evaluated Variables**: Direct reuse of EDA numerical correlation output comparing raw closing price levels (`Close`) and daily trading volume (`Volume`).
   - **Single-Asset Intra-Dataset Scope**: Evaluates contemporaneous feature co-movement within a single asset's historical observations; does not represent cross-asset portfolio diversification correlation.
   - **Non-Stationarity Limitations**: Raw asset prices frequently exhibit non-stationary trends, which can introduce spurious price-level correlation without true economic linkage.
   - **Non-Causation**: Empirical correlation indicates contemporaneous linear association only; it does not establish causation, infer directional order flow (buying or selling pressure), or provide lead-lag predictive capability.

---

## 11. Phase 11 — Report Generation & Analytical Export Architecture

### 11.1 Purpose and Scope
Phase 11 develops a dedicated, modular reporting engine independent of Streamlit UI rendering. It allows users to export all analytical outputs, technical charts, risk distributions, and Phase 10 qualitative insights into publication-quality PDF documents, responsive standalone HTML dossiers, and standardized machine-readable CSV datasets.

### 11.2 Package Structure
Located under `src/stock_analyzer/reporting/`:
```text
src/stock_analyzer/reporting/
├── __init__.py           # Package exports for StockReportGenerator, PDF, HTML, and CSV export functions
├── report_generator.py   # StockReportGenerator central orchestrator and batch archival pipeline
├── pdf_report.py         # Multi-page publication-quality PDF generator using ReportLab
├── html_report.py        # Responsive interactive HTML report generator using Plotly
└── data_export.py        # Standardized CSV exporters for OHLCV, analytical datasets, and insights
```

### 11.3 PDF Report Generation (`pdf_report.py`)
- **Technology Stack**: ReportLab 5.1.2 (pure Python, Python 3.11 compatible, zero external C-binary dependencies).
- **Two-Pass Numbered Canvas**: Implements `NumberedCanvas(canvas.Canvas)` to dynamically render running headers ("Stock Market Data Analyzer | Akash Das — {ticker} Report") and "Page X of Y" footers with timestamps across pages 2+.
- **Document Flow**:
  1. **Cover Page**: Title, author attribution, asset metadata block, generation timestamp, and prominent amber warning banner for synthetic data.
  2. **Executive Summary**: 4-quadrant structured grid (Key Positives, Key Negatives, Risk Observations, Data Limitations) and KPI overview table.
  3. **Dataset Profile**: Ingestion profile table with sample statistics, date ranges, and available OHLCV features.
  4. **Price & Technical Analysis**: High-resolution embedded Matplotlib chart showing Closing price with SMA 20, SMA 50, EMA 20, and volume subplot.
  5. **Financial Returns Analysis**: Geometric compound returns, daily win rate, max gain/loss metrics table, and embedded cumulative growth chart.
  6. **Risk & Volatility Analysis**: Daily and annualized volatility (252 sessions), maximum drawdown with peak/trough dates, and embedded underwater drawdown and rolling volatility charts.
  7. **Trading Volume & Turnover**: Volume ratio against 20-day baseline average and Phase 10 evidence-based turnover narrative (strictly zero institutional attribution).
  8. **Structured Insights**: Categorized insight cards with severity color-coding, observation text, evidence tags, and limitation callouts.
  9. **Regulatory Disclaimers**: Methodology, non-causation, non-stationarity, and non-financial advice regulatory disclaimers.

### 11.4 HTML Report Generation (`html_report.py`)
- **Interactive Visualization**: Direct embedding of interactive Plotly charts with hover tooltips, period selectors, and range sliders.
- **Dual Distribution Modes**:
  - **CDN Mode (`embed_plotly_js=False`)**: Lightweight (~120–150 KB) HTML file referencing `https://cdn.plot.ly/plotly-2.35.2.min.js`. Clearly labeled as CDN-dependent.
  - **Offline Standalone Mode (`embed_plotly_js=True`)**: Fully self-contained (~4.8 MB) HTML file embedding the entire Plotly JS library via `plotly.offline.get_plotlyjs()`. Works 100% offline with zero internet access.
- **Security**: Strict HTML escaping (`html.escape`) across all user-supplied metadata, ticker symbols, and observations to prevent XSS / unsafe injection.
- **Responsive Layout**: Sticky top navigation bar, 4-card executive summary grid, KPI metric cards, and categorized expandable insight cards.

### 11.5 Standardized CSV Data Exports (`data_export.py`)
- **Cleaned Base OHLCV Export**: Standardized date formatting (`YYYY-MM-DD`) and verified column headers.
- **Comprehensive Analytical Export**: Single unified dataset combining base OHLCV with `SMA_20`, `SMA_50`, `EMA_20`, `Daily_Return`, `Cumulative_Return`, `Drawdown`, `Rolling_Vol_21`, `Rolling_Vol_63`, ticker identifier, and synthetic data tagging (`Is_Synthetic`).
- **Structured Insights Export**: Tabular export containing `Ticker`, `Category`, `Title`, `Severity`, `Observation`, `Supporting_Evidence`, and `Limitations`.

### 11.6 Public Orchestrator (`report_generator.py`)
- **Class `StockReportGenerator`**: Unified public interface providing:
  - `generate_pdf_report(output_path=None) -> Union[str, bytes]`
  - `generate_html_report(output_path=None, embed_plotly_js=False) -> Union[str, bytes]`
  - `export_cleaned_csv(output_path=None) -> Union[str, bytes]`
  - `export_comprehensive_csv(output_path=None) -> Union[str, bytes]`
  - `export_insights_csv(output_path=None) -> Union[str, bytes]`
  - `generate_all_reports(output_dir="reports/generated", embed_plotly_js=False) -> Dict[str, str]`
- **Defensive Design**: Deep-copies input DataFrame ensuring complete caller immutability; validates required columns; sanitizes filenames against special characters.

### 11.7 Streamlit Dashboard Integration (`app/views.py`)
- Integrated as Tab 5: **`📑 Reports & Downloads`**.
- Provides real-time download buttons for PDF research reports, interactive HTML dossiers (with CDN/offline toggle), and analytical CSV exports.
- Includes a batch action button to generate and archive all 4 reporting artifacts locally to `reports/generated/`.
- Preserves all existing dashboard tabs, KPI metrics, dark theme styling, and headline visibility.




