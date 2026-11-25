"""Analytical insights and evidence-based market interpretation engine.

Responsibility:
    Translate quantitative indicators, returns, risk metrics, and exploratory
    distributions into understandable, deterministic financial observations.
    Synthesize positive and negative observations, risk characteristics, and
    data limitations without generating predictive claims or investment advice.

Boundaries:
    This module performs analytical interpretation only. It strictly avoids:
    - Investment recommendations (buy/sell/hold).
    - Price predictions or target price claims.
    - Black-box scoring or arbitrary rating scales.
    - Duplication of underlying analytical calculations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from stock_analyzer.analysis.eda import ExploratoryDataAnalyzer
from stock_analyzer.analysis.indicators import TechnicalIndicators
from stock_analyzer.analysis.returns import ReturnAnalyzer
from stock_analyzer.analysis.risk import RiskAnalyzer
from stock_analyzer.data.exceptions import (
    EmptyDataError,
    MissingColumnError,
    StockDataError,
    DataValidationError,
)

# Standard market data columns required for comprehensive insight generation
REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]


class InsightCategory(str, Enum):
    """Categorical classification of generated financial insights."""

    PRICE_TREND = "Price Trend"
    MOVING_AVERAGES = "Moving Averages"
    RETURNS = "Returns Analysis"
    RISK_AND_VOLATILITY = "Risk & Volatility"
    TRADING_VOLUME = "Trading Volume"
    CORRELATION = "Correlation"
    OVERALL_SUMMARY = "Overall Summary"


class InsightSeverity(str, Enum):
    """Semantic sentiment or operational tone of an analytical observation."""

    INFO = "info"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    WARNING = "warning"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class MarketInsight:
    """Structured, reproducible financial insight unit with empirical evidence."""

    category: InsightCategory
    title: str
    observation: str
    evidence: Dict[str, Any]
    severity: InsightSeverity
    description: str
    limitations: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert insight to standard dictionary representation."""
        return {
            "category": self.category.value,
            "title": self.title,
            "observation": self.observation,
            "evidence": self.evidence,
            "severity": self.severity.value,
            "description": self.description,
            "limitations": self.limitations,
        }


