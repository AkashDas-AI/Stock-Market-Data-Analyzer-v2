"""Interactive charting module using Plotly.

Responsibility:
    Create interactive, standalone Plotly visualizations including candlestick charts
    with volume subplots, moving average overlays, returns trajectories, underwater
    drawdown curves, rolling volatility curves, and correlation heatmaps.

Architecture Boundaries (Phase 8):
    - Generates standalone Plotly Figure objects.
    - Exports standalone interactive HTML files (loading Plotly JS via external CDN, independent of Streamlit).
    - NO Streamlit dashboard UI or server sessions (Phase 9).
    - NO automated investment recommendations (Phase 10).
    - NO report generation (Phase 11).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
REQUIRED_CANDLE_COLUMNS: List[str] = ["Date", "Open", "High", "Low", "Close"]


class InteractiveChartGenerator:
    """Generates publication-quality interactive Plotly visualizations."""

    def __init__(self, df: pd.DataFrame, ticker: Optional[str] = None) -> None:
        """Initialize the interactive chart generator with a stock DataFrame.

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
                f"Expected pandas DataFrame for interactive chart generation, received {type(df).__name__}."
            )
        if df.empty:
            raise EmptyDataError("Cannot generate interactive charts from an empty DataFrame.")

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

    def _save_figure(self, fig: go.Figure, output_path: Optional[Union[str, Path]]) -> None:
        """Helper to export Plotly figure to standalone HTML via external CDN.

        Note on External CDN Loading:
            Exported HTML files load Plotly JavaScript dynamically through an external CDN
            (include_plotlyjs="cdn"). This keeps HTML file sizes compact (~15-20 KB),
            but requires an active internet connection in the client browser to load the Plotly JS
            library. It does not embed the full ~3.5 MB library inline for offline execution.
        """
        if output_path is not None:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(str(out_file), include_plotlyjs="cdn", full_html=True)

    # =========================================================================
    # 1. Interactive Candlestick Chart (with optional Volume Subplot)
    # =========================================================================

    def create_candlestick_chart(
        self,
        include_volume: bool = True,
        output_path: Optional[Union[str, Path]] = None,
    ) -> go.Figure:
        """Create an interactive financial candlestick chart with hover details and range selectors.

        Args:
            include_volume: Whether to include a shared-axis volume subplot.
            output_path: Optional HTML file path to export standalone visualization.

        Returns:
            Plotly graph_objects Figure.

        Raises:
            MissingColumnError: If Open, High, or Low columns are missing.
        """
        missing = [c for c in REQUIRED_CANDLE_COLUMNS if c not in self.df.columns]
        if missing:
            raise MissingColumnError(f"Candlestick chart requires columns: {missing}")

        has_volume = include_volume and ("Volume" in self.df.columns)
        ctx = self._get_title_context()

        if has_volume:
            fig = make_subplots(
                rows=2,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.75, 0.25],
            )

            # 1. Candlestick trace
            fig.add_trace(
                go.Candlestick(
                    x=self.df["Date"],
                    open=self.df["Open"],
                    high=self.df["High"],
                    low=self.df["Low"],
                    close=self.df["Close"],
                    name="OHLC Price",
                    increasing_line_color="#16A34A",
                    decreasing_line_color="#DC2626",
                ),
                row=1,
                col=1,
            )

            # 2. Volume bar trace
            colors = [
                "#16A34A" if c >= o else "#DC2626"
                for o, c in zip(self.df["Open"], self.df["Close"])
            ]
            fig.add_trace(
                go.Bar(
                    x=self.df["Date"],
                    y=self.df["Volume"],
                    name="Trading Volume",
                    marker_color=colors,
                    opacity=0.7,
                ),
                row=2,
                col=1,
            )

            fig.update_layout(
                title=f"Interactive Candlestick & Volume Chart — {ctx}",
                yaxis_title="Price ($)",
                yaxis2_title="Volume",
                xaxis2_title="Date",
                xaxis_rangeslider_visible=False,
                xaxis2_rangeslider_visible=True,
                hovermode="x unified",
                template="plotly_white",
            )
        else:
            fig = go.Figure(
                data=[
                    go.Candlestick(
                        x=self.df["Date"],
                        open=self.df["Open"],
                        high=self.df["High"],
                        low=self.df["Low"],
                        close=self.df["Close"],
                        name="OHLC Price",
                        increasing_line_color="#16A34A",
                        decreasing_line_color="#DC2626",
                    )
                ]
            )

            fig.update_layout(
                title=f"Interactive Candlestick Chart — {ctx}",
                yaxis_title="Price ($)",
                xaxis_title="Date",
                xaxis_rangeslider_visible=True,
                hovermode="x unified",
                template="plotly_white",
            )

        # Configure range selector buttons
        fig.update_xaxes(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=3, label="3m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(step="all", label="All"),
                ])
            )
        )

        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 2. Interactive Moving Averages Chart
    # =========================================================================

    def create_moving_averages_chart(
        self,
        show_sma_20: bool = True,
        show_sma_50: bool = True,
        show_ema_20: bool = True,
        output_path: Optional[Union[str, Path]] = None,
    ) -> go.Figure:
        """Create interactive moving average overlay chart (Close, SMA 20, SMA 50, EMA 20).

        Auto-computes moving averages using TechnicalIndicators if absent in df.
        Allows toggling visibility of individual indicators.

        Args:
            show_sma_20: Whether to display SMA 20 overlay line (default: True).
            show_sma_50: Whether to display SMA 50 overlay line (default: True).
            show_ema_20: Whether to display EMA 20 overlay line (default: True).
            output_path: Optional HTML file path to export standalone visualization.

        Returns:
            Plotly graph_objects Figure.
        """
        work_df = self.df
        needed_mas = ["SMA_20", "SMA_50", "EMA_20"]
        if not all(col in work_df.columns for col in needed_mas):
            ti = TechnicalIndicators(self.df, price_column="Close")
            work_df = ti.calculate_moving_averages()

        fig = go.Figure()

        # Close Price trace
        fig.add_trace(
            go.Scatter(
                x=work_df["Date"],
                y=work_df["Close"],
                mode="lines",
                name="Close Price",
                line=dict(color="#1E293B", width=1.8),
            )
        )

        # SMA 20
        if show_sma_20 and "SMA_20" in work_df.columns and work_df["SMA_20"].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=work_df["Date"],
                    y=work_df["SMA_20"],
                    mode="lines",
                    name="SMA 20",
                    line=dict(color="#2563EB", width=1.8),
                )
            )

        # EMA 20
        if show_ema_20 and "EMA_20" in work_df.columns and work_df["EMA_20"].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=work_df["Date"],
                    y=work_df["EMA_20"],
                    mode="lines",
                    name="EMA 20",
                    line=dict(color="#D97706", width=1.8, dash="dash"),
                )
            )

        # SMA 50
        if show_sma_50 and "SMA_50" in work_df.columns and work_df["SMA_50"].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=work_df["Date"],
                    y=work_df["SMA_50"],
                    mode="lines",
                    name="SMA 50",
                    line=dict(color="#DC2626", width=2.0),
                )
            )

        active_inds = ["Close"]
        if show_sma_20:
            active_inds.append("SMA 20")
        if show_sma_50:
            active_inds.append("SMA 50")
        if show_ema_20:
            active_inds.append("EMA 20")
        ind_str = ", ".join(active_inds)

        ctx = self._get_title_context()
        fig.update_layout(
            title=f"Technical Moving Averages ({ind_str}) — {ctx}",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            hovermode="x unified",
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )

        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 3. Interactive Trading Volume Chart
    # =========================================================================

    def create_volume_chart(
        self,
        output_path: Optional[Union[str, Path]] = None,
    ) -> go.Figure:
        """Create interactive volume bar chart color-coded by daily price action.

        Args:
            output_path: Optional HTML file path to export standalone visualization.

        Returns:
            Plotly graph_objects Figure.

        Raises:
            MissingColumnError: If Volume column is missing.
        """
        if "Volume" not in self.df.columns:
            raise MissingColumnError("Trading volume chart requires 'Volume' column.")

        if "Open" in self.df.columns and "Close" in self.df.columns:
            colors = [
                "#16A34A" if c >= o else "#DC2626"
                for o, c in zip(self.df["Open"], self.df["Close"])
            ]
        else:
            colors = ["#0284C7"] * len(self.df)

        fig = go.Figure(
            data=[
                go.Bar(
                    x=self.df["Date"],
                    y=self.df["Volume"],
                    marker_color=colors,
                    name="Trading Volume",
                    opacity=0.75,
                )
            ]
        )

        mean_vol = float(self.df["Volume"].mean())
        fig.add_hline(
            y=mean_vol,
            line_dash="dash",
            line_color="#F59E0B",
            annotation_text=f"Mean: {mean_vol:,.0f}",
            annotation_position="top left",
        )

        ctx = self._get_title_context()
        fig.update_layout(
            title=f"Trading Volume History — {ctx}",
            xaxis_title="Date",
            yaxis_title="Volume (Shares)",
            hovermode="x unified",
            template="plotly_white",
        )

        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 4. Interactive Daily Returns Chart
    # =========================================================================

    def create_daily_returns_chart(
        self,
        output_path: Optional[Union[str, Path]] = None,
    ) -> go.Figure:
        """Create interactive daily returns bar chart with zero reference baseline.

        Args:
            output_path: Optional HTML file path to export standalone visualization.

        Returns:
            Plotly graph_objects Figure.
        """
        if "Daily_Return" in self.df.columns:
            daily_ret = self.df["Daily_Return"]
        else:
            analyzer = ReturnAnalyzer(self.df, price_column="Close")
            daily_ret = analyzer.calculate_daily_returns()

        colors = ["#16A34A" if r >= 0 else "#DC2626" for r in daily_ret.fillna(0.0)]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=self.df["Date"],
                    y=daily_ret * 100.0,
                    marker_color=colors,
                    name="Daily Return (%)",
                )
            ]
        )

        fig.add_hline(y=0.0, line_color="#475569", line_width=1.0)

        ctx = self._get_title_context()
        fig.update_layout(
            title=f"Daily Percentage Returns — {ctx}",
            xaxis_title="Date",
            yaxis_title="Daily Return (%)",
            hovermode="x unified",
            template="plotly_white",
        )

        self._save_figure(fig, output_path)
        return fig

    def create_daily_returns_distribution_chart(
        self,
        bins: int = 30,
        output_path: Optional[Union[str, Path]] = None,
    ) -> go.Figure:
        """Create interactive daily return distribution histogram with mean and standard deviation markers.

        Args:
            bins: Number of histogram bins.
            output_path: Optional HTML file path to export standalone visualization.

        Returns:
            Plotly graph_objects Figure.
        """
        if "Daily_Return" in self.df.columns:
            daily_ret = self.df["Daily_Return"].dropna() * 100.0
        else:
            analyzer = ReturnAnalyzer(self.df, price_column="Close")
            daily_ret = analyzer.calculate_daily_returns().dropna() * 100.0

        fig = go.Figure(
            data=[
                go.Histogram(
                    x=daily_ret,
                    nbinsx=bins,
                    name="Daily Return (%)",
                    marker_color="#3B82F6",
                    opacity=0.75,
                )
            ]
        )

        mean_val = float(daily_ret.mean()) if not daily_ret.empty else 0.0
        std_val = float(daily_ret.std(ddof=1)) if len(daily_ret) > 1 else 0.0

        fig.add_vline(
            x=mean_val,
            line_dash="dash",
            line_color="#DC2626",
            annotation_text=f"Mean: {mean_val:.2f}%",
            annotation_position="top left",
        )
        if std_val > 0:
            fig.add_vline(
                x=mean_val + std_val,
                line_dash="dot",
                line_color="#16A34A",
                annotation_text=f"+1σ: {mean_val+std_val:.2f}%",
                annotation_position="top right",
            )
            fig.add_vline(
                x=mean_val - std_val,
                line_dash="dot",
                line_color="#16A34A",
                annotation_text=f"-1σ: {mean_val-std_val:.2f}%",
                annotation_position="top left",
            )

        ctx = self._get_title_context()
        fig.update_layout(
            title=f"Daily Return Distribution — {ctx}",
            xaxis_title="Daily Return (%)",
            yaxis_title="Frequency",
            template="plotly_white",
        )

        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 5. Interactive Cumulative Returns Chart
    # =========================================================================

    def create_cumulative_returns_chart(
        self,
        output_path: Optional[Union[str, Path]] = None,
    ) -> go.Figure:
        """Create interactive cumulative compound return trajectory chart.

        Args:
            output_path: Optional HTML file path to export standalone visualization.

        Returns:
            Plotly graph_objects Figure.
        """
        if "Cumulative_Return" in self.df.columns:
            cum_ret = self.df["Cumulative_Return"]
        else:
            analyzer = ReturnAnalyzer(self.df, price_column="Close")
            cum_ret = analyzer.calculate_cumulative_returns()

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=self.df["Date"],
                    y=cum_ret * 100.0,
                    mode="lines",
                    name="Cumulative Compound Return (%)",
                    line=dict(color="#059669", width=2.0),
                )
            ]
        )

        fig.add_hline(y=0.0, line_dash="dash", line_color="#94A3B8")

        ctx = self._get_title_context()
        fig.update_layout(
            title=f"Cumulative Compound Return Trajectory — {ctx}",
            xaxis_title="Date",
            yaxis_title="Cumulative Return (%)",
            hovermode="x unified",
            template="plotly_white",
        )

        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 6. Interactive Underwater Drawdown Chart
    # =========================================================================

    def create_drawdown_chart(
        self,
        output_path: Optional[Union[str, Path]] = None,
    ) -> go.Figure:
        """Create interactive underwater drawdown plot with MDD point annotation.

        Args:
            output_path: Optional HTML file path to export standalone visualization.

        Returns:
            Plotly graph_objects Figure.
        """
        risk_analyzer = RiskAnalyzer(self.df, price_column="Close")
        dd = risk_analyzer.calculate_drawdown_series() * 100.0
        mdd_res = risk_analyzer.calculate_max_drawdown()

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=self.df["Date"],
                    y=dd,
                    mode="lines",
                    name="Drawdown (%)",
                    line=dict(color="#DC2626", width=1.5),
                    fill="tozeroy",
                    fillcolor="rgba(239, 68, 68, 0.25)",
                )
            ]
        )

        fig.add_hline(y=0.0, line_color="#475569", line_width=1.0)

        # Annotate MDD trough if available
        if mdd_res["trough_date"] is not None and not np.isnan(mdd_res["max_drawdown_pct"]):
            fig.add_trace(
                go.Scatter(
                    x=[mdd_res["trough_date"]],
                    y=[mdd_res["max_drawdown_pct"]],
                    mode="markers+text",
                    name="Maximum Drawdown",
                    marker=dict(color="#7F1D1D", size=10, symbol="x"),
                    text=[f"MDD: {mdd_res['max_drawdown_pct']:.2f}%"],
                    textposition="bottom center",
                )
            )

        ctx = self._get_title_context()
        fig.update_layout(
            title=f"Historical Drawdown from Peak (Underwater Plot) — {ctx}",
            xaxis_title="Date",
            yaxis_title="Drawdown (%)",
            hovermode="x unified",
            template="plotly_white",
        )

        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 7. Interactive Rolling Volatility Chart
    # =========================================================================

    def create_rolling_volatility_chart(
        self,
        windows: Union[int, Sequence[int]] = (21, 63),
        window: Optional[Union[int, Sequence[int]]] = None,
        annualization_factor: int = 252,
        output_path: Optional[Union[str, Path]] = None,
    ) -> go.Figure:
        """Create interactive rolling annualized volatility line chart using RiskAnalyzer.

        Supports single or multiple rolling windows (defaults to 21-day and 63-day,
        representing approximately 1-month and 3-month lookback windows).

        Args:
            windows: Rolling window length(s) in days. Defaults to (21, 63).
            window: Backward-compatible alias for a single or sequence of windows.
            annualization_factor: Scaling factor (default: 252).
            output_path: Optional HTML file path to export standalone visualization.

        Returns:
            Plotly graph_objects Figure.
        """
        raw_windows = window if window is not None else windows
        if isinstance(raw_windows, (int, np.integer)):
            target_windows = [int(raw_windows)]
        else:
            target_windows = [int(w) for w in raw_windows]

        fig = go.Figure()
        colors = ["#9333EA", "#2563EB", "#059669", "#D97706", "#DC2626"]
        risk_analyzer = RiskAnalyzer(self.df, price_column="Close")

        for idx, w in enumerate(target_windows):
            color = colors[idx % len(colors)]
            # Delegate calculation strictly to analytical RiskAnalyzer
            rolling_vol_dec = risk_analyzer.calculate_rolling_volatility(
                window=w, annualization_factor=annualization_factor
            )
            rolling_annual_vol = rolling_vol_dec * 100.0
            fig.add_trace(
                go.Scatter(
                    x=self.df["Date"],
                    y=rolling_annual_vol,
                    mode="lines",
                    name=f"Rolling {w}d Vol (%)",
                    line=dict(color=color, width=1.8),
                )
            )

        primary_w = target_windows[0]
        primary_vol = risk_analyzer.calculate_rolling_volatility(
            window=primary_w, annualization_factor=annualization_factor
        ) * 100.0
        mean_vol = float(primary_vol.dropna().mean()) if not primary_vol.dropna().empty else 0.0
        if mean_vol > 0:
            fig.add_hline(
                y=mean_vol,
                line_dash="dash",
                line_color="#F59E0B",
                annotation_text=f"{primary_w}d Mean: {mean_vol:.1f}%",
                annotation_position="top left",
            )

        ctx = self._get_title_context()
        w_label = ", ".join(f"{w}d" for w in target_windows)
        fig.update_layout(
            title=f"Rolling Annualized Volatility ({w_label}) — {ctx}",
            xaxis_title="Date",
            yaxis_title="Annualized Volatility (%)",
            hovermode="x unified",
            template="plotly_white",
        )

        self._save_figure(fig, output_path)
        return fig

    # =========================================================================
    # 8. Interactive Correlation Heatmap
    # =========================================================================

    def create_correlation_heatmap(
        self,
        method: str = "pearson",
        output_path: Optional[Union[str, Path]] = None,
    ) -> go.Figure:
        """Create interactive correlation heatmap with annotated coefficients and hover tooltips.

        Args:
            method: Correlation method ('pearson', 'spearman', 'kendall').
            output_path: Optional HTML file path to export standalone visualization.

        Returns:
            Plotly graph_objects Figure.
        """
        eda_analyzer = ExploratoryDataAnalyzer(self.df, ticker=self.ticker)
        corr_matrix = eda_analyzer.compute_correlations(method=method)

        features = list(corr_matrix.columns)
        z_vals = corr_matrix.values

        # Annotated text values
        text_vals = [[f"{val:.3f}" for val in row] for row in z_vals]

        fig = go.Figure(
            data=[
                go.Heatmap(
                    z=z_vals,
                    x=features,
                    y=features,
                    text=text_vals,
                    texttemplate="%{text}",
                    textfont={"size": 11},
                    colorscale="RdBu",
                    zmin=-1.0,
                    zmax=1.0,
                    colorbar=dict(title=f"{method.capitalize()} Corr"),
                )
            ]
        )

        ctx = self._get_title_context()
        fig.update_layout(
            title=f"Feature Correlation Heatmap ({method.capitalize()}) — {ctx}",
            xaxis_title="Feature",
            yaxis_title="Feature",
            template="plotly_white",
            yaxis_autorange="reversed",
        )

        self._save_figure(fig, output_path)
        return fig


