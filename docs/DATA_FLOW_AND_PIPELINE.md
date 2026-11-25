# Data Flow & Pipeline Architecture

**Project Author:** Akash Das  
**Pipeline Type:** Vectorized, Invariant-Guarded Quantitative Data Pipeline  
**Execution Runtime:** Python 3.11 with Pandas and NumPy Vectorization  

---

## 1. End-to-End Pipeline Overview

The **Stock Market Data Analyzer** pipeline executes a deterministic, multi-stage data processing workflow. Every raw price record passes through structural ingestion, invariant verification, quantitative modeling, heuristic insight extraction, and multi-format presentation:

```text
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  Data Ingress   │ ───►  │ Data Cleaning & │ ───►  │  Quantitative   │
│  (API / CSV)    │       │ Invariant Guard │       │ Modeling Engine │
└─────────────────┘       └─────────────────┘       └─────────────────┘
                                                             │
                          ┌─────────────────┐                ▼
                          │  Multi-Format   │ ◄───  ┌─────────────────┐
                          │ Presentation &  │       │    Automated    │
                          │ Report Exports  │       │ Insights Engine │
                          └─────────────────┘       └─────────────────┘
```

---

## 2. Stage-by-Stage Pipeline Detail

### Stage 1: Data Ingestion (`data.fetcher` & `data.loader`)
- **Yahoo Finance Fetcher (`StockDataFetcher`):**
  - Accepts `ticker: str`, `start_date: str`, `end_date: str`.
  - Normalizes ticker symbols to uppercase alphanumeric strings.
  - Resolves Yahoo Finance's exclusive end-date boundary by adjusting the requested temporal query window, guaranteeing user-selected end dates are captured.
  - Extracts standard OHLCV columns and validates that the returned payload is non-empty.
- **Local File Loader (`StockDataLoader`):**
  - Ingests synthetic baseline (`data/sample/sample_stock.csv`) or arbitrary user-supplied CSV files.
  - Enforces mandatory column availability (`Date`, `Open`, `High`, `Low`, `Close`, `Volume`).
  - Converts calendar timestamps into `datetime64[ns]` ISO 8601 records.

### Stage 2: Data Cleaning & Invariant Guard (`data.cleaner`)
`StockDataCleaner.clean()` enforces structural data integrity without mutating caller inputs:
1. **Defensive Deep Copying:** Copies input DataFrame (`df.copy(deep=True)`).
2. **Chronological Monotonicity:** Sorts records strictly by `Date` ascending.
3. **Deduplication:** Identifies duplicate date records and retains the latest occurrence.
4. **Financial Invariant Assertions:**
   - Evaluates price bounds: $\text{High} \ge \max(\text{Open}, \text{Close})$ and $\text{Low} \le \min(\text{Open}, \text{Close})$.
   - Positivity constraint: Asserts $\text{Low} > 0$, $\text{Open} > 0$, $\text{Close} > 0$.
   - Non-negative volume constraint: Asserts $\text{Volume} \ge 0$.
5. **Missing Value Resolution:** Applies forward-fill (`ffill`) followed by backward-fill (`bfill`) to resolve internal market closure gaps without forward-looking leakage.

### Stage 3: Quantitative Modeling Engine (`analysis/`)
Vectorized calculation of technical indicators, financial returns, and risk metrics:
1. **Technical Indicators (`TechnicalIndicators`):**
   - 20-day Simple Moving Average: $\text{SMA}_{20, t} = \frac{1}{20}\sum_{i=0}^{19} \text{Close}_{t-i}$
   - 50-day Simple Moving Average: $\text{SMA}_{50, t} = \frac{1}{50}\sum_{i=0}^{49} \text{Close}_{t-i}$
   - 20-day Exponential Moving Average: $\text{EMA}_{20, t} = \alpha \cdot \text{Close}_t + (1 - \alpha) \cdot \text{EMA}_{20, t-1}$, with $\alpha = \frac{2}{21}$ and `adjust=False`.
2. **Returns Modeling (`ReturnAnalyzer`):**
   - Daily percentage return: $R_t = \frac{\text{Close}_t - \text{Close}_{t-1}}{\text{Close}_{t-1}}$
   - Compounded cumulative return: $\text{CumReturn}_t = \prod_{i=1}^t (1 + R_i) - 1$
3. **Risk & Volatility Modeling (`RiskAnalyzer`):**
   - Realized annual volatility: $\sigma_{\text{annual}} = \text{std}(R, ddof=1) \times \sqrt{252}$
   - Rolling volatilities: Sliding window annualized standard deviations over 21 sessions (~1 month) and 63 sessions (~1 quarter).
   - Peak-to-trough drawdown series: $\text{Drawdown}_t = \frac{\text{Close}_t - \max_{0 \le s \le t}(\text{Close}_s)}{\max_{0 \le s \le t}(\text{Close}_s)}$
   - Maximum Drawdown (MDD): Minimum drawdown depth and duration metrics.

### Stage 4: Automated Insights Engine (`analysis.insights`)
`StockInsightAnalyzer` evaluates the quantitative matrix against rule-based heuristic criteria:
- **Price Trend:** Evaluates moving average alignment (Bullish: Price > SMA20 > SMA50; Bearish: Price < SMA20 < SMA50).
- **Volatility Dynamics:** Compares 21-day rolling volatility against annual baseline to detect compression or expansion regimes.
- **Risk Exposure:** Evaluates maximum drawdown depth against cautionary thresholds (-10%, -20%).
- **Market Turnover:** Detects elevated volume surges relative to the 20-day baseline turnover.
- **Correlation:** Computes pairwise linear association between price moves and volume turnover.

### Stage 5: Multi-Format Presentation & Export (`reporting/`)
The analytical matrix feeds directly into:
1. **Interactive Streamlit UI (`app/`):** Cached reactive state updates 5 workspace tabs in real time.
2. **Vector PDF Generation (`PDFReportGenerator`):** Formats metrics into a multi-page vector institutional report (10–11 pages; 11 pages for synthetic dataset configurations) with embedded high-resolution figures.
3. **Interactive HTML (`HTMLReportGenerator`):** Compiles standalone Plotly figures with navigation anchors.
4. **Standardized CSV Exports (`data_export`):** Exports cleaned OHLCV, analytical datasets, and qualitative summaries with self-describing metadata columns (`Is_Synthetic`, `Data_Source`).

---

## 3. Data Immutability Contract

Every stage of the pipeline guarantees zero side effects on caller memory:

```python
original = df.copy(deep=True)
clean_df = cleaner.clean(df)

# Assert caller data was never mutated
pd.testing.assert_frame_equal(df, original)
```

This immutability contract prevents subtle cross-tab contamination and guarantees that switching tickers or dates always operates on fresh, uncorrupted data.
