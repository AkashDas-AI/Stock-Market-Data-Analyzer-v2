# Screenshot & UI Visual Reference Guide

**Project Author:** Akash Das  
**Theme:** Custom Institutional Dark Theme (`#0E1117` background, `#161B22` cards, `#FFFFFF` text)  
**Accessibility:** WCAG 2.1 AA Compliant High-Contrast Ratio  

---

## 1. Visual Hierarchy & Design System

The **Stock Market Data Analyzer** features an institutional dark-mode user interface designed for high-density financial time-series inspection:

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│  📈 Stock Market Data Analyzer                                                   │
│  Interactive Quantitative Financial Analysis & Technical Indicators Dashboard     │
├──────────────────────────────────────────────────────────────────────────────────┤
│  ⚠️ SYNTHETIC SAMPLE DATA ACTIVE: The loaded dataset contains synthetic prices...  │
├──────────────────────────────────────────────────────────────────────────────────┤
│  Financial Overview — AAPL                                                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐  │
│  │ Latest Close │ │ First Close  │ │ Cum Return   │ │ Realized Vol │ │ Max DD │  │
│  │ $346.00      │ │ $276.97      │ │ +24.92%      │ │ 25.07%       │ │ -13.82%│  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └────────┘  │
├──────────────────────────────────────────────────────────────────────────────────┤
│  [1. Price & Technical] [2. Returns & Risk] [3. Insights] [4. Data] [5. Reports] │
│                                                                                  │
│  Interactive Candlestick & Volume Chart — AAPL                                   │
│  [1m] [3m] [6m] [YTD] [1y] [All]                                                 │
│  ▲ Price ($)                                                                     │
│  │    ┼  ┼  ┼┼  ┼                                                                │
│  └───┼──┼──┼──┼───────────────────────────────────────────────────────────────   │
│  ▲ Volume (Shares)                                                               │
│  │   █  █  ██  █                                                                 │
│  └────────────────────────────────────────────────────────────────────────────   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Key Interface Views & Component Breakdown

### 2.1 Main Dashboard Header
- **Visual Design:** Bright white bold typography (`#FFFFFF`, 32px, font-weight 700) with custom padding (`padding-bottom: 0.5rem`).
- **Contrast Rationale:** Overrides default dark-blue markdown styling to eliminate low-contrast visual strain against dark backgrounds.
- **Sub-headline:** Slate gray subtitle displaying author attribution and system version (`#94A3B8`).

### 2.2 Ingestion Status Banners
1. **Synthetic Data Warning Banner (Amber):**
   - Triggered when `Sample Dataset (Synthetic)` is active.
   - Distinct gold/amber styling (`background: #FEF3C7; border: 1.5px solid #F59E0B; color: #92400E`).
   - Advises users that price points represent synthetic observations for offline testing.
2. **Controlled Error / Validation Banner (Crimson):**
   - Triggered upon network disconnects, invalid date ranges, or non-existent ticker queries.
   - Clean crimson callout (`background: #450A0A; border: 1px solid #DC2626; color: #FCA5A5`).
   - Prevents unhandled tracebacks from leaking into the user interface.

### 2.3 Executive Financial KPI Cards
Positioned directly above the workspace tabs in a 6-column grid:
- **Latest Close:** Dynamic price display formatted to two decimals (`$346.00`).
- **First Close:** Initial session price (`$276.97`).
- **Cumulative Return:** Compounded growth highlighted in green for positive performance (`+24.92%`) or red for negative performance.
- **Annualized Volatility:** Realized standard deviation ($\sigma \times \sqrt{252}$) displayed as a percentage (`25.07%`).
- **Max Drawdown (MDD):** Deepest peak-to-trough decline highlighted in teal/red (`-13.82%`).
- **Total Observations:** Number of trading sessions evaluated (`252 Days`).

### 2.4 Tab 1: Price & Technical Analysis
- **Primary Visual:** Plotly interactive candlestick chart with green/red candles.
- **Indicator Overlays:**
  - 20-Day Simple Moving Average (Cyan curve: `#06B6D4`).
  - 50-Day Simple Moving Average (Amber curve: `#F59E0B`).
  - 20-Day Exponential Moving Average (Magenta curve: `#EC4899`).
