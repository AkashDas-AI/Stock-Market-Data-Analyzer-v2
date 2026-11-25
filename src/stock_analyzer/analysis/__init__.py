"""Statistical, indicator, return, risk, and insights analytical subpackage."""

# Phase 5: Exploratory Data Analysis
from stock_analyzer.analysis.eda import (
    ExploratoryDataAnalyzer,
    generate_summary_statistics,
    compute_correlation_matrix,
    generate_eda_summary,
    plot_price_distribution,
    plot_volume_distribution,
    plot_ohlc_distributions,
    plot_correlation_heatmap,
    plot_high_low_spread,
)

# Phase 6: Technical Moving Averages
from stock_analyzer.analysis.indicators import (
    TechnicalIndicators,
    calculate_sma_20,
    calculate_sma_50,
    calculate_ema_20,
    calculate_moving_averages,
    add_moving_averages,
)

# Phase 7: Performance Returns & Risk Analytics
from stock_analyzer.analysis.returns import (
    ReturnAnalyzer,
    calculate_daily_returns,
    calculate_cumulative_returns,
    add_return_metrics,
)
from stock_analyzer.analysis.risk import (
    RiskAnalyzer,
    calculate_daily_volatility,
    calculate_annualized_volatility,
    calculate_rolling_volatility,
    calculate_drawdown_series,
    calculate_max_drawdown,
)

# Phase 10: Insights and Interpretation
from stock_analyzer.analysis.insights import (
    StockInsightAnalyzer,
    InsightsEngine,
    MarketInsight,
    InsightSummary,
    InsightCategory,
    InsightSeverity,
    InsightThresholds,
    generate_stock_insights,
)

__all__ = [
    # Phase 5: EDA
    "ExploratoryDataAnalyzer",
    "generate_summary_statistics",
    "compute_correlation_matrix",
    "generate_eda_summary",
    "plot_price_distribution",
    "plot_volume_distribution",
    "plot_ohlc_distributions",
    "plot_correlation_heatmap",
    "plot_high_low_spread",
    # Phase 6: Indicators
    "TechnicalIndicators",
    "calculate_sma_20",
    "calculate_sma_50",
    "calculate_ema_20",
    "calculate_moving_averages",
    "add_moving_averages",
    # Phase 7: Returns & Risk
    "ReturnAnalyzer",
    "calculate_daily_returns",
    "calculate_cumulative_returns",
    "add_return_metrics",
    "RiskAnalyzer",
    "calculate_daily_volatility",
    "calculate_annualized_volatility",
    "calculate_rolling_volatility",
    "calculate_drawdown_series",
    "calculate_max_drawdown",
    # Phase 10: Insights
    "StockInsightAnalyzer",
    "InsightsEngine",
    "MarketInsight",
    "InsightSummary",
    "InsightCategory",
    "InsightSeverity",
    "InsightThresholds",
    "generate_stock_insights",
]
