# Data Dictionary & Schema Specification

**Project Author:** Akash Das  
**Scope:** Raw, Derived, and Exported Schemas across the Stock Market Data Analyzer  

---

## 1. Primary Market Data Schema (Base OHLCV)

Every ingested stock time-series adheres to this standard schema:

| Column Name | Data Type | Nullable | Mathematical Constraint | Description |
| :--- | :--- | :---: | :--- | :--- |
| **`Date`** | `datetime64[ns]` | No | Unique, Monotonic Ascending | Calendar date of the market trading session (`YYYY-MM-DD`). |
| **`Open`** | `float64` | No | $> 0$ | First transaction price at market session open. |
| **`High`** | `float64` | No | $\ge \max(\text{Open}, \text{Close})$ | Highest transaction price recorded during session. |
| **`Low`** | `float64` | No | $\le \min(\text{Open}, \text{Close}), > 0$ | Lowest transaction price recorded during session. |
| **`Close`** | `float64` | No | $> 0$ | Final transaction price at market session close. |
| **`Adj Close`** | `float64` | Yes | $> 0$ | Close price adjusted for splits and dividend distributions. |
| **`Volume`** | `int64` | No | $\ge 0$ | Total number of equity shares traded during session. |
| **`Is_Synthetic`**| `bool` | Yes | `True` or `False` | Boolean indicator appended when dataset has synthetic origin. |

---

## 2. Derived Technical Indicators

| Column Name | Formula / Definition | Lookback Window | Description |
| :--- | :--- | :---: | :--- |
| **`SMA_20`** | $\frac{1}{20}\sum_{i=0}^{19} \text{Close}_{t-i}$ | 20 sessions | Short-term trend-smoothing moving average. First 19 rows are `NaN`. |
| **`SMA_50`** | $\frac{1}{50}\sum_{i=0}^{49} \text{Close}_{t-i}$ | 50 sessions | Medium-term trend-smoothing moving average. First 49 rows are `NaN`. |
| **`EMA_20`** | $\alpha \cdot \text{Close}_t + (1 - \alpha) \cdot \text{EMA}_{t-1}$ where $\alpha = \frac{2}{21}$ | 20 sessions | Exponentially weighted trend average. Prioritizes recent sessions. |

---

## 3. Return & Risk Metrics

| Metric / Column | Formula | Interpretation |
| :--- | :--- | :--- |
| **`Daily_Return`** | $\frac{\text{Close}_t - \text{Close}_{t-1}}{\text{Close}_{t-1}}$ | 1-day arithmetic return percentage. First observation is `NaN`. |
| **`Cumulative_Return`** | $\prod_{i=1}^t (1 + \text{Daily\_Return}_i) - 1$ | Compounded wealth growth factor of initial capital. |
| **`Annualized_Volatility`** | $\sigma_{\text{daily}} \times \sqrt{252}$ | Sample standard deviation ($ddof=1$) annualized to 252 sessions. |
| **`Rolling_Vol_21`** | $\text{std}(R_{t-20:t}, ddof=1) \times \sqrt{252}$ | 21-session (~1 month) sliding-window annualized volatility. |
| **`Rolling_Vol_63`** | $\text{std}(R_{t-62:t}, ddof=1) \times \sqrt{252}$ | 63-session (~1 quarter) sliding-window annualized volatility. |
| **`Drawdown`** | $\frac{\text{Close}_t - \max_{0 \le s \le t}(\text{Close}_s)}{\max_{0 \le s \le t}(\text{Close}_s)}$ | Percentage decline from historical running peak. Always $\le 0$. |
| **`Max_Drawdown (MDD)`**| $\min(\text{Drawdown})$ | Deepest peak-to-trough equity decline across evaluated history. |

---

## 4. Exported CSV Schemas

### 4.1 Cleaned OHLCV CSV (`export_cleaned_data_csv`)
- **Columns (7):** `['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Is_Synthetic']`
- *Note:* `Is_Synthetic` column is explicitly attached when exporting synthetic data to guarantee self-describing provenance outside the dashboard.

### 4.2 Comprehensive Analytical Dataset CSV (`export_comprehensive_analysis_csv`)
- **Columns (16):**  
  `['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'SMA_20', 'SMA_50', 'EMA_20', 'Daily_Return', 'Cumulative_Return', 'Drawdown', 'Rolling_Vol_21', 'Rolling_Vol_63', 'Is_Synthetic']`

### 4.3 Qualitative Insights Summary CSV (`export_insights_summary_csv`)
- **Columns (9):**  
  `['Ticker', 'Data_Source', 'Is_Synthetic', 'Category', 'Title', 'Severity', 'Observation', 'Supporting_Evidence', 'Limitations']`
- **Severity Levels:** `positive`, `warning`, `danger`, `info`.
- **Categories:** `Price Trend`, `Volatility Dynamics`, `Risk Exposure`, `Trading Volume`, `Feature Correlation`.
