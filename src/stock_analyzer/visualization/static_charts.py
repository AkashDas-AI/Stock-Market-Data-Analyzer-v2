"""Static charting module using Matplotlib and Seaborn.

Responsibility:
    Generate publication-quality static charts for stock price series,
    moving average overlays, trading volume, returns distributions,
    underwater drawdown plots, rolling volatility, and correlation heatmaps.

Architecture Boundaries (Phase 8):
    - Visualization layer only.
    - Reuses analytical calculations from eda.py, indicators.py, returns.py, and risk.py.
    - NO Streamlit dashboard UI or interactive controls (Phase 9).
    - NO automated investment recommendations (Phase 10).
    - NO report generation (Phase 11).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import matplotlib.dates as mdates
import matplotlib.figure
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from stock_analyzer.analysis.eda import ExploratoryDataAnalyzer
from stock_analyzer.analysis.indicators import TechnicalIndicators
from stock_analyzer.analysis.returns import ReturnAnalyzer
from stock_analyzer.analysis.risk import RiskAnalyzer
from stock_analyzer.data.exceptions import (
    DataValidationError,
    EmptyDataError,
    MissingColumnError,
)

REQUIRED_BASE_COLUMNS: List[str] = ["Date", "Close"]
REQUIRED_OHLCV_COLUMNS: List[str] = ["Date", "Open", "High", "Low", "Close", "Volume"]
DEFAULT_CHART_DIR: Path = Path("outputs/charts")


class StaticChartGenerator:
    """Generates publication-quality static visualizations using Matplotlib and Seaborn."""

    def __init__(self, df: pd.DataFrame, ticker: Optional[str] = None) -> None:
        """Initialize the static chart generator with a stock DataFrame.

        Args:
            df: Cleaned stock DataFrame containing price and volume series.
            ticker: Optional ticker symbol. Inferred from df.attrs if omitted.

        Raises:
            TypeError: If df is not a pandas DataFrame.
            EmptyDataError: If df is empty.
            MissingColumnError: If df lacks required columns ('Date', 'Close').
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame for static chart generation, received {type(df).__name__}."
            )
        if df.empty:
            raise EmptyDataError("Cannot generate charts from an empty DataFrame.")

        missing_base = [col for col in REQUIRED_BASE_COLUMNS if col not in df.columns]
        if missing_base:
            raise MissingColumnError(
                f"DataFrame lacks required columns for charting: {missing_base}."
            )

        # Defensive deep copy to guarantee input immutability
        working_df = df.copy(deep=True)

        # Enforce chronological ordering ascending by Date if Date is present
        if "Date" in working_df.columns:
            try:
                date_dt = pd.to_datetime(working_df["Date"])
                sort_indices = np.argsort(date_dt.values)
                working_df = working_df.iloc[sort_indices].reset_index(drop=True)
            except Exception:
                working_df = working_df.sort_values(by="Date", ascending=True).reset_index(drop=True)

        self.df = working_df
        self.ticker = str(ticker or df.attrs.get("ticker", "STOCK")).upper()
        self.is_synthetic = bool(df.attrs.get("is_synthetic", False))

    def _get_title_context(self) -> str:
        """Construct a standardized title suffix containing ticker, date range, and synthetic tag."""
        date_str = ""
        if "Date" in self.df.columns:
            try:
                min_d = pd.to_datetime(self.df["Date"]).min().strftime("%Y-%m-%d")
                max_d = pd.to_datetime(self.df["Date"]).max().strftime("%Y-%m-%d")
                date_str = f" ({min_d} to {max_d})"
            except Exception:
                date_str = ""

        synthetic_tag = " [SYNTHETIC DATA]" if self.is_synthetic else ""
        return f"{self.ticker}{date_str}{synthetic_tag}"

    def _save_figure(self, fig: matplotlib.figure.Figure, output_path: Optional[Union[str, Path]]) -> None:
        """Helper to safely save figure to destination directory at high resolution."""
        if output_path is not None:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(out_file, dpi=300, bbox_inches="tight")

    # =========================================================================
    # 1. Historical Closing Price Chart
    # =========================================================================

    def plot_closing_price(
        self, output_path: Optional[Union[str, Path]] = None
    ) -> matplotlib.figure.Figure:
        """Plot historical closing price time series with central tendency lines.

        Args:
            output_path: Optional file path to export PNG.

        Returns:
            Matplotlib Figure object.
        """
        fig, ax = plt.subplots(figsize=(10, 5))
        dates = pd.to_datetime(self.df["Date"])
        close = self.df["Close"]

        ax.plot(dates, close, color="#1E3A8A", linewidth=1.8, label="Close Price")

        mean_price = float(close.mean())
        ax.axhline(
            mean_price,
            color="#DC2626",
            linestyle="--",
            linewidth=1.3,
            label=f"Mean: ${mean_price:.2f}",
        )

        ctx = self._get_title_context()
        ax.set_title(f"Historical Closing Price — {ctx}", fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel("Date", fontsize=10)
        ax.set_ylabel("Price ($)", fontsize=10)
        ax.legend(loc="upper left", frameon=True)
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 2. Static OHLC / Candlestick Chart
    # =========================================================================

    def plot_ohlc_bars(
        self, max_bars: int = 60, output_path: Optional[Union[str, Path]] = None
    ) -> matplotlib.figure.Figure:
        """Plot static candlestick / OHLC bar chart using native Matplotlib.

        Args:
            max_bars: Maximum number of recent bars to display for visual clarity.
            output_path: Optional file path to export PNG.

        Returns:
            Matplotlib Figure object.

        Raises:
            MissingColumnError: If df lacks Open, High, or Low columns.
        """
        required = ["Open", "High", "Low", "Close"]
        missing = [c for c in required if c not in self.df.columns]
        if missing:
            raise MissingColumnError(f"Candlestick chart requires columns: {missing}")

        plot_df = self.df.tail(max_bars).copy().reset_index(drop=True)
        fig, ax = plt.subplots(figsize=(12, 6))

        for idx, row in plot_df.iterrows():
            o, h, l, c = row["Open"], row["High"], row["Low"], row["Close"]
            color = "#16A34A" if c >= o else "#DC2626"

            # High-Low wick
            ax.vlines(idx, l, h, color=color, linewidth=1.2, alpha=0.9)
            # Open-Close body
            body_bottom = min(o, c)
            body_height = max(abs(c - o), 0.05)  # minimum height for doji bars
            rect = plt.Rectangle(
                (idx - 0.35, body_bottom),
                0.7,
                body_height,
                facecolor=color,
                edgecolor=color,
                alpha=0.85,
            )
            ax.add_patch(rect)

        # X-tick formatting
        step = max(1, len(plot_df) // 10)
        tick_indices = list(range(0, len(plot_df), step))
        date_labels = [pd.to_datetime(plot_df.loc[i, "Date"]).strftime("%Y-%m-%d") for i in tick_indices]
        ax.set_xticks(tick_indices)
        ax.set_xticklabels(date_labels, rotation=35, ha="right", fontsize=9)
        ax.set_xlim(-1, len(plot_df))

        ctx = self._get_title_context()
        ax.set_title(f"OHLC Candlestick Chart (Recent {len(plot_df)} Sessions) — {ctx}", fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel("Date", fontsize=10)
        ax.set_ylabel("Price ($)", fontsize=10)
        ax.grid(True, linestyle=":", alpha=0.5)

        plt.tight_layout()
        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 3. Moving Average Comparison Chart
    # =========================================================================

    def plot_moving_averages(
        self, output_path: Optional[Union[str, Path]] = None
    ) -> matplotlib.figure.Figure:
        """Plot closing price overlaid with SMA 20, SMA 50, and EMA 20.

        Auto-calculates moving averages using TechnicalIndicators if absent in df.

        Args:
            output_path: Optional file path to export PNG.

        Returns:
            Matplotlib Figure object.
        """
        # Ensure moving average columns are available
        work_df = self.df
        needed_mas = ["SMA_20", "SMA_50", "EMA_20"]
        if not all(col in work_df.columns for col in needed_mas):
            ti = TechnicalIndicators(self.df, price_column="Close")
            work_df = ti.calculate_moving_averages()

        fig, ax = plt.subplots(figsize=(11, 6))
        dates = pd.to_datetime(work_df["Date"])

        ax.plot(dates, work_df["Close"], color="#1E293B", linewidth=1.5, label="Close Price", alpha=0.8)
        if "SMA_20" in work_df.columns and work_df["SMA_20"].notna().any():
            ax.plot(dates, work_df["SMA_20"], color="#2563EB", linewidth=1.8, label="SMA 20")
        if "EMA_20" in work_df.columns and work_df["EMA_20"].notna().any():
            ax.plot(dates, work_df["EMA_20"], color="#D97706", linewidth=1.8, linestyle="--", label="EMA 20")
        if "SMA_50" in work_df.columns and work_df["SMA_50"].notna().any():
            ax.plot(dates, work_df["SMA_50"], color="#DC2626", linewidth=2.0, label="SMA 50")

        ctx = self._get_title_context()
        ax.set_title(f"Moving Average Comparison (Close, SMA 20, SMA 50, EMA 20) — {ctx}", fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel("Date", fontsize=10)
        ax.set_ylabel("Price ($)", fontsize=10)
        ax.legend(loc="upper left", frameon=True)
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        self._save_figure(fig, output_path)
        return fig

    def plot_price_and_averages(
        self, output_path: Optional[Union[str, Path]] = None
    ) -> matplotlib.figure.Figure:
        """Alias for plot_moving_averages matching starter method signature."""
        return self.plot_moving_averages(output_path=output_path)

    # =========================================================================
    # 4. Trading Volume Chart
    # =========================================================================

    def plot_trading_volume(
        self, output_path: Optional[Union[str, Path]] = None
    ) -> matplotlib.figure.Figure:
        """Plot trading volume bars color-coded by daily price direction.

        Args:
            output_path: Optional file path to export PNG.

        Returns:
            Matplotlib Figure object.

        Raises:
            MissingColumnError: If Volume column is missing.
        """
        if "Volume" not in self.df.columns:
            raise MissingColumnError("Trading volume chart requires 'Volume' column.")

        fig, ax = plt.subplots(figsize=(10, 5))
        dates = pd.to_datetime(self.df["Date"])
        vol = self.df["Volume"]

        # Color by price change if Open or Close is present
        if "Open" in self.df.columns and "Close" in self.df.columns:
            colors = ["#16A34A" if c >= o else "#DC2626" for o, c in zip(self.df["Open"], self.df["Close"])]
        else:
            colors = ["#0284C7"] * len(self.df)

        ax.bar(dates, vol, color=colors, alpha=0.7, width=0.8)

        mean_vol = float(vol.mean())
        ax.axhline(mean_vol, color="#F59E0B", linestyle="--", linewidth=1.5, label=f"Mean Volume: {mean_vol:,.0f}")

        ctx = self._get_title_context()
        ax.set_title(f"Trading Volume History — {ctx}", fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel("Date", fontsize=10)
        ax.set_ylabel("Volume (Shares)", fontsize=10)
        ax.legend(loc="upper left", frameon=True)
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 5. Daily Returns Time Series
    # =========================================================================

    def plot_daily_returns_time_series(
        self, output_path: Optional[Union[str, Path]] = None
    ) -> matplotlib.figure.Figure:
        """Plot daily percentage returns time series with baseline zero.

        Args:
            output_path: Optional file path to export PNG.

        Returns:
            Matplotlib Figure object.
        """
        if "Daily_Return" in self.df.columns:
            daily_ret = self.df["Daily_Return"]
        else:
            analyzer = ReturnAnalyzer(self.df, price_column="Close")
            daily_ret = analyzer.calculate_daily_returns()

        fig, ax = plt.subplots(figsize=(10, 5))
        dates = pd.to_datetime(self.df["Date"])

        ax.plot(dates, daily_ret * 100.0, color="#2563EB", linewidth=1.2, marker="o", markersize=2.5)
        ax.axhline(0.0, color="#475569", linestyle="--", linewidth=1.0)

        ctx = self._get_title_context()
        ax.set_title(f"Daily Percentage Returns — {ctx}", fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel("Date", fontsize=10)
        ax.set_ylabel("Daily Return (%)", fontsize=10)
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 6. Daily Returns Distribution
    # =========================================================================

    def plot_daily_returns_distribution(
        self, bins: int = 30, output_path: Optional[Union[str, Path]] = None
    ) -> matplotlib.figure.Figure:
        """Plot histogram and KDE distribution of daily percentage returns.

        Args:
            bins: Number of histogram bins.
            output_path: Optional file path to export PNG.

        Returns:
            Matplotlib Figure object.
        """
        if "Daily_Return" in self.df.columns:
            daily_ret = self.df["Daily_Return"].dropna() * 100.0
        else:
            analyzer = ReturnAnalyzer(self.df, price_column="Close")
            daily_ret = analyzer.calculate_daily_returns().dropna() * 100.0

        fig, ax = plt.subplots(figsize=(9, 5))
        sns.histplot(daily_ret, bins=bins, kde=True, ax=ax, color="#3B82F6", edgecolor="white", alpha=0.7)

        mean_val = float(daily_ret.mean())
        std_val = float(daily_ret.std(ddof=1)) if len(daily_ret) > 1 else 0.0

        ax.axvline(mean_val, color="#DC2626", linestyle="--", linewidth=1.6, label=f"Mean: {mean_val:.2f}%")
        ax.axvline(mean_val + std_val, color="#16A34A", linestyle=":", linewidth=1.4, label=f"+1 Std ({mean_val+std_val:.2f}%)")
        ax.axvline(mean_val - std_val, color="#16A34A", linestyle=":", linewidth=1.4, label=f"-1 Std ({mean_val-std_val:.2f}%)")

        ctx = self._get_title_context()
        ax.set_title(f"Daily Return Distribution — {ctx}", fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel("Daily Return (%)", fontsize=10)
        ax.set_ylabel("Frequency", fontsize=10)
        ax.legend(loc="upper right", frameon=True)
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 7. Cumulative Returns Chart
    # =========================================================================

    def plot_cumulative_returns(
        self, output_path: Optional[Union[str, Path]] = None
    ) -> matplotlib.figure.Figure:
        """Plot cumulative compound return trajectory over time.

        Args:
            output_path: Optional file path to export PNG.

        Returns:
            Matplotlib Figure object.
        """
        if "Cumulative_Return" in self.df.columns:
            cum_ret = self.df["Cumulative_Return"]
        else:
            analyzer = ReturnAnalyzer(self.df, price_column="Close")
            cum_ret = analyzer.calculate_cumulative_returns()

        fig, ax = plt.subplots(figsize=(10, 5))
        dates = pd.to_datetime(self.df["Date"])

        ax.plot(dates, cum_ret * 100.0, color="#059669", linewidth=2.0, label="Cumulative Return (%)")
        ax.axhline(0.0, color="#94A3B8", linestyle="--", linewidth=1.0)

        final_ret = float(cum_ret.dropna().iloc[-1]) if not cum_ret.dropna().empty else 0.0
        ax.scatter([dates.iloc[-1]], [final_ret * 100.0], color="#059669", s=40, zorder=5)

        ctx = self._get_title_context()
        ax.set_title(f"Cumulative Compound Return Trajectory — {ctx}", fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel("Date", fontsize=10)
        ax.set_ylabel("Cumulative Return (%)", fontsize=10)
        ax.legend(loc="upper left", frameon=True)
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 8. Underwater Drawdown Chart
    # =========================================================================

    def plot_drawdown(
        self, output_path: Optional[Union[str, Path]] = None
    ) -> matplotlib.figure.Figure:
        """Plot underwater drawdown curve with shaded area and MDD annotation.

        Args:
            output_path: Optional file path to export PNG.

        Returns:
            Matplotlib Figure object.
        """
        risk_analyzer = RiskAnalyzer(self.df, price_column="Close")
        dd = risk_analyzer.calculate_drawdown_series() * 100.0
        mdd_res = risk_analyzer.calculate_max_drawdown()

        fig, ax = plt.subplots(figsize=(10, 5))
        dates = pd.to_datetime(self.df["Date"])

        ax.plot(dates, dd, color="#DC2626", linewidth=1.5, label="Drawdown (%)")
        ax.fill_between(dates, dd, 0.0, color="#EF4444", alpha=0.3)
        ax.axhline(0.0, color="#475569", linestyle="-", linewidth=1.0)

        # Annotate MDD trough if available
        if mdd_res["trough_index"] is not None and not np.isnan(mdd_res["max_drawdown_pct"]):
            t_idx = mdd_res["trough_index"]
            mdd_pct = mdd_res["max_drawdown_pct"]
            ax.scatter([dates.iloc[t_idx]], [mdd_pct], color="#7F1D1D", s=50, zorder=5)
            ax.annotate(
                f"MDD: {mdd_pct:.1f}%\n({mdd_res['trough_date']})",
                xy=(dates.iloc[t_idx], mdd_pct),
                xytext=(15, -15),
                textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color="#7F1D1D", lw=1.2),
                fontsize=9,
                fontweight="bold",
                color="#7F1D1D",
            )

        ctx = self._get_title_context()
        ax.set_title(f"Historical Drawdown from Peak (Underwater Plot) — {ctx}", fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel("Date", fontsize=10)
        ax.set_ylabel("Drawdown (%)", fontsize=10)
        ax.legend(loc="lower left", frameon=True)
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 9. Rolling Volatility Chart
    # =========================================================================

    def plot_rolling_volatility(
        self,
        windows: Union[int, Sequence[int]] = (21, 63),
        window: Optional[Union[int, Sequence[int]]] = None,
        annualization_factor: int = 252,
        output_path: Optional[Union[str, Path]] = None,
    ) -> matplotlib.figure.Figure:
        """Plot rolling annualized volatility time series using RiskAnalyzer.

        Supports single or multiple rolling windows (defaults to 21-day and 63-day,
        representing approximately 1-month and 3-month lookback windows).

        Args:
            windows: Rolling window size(s) in days. Defaults to (21, 63).
            window: Backward-compatible alias for a single or sequence of windows.
            annualization_factor: Number of trading sessions per year (default: 252).
            output_path: Optional file path to export PNG.

        Returns:
            Matplotlib Figure object.
        """
        raw_windows = window if window is not None else windows
        if isinstance(raw_windows, (int, np.integer)):
            target_windows = [int(raw_windows)]
        else:
            target_windows = [int(w) for w in raw_windows]

        fig, ax = plt.subplots(figsize=(10, 5))
        dates = pd.to_datetime(self.df["Date"])
        colors = ["#9333EA", "#2563EB", "#059669", "#D97706", "#DC2626"]
        risk_analyzer = RiskAnalyzer(self.df, price_column="Close")

        for idx, w in enumerate(target_windows):
            color = colors[idx % len(colors)]
            # Delegate calculation strictly to analytical RiskAnalyzer
            rolling_vol_dec = risk_analyzer.calculate_rolling_volatility(
                window=w, annualization_factor=annualization_factor
            )
            rolling_annual_vol = rolling_vol_dec * 100.0
            ax.plot(dates, rolling_annual_vol, color=color, linewidth=1.8, label=f"Rolling {w}d Vol (%)")

        # Baseline horizontal line using primary window's mean if valid
        primary_w = target_windows[0]
        primary_vol = risk_analyzer.calculate_rolling_volatility(
            window=primary_w, annualization_factor=annualization_factor
        ) * 100.0
        mean_vol = float(primary_vol.dropna().mean()) if not primary_vol.dropna().empty else 0.0
        if mean_vol > 0:
            ax.axhline(mean_vol, color="#F59E0B", linestyle="--", linewidth=1.4, label=f"{primary_w}d Mean: {mean_vol:.1f}%")

        ctx = self._get_title_context()
        w_label = ", ".join(f"{w}d" for w in target_windows)
        ax.set_title(f"Rolling Annualized Volatility ({w_label}) — {ctx}", fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel("Date", fontsize=10)
        ax.set_ylabel("Annualized Volatility (%)", fontsize=10)
        ax.legend(loc="upper left", frameon=True)
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 10. Correlation Heatmap
    # =========================================================================

    def plot_correlation_heatmap(
        self,
        method: str = "pearson",
        annot: bool = True,
        output_path: Optional[Union[str, Path]] = None,
    ) -> matplotlib.figure.Figure:
        """Plot annotated heatmap of numerical feature correlations.

        Args:
            method: Correlation method ('pearson', 'spearman', 'kendall').
            annot: Whether to annotate cells with correlation values.
            output_path: Optional file path to export PNG.

        Returns:
            Matplotlib Figure object.
        """
        eda_analyzer = ExploratoryDataAnalyzer(self.df, ticker=self.ticker)
        return eda_analyzer.plot_correlation_heatmap(method=method, annot=annot, output_path=output_path)


# =============================================================================
# Functional Convenience Wrappers for Static Charts
# =============================================================================


def plot_closing_price(
    df: pd.DataFrame, ticker: Optional[str] = None, output_path: Optional[Union[str, Path]] = None
) -> matplotlib.figure.Figure:
    """Convenience wrapper for historical closing price chart."""
    generator = StaticChartGenerator(df, ticker=ticker)
    return generator.plot_closing_price(output_path=output_path)


def plot_ohlc_bars(
    df: pd.DataFrame, max_bars: int = 60, ticker: Optional[str] = None, output_path: Optional[Union[str, Path]] = None
) -> matplotlib.figure.Figure:
    """Convenience wrapper for static OHLC candlestick bar chart."""
    generator = StaticChartGenerator(df, ticker=ticker)
    return generator.plot_ohlc_bars(max_bars=max_bars, output_path=output_path)


def plot_moving_averages(
    df: pd.DataFrame, ticker: Optional[str] = None, output_path: Optional[Union[str, Path]] = None
) -> matplotlib.figure.Figure:
    """Convenience wrapper for moving average comparison chart."""
    generator = StaticChartGenerator(df, ticker=ticker)
    return generator.plot_moving_averages(output_path=output_path)


def plot_price_and_averages(
    df: pd.DataFrame, ticker: Optional[str] = None, output_path: Optional[Union[str, Path]] = None
) -> matplotlib.figure.Figure:
    """Alias for plot_moving_averages."""
    return plot_moving_averages(df, ticker=ticker, output_path=output_path)


def plot_trading_volume(
    df: pd.DataFrame, ticker: Optional[str] = None, output_path: Optional[Union[str, Path]] = None
) -> matplotlib.figure.Figure:
    """Convenience wrapper for trading volume bar chart."""
    generator = StaticChartGenerator(df, ticker=ticker)
    return generator.plot_trading_volume(output_path=output_path)


def plot_daily_returns_time_series(
    df: pd.DataFrame, ticker: Optional[str] = None, output_path: Optional[Union[str, Path]] = None
) -> matplotlib.figure.Figure:
    """Convenience wrapper for daily returns time series plot."""
    generator = StaticChartGenerator(df, ticker=ticker)
    return generator.plot_daily_returns_time_series(output_path=output_path)


def plot_daily_returns_distribution(
    df: pd.DataFrame, bins: int = 30, ticker: Optional[str] = None, output_path: Optional[Union[str, Path]] = None
) -> matplotlib.figure.Figure:
    """Convenience wrapper for daily return distribution histogram/KDE."""
    generator = StaticChartGenerator(df, ticker=ticker)
    return generator.plot_daily_returns_distribution(bins=bins, output_path=output_path)


def plot_cumulative_returns(
    df: pd.DataFrame, ticker: Optional[str] = None, output_path: Optional[Union[str, Path]] = None
) -> matplotlib.figure.Figure:
    """Convenience wrapper for cumulative compound return trajectory."""
    generator = StaticChartGenerator(df, ticker=ticker)
    return generator.plot_cumulative_returns(output_path=output_path)


def plot_drawdown(
    df: pd.DataFrame, ticker: Optional[str] = None, output_path: Optional[Union[str, Path]] = None
) -> matplotlib.figure.Figure:
    """Convenience wrapper for underwater drawdown chart."""
    generator = StaticChartGenerator(df, ticker=ticker)
    return generator.plot_drawdown(output_path=output_path)


def plot_rolling_volatility(
    df: pd.DataFrame,
    windows: Union[int, Sequence[int]] = (21, 63),
    window: Optional[Union[int, Sequence[int]]] = None,
    annualization_factor: int = 252,
    ticker: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> matplotlib.figure.Figure:
    """Convenience wrapper for rolling annualized volatility chart."""
    generator = StaticChartGenerator(df, ticker=ticker)
    return generator.plot_rolling_volatility(
        windows=windows, window=window, annualization_factor=annualization_factor, output_path=output_path
    )


def plot_correlation_heatmap(
    df: pd.DataFrame, method: str = "pearson", annot: bool = True, ticker: Optional[str] = None, output_path: Optional[Union[str, Path]] = None
) -> matplotlib.figure.Figure:
    """Convenience wrapper for feature correlation heatmap."""
    generator = StaticChartGenerator(df, ticker=ticker)
    return generator.plot_correlation_heatmap(method=method, annot=annot, output_path=output_path)
