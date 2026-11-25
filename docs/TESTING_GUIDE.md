# Testing Guide & Quality Assurance Manual

**Project Author:** Akash Das  
**Current Test Baseline:** 268 Passed | 0 Failed | 0 Errors | 0 Warnings  
**Test Framework:** Pytest 9.2+, Python 3.11  

---

## 1. Testing Philosophy & Architecture

The **Stock Market Data Analyzer** adheres to an institutional test-driven development (TDD) and regression methodology. The test suite guarantees:
- **Zero Flakiness:** External network calls (such as Yahoo Finance API queries) are deterministically mocked in unit tests, ensuring runs execute offline without internet dependency.
- **Defensive Immutability:** Analytical functions and generators are asserted to never mutate caller DataFrames in-place (`pd.testing.assert_frame_equal`).
- **Mathematical Exactness:** Financial calculations (sample standard deviation $ddof=1$, geometric returns compounding, exponential weighting, peak-to-trough drawdowns) are verified against analytical ground truths.
- **Edge-Case Resilience:** Short histories (<20 periods), empty DataFrames, missing columns, price boundary inversions ($High < Low$), and zero volume raise explicit domain exceptions.

---

## 2. Complete Test Suite Inventory (268 Tests)

The test suite consists of **13 dedicated test modules** located in `tests/`:

| Module | Test Count | Scope & Coverage |
| :--- | :---: | :--- |
| **`tests/test_cleaner.py`** | 21 | Tests `StockDataCleaner`: price sanity invariants ($H \ge \max(O,C)$, $L \le \min(O,C)$), positive prices, volume constraints, duplicate date deduplication, chronological sorting, forward/backward filling of NaNs. |
| **`tests/test_dashboard.py`** | 40 | Tests Streamlit controllers, `data_manager`, KPI metrics rendering, view toggle logic, live fetcher regression, inclusive date filtering, high-contrast title CSS, and Tab 5 report download buttons. |
| **`tests/test_eda.py`** | 24 | Tests `ExploratoryDataAnalyzer`: summary statistics (mean, median, sample std $ddof=1$, IQR, percentiles), price/volume dynamics, Pearson correlation matrix calculation, and static EDA plots. |
| **`tests/test_fetcher.py`** | 10 | Tests `StockDataFetcher`: valid ticker initialization, parameter validation, inclusive end-date adjustments, empty response handling, network timeouts, and fallback mechanisms. |
| **`tests/test_indicators.py`** | 19 | Tests `TechnicalIndicators`: SMA 20, SMA 50, EMA 20 ($\alpha = 2/21$, `adjust=False`), warmup NaN assertions, lookback validation, and input DataFrame immutability. |
| **`tests/test_insights.py`** | 33 | Tests `StockInsightAnalyzer`: qualitative insight heuristics, categorization (`PRICE_TREND`, `VOLATILITY`, `RISK`, `TRADING_VOLUME`, `CORRELATION`), severity ratings, evidence dictionaries, and limitations. |
| **`tests/test_integration.py`** | 1 | End-to-end pipeline integration: loading $\rightarrow$ cleaning $\rightarrow$ indicators $\rightarrow$ returns $\rightarrow$ risk $\rightarrow$ static and interactive visualization export. |
| **`tests/test_interactive_charts.py`** | 18 | Tests `InteractiveChartGenerator`: Plotly candlestick generation, synchronized volume subplots, daily return bars, cumulative trajectory vs drawdown, and rolling volatility lines. |
| **`tests/test_loader.py`** | 9 | Tests `StockDataLoader`: local CSV ingestion, synthetic demonstration dataset loading, schema enforcement, column remapping, and date parsing. |
| **`tests/test_reporting.py`** | 41 | Tests `PDFReportGenerator`, `HTMLReportGenerator`, `StockReportGenerator`, and CSV exports: PDF layout, Section 2 profile extraction, HTML escaping, Plotly offline bundles, synthetic data tagging, and context freshness. |
| **`tests/test_returns.py`** | 15 | Tests `ReturnAnalyzer`: 1-day percentage price returns, geometric cumulative returns compounding $\prod (1 + R) - 1$, first observation NaN assertion, and immutability. |
| **`tests/test_risk.py`** | 19 | Tests `RiskAnalyzer`: realized annualized return volatility ($\sqrt{252}$ scaling, $ddof=1$), 21-day/63-day rolling volatility, rolling drawdown series, and Maximum Drawdown (MDD). |
| **`tests/test_static_charts.py`** | 18 | Tests `StaticChartGenerator`: Matplotlib/Seaborn 300 DPI publication plots, figure creation, axis labeling, and chart file routing. |
| **Total Test Count** | **268** | **100% Pass Rate Across All 13 Test Modules** |

---

## 3. Running the Test Suite

### 3.1 Execute Full Test Suite
Run all 268 automated tests from the project root:
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### 3.2 Quick Quiet Execution
Run quiet summary execution:
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### 3.3 Running Specific Test Modules
Execute tests for a specific analytical or reporting subsystem:
```powershell
# Reporting subsystem (PDF, HTML, CSVs, Freshness)
.\.venv\Scripts\python.exe -m pytest tests/test_reporting.py -v

# Streamlit dashboard and UI controllers
.\.venv\Scripts\python.exe -m pytest tests/test_dashboard.py -v

# Quantitative risk and drawdown models
.\.venv\Scripts\python.exe -m pytest tests/test_risk.py -v
```

### 3.4 Fast-Fail Mode
Stop execution immediately upon encountering the first failure:
```powershell
.\.venv\Scripts\python.exe -m pytest -x
```

---

## 4. Pytest Configuration (`pytest.ini`)

The project configuration in `pytest.ini` standardizes test discovery and execution flags:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -ra
filterwarnings =
    ignore::DeprecationWarning
```

---

## 5. Mocking Strategy & API Isolation

To eliminate external network dependencies, unit tests mocking `yfinance` queries inject deterministic synthetic DataFrames:

```python
import unittest.mock
import pandas as pd

def test_live_fetch_success_mocked(sample_reporting_df, monkeypatch):
    """Verify live fetch workflow using mocked API response."""
    mock_fetcher = unittest.mock.MagicMock()
    mock_fetcher.fetch_data.return_value = sample_reporting_df
    
    with unittest.mock.patch("stock_analyzer.data.fetcher.StockDataFetcher", return_value=mock_fetcher):
        # Fetching executes deterministically without network calls
        ...
```

---

## 6. Verification Checklist Before Code Contributions

Before opening a pull request or creating Git commits, verify that:
1. All 268 tests pass with zero failures: `pytest -q`
2. Sample stock dataset hash is unmodified:
   `Get-FileHash 'data/sample/sample_stock.csv' -Algorithm SHA256`  
   Matches: `8AF5CC11712AB486248A04F2B95D85E8F1B77B29C7FFF39B29D8950E3DFCB196`
3. No caller DataFrame is mutated in analytical functions.
4. All new functions include comprehensive type hints and docstrings.