# =============================================================================
# Functional Convenience Wrappers for Interactive Charts
# =============================================================================


def create_candlestick_chart(
    df: pd.DataFrame,
    include_volume: bool = True,
    ticker: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> go.Figure:
    """Convenience wrapper for interactive Candlestick and volume chart."""
    generator = InteractiveChartGenerator(df, ticker=ticker)
    return generator.create_candlestick_chart(include_volume=include_volume, output_path=output_path)


def create_moving_averages_chart(
    df: pd.DataFrame,
    show_sma_20: bool = True,
    show_sma_50: bool = True,
    show_ema_20: bool = True,
    ticker: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> go.Figure:
    """Convenience wrapper for interactive moving average chart."""
    generator = InteractiveChartGenerator(df, ticker=ticker)
    return generator.create_moving_averages_chart(
        show_sma_20=show_sma_20,
        show_sma_50=show_sma_50,
        show_ema_20=show_ema_20,
        output_path=output_path,
    )


def create_daily_returns_distribution_chart(
    df: pd.DataFrame,
    bins: int = 30,
    ticker: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> go.Figure:
    """Convenience wrapper for interactive daily return distribution histogram."""
    generator = InteractiveChartGenerator(df, ticker=ticker)
    return generator.create_daily_returns_distribution_chart(bins=bins, output_path=output_path)


def create_volume_chart(
    df: pd.DataFrame,
    ticker: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> go.Figure:
    """Convenience wrapper for interactive trading volume chart."""
    generator = InteractiveChartGenerator(df, ticker=ticker)
    return generator.create_volume_chart(output_path=output_path)


def create_daily_returns_chart(
    df: pd.DataFrame,
    ticker: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> go.Figure:
    """Convenience wrapper for interactive daily returns chart."""
    generator = InteractiveChartGenerator(df, ticker=ticker)
    return generator.create_daily_returns_chart(output_path=output_path)


def create_cumulative_returns_chart(
    df: pd.DataFrame,
    ticker: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> go.Figure:
    """Convenience wrapper for interactive cumulative compound returns chart."""
    generator = InteractiveChartGenerator(df, ticker=ticker)
    return generator.create_cumulative_returns_chart(output_path=output_path)


def create_drawdown_chart(
    df: pd.DataFrame,
    ticker: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> go.Figure:
    """Convenience wrapper for interactive underwater drawdown chart."""
    generator = InteractiveChartGenerator(df, ticker=ticker)
    return generator.create_drawdown_chart(output_path=output_path)


def create_rolling_volatility_chart(
    df: pd.DataFrame,
    windows: Union[int, Sequence[int]] = (21, 63),
    window: Optional[Union[int, Sequence[int]]] = None,
    annualization_factor: int = 252,
    ticker: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> go.Figure:
    """Convenience wrapper for interactive rolling volatility chart."""
    generator = InteractiveChartGenerator(df, ticker=ticker)
    return generator.create_rolling_volatility_chart(
        windows=windows, window=window, annualization_factor=annualization_factor, output_path=output_path
    )


def create_correlation_heatmap(
    df: pd.DataFrame,
    method: str = "pearson",
    ticker: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> go.Figure:
    """Convenience wrapper for interactive correlation heatmap."""
    generator = InteractiveChartGenerator(df, ticker=ticker)
    return generator.create_correlation_heatmap(method=method, output_path=output_path)
