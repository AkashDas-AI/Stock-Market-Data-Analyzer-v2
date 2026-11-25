"""Static and interactive visualization subpackage.

Provides publication-quality static visualizations (Matplotlib/Seaborn)
and interactive dashboard-ready charts (Plotly).
"""

from stock_analyzer.visualization.static_charts import (
    StaticChartGenerator,
    plot_closing_price,
    plot_ohlc_bars,
    plot_moving_averages,
    plot_price_and_averages,
    plot_trading_volume,
    plot_daily_returns_time_series,
    plot_daily_returns_distribution,
    plot_cumulative_returns,
    plot_drawdown,
    plot_rolling_volatility,
    plot_correlation_heatmap as plot_static_correlation_heatmap,
)
from stock_analyzer.visualization.interactive_charts import (
    InteractiveChartGenerator,
    create_candlestick_chart,
    create_moving_averages_chart,
    create_volume_chart,
    create_daily_returns_chart,
    create_daily_returns_distribution_chart,
    create_cumulative_returns_chart,
    create_drawdown_chart,
    create_rolling_volatility_chart,
    create_correlation_heatmap as create_interactive_correlation_heatmap,
)

__all__ = [
    # Static Charts
    "StaticChartGenerator",
    "plot_closing_price",
    "plot_ohlc_bars",
    "plot_moving_averages",
    "plot_price_and_averages",
    "plot_trading_volume",
    "plot_daily_returns_time_series",
    "plot_daily_returns_distribution",
    "plot_cumulative_returns",
    "plot_drawdown",
    "plot_rolling_volatility",
    "plot_static_correlation_heatmap",
    # Interactive Charts
    "InteractiveChartGenerator",
    "create_candlestick_chart",
    "create_moving_averages_chart",
    "create_volume_chart",
    "create_daily_returns_chart",
    "create_daily_returns_distribution_chart",
    "create_cumulative_returns_chart",
    "create_drawdown_chart",
    "create_rolling_volatility_chart",
    "create_interactive_correlation_heatmap",
]