@dataclass
class InsightSummary:
    """Comprehensive analytical synthesis across all evaluated dimensions."""

    ticker: str
    period_start: Optional[str]
    period_end: Optional[str]
    observation_count: int
    positive_observations: List[str] = field(default_factory=list)
    negative_observations: List[str] = field(default_factory=list)
    risk_observations: List[str] = field(default_factory=list)
    data_limitations: List[str] = field(default_factory=list)
    insights: List[MarketInsight] = field(default_factory=list)
    is_synthetic: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary representation."""
        return {
            "ticker": self.ticker,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "observation_count": self.observation_count,
            "positive_observations": self.positive_observations,
            "negative_observations": self.negative_observations,
            "risk_observations": self.risk_observations,
            "data_limitations": self.data_limitations,
            "insights": [ins.to_dict() for ins in self.insights],
            "is_synthetic": self.is_synthetic,
        }


@dataclass
class InsightThresholds:
    """Configurable numerical thresholds with documented analytical rationales."""

    # Volatility thresholds (Annualized 252-day basis)
    # Rationale: <15% is typical of low-beta/broad market defensive indices; >30% represents elevated dispersion.
    volatility_low_threshold: float = 0.15
    volatility_high_threshold: float = 0.30

    # Drawdown thresholds (Peak-to-trough percentage decline)
    # Rationale: -10% represents standard market correction; -20% represents formal bear market territory.
    drawdown_correction_threshold: float = -0.10
    drawdown_bear_threshold: float = -0.20

    # Trading volume baseline and surge multipliers
    # Rationale: 20 trading days represents approx 1 calendar month of trading activity baseline.
    volume_baseline_window: int = 20
    volume_surge_multiplier: float = 1.5
    volume_dryup_multiplier: float = 0.5

    # Linear correlation strength benchmarks (|r|)
    # Rationale: Standard statistical conventions for Pearson r correlation magnitude.
    correlation_strong_threshold: float = 0.70
    correlation_moderate_threshold: float = 0.40

    # Moving average window configurations
    short_ma_window: int = 20
    long_ma_window: int = 50


class StockInsightAnalyzer:
    """Primary interpretation engine translating quantitative metrics into structured insights.

    Reuses existing analytical modules (TechnicalIndicators, ReturnAnalyzer, RiskAnalyzer,
    ExploratoryDataAnalyzer) while guaranteeing input DataFrame immutability, deterministic
    execution, and evidence-grounded textual observations.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        ticker: Optional[str] = None,
        price_column: str = "Close",
        thresholds: Optional[InsightThresholds] = None,
    ) -> None:
        """Initialize insight engine with cleaned stock DataFrame.

        Args:
            df: Cleaned stock DataFrame containing standard OHLCV columns.
            ticker: Optional ticker symbol. If omitted, extracted from df.attrs or defaulted to 'STOCK'.
            price_column: Column name used for price and return calculations. Defaults to 'Close'.
            thresholds: Optional custom InsightThresholds configuration.

        Raises:
            TypeError: If df is not a pandas DataFrame.
            EmptyDataError: If df is empty.
            MissingColumnError: If df lacks required columns or price_column.
            DataValidationError: If price_column is not numeric.
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError(
                f"Expected pandas DataFrame for insight analysis, received {type(df).__name__}."
            )
        if df.empty:
            raise EmptyDataError("Cannot generate insights from an empty DataFrame.")

        if price_column not in df.columns:
            raise MissingColumnError(
                f"Specified price column '{price_column}' not found in DataFrame columns: {list(df.columns)}."
            )

        if not pd.api.types.is_numeric_dtype(df[price_column]):
            raise DataValidationError(
                f"Price column '{price_column}' must have numeric data type, found {df[price_column].dtype}."
            )

        # Defensive deep copy preserving caller DataFrame immutability
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
        self.price_column = price_column
        self.ticker = str(ticker or df.attrs.get("ticker", "STOCK")).upper()
        self.is_synthetic = bool(df.attrs.get("is_synthetic", False))
        self.thresholds = thresholds or InsightThresholds()

        # Instantiate underlying domain analyzers reusing established logic
        self._indicators = TechnicalIndicators(self.df, price_column=self.price_column)
        self._returns = ReturnAnalyzer(self.df, price_column=self.price_column)
        self._risk = RiskAnalyzer(self.df, price_column=self.price_column)
        self._eda = ExploratoryDataAnalyzer(self.df, ticker=self.ticker)

    # =========================================================================
    # A. Price Trend Insights
    # =========================================================================

    def generate_price_trend_insights(self) -> List[MarketInsight]:
        """Evaluate start-to-end price trajectory, net change, and directional momentum."""
        insights: List[MarketInsight] = []
        n_obs = len(self.df)
        if n_obs < 2:
            insights.append(
                MarketInsight(
                    category=InsightCategory.PRICE_TREND,
                    title="Insufficient Price History",
                    observation=f"Dataset contains only {n_obs} observation; multi-session trend cannot be evaluated.",
                    evidence={"observation_count": n_obs},
                    severity=InsightSeverity.INFO,
                    description="At least two consecutive trading sessions are required to compute price trajectory.",
                    limitations="Single-observation data points provide a static snapshot without directional context.",
                )
            )
            return insights

        prices = self.df[self.price_column].dropna()
        if len(prices) < 2:
            return insights

        first_close = float(prices.iloc[0])
        latest_close = float(prices.iloc[-1])
        abs_change = latest_close - first_close
        pct_change = (abs_change / first_close) if first_close != 0 else 0.0

        first_date = str(self.df["Date"].iloc[0]) if "Date" in self.df.columns else "start"
        latest_date = str(self.df["Date"].iloc[-1]) if "Date" in self.df.columns else "end"

        # Determine directional sentiment
        if abs_change > 0:
            severity = InsightSeverity.POSITIVE
            direction_desc = "upward price appreciation"
            obs_text = (
                f"The stock demonstrated positive overall performance over the selected period, "
                f"advancing by {abs_change:+.2f} ({pct_change:+.2%}) from ${first_close:.2f} "
                f"on {first_date} to ${latest_close:.2f} on {latest_date}."
            )
        elif abs_change < 0:
            severity = InsightSeverity.NEGATIVE
            direction_desc = "net price contraction"
            obs_text = (
                f"The stock experienced negative overall performance over the selected period, "
                f"declining by {abs_change:+.2f} ({pct_change:+.2%}) from ${first_close:.2f} "
                f"on {first_date} to ${latest_close:.2f} on {latest_date}."
            )
        else:
            severity = InsightSeverity.NEUTRAL
            direction_desc = "flat price performance"
            obs_text = (
                f"The stock closed unchanged at ${latest_close:.2f} across the selected period "
                f"between {first_date} and {latest_date}."
            )

        evidence = {
            "first_close": round(first_close, 4),
            "latest_close": round(latest_close, 4),
            "absolute_change": round(abs_change, 4),
            "percentage_change": round(pct_change, 6),
            "period_start_date": first_date,
            "period_end_date": latest_date,
            "total_observations": n_obs,
        }

        insights.append(
            MarketInsight(
                category=InsightCategory.PRICE_TREND,
                title=f"Net Trajectory: {direction_desc.capitalize()}",
                observation=obs_text,
                evidence=evidence,
                severity=severity,
                description=(
                    f"Overall price change compares the earliest closing price against the latest "
                    f"recorded observation in the active window."
                ),
                limitations=(
                    "Start-to-end price comparison evaluates endpoints only and does not capture "
                    "interim volatility or intra-period high/low extremes."
                ),
            )
        )

        return insights

    # =========================================================================
    # B. Moving Average Insights
    # =========================================================================

    def generate_moving_average_insights(self) -> List[MarketInsight]:
        """Evaluate closing price positions relative to SMA 20, SMA 50, and EMA 20."""
        insights: List[MarketInsight] = []
        n_obs = len(self.df)
        prices = self.df[self.price_column]
        latest_close = float(prices.iloc[-1])

        # 1. Evaluate SMA 20 (Short-term trend, ~1 month)
        if n_obs >= self.thresholds.short_ma_window:
            sma_20_series = self._indicators.calculate_sma_20()
            latest_sma_20 = sma_20_series.iloc[-1]
            if not np.isnan(latest_sma_20):
                diff_sma_20 = latest_close - latest_sma_20
                pct_sma_20 = (diff_sma_20 / latest_sma_20) if latest_sma_20 != 0 else 0.0

                if diff_sma_20 >= 0:
                    sev = InsightSeverity.POSITIVE
                    rel_text = "above"
                    implication = "indicating short-term positive momentum relative to the 1-month average."
                else:
                    sev = InsightSeverity.NEGATIVE
                    rel_text = "below"
                    implication = "indicating short-term downward pressure relative to the 1-month average."

                insights.append(
                    MarketInsight(
                        category=InsightCategory.MOVING_AVERAGES,
                        title=f"Price vs SMA 20: Trading {rel_text.capitalize()} 1-Month Trend",
                        observation=(
                            f"The latest closing price of ${latest_close:.2f} is trading {rel_text} "
                            f"its 20-day Simple Moving Average (${latest_sma_20:.2f}) by "
                            f"{diff_sma_20:+.2f} ({pct_sma_20:+.2%}), {implication}"
                        ),
                        evidence={
                            "latest_close": round(latest_close, 4),
                            "sma_20": round(float(latest_sma_20), 4),
                            "diff_dollars": round(diff_sma_20, 4),
                            "diff_percentage": round(pct_sma_20, 6),
                            "window_size": 20,
                        },
                        severity=sev,
                        description="Compares the latest closing price to the 20-day simple arithmetic moving average.",
                        limitations=(
                            "Moving averages are lagging trend-following metrics and do not predict "
                            "turning points or guarantee future price levels."
                        ),
                    )
                )
        else:
            insights.append(
                MarketInsight(
                    category=InsightCategory.MOVING_AVERAGES,
                    title="SMA 20 Unavailable: Insufficient History",
                    observation=(
                        f"Dataset contains {n_obs} observations, which is fewer than the 20 trading sessions "
                        f"required to compute SMA 20 without lookback bias."
                    ),
                    evidence={"observation_count": n_obs, "required_minimum": 20},
                    severity=InsightSeverity.INFO,
                    description="A 20-day simple moving average requires at least 20 historical daily bars.",
                    limitations="Early observations in truncated windows contain NaN values by design.",
                )
            )

        # 2. Evaluate SMA 50 (Medium-term trend, ~2.5 months)
        if n_obs >= self.thresholds.long_ma_window:
            sma_50_series = self._indicators.calculate_sma_50()
            latest_sma_50 = sma_50_series.iloc[-1]
            if not np.isnan(latest_sma_50):
                diff_sma_50 = latest_close - latest_sma_50
                pct_sma_50 = (diff_sma_50 / latest_sma_50) if latest_sma_50 != 0 else 0.0

                if diff_sma_50 >= 0:
                    sev = InsightSeverity.POSITIVE
                    rel_text = "above"
                    implication = "consistent with a constructive medium-term trend structure."
                else:
                    sev = InsightSeverity.NEGATIVE
                    rel_text = "below"
                    implication = "consistent with medium-term trend softening."

                insights.append(
                    MarketInsight(
                        category=InsightCategory.MOVING_AVERAGES,
                        title=f"Price vs SMA 50: Trading {rel_text.capitalize()} Medium-Term Benchmark",
                        observation=(
                            f"The latest closing price of ${latest_close:.2f} is positioned {rel_text} "
                            f"its 50-day Simple Moving Average (${latest_sma_50:.2f}) by "
                            f"{diff_sma_50:+.2f} ({pct_sma_50:+.2%}), {implication}"
                        ),
                        evidence={
                            "latest_close": round(latest_close, 4),
                            "sma_50": round(float(latest_sma_50), 4),
                            "diff_dollars": round(diff_sma_50, 4),
                            "diff_percentage": round(pct_sma_50, 6),
                            "window_size": 50,
                        },
                        severity=sev,
                        description="Compares the latest closing price to the 50-day simple moving average.",
                        limitations="The 50-day moving average reflects significant lookback smoothing and reacts slowly to sharp inflections.",
                    )
                )

                # 3. Evaluate Dual MA Relationship (SMA 20 vs SMA 50)
                if n_obs >= self.thresholds.short_ma_window:
                    latest_sma_20 = self._indicators.calculate_sma_20().iloc[-1]
                    if not np.isnan(latest_sma_20):
                        ma_diff = latest_sma_20 - latest_sma_50
                        ma_pct = (ma_diff / latest_sma_50) if latest_sma_50 != 0 else 0.0
                        if ma_diff >= 0:
                            ma_sev = InsightSeverity.POSITIVE
                            ma_obs = (
                                f"The 20-day SMA (${latest_sma_20:.2f}) is situated above the 50-day SMA "
                                f"(${latest_sma_50:.2f}) by {ma_diff:+.2f} ({ma_pct:+.2%}), indicating "
                                f"that recent 1-month average prices exceed the broader 2.5-month trend baseline."
                            )
                        else:
                            ma_sev = InsightSeverity.NEGATIVE
                            ma_obs = (
                                f"The 20-day SMA (${latest_sma_20:.2f}) is situated below the 50-day SMA "
                                f"(${latest_sma_50:.2f}) by {ma_diff:+.2f} ({ma_pct:+.2%}), indicating "
                                f"that recent 1-month price momentum lags the broader 2.5-month trend baseline."
                            )

                        insights.append(
                            MarketInsight(
                                category=InsightCategory.MOVING_AVERAGES,
                                title="Dual Moving Average Alignment (SMA 20 vs SMA 50)",
                                observation=ma_obs,
                                evidence={
                                    "sma_20": round(float(latest_sma_20), 4),
                                    "sma_50": round(float(latest_sma_50), 4),
                                    "spread_dollars": round(ma_diff, 4),
                                    "spread_percentage": round(ma_pct, 6),
                                },
                                severity=ma_sev,
                                description="Evaluates relative positioning between short-term (20-day) and medium-term (50-day) averages.",
                                limitations="Moving average spreads represent historical lagging relationships and do not forecast trend endurance.",
                            )
                        )
        else:
            insights.append(
                MarketInsight(
                    category=InsightCategory.MOVING_AVERAGES,
                    title="SMA 50 Unavailable: Insufficient History",
                    observation=(
                        f"Dataset contains {n_obs} observations, which is fewer than the 50 trading sessions "
                        f"required to establish a valid SMA 50 medium-term baseline."
                    ),
                    evidence={"observation_count": n_obs, "required_minimum": 50},
                    severity=InsightSeverity.INFO,
                    description="A 50-day moving average requires at least 50 historical daily records.",
                    limitations="Standard statistical convention dictates leaving incomplete warm-up windows as unpopulated NaNs.",
                )
            )

        # 4. Evaluate EMA 20 (Exponentially weighted responsive trend)
        if n_obs >= 2:
            ema_20_series = self._indicators.calculate_ema_20()
            latest_ema_20 = ema_20_series.iloc[-1]
            if not np.isnan(latest_ema_20):
                diff_ema_20 = latest_close - latest_ema_20
                pct_ema_20 = (diff_ema_20 / latest_ema_20) if latest_ema_20 != 0 else 0.0
                rel_text = "above" if diff_ema_20 >= 0 else "below"
                sev = InsightSeverity.POSITIVE if diff_ema_20 >= 0 else InsightSeverity.NEGATIVE

                insights.append(
                    MarketInsight(
                        category=InsightCategory.MOVING_AVERAGES,
                        title=f"Price vs EMA 20: Weighted Responsive Trend ({rel_text.capitalize()})",
                        observation=(
                            f"The latest closing price (${latest_close:.2f}) is positioned {rel_text} "
                            f"the 20-day Exponential Moving Average (${latest_ema_20:.2f}) by "
                            f"{diff_ema_20:+.2f} ({pct_ema_20:+.2%}), reflecting recency-weighted price alignment."
                        ),
                        evidence={
                            "latest_close": round(latest_close, 4),
                            "ema_20": round(float(latest_ema_20), 4),
                            "diff_dollars": round(diff_ema_20, 4),
                            "diff_percentage": round(pct_ema_20, 6),
                            "span": 20,
                        },
                        severity=sev,
                        description="Compares closing price against the 20-period exponential moving average (higher weight on recent days).",
                        limitations="Exponential weighting accelerates responsiveness to price shocks, which can increase sensitivity to noise.",
                    )
                )

        return insights

    # =========================================================================
    # C. Returns Insights
    # =========================================================================

    def generate_returns_insights(self) -> List[MarketInsight]:
        """Evaluate daily percentage returns, compounded cumulative growth, and session win rates."""
        insights: List[MarketInsight] = []
        daily_returns = self._returns.calculate_daily_returns().dropna()

        if len(daily_returns) == 0:
            insights.append(
                MarketInsight(
                    category=InsightCategory.RETURNS,
                    title="Insufficient Return Observations",
                    observation="No valid percentage return observations available for analysis.",
                    evidence={"valid_returns_count": 0},
                    severity=InsightSeverity.INFO,
                    description="Return analysis requires at least two chronological price points.",
                    limitations="Missing return calculations prevent statistical aggregation.",
                )
            )
            return insights

        n_sessions = len(daily_returns)
        positive_sessions = int((daily_returns > 0).sum())
        negative_sessions = int((daily_returns < 0).sum())
        flat_sessions = int((daily_returns == 0).sum())
        win_rate = positive_sessions / n_sessions if n_sessions > 0 else 0.0

        mean_return = float(daily_returns.mean())
        median_return = float(daily_returns.median())
        best_day_val = float(daily_returns.max())
        worst_day_val = float(daily_returns.min())

        best_idx = daily_returns.idxmax()
        worst_idx = daily_returns.idxmin()
        best_date = str(self.df["Date"].iloc[best_idx]) if "Date" in self.df.columns else f"session {best_idx}"
        worst_date = str(self.df["Date"].iloc[worst_idx]) if "Date" in self.df.columns else f"session {worst_idx}"

        # Compounded cumulative return (preserving compounding, not cumulative sum)
        cum_series = self._returns.calculate_cumulative_returns().dropna()
        final_cum_return = float(cum_series.iloc[-1]) if len(cum_series) > 0 else 0.0

        # 1. Compounded Cumulative Return Insight
        cum_sev = InsightSeverity.POSITIVE if final_cum_return > 0 else (
            InsightSeverity.NEGATIVE if final_cum_return < 0 else InsightSeverity.NEUTRAL
        )
        insights.append(
            MarketInsight(
                category=InsightCategory.RETURNS,
                title="Cumulative Compounded Performance",
                observation=(
                    f"Over {n_sessions} active trading sessions, the asset delivered a cumulative "
                    f"compounded return of {final_cum_return:+.2%}. Baseline capital of $1.00 grew "
                    f"to ${(1.0 + final_cum_return):.4f}."
                ),
                evidence={
                    "cumulative_return": round(final_cum_return, 6),
                    "ending_wealth_factor": round(1.0 + final_cum_return, 4),
                    "evaluated_sessions": n_sessions,
                },
                severity=cum_sev,
                description="Reflects exact geometric compounding of daily percentage returns from the initial baseline.",
                limitations="Cumulative return reflects holding-period performance and assumes zero transaction costs, slippage, or cash-flow events.",
            )
        )

        # 2. Session Asymmetry & Win Rate Insight
        win_sev = InsightSeverity.POSITIVE if win_rate >= 0.52 else (
            InsightSeverity.NEGATIVE if win_rate <= 0.48 else InsightSeverity.NEUTRAL
        )
        insights.append(
            MarketInsight(
                category=InsightCategory.RETURNS,
                title=f"Session Win/Loss Ratio: {win_rate:.1%} Positive Days",
                observation=(
                    f"Out of {n_sessions} return observations, {positive_sessions} sessions ({win_rate:.1%}) "
                    f"recorded price increases, {negative_sessions} sessions ({negative_sessions / n_sessions:.1%}) "
                    f"closed lower, and {flat_sessions} sessions were unchanged. Mean daily return was {mean_return:+.3%} "
                    f"(median: {median_return:+.3%})."
                ),
                evidence={
                    "total_sessions": n_sessions,
                    "positive_sessions": positive_sessions,
                    "negative_sessions": negative_sessions,
                    "flat_sessions": flat_sessions,
                    "win_rate": round(win_rate, 4),
                    "mean_daily_return": round(mean_return, 6),
                    "median_daily_return": round(median_return, 6),
                },
                severity=win_sev,
                description="Distribution of single-day price directional moves across the observation window.",
                limitations="Session win rate evaluates frequency of gains, not magnitude; asymmetric losses can outweigh a high win rate.",
            )
        )

        # 3. Extremes and Tail Day Insight
        insights.append(
            MarketInsight(
                category=InsightCategory.RETURNS,
                title="Historical Single-Day Performance Extremes",
                observation=(
                    f"The highest single-session gain was {best_day_val:+.2%} on {best_date}, "
                    f"while the most severe single-session decline was {worst_day_val:+.2%} on {worst_date}."
                ),
                evidence={
                    "best_day_return": round(best_day_val, 6),
                    "best_day_date": best_date,
                    "worst_day_return": round(worst_day_val, 6),
                    "worst_day_date": worst_date,
                    "spread_percentage": round(best_day_val - worst_day_val, 6),
                },
                severity=InsightSeverity.INFO,
                description="Identifies the historical maximum single-day gain and maximum single-day loss in the sample.",
                limitations="Historical extremes capture realized historical outliers; future tail shocks can exceed historical records.",
            )
        )

        return insights

    # =========================================================================
    # D. Volatility and Risk Insights
    # =========================================================================

    def generate_risk_insights(self) -> List[MarketInsight]:
        """Evaluate annualized volatility, maximum historical drawdown, and rolling risk behavior."""
        insights: List[MarketInsight] = []
        n_obs = len(self.df)

        if n_obs < 2:
            insights.append(
                MarketInsight(
                    category=InsightCategory.RISK_AND_VOLATILITY,
                    title="Insufficient Data for Risk Assessment",
                    observation="Risk metrics require at least two observations to establish historical variance.",
                    evidence={"observation_count": n_obs},
                    severity=InsightSeverity.INFO,
                    description="Standard deviation calculations with sample degrees of freedom (ddof=1) require N >= 2.",
                    limitations="Risk cannot be calculated for zero-variance or single-observation inputs.",
                )
            )
            return insights

        # 1. Annualized Volatility Evaluation
        annual_vol = self._risk.calculate_annualized_volatility()
        daily_vol = self._risk.calculate_daily_volatility()

        if not np.isnan(annual_vol):
            if annual_vol < self.thresholds.volatility_low_threshold:
                vol_class = "Low Volatility"
                vol_sev = InsightSeverity.POSITIVE
                vol_desc = "reflecting subdued price dispersion and conservative return variance."
            elif annual_vol <= self.thresholds.volatility_high_threshold:
                vol_class = "Moderate Volatility"
                vol_sev = InsightSeverity.NEUTRAL
                vol_desc = "consistent with typical single-stock equity market variance."
            else:
                vol_class = "Elevated Volatility"
                vol_sev = InsightSeverity.WARNING
                vol_desc = "indicating substantial price dispersion and elevated risk exposure."

            insights.append(
                MarketInsight(
                    category=InsightCategory.RISK_AND_VOLATILITY,
                    title=f"Annualized Risk Profile: {vol_class} ({annual_vol:.1%})",
                    observation=(
                        f"Realized annualized volatility over the period was {annual_vol:.2%} "
                        f"(daily volatility: {daily_vol:.2%}), {vol_desc}"
                    ),
                    evidence={
                        "annualized_volatility": round(annual_vol, 6),
                        "daily_volatility": round(daily_vol, 6),
                        "annualization_factor": 252,
                        "classification": vol_class,
                    },
                    severity=vol_sev,
                    description="Sample standard deviation of daily percentage returns scaled by sqrt(252).",
                    limitations="Standard deviation assumes symmetric dispersion around the mean and treats upside and downside variability equally.",
                )
            )

        # 2. Maximum Drawdown (MDD) Evaluation
        mdd_data = self._risk.calculate_max_drawdown()
        mdd = mdd_data.get("max_drawdown", 0.0)
        peak_date = mdd_data.get("peak_date", "N/A")
        trough_date = mdd_data.get("trough_date", "N/A")

        if mdd <= self.thresholds.drawdown_bear_threshold:
            mdd_class = "Severe Drawdown (Bear Territory)"
            mdd_sev = InsightSeverity.NEGATIVE
            mdd_desc = "exceeding formal bear market threshold (-20%)."
        elif mdd <= self.thresholds.drawdown_correction_threshold:
            mdd_class = "Moderate Drawdown (Correction Territory)"
            mdd_sev = InsightSeverity.WARNING
            mdd_desc = "consistent with standard market correction parameters (-10% to -20%)."
        else:
            mdd_class = "Mild Drawdown"
            mdd_sev = InsightSeverity.POSITIVE
            mdd_desc = "reflecting resilient capital retention and limited historical decline."

        insights.append(
            MarketInsight(
                category=InsightCategory.RISK_AND_VOLATILITY,
                title=f"Capital Protection & Drawdown: {mdd_class} ({mdd:.1%})",
                observation=(
                    f"The maximum historical peak-to-trough decline (Maximum Drawdown) was {mdd:.2%}, {mdd_desc} "
                    f"The peak was registered on {peak_date} and bottomed on {trough_date}."
                ),
                evidence={
                    "max_drawdown": round(float(mdd), 6),
                    "peak_date": str(peak_date),
                    "trough_date": str(trough_date),
                    "classification": mdd_class,
                },
                severity=mdd_sev,
                description="Maximum percentage contraction from prior high-water mark across the observation history.",
                limitations="Maximum drawdown is path-dependent and reflects past worst-case drops; it does not set a floor for future market events.",
            )
        )

        # 3. Rolling Volatility Evaluation (21-day sliding risk)
        if n_obs >= 21:
            try:
                rolling_vol_21 = self._risk.calculate_rolling_volatility(window=21).dropna()
                if len(rolling_vol_21) > 0:
                    latest_rvol = float(rolling_vol_21.iloc[-1])
                    avg_rvol = float(rolling_vol_21.mean())
                    max_rvol = float(rolling_vol_21.max())

                    if latest_rvol > avg_rvol * 1.15:
                        rvol_trend = "expanding"
                        rvol_sev = InsightSeverity.WARNING
                        rvol_comment = "Recent 21-day price dispersion has expanded relative to the average rolling volatility level."
                    elif latest_rvol < avg_rvol * 0.85:
                        rvol_trend = "compressing"
                        rvol_sev = InsightSeverity.POSITIVE
                        rvol_comment = "Recent 21-day price dispersion has compressed into a lower-volatility regime."
                    else:
                        rvol_trend = "stable"
                        rvol_sev = InsightSeverity.INFO
                        rvol_comment = "Recent 21-day price dispersion is tracking near its historical average rolling level."

                    insights.append(
                        MarketInsight(
                            category=InsightCategory.RISK_AND_VOLATILITY,
                            title=f"Rolling Risk Regime: {rvol_trend.capitalize()} Volatility ({latest_rvol:.1%})",
                            observation=(
                                f"Latest 21-day rolling volatility stands at {latest_rvol:.2%} "
                                f"(vs historical rolling average of {avg_rvol:.2%}, period peak of {max_rvol:.2%}). "
                                f"{rvol_comment}"
                            ),
                            evidence={
                                "latest_rolling_vol_21": round(latest_rvol, 6),
                                "mean_rolling_vol_21": round(avg_rvol, 6),
                                "max_rolling_vol_21": round(max_rvol, 6),
                                "regime_trend": rvol_trend,
                            },
                            severity=rvol_sev,
                            description="21-day rolling window annualized standard deviation tracking temporal risk clustering.",
                            limitations="Rolling volatility metrics require sufficient warm-up periods and exhibit window-boundary sensitivity.",
                        )
                    )
            except Exception:
                pass

        return insights

    # =========================================================================
    # E. Trading Volume Insights
    # =========================================================================

    def generate_volume_insights(self) -> List[MarketInsight]:
        """Evaluate recent volume against historical moving average baselines."""
        insights: List[MarketInsight] = []
        if "Volume" not in self.df.columns:
            return insights

        volume_series = pd.to_numeric(self.df["Volume"], errors="coerce").dropna()
        n_vol = len(volume_series)

        # Baseline volume window (default 20 days, or available length if >= 5)
        if n_vol < 5 or (volume_series == 0).all():
            insights.append(
                MarketInsight(
                    category=InsightCategory.TRADING_VOLUME,
                    title="Volume Observations Unavailable / Insufficient",
                    observation="Insufficient non-zero trading volume observations available to establish a baseline.",
                    evidence={"valid_volume_observations": n_vol},
                    severity=InsightSeverity.INFO,
                    description="Trading volume interpretations require at least 5 active non-zero sessions.",
                    limitations="Datasets lacking reliable volume columns cannot establish a volume baseline or evaluate trading turnover.",
                )
            )
            return insights

        window = min(self.thresholds.volume_baseline_window, n_vol)
        baseline_avg_volume = float(volume_series.iloc[-window:].mean())
        latest_volume = float(volume_series.iloc[-1])
        vol_ratio = (latest_volume / baseline_avg_volume) if baseline_avg_volume > 0 else 1.0

        if vol_ratio >= self.thresholds.volume_surge_multiplier:
            v_status = "Elevated Trading Volume"
            v_sev = InsightSeverity.WARNING
            v_obs = (
                f"Latest trading volume of {latest_volume:,.0f} shares reflects higher-than-average trading activity "
                f"at {vol_ratio:.2f}x relative to the trailing {window}-day baseline average ({baseline_avg_volume:,.0f} shares), "
                f"indicating increased market turnover."
            )
        elif vol_ratio <= self.thresholds.volume_dryup_multiplier:
            v_status = "Reduced Trading Volume"
            v_sev = InsightSeverity.INFO
            v_obs = (
                f"Latest trading volume of {latest_volume:,.0f} shares reflects reduced trading volume at {vol_ratio:.2f}x "
                f"relative to the trailing {window}-day baseline average ({baseline_avg_volume:,.0f} shares), "
                f"indicating subdued market activity."
            )
        else:
            v_status = "Typical Trading Volume"
            v_sev = InsightSeverity.INFO
            v_obs = (
                f"Latest trading volume of {latest_volume:,.0f} shares is consistent with the trailing {window}-day "
                f"average of {baseline_avg_volume:,.0f} shares (volume ratio: {vol_ratio:.2f}x)."
            )

        insights.append(
            MarketInsight(
                category=InsightCategory.TRADING_VOLUME,
                title=f"Trading Activity: {v_status}",
                observation=v_obs,
                evidence={
                    "latest_volume": int(latest_volume),
                    "baseline_average_volume": int(baseline_avg_volume),
                    "volume_ratio": round(vol_ratio, 4),
                    "comparison_window": window,
                },
                severity=v_sev,
                description=f"Compares the latest daily trading volume against the trailing {window}-session average.",
                limitations=(
                    "Exchange volume reflects total aggregate share turnover but does not identify participant classes "
                    "or distinguish buyer-initiated from seller-initiated order flow without tick-level order book data."
                ),
            )
        )

        return insights

    # =========================================================================
    # F. Correlation Insights
    # =========================================================================

    def generate_correlation_insights(self) -> List[MarketInsight]:
        """Evaluate numerical feature correlations and emphasize non-causation boundaries."""
        insights: List[MarketInsight] = []
        n_obs = len(self.df)
        if n_obs < 10:
            return insights

        try:
            # Direct reuse of existing EDA correlation output
            corr_matrix = self._eda.compute_correlations(method="pearson")
            if "Close" in corr_matrix.columns and "Volume" in corr_matrix.columns:
                corr_val = float(corr_matrix.loc["Close", "Volume"])
                abs_corr = abs(corr_val)

                if abs_corr >= self.thresholds.correlation_strong_threshold:
                    strength = "Strong"
                    direction = "positive co-movement" if corr_val > 0 else "inverse co-movement"
                elif abs_corr >= self.thresholds.correlation_moderate_threshold:
                    strength = "Moderate"
                    direction = "positive co-movement" if corr_val > 0 else "inverse co-movement"
                else:
                    strength = "Weak / Low"
                    direction = "negligible linear co-movement"

                corr_text = (
                    f"Sample Pearson correlation between raw closing price ('Close') and trading volume ('Volume') "
                    f"is {strength.lower()} at r = {corr_val:+.2f} ({direction}) across {n_obs} sessions for {self.ticker}. "
                    f"Crucially, empirical correlation measures contemporaneous linear association only and does not "
                    f"establish causation, infer buying or selling pressure, or predict future price moves."
                )

                limitations_text = (
                    "Price-volume correlation is evaluated between raw price levels ('Close') and share turnover ('Volume') "
                    "for this single asset only (not a cross-stock correlation). Raw price time series are frequently "
                    "non-stationary, meaning price-level correlations may reflect shared trends rather than direct economic "
                    "linkages. Correlation does not imply causation, does not measure directional order flow, and provides "
                    "no lead-lag predictability."
                )

                insights.append(
                    MarketInsight(
                        category=InsightCategory.CORRELATION,
                        title=f"Price-Volume Co-Movement: {strength} ({corr_val:+.2f})",
                        observation=corr_text,
                        evidence={
                            "correlation_r": round(corr_val, 4),
                            "variable_x": "Close (raw price level)",
                            "variable_y": "Volume (daily share turnover)",
                            "features": ["Close", "Volume"],
                            "correlation_method": "pearson",
                            "strength": strength,
                            "observation_count": n_obs,
                            "asset_scope": "single_ticker_intra_asset",
                        },
                        severity=InsightSeverity.INFO,
                        description="Pearson correlation between raw closing price levels and daily trading volume from the EDA feature matrix.",
                        limitations=limitations_text,
                    )
                )
        except Exception:
            pass

        return insights

    # =========================================================================
    # G. Overall Stock Analysis Summary
    # =========================================================================

    def generate_all_insights(self) -> List[MarketInsight]:
        """Generate complete, deterministic collection of insights across all categories."""
        all_insights: List[MarketInsight] = []
        all_insights.extend(self.generate_price_trend_insights())
        all_insights.extend(self.generate_moving_average_insights())
        all_insights.extend(self.generate_returns_insights())
        all_insights.extend(self.generate_risk_insights())
        all_insights.extend(self.generate_volume_insights())
        all_insights.extend(self.generate_correlation_insights())
        return all_insights

    def generate_summary(self) -> InsightSummary:
        """Synthesize overall analysis summary categorizing strengths, risks, and limitations.

        Strict Boundaries:
            - Never generates overall numerical scores (e.g. no '7.5/10').
            - Never produces investment recommendations (no 'buy', 'sell', 'hold').
            - Strictly evidence-based, extracting takeaways directly from individual insights.
        """
        insights = self.generate_all_insights()

        positives: List[str] = []
        negatives: List[str] = []
        risks: List[str] = []
        limitations: List[str] = []

        # Deduplicate and extract salient points based on insight evaluation
        for ins in insights:
            if ins.severity == InsightSeverity.POSITIVE:
                positives.append(ins.observation)
            elif ins.severity == InsightSeverity.NEGATIVE:
                negatives.append(ins.observation)
            elif ins.severity == InsightSeverity.WARNING:
                risks.append(ins.observation)

            if ins.limitations and ins.limitations not in limitations:
                limitations.append(ins.limitations)

        # Baseline universal limitations
        universal_limitation = (
            "Historical financial observations reflect realized market conditions and do not predict "
            "future returns, guarantee price trends, or bound tail risk."
        )
        if universal_limitation not in limitations:
            limitations.append(universal_limitation)

        if self.is_synthetic:
            synthetic_limitation = (
                "DATASET IS SYNTHETIC: Observations originate from an offline synthetic fixture "
                "(data/sample/sample_stock.csv) and must not be treated as actual exchange data."
            )
            limitations.insert(0, synthetic_limitation)

        first_date = str(self.df["Date"].iloc[0]) if "Date" in self.df.columns else None
        latest_date = str(self.df["Date"].iloc[-1]) if "Date" in self.df.columns else None

        return InsightSummary(
            ticker=self.ticker,
            period_start=first_date,
            period_end=latest_date,
            observation_count=len(self.df),
            positive_observations=positives,
            negative_observations=negatives,
            risk_observations=risks,
            data_limitations=limitations,
            insights=insights,
            is_synthetic=self.is_synthetic,
        )


# =============================================================================
# Backward-Compatible Adapter & Functional Convenience Wrappers
# =============================================================================


class InsightsEngine:
    """Backward-compatible adapter matching earlier starter interface."""

    def __init__(self, analysis_results: Union[Dict[str, Any], pd.DataFrame]) -> None:
        """Initialize adapter with DataFrame or pre-computed results dictionary."""
        if isinstance(analysis_results, pd.DataFrame):
            self.analyzer = StockInsightAnalyzer(analysis_results)
        elif isinstance(analysis_results, dict) and "data" in analysis_results:
            self.analyzer = StockInsightAnalyzer(analysis_results["data"])
        else:
            self.analyzer = None
            self.results = analysis_results

    def generate_trend_insights(self) -> List[str]:
        """Generate textual insights on trend direction and moving average positioning."""
        if self.analyzer:
            insights = self.analyzer.generate_price_trend_insights()
            insights.extend(self.analyzer.generate_moving_average_insights())
            return [ins.observation for ins in insights]
        return ["Trend insight adapter requires DataFrame input."]

    def generate_risk_insights(self) -> List[str]:
        """Generate textual insights on volatility level and drawdown severity."""
        if self.analyzer:
            insights = self.analyzer.generate_risk_insights()
            return [ins.observation for ins in insights]
        return ["Risk insight adapter requires DataFrame input."]


def generate_stock_insights(
    df: pd.DataFrame,
    ticker: Optional[str] = None,
    price_column: str = "Close",
    thresholds: Optional[InsightThresholds] = None,
) -> InsightSummary:
    """Functional convenience wrapper generating complete insight summary for a stock DataFrame.

    Args:
        df: Cleaned stock DataFrame.
        ticker: Optional ticker symbol.
        price_column: Column name to analyze (defaults to 'Close').
        thresholds: Optional InsightThresholds customization.

    Returns:
        Structured InsightSummary instance.
    """
    analyzer = StockInsightAnalyzer(
        df=df,
        ticker=ticker,
        price_column=price_column,
        thresholds=thresholds,
    )
    return analyzer.generate_summary()