- **Volume Subplot:** Lower subplot synchronized to horizontal time axis; colored green for up sessions and red for down sessions.
- **Interactivity Controls:** Hover tooltips displaying exact OHLCV values, range slider along the bottom, and period buttons (`1m`, `3m`, `6m`, `YTD`, `1y`, `All`).

### 2.5 Tab 2: Returns & Risk Analysis
- **Daily Returns Bar Chart:** Horizontal zero-line with vertical bars displaying day-over-day price shifts. Includes horizontal dashed markers for the arithmetic mean and $\pm 2\sigma$ statistical threshold bands.
- **Compounded Return vs. Underwater Drawdown:**
  - Top Panel: Wealth index trajectory starting at $0\%$ and compounding geometrically over time.
  - Bottom Panel: Filled red area chart displaying drawdown depth beneath the $0\%$ all-time high line.
- **Rolling Volatility:** Multi-line plot tracking the 21-day (~1 month) and 63-day (~1 quarter) annualized rolling volatility.

### 2.6 Tab 3: Insights & Interpretation
- **Quadrant Summary:** High-level summary of positive signals, cautionary risks, volatility alerts, and data limitations.
- **Categorized Cards:**
  - Severity-colored left border (Green: Positive, Amber: Warning, Red: Danger, Blue: Info).
  - Explicit metric evidence strings (e.g., `SMA20=340.21; Close=346.00; Spread=+1.7%`).
  - Limitations notice detailing non-causation boundaries and aggregate volume constraints.

### 2.7 Tab 4: Data Preview & Statistics
- **Descriptive Statistics Table:** Pandas summary table formatted for financial display.
- **Correlation Heatmap:** Annotated Seaborn/Plotly matrix displaying pairwise linear correlations between `Open`, `High`, `Low`, `Close`, and `Volume`.
- **Searchable Data Grid:** Full tabular record browser with chronological pagination.

### 2.8 Tab 5: Reports & Downloads
- **Download Controls Grid:** 5 dedicated download cards:
  1. `Download Research Report (PDF)`: Multi-page vector publication document (10–11 pages; 11 pages for synthetic dataset configurations).
  2. `Download Interactive Report (HTML)`: Standalone Plotly responsive document.
  3. `Download Cleaned OHLCV (CSV)`: Validated base price records.
  4. `Download Analytical Dataset (CSV)`: 16-column dataset including all indicators and risk metrics.
  5. `Download Insights Summary (CSV)`: Tabular export of all qualitative findings.
- **Batch Generator:** One-click button generating all five artifacts simultaneously into `reports/generated/`.

---

## 3. Captured Application Screenshots Inventory

The repository includes high-resolution UI captures located under [`images/`](../images):

| Image Reference | Source Path | View & Purpose |
| :--- | :--- | :--- |
| **Dashboard Overview** | [`images/dashboard/dashboard_overview.png`](../images/dashboard/dashboard_overview.png) | High-level application layout, KPI cards, sidebar controls, and synthetic data banner |
| **Candlestick & Technical** | [`images/dashboard/candlestick_chart.png`](../images/dashboard/candlestick_chart.png) | Tab 1 interactive Plotly candlestick chart with volume subplot and SMA/EMA overlays |
| **Returns & Risk Analysis** | [`images/dashboard/returns_and_risk.png`](../images/dashboard/returns_and_risk.png) | Tab 2 daily return distribution, cumulative wealth trajectory, and underwater drawdown |
| **Insights & Interpretation** | [`images/dashboard/insights_view.png`](../images/dashboard/insights_view.png) | Tab 3 structured heuristic cards, quadrant summary, momentum signals, and evidence metrics |
| **Reports & Downloads** | [`images/reports/report_downloads.png`](../images/reports/report_downloads.png) | Tab 5 multi-format export cards for PDF, HTML, and CSV analytical dossiers |

