"""Exploratory Data Analysis (EDA) module.

Responsibility:
    Compute descriptive statistics, distribution metrics, price-volume spreads,
    and Pearson correlation structures for cleaned stock datasets.

Architecture Boundaries (Phase 5):
    - Strictly descriptive analysis.
    - NO moving averages (Phase 6).
    - NO returns, volatility, or drawdown metrics (Phase 7).
    - NO Plotly interactive charts (Phase 8).
    - NO Streamlit dashboard functionality (Phase 9).
    - NO automated investment recommendations or predictions (Phase 10).
    - NO report generation (Phase 11).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from stock_analyzer.data.exceptions import (
    DataValidationError,
    EmptyDataError,
    MissingColumnError,
)

REQUIRED_COLUMNS: List[str] = ["Date", "Open", "High", "Low", "Close", "Volume"]
NUMERIC_PRICE_COLUMNS: List[str] = ["Open", "High", "Low", "Close"]
ALL_NUMERIC_COLUMNS: List[str] = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
DEFAULT_CHART_DIR: Path = Path("outputs/charts")


class ExploratoryDataAnalyzer:
    """Performs statistical profiling, distribution analysis, and correlation analysis on stock data.

    Adheres strictly to Phase 5 scope boundaries: focus is purely descriptive.
    Does not compute forward-looking indicators, moving averages, or risk/return measures.
    """

    def __init__(self, df: pd.DataFrame, ticker: Optional[str] = None) -> None:
        """Initialize the EDA analyzer with a cleaned stock DataFrame.

        Args:
            df: Cleaned stock DataFrame adhering to standard schema (OHLCV).
            ticker: Optional stock ticker symbol. Inferred from df.attrs if omitted.

        Raises:
            TypeError: If df is not a pandas DataFrame.
            EmptyDataError: If df is empty.
            MissingColumnError: If df lacks required OHLCV columns.
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame for exploratory analysis, received {type(df).__name__}."
            )
        if df.empty:
            raise EmptyDataError("Cannot perform exploratory data analysis on an empty DataFrame.")

        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise MissingColumnError(
                f"DataFrame lacks mandatory OHLCV columns required for EDA: {missing_cols}."
            )

        # Defensive deep copy to preserve input immutability
        self.df = df.copy()

        # Resolve metadata
        self.ticker = str(ticker or self.df.attrs.get("ticker", "STOCK")).upper()
        self.is_synthetic = bool(self.df.attrs.get("is_synthetic", False))

        # Identify numeric columns present in this dataset
        self.numeric_cols = [col for col in ALL_NUMERIC_COLUMNS if col in self.df.columns]

    def _get_title_context(self) -> str:
        """Construct context suffix for chart titles including ticker and date bounds."""
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

    def compute_summary_statistics(
        self, percentiles: Optional[List[float]] = None
    ) -> pd.DataFrame:
        """Compute comprehensive descriptive summary statistics for numeric OHLCV features.

        Metrics calculated:
            - count: Count of non-null observations.
            - mean: Arithmetic mean.
            - std: Sample standard deviation (ddof=1).
            - min: Minimum observed value.
            - 25%: 25th percentile (first quartile, Q1).
            - 50%: 50th percentile (median, Q2).
            - 75%: 75th percentile (third quartile, Q3).
            - max: Maximum observed value.
            - iqr: Interquartile range (Q3 - Q1).
            - Optional custom percentiles if specified.

        Args:
            percentiles: Optional list of floats between 0.0 and 1.0.

        Returns:
            A labelled pandas DataFrame indexed by metric name with columns corresponding
            to the numeric OHLCV features.

        Raises:
            ValueError: If any percentile is outside the [0.0, 1.0] range.
        """
        if percentiles is not None:
            for p in percentiles:
                if not (0.0 <= p <= 1.0):
                    raise ValueError(
                        f"Percentile values must be between 0.0 and 1.0 inclusive, got {p}."
                    )

        # Base percentiles
        base_percentiles = [0.25, 0.50, 0.75]
        if percentiles:
            all_percentiles = sorted(list(set(base_percentiles + percentiles)))
        else:
            all_percentiles = base_percentiles

        # Compute standard describe
        desc = self.df[self.numeric_cols].describe(percentiles=all_percentiles)

        # Compute IQR (75% - 25%)
        if "25%" in desc.index and "75%" in desc.index:
            iqr_series = desc.loc["75%"] - desc.loc["25%"]
            iqr_df = pd.DataFrame([iqr_series], index=["iqr"])
            desc = pd.concat([desc, iqr_df])

        return desc

    def compute_price_and_volume_summary(self) -> Dict[str, Any]:
        """Perform comprehensive price and volume exploration.

        Analyzes:
            - Open, High, Low, Close price ranges and observed extremes.
            - Daily High-Low price spread (absolute and percentage relative to Close).
            - Trading volume distribution and extremes.
            - Basic linear price-volume relationship.

        Returns:
            Dictionary containing descriptive summary metrics and observed extremes.
        """
        high = self.df["High"]
        low = self.df["Low"]
        close = self.df["Close"]
        volume = self.df["Volume"]

        # Daily High-Low spread
        spread = high - low
        # Avoid division by zero
        spread_pct = np.where(close > 0, (spread / close) * 100.0, np.nan)
        spread_pct_series = pd.Series(spread_pct, index=self.df.index)

        # Period extremes with dates if available
        period_high = float(high.max())
        period_low = float(low.min())
        total_range = period_high - period_low
        range_ratio = (period_high / period_low) if period_low > 0 else np.nan

        high_idx = high.idxmax()
        low_idx = low.idxmin()
        max_vol_idx = volume.idxmax()
        min_vol_idx = volume.idxmin()

        high_date = str(self.df.loc[high_idx, "Date"]) if "Date" in self.df.columns else None
        low_date = str(self.df.loc[low_idx, "Date"]) if "Date" in self.df.columns else None
        max_vol_date = (
            str(self.df.loc[max_vol_idx, "Date"]) if "Date" in self.df.columns else None
        )
        min_vol_date = (
            str(self.df.loc[min_vol_idx, "Date"]) if "Date" in self.df.columns else None
        )

        # Price-volume correlation (descriptive)
        pv_corr = float(close.corr(volume, method="pearson"))

        summary: Dict[str, Any] = {
            "ticker": self.ticker,
            "is_synthetic": self.is_synthetic,
            "total_observations": int(len(self.df)),
            "date_range": {
                "start": str(self.df["Date"].min()) if "Date" in self.df.columns else None,
                "end": str(self.df["Date"].max()) if "Date" in self.df.columns else None,
            },
            "price_extremes": {
                "period_high": period_high,
                "period_high_date": high_date,
                "period_low": period_low,
                "period_low_date": low_date,
                "total_range": total_range,
                "range_ratio": float(range_ratio) if not np.isnan(range_ratio) else None,
                "min_close": float(close.min()),
                "max_close": float(close.max()),
                "mean_close": float(close.mean()),
                "median_close": float(close.median()),
            },
            "daily_spread": {
                "min_spread": float(spread.min()),
                "max_spread": float(spread.max()),
                "mean_spread": float(spread.mean()),
                "median_spread": float(spread.median()),
                "std_spread": float(spread.std(ddof=1)) if len(spread) > 1 else 0.0,
                "mean_spread_pct": float(spread_pct_series.mean()),
                "max_spread_pct": float(spread_pct_series.max()),
            },
            "volume_summary": {
                "min_volume": float(volume.min()),
                "min_volume_date": min_vol_date,
                "max_volume": float(volume.max()),
                "max_volume_date": max_vol_date,
                "mean_volume": float(volume.mean()),
                "median_volume": float(volume.median()),
                "total_volume": float(volume.sum()),
            },
            "price_volume_relationship": {
                "pearson_correlation": pv_corr,
                "interpretation": (
                    "Positive correlation indicates volume tends to expand with higher prices; "
                    "negative correlation indicates volume tends to expand at lower price levels. "
                    "Note: Correlation reflects linear co-movement only and does not establish causation."
                ),
            },
        }

        return summary

    def compute_correlations(self, method: str = "pearson") -> pd.DataFrame:
        """Compute correlation matrix among numeric OHLCV features.

        Requirements:
            - Measures linear (or monotonic) association between numeric OHLCV fields.
            - Handled pairwise without dropping entire rows unnecessarily.
            - Symmetrical with diagonal values equal to 1.0.
            - Purely descriptive; does not imply causal relationship.

        Args:
            method: Correlation coefficient to compute ('pearson', 'spearman', or 'kendall').
                    Defaults to 'pearson'.

        Returns:
            Labelled pandas DataFrame representing the correlation matrix.

        Raises:
            ValueError: If an unsupported correlation method is provided.
        """
        valid_methods = ("pearson", "spearman", "kendall")
        if method.lower() not in valid_methods:
            raise ValueError(
                f"Unsupported correlation method '{method}'. Must be one of {valid_methods}."
            )

        corr_matrix = self.df[self.numeric_cols].corr(method=method.lower())
        return corr_matrix

    # =========================================================================
    # Exploratory Visualization Methods (Matplotlib & Seaborn)
    # =========================================================================

    def _save_figure(self, fig: plt.Figure, output_path: Optional[Union[str, Path]]) -> None:
        """Helper to safely save figure to destination directory."""
        if output_path is not None:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(out_file, dpi=300, bbox_inches="tight")

    def plot_price_distribution(
        self,
        column: str = "Close",
        bins: int = 30,
        output_path: Optional[Union[str, Path]] = None,
    ) -> plt.Figure:
        """Plot distribution histogram and KDE for a specified price column.

        Args:
            column: Name of the price column to visualize (default: 'Close').
            bins: Number of histogram bins.
            output_path: Optional path to save the chart image.

        Returns:
            Matplotlib Figure object.

        Raises:
            KeyError: If the specified column does not exist in the dataset.
        """
        if column not in self.df.columns:
            raise KeyError(f"Column '{column}' not found in DataFrame columns: {list(self.df.columns)}")

        fig, ax = plt.subplots(figsize=(9, 5))
        series = self.df[column].dropna()

        sns.histplot(
            series,
            bins=bins,
            kde=True,
            ax=ax,
            color="#2563EB",
            edgecolor="white",
            alpha=0.6,
        )

        mean_val = float(series.mean())
        median_val = float(series.median())

        ax.axvline(
            mean_val,
            color="#DC2626",
            linestyle="--",
            linewidth=1.8,
            label=f"Mean: {mean_val:.2f}",
        )
        ax.axvline(
            median_val,
            color="#16A34A",
            linestyle="-.",
            linewidth=1.8,
            label=f"Median: {median_val:.2f}",
        )

        ctx = self._get_title_context()
        ax.set_title(f"Price Distribution: {column} — {ctx}", fontsize=13, fontweight="bold", pad=12)
        ax.set_xlabel(f"{column} Price ($)", fontsize=11)
        ax.set_ylabel("Frequency / Count", fontsize=11)
        ax.legend(frameon=True, loc="upper right")
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        self._save_figure(fig, output_path)
        return fig

    def plot_volume_distribution(
        self,
        bins: int = 30,
        output_path: Optional[Union[str, Path]] = None,
    ) -> plt.Figure:
        """Plot trading volume distribution with statistical central tendency lines.

        Args:
            bins: Number of histogram bins.
            output_path: Optional path to save the chart image.

        Returns:
            Matplotlib Figure object.
        """
        fig, ax = plt.subplots(figsize=(9, 5))
        vol = self.df["Volume"].dropna()

        sns.histplot(
            vol,
            bins=bins,
            kde=True,
            ax=ax,
            color="#0D9488",
            edgecolor="white",
            alpha=0.6,
        )

        mean_vol = float(vol.mean())
        median_vol = float(vol.median())

        ax.axvline(
            mean_vol,
            color="#DC2626",
            linestyle="--",
            linewidth=1.8,
            label=f"Mean Volume: {mean_vol:,.0f}",
        )
        ax.axvline(
            median_vol,
            color="#F59E0B",
            linestyle="-.",
            linewidth=1.8,
            label=f"Median Volume: {median_vol:,.0f}",
        )

        ctx = self._get_title_context()
        ax.set_title(f"Trading Volume Distribution — {ctx}", fontsize=13, fontweight="bold", pad=12)
        ax.set_xlabel("Trading Volume (Shares)", fontsize=11)
        ax.set_ylabel("Frequency / Count", fontsize=11)
        ax.ticklabel_format(style="plain", axis="x")
        ax.legend(frameon=True, loc="upper right")
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        self._save_figure(fig, output_path)
        return fig

    def plot_ohlc_distributions(
        self,
        output_path: Optional[Union[str, Path]] = None,
    ) -> plt.Figure:
        """Plot comparative boxplots across all numeric OHLC columns to visualize dispersion.

        Args:
            output_path: Optional path to save the chart image.

        Returns:
            Matplotlib Figure object.
        """
        price_cols = [c for c in ["Open", "High", "Low", "Close", "Adj Close"] if c in self.df.columns]

        fig, ax = plt.subplots(figsize=(8, 5))
        sns.boxplot(
            data=self.df[price_cols],
            ax=ax,
            palette="Set2",
            showmeans=True,
            meanprops={"marker": "o", "markerfacecolor": "white", "markeredgecolor": "black"},
        )

        ctx = self._get_title_context()
        ax.set_title(f"OHLC Price Boxplot Distributions — {ctx}", fontsize=13, fontweight="bold", pad=12)
        ax.set_xlabel("Price Metric", fontsize=11)
        ax.set_ylabel("Price ($)", fontsize=11)
        ax.grid(True, linestyle=":", alpha=0.6)

        plt.tight_layout()
        self._save_figure(fig, output_path)
        return fig

    def plot_correlation_heatmap(
        self,
        method: str = "pearson",
        output_path: Optional[Union[str, Path]] = None,
        annot: bool = True,
    ) -> plt.Figure:
        """Plot annotated heatmap of the correlation matrix across numerical OHLCV features.

        Args:
            method: Correlation method ('pearson', 'spearman', or 'kendall').
            output_path: Optional path to save the chart image.
            annot: Whether to annotate cells with correlation values.

        Returns:
            Matplotlib Figure object.
        """
        corr = self.compute_correlations(method=method)

        fig, ax = plt.subplots(figsize=(7, 6))
        sns.heatmap(
            corr,
            annot=annot,
            fmt=".3f",
            cmap="coolwarm",
            vmin=-1.0,
            vmax=1.0,
            center=0.0,
            square=True,
            linewidths=0.5,
            cbar_kws={"shrink": 0.8, "label": f"{method.capitalize()} Correlation Coefficient"},
            ax=ax,
        )

        ctx = self._get_title_context()
        ax.set_title(
            f"Feature Correlation Heatmap ({method.capitalize()}) — {ctx}",
            fontsize=13,
            fontweight="bold",
            pad=14,
        )

        plt.tight_layout()
        self._save_figure(fig, output_path)
        return fig

    def plot_high_low_spread(
        self,
        output_path: Optional[Union[str, Path]] = None,
    ) -> plt.Figure:
        """Plot daily High-Low price spread distribution and temporal progression.

        Args:
            output_path: Optional path to save the chart image.

        Returns:
            Matplotlib Figure object with 2 subplots (Time Series and Distribution).
        """
        fig, (ax_ts, ax_hist) = plt.subplots(nrows=2, ncols=1, figsize=(10, 7), sharex=False)

        spread = self.df["High"] - self.df["Low"]

        # 1. Spread over time
        if "Date" in self.df.columns:
            dates = pd.to_datetime(self.df["Date"])
            ax_ts.plot(dates, spread, color="#7C3AED", linewidth=1.5, marker="o", markersize=3)
            ax_ts.set_xlabel("Date", fontsize=10)
        else:
            ax_ts.plot(spread, color="#7C3AED", linewidth=1.5)
            ax_ts.set_xlabel("Observation Index", fontsize=10)

        mean_spread = float(spread.mean())
        ax_ts.axhline(
            mean_spread,
            color="#DC2626",
            linestyle="--",
            linewidth=1.5,
            label=f"Mean Spread: ${mean_spread:.2f}",
        )
        ax_ts.set_ylabel("High - Low Spread ($)", fontsize=10)
        ax_ts.set_title("Daily Price Spread Over Time", fontsize=11, fontweight="bold")
        ax_ts.legend(loc="upper right", frameon=True)
        ax_ts.grid(True, linestyle=":", alpha=0.6)

        # 2. Spread distribution
        sns.histplot(
            spread,
            bins=25,
            kde=True,
            ax=ax_hist,
            color="#9333EA",
            edgecolor="white",
            alpha=0.6,
        )
        ax_hist.axvline(
            mean_spread,
            color="#DC2626",
            linestyle="--",
            linewidth=1.5,
            label=f"Mean: ${mean_spread:.2f}",
        )
        ax_hist.axvline(
            float(spread.median()),
            color="#16A34A",
            linestyle="-.",
            linewidth=1.5,
            label=f"Median: ${float(spread.median()):.2f}",
        )
        ax_hist.set_xlabel("High - Low Spread ($)", fontsize=10)
        ax_hist.set_ylabel("Frequency", fontsize=10)
        ax_hist.set_title("Daily Price Spread Distribution", fontsize=11, fontweight="bold")
        ax_hist.legend(loc="upper right", frameon=True)
        ax_hist.grid(True, linestyle=":", alpha=0.6)

        ctx = self._get_title_context()
        fig.suptitle(f"Daily High-Low Price Spread Analysis — {ctx}", fontsize=13, fontweight="bold", y=1.02)

        plt.tight_layout()
        self._save_figure(fig, output_path)
        return fig


# =============================================================================
# Functional Convenience Wrappers
# =============================================================================


def generate_summary_statistics(
    df: pd.DataFrame, percentiles: Optional[List[float]] = None
) -> pd.DataFrame:
    """Convenience wrapper to compute summary statistics for a stock DataFrame."""
    analyzer = ExploratoryDataAnalyzer(df)
    return analyzer.compute_summary_statistics(percentiles=percentiles)


def compute_correlation_matrix(
    df: pd.DataFrame, method: str = "pearson"
) -> pd.DataFrame:
    """Convenience wrapper to compute correlation matrix for a stock DataFrame."""
    analyzer = ExploratoryDataAnalyzer(df)
    return analyzer.compute_correlations(method=method)


def generate_eda_summary(
    df: pd.DataFrame, ticker: Optional[str] = None
) -> Dict[str, Any]:
    """Convenience wrapper to compute comprehensive price and volume summary dictionary."""
    analyzer = ExploratoryDataAnalyzer(df, ticker=ticker)
    return analyzer.compute_price_and_volume_summary()


def plot_price_distribution(
    df: pd.DataFrame,
    column: str = "Close",
    bins: int = 30,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Convenience wrapper to plot price distribution."""
    analyzer = ExploratoryDataAnalyzer(df)
    return analyzer.plot_price_distribution(column=column, bins=bins, output_path=output_path)


def plot_volume_distribution(
    df: pd.DataFrame,
    bins: int = 30,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Convenience wrapper to plot trading volume distribution."""
    analyzer = ExploratoryDataAnalyzer(df)
    return analyzer.plot_volume_distribution(bins=bins, output_path=output_path)


def plot_ohlc_distributions(
    df: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Convenience wrapper to plot OHLC boxplot distributions."""
    analyzer = ExploratoryDataAnalyzer(df)
    return analyzer.plot_ohlc_distributions(output_path=output_path)


def plot_correlation_heatmap(
    df: pd.DataFrame,
    method: str = "pearson",
    output_path: Optional[Union[str, Path]] = None,
    annot: bool = True,
) -> plt.Figure:
    """Convenience wrapper to plot correlation heatmap."""
    analyzer = ExploratoryDataAnalyzer(df)
    return analyzer.plot_correlation_heatmap(method=method, output_path=output_path, annot=annot)


def plot_high_low_spread(
    df: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Convenience wrapper to plot High-Low spread progression and distribution."""
    analyzer = ExploratoryDataAnalyzer(df)
    return analyzer.plot_high_low_spread(output_path=output_path)
