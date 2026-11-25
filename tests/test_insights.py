"""Unit tests for Phase 10: Insights and Interpretation engine."""

from datetime import date
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from stock_analyzer.analysis.insights import (
    InsightCategory,
    InsightSeverity,
    InsightSummary,
    InsightThresholds,
    InsightsEngine,
    MarketInsight,
    StockInsightAnalyzer,
    generate_stock_insights,
)
from stock_analyzer.data.exceptions import (
    DataValidationError,
    EmptyDataError,
    MissingColumnError,
)
from stock_analyzer.data.loader import load_stock_csv


@pytest.fixture
def synthetic_sample_df() -> pd.DataFrame:
    """Load the actual synthetic sample dataset with metadata."""
    sample_path = Path("data/sample/sample_stock.csv")
    df = load_stock_csv(str(sample_path))
    return df


@pytest.fixture
def rising_trend_df() -> pd.DataFrame:
    """Deterministic DataFrame with steadily rising prices across 60 trading days."""
    dates = pd.date_range(start="2026-01-01", periods=60, freq="B").strftime("%Y-%m-%d")
    n = len(dates)
    # Monotonically increasing close prices
    closes = [100.0 + i * 1.5 for i in range(n)]
    opens = [c - 0.5 for c in closes]
    highs = [c + 1.0 for c in closes]
    lows = [o - 1.0 for o in opens]
    volumes = [1000000 + i * 5000 for i in range(n)]

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volumes,
        }
    )
    df.attrs["ticker"] = "RISING"
    df.attrs["is_synthetic"] = False
    return df


@pytest.fixture
def falling_trend_df() -> pd.DataFrame:
    """Deterministic DataFrame with falling prices and a severe drawdown across 60 days."""
    dates = pd.date_range(start="2026-01-01", periods=60, freq="B").strftime("%Y-%m-%d")
    n = len(dates)
    # Monotonically declining close prices
    closes = [200.0 - i * 1.5 for i in range(n)]
    opens = [c + 0.5 for c in closes]
    highs = [o + 1.0 for o in opens]
    lows = [c - 1.0 for c in closes]
    volumes = [2000000 for _ in range(n)]

    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volumes,
        }
    )
    df.attrs["ticker"] = "FALLING"
    df.attrs["is_synthetic"] = False
    return df


# =============================================================================
# 1. Validation & Immutability Tests
# =============================================================================


class TestInsightEngineValidation:
    """Validation safeguards and input immutability tests."""

    def test_invalid_input_type_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected pandas DataFrame"):
            StockInsightAnalyzer("not_a_dataframe")

    def test_empty_dataframe_raises_empty_data_error(self):
        with pytest.raises(EmptyDataError, match="Cannot generate insights from an empty DataFrame"):
            StockInsightAnalyzer(pd.DataFrame())

    def test_missing_price_column_raises_missing_column_error(self, rising_trend_df):
        with pytest.raises(MissingColumnError, match="Specified price column 'NonExistent'"):
            StockInsightAnalyzer(rising_trend_df, price_column="NonExistent")

    def test_non_numeric_price_column_raises_data_validation_error(self):
        df = pd.DataFrame({"Date": ["2026-01-01"], "Close": ["not_numeric"]})
        with pytest.raises(DataValidationError, match="must have numeric data type"):
            StockInsightAnalyzer(df, price_column="Close")

    def test_input_dataframe_immutability(self, rising_trend_df):
        original_data = rising_trend_df.copy(deep=True)
        original_attrs = rising_trend_df.attrs.copy()

        analyzer = StockInsightAnalyzer(rising_trend_df)
        _ = analyzer.generate_summary()

        pd.testing.assert_frame_equal(rising_trend_df, original_data)
        assert rising_trend_df.attrs == original_attrs


# =============================================================================
# 2. Price Trend Insights Tests
# =============================================================================


class TestPriceTrendInsights:
    """Tests for start-to-end price trajectory evaluation."""

    def test_positive_price_performance_and_evidence(self, rising_trend_df):
        analyzer = StockInsightAnalyzer(rising_trend_df)
        insights = analyzer.generate_price_trend_insights()

        assert len(insights) >= 1
        trend_ins = insights[0]
        assert trend_ins.category == InsightCategory.PRICE_TREND
        assert trend_ins.severity == InsightSeverity.POSITIVE
        assert "positive overall performance" in trend_ins.observation
        assert trend_ins.evidence["first_close"] == 100.0
        assert trend_ins.evidence["latest_close"] == 188.5
        assert trend_ins.evidence["absolute_change"] > 0
        assert trend_ins.evidence["percentage_change"] > 0

    def test_negative_price_performance_and_evidence(self, falling_trend_df):
        analyzer = StockInsightAnalyzer(falling_trend_df)
        insights = analyzer.generate_price_trend_insights()

        assert len(insights) >= 1
        trend_ins = insights[0]
        assert trend_ins.category == InsightCategory.PRICE_TREND
        assert trend_ins.severity == InsightSeverity.NEGATIVE
        assert "negative overall performance" in trend_ins.observation
        assert trend_ins.evidence["first_close"] == 200.0
        assert trend_ins.evidence["latest_close"] == 111.5
        assert trend_ins.evidence["absolute_change"] < 0
        assert trend_ins.evidence["percentage_change"] < 0

    def test_flat_price_performance(self):
        df = pd.DataFrame(
            {
                "Date": ["2026-01-01", "2026-01-02", "2026-01-05"],
                "Open": [100.0, 101.0, 99.0],
                "High": [102.0, 103.0, 101.0],
                "Low": [98.0, 99.0, 97.0],
                "Close": [100.0, 105.0, 100.0],  # Start and end at 100.0
                "Volume": [1000, 1000, 1000],
            }
        )
        analyzer = StockInsightAnalyzer(df)
        insights = analyzer.generate_price_trend_insights()
        assert len(insights) >= 1
        assert insights[0].severity == InsightSeverity.NEUTRAL
        assert "closed unchanged" in insights[0].observation

    def test_single_observation_insufficient_history(self):
        df = pd.DataFrame(
            {
                "Date": ["2026-01-01"],
                "Open": [100.0],
                "High": [105.0],
                "Low": [95.0],
                "Close": [102.0],
                "Volume": [1000],
            }
        )
        analyzer = StockInsightAnalyzer(df)
        insights = analyzer.generate_price_trend_insights()
        assert len(insights) == 1
        assert "Insufficient Price History" in insights[0].title


# =============================================================================
# 3. Moving Average Insights Tests
# =============================================================================


class TestMovingAverageInsights:
    """Tests for SMA 20, SMA 50, EMA 20, and dual MA alignment interpretations."""

    def test_price_above_moving_averages_in_rising_trend(self, rising_trend_df):
        analyzer = StockInsightAnalyzer(rising_trend_df)
        insights = analyzer.generate_moving_average_insights()

        # In rising trend, price should be above SMA 20, SMA 50, and EMA 20
        sma_20_ins = [i for i in insights if "SMA 20" in i.title and "Dual" not in i.title][0]
        sma_50_ins = [i for i in insights if "SMA 50" in i.title and "Dual" not in i.title][0]
        ema_20_ins = [i for i in insights if "EMA 20" in i.title][0]
        dual_ins = [i for i in insights if "Dual" in i.title][0]

        assert sma_20_ins.severity == InsightSeverity.POSITIVE
        assert "trading above its 20-day Simple Moving Average" in sma_20_ins.observation

        assert sma_50_ins.severity == InsightSeverity.POSITIVE
        assert "positioned above its 50-day Simple Moving Average" in sma_50_ins.observation

        assert ema_20_ins.severity == InsightSeverity.POSITIVE
        assert "positioned above the 20-day Exponential Moving Average" in ema_20_ins.observation

        assert dual_ins.severity == InsightSeverity.POSITIVE
        assert "situated above the 50-day SMA" in dual_ins.observation

    def test_price_below_moving_averages_in_falling_trend(self, falling_trend_df):
        analyzer = StockInsightAnalyzer(falling_trend_df)
        insights = analyzer.generate_moving_average_insights()

        sma_20_ins = [i for i in insights if "SMA 20" in i.title and "Dual" not in i.title][0]
        sma_50_ins = [i for i in insights if "SMA 50" in i.title and "Dual" not in i.title][0]

        assert sma_20_ins.severity == InsightSeverity.NEGATIVE
        assert "trading below its 20-day Simple Moving Average" in sma_20_ins.observation

        assert sma_50_ins.severity == InsightSeverity.NEGATIVE
        assert "positioned below its 50-day Simple Moving Average" in sma_50_ins.observation

    def test_insufficient_history_for_sma20_and_sma50(self):
        # 15 observations: fewer than 20
        dates = pd.date_range("2026-01-01", periods=15, freq="B").strftime("%Y-%m-%d")
        df_short = pd.DataFrame(
            {
                "Date": dates,
                "Open": [100.0] * 15,
                "High": [105.0] * 15,
                "Low": [95.0] * 15,
                "Close": [102.0] * 15,
                "Volume": [1000] * 15,
            }
        )
        analyzer = StockInsightAnalyzer(df_short)
        insights = analyzer.generate_moving_average_insights()

        titles = [i.title for i in insights]
        assert any("SMA 20 Unavailable" in t for t in titles)
        assert any("SMA 50 Unavailable" in t for t in titles)

    def test_intermediate_history_sma20_available_sma50_unavailable(self):
        # 30 observations: >= 20, but < 50
        dates = pd.date_range("2026-01-01", periods=30, freq="B").strftime("%Y-%m-%d")
        df_mid = pd.DataFrame(
            {
                "Date": dates,
                "Open": [100.0 + i for i in range(30)],
                "High": [105.0 + i for i in range(30)],
                "Low": [95.0 + i for i in range(30)],
                "Close": [102.0 + i for i in range(30)],
                "Volume": [1000] * 30,
            }
        )
        analyzer = StockInsightAnalyzer(df_mid)
        insights = analyzer.generate_moving_average_insights()

        titles = [i.title for i in insights]
        assert any("Price vs SMA 20" in t for t in titles)
        assert any("SMA 50 Unavailable" in t for t in titles)


# =============================================================================
# 4. Returns Insights Tests
# =============================================================================


class TestReturnsInsights:
    """Tests for returns, compounding, asymmetry, and extremes."""

    def test_positive_and_negative_cumulative_returns(self, rising_trend_df, falling_trend_df):
        # Rising trend -> positive cumulative return
        analyzer_rise = StockInsightAnalyzer(rising_trend_df)
        rise_ret_ins = [i for i in analyzer_rise.generate_returns_insights() if "Cumulative" in i.title][0]
        assert rise_ret_ins.severity == InsightSeverity.POSITIVE
        assert rise_ret_ins.evidence["cumulative_return"] > 0

        # Falling trend -> negative cumulative return
        analyzer_fall = StockInsightAnalyzer(falling_trend_df)
        fall_ret_ins = [i for i in analyzer_fall.generate_returns_insights() if "Cumulative" in i.title][0]
        assert fall_ret_ins.severity == InsightSeverity.NEGATIVE
        assert fall_ret_ins.evidence["cumulative_return"] < 0

    def test_session_win_rate_and_asymmetry(self, rising_trend_df):
        analyzer = StockInsightAnalyzer(rising_trend_df)
        insights = analyzer.generate_returns_insights()
        win_ins = [i for i in insights if "Win/Loss" in i.title][0]

        assert "positive_sessions" in win_ins.evidence
        assert "negative_sessions" in win_ins.evidence
        assert "win_rate" in win_ins.evidence
        assert win_ins.evidence["win_rate"] == 1.0  # Monotonically rising df has 100% positive sessions

    def test_historical_extremes_best_and_worst_days(self, synthetic_sample_df):
        analyzer = StockInsightAnalyzer(synthetic_sample_df)
        insights = analyzer.generate_returns_insights()
        extreme_ins = [i for i in insights if "Extremes" in i.title][0]

        assert "best_day_return" in extreme_ins.evidence
        assert "worst_day_return" in extreme_ins.evidence
        assert extreme_ins.evidence["best_day_return"] > 0
        assert extreme_ins.evidence["worst_day_return"] < 0

    def test_cumulative_returns_uses_compounding_not_sum(self):
        # 3 sessions: +10%, -10%, +10%
        # Sum = +10%
        # Compounded = (1.10 * 0.90 * 1.10) - 1 = 1.089 - 1 = +8.9%
        df = pd.DataFrame(
            {
                "Date": ["2026-01-01", "2026-01-02", "2026-01-05", "2026-01-06"],
                "Open": [100.0, 110.0, 99.0, 108.9],
                "High": [102.0, 112.0, 101.0, 110.0],
                "Low": [98.0, 108.0, 97.0, 106.0],
                "Close": [100.0, 110.0, 99.0, 108.9],
                "Volume": [1000] * 4,
            }
        )
        analyzer = StockInsightAnalyzer(df)
        ret_ins = [i for i in analyzer.generate_returns_insights() if "Cumulative" in i.title][0]
        # Compounded return is exactly 0.089 (8.9%), NOT 0.10 (10.0%)
        assert pytest.approx(ret_ins.evidence["cumulative_return"], 0.001) == 0.089


# =============================================================================
# 5. Risk and Volatility Insights Tests
# =============================================================================


class TestRiskAndVolatilityInsights:
    """Tests for volatility classification, drawdown severity, and rolling risk."""

    def test_volatility_classification_thresholds(self):
        # 1. Custom thresholds: low (<10%), high (>25%)
        thresholds = InsightThresholds(volatility_low_threshold=0.10, volatility_high_threshold=0.25)

        # Flat prices -> zero/low volatility
        dates = pd.date_range("2026-01-01", periods=30, freq="B").strftime("%Y-%m-%d")
        df_low = pd.DataFrame(
            {
                "Date": dates,
                "Open": [100.0] * 30,
                "High": [100.1] * 30,
                "Low": [99.9] * 30,
                "Close": [100.0 + (i % 2) * 0.05 for i in range(30)],
                "Volume": [1000] * 30,
            }
        )
        analyzer_low = StockInsightAnalyzer(df_low, thresholds=thresholds)
        insights_low = analyzer_low.generate_risk_insights()
        vol_ins = [i for i in insights_low if "Annualized Risk" in i.title][0]
        assert vol_ins.evidence["classification"] == "Low Volatility"
        assert vol_ins.severity == InsightSeverity.POSITIVE

    def test_drawdown_severity_bear_territory(self, falling_trend_df):
        # falling_trend_df drops from 200 to 111.5 (-44.25% drawdown) -> Bear Territory
        analyzer = StockInsightAnalyzer(falling_trend_df)
        insights = analyzer.generate_risk_insights()
        dd_ins = [i for i in insights if "Drawdown" in i.title][0]

        assert dd_ins.severity == InsightSeverity.NEGATIVE
        assert "Bear Territory" in dd_ins.evidence["classification"]
        assert dd_ins.evidence["max_drawdown"] <= -0.20

    def test_drawdown_severity_mild_territory(self, rising_trend_df):
        # Monotonically rising df has 0% drawdown -> Mild Drawdown
        analyzer = StockInsightAnalyzer(rising_trend_df)
        insights = analyzer.generate_risk_insights()
        dd_ins = [i for i in insights if "Drawdown" in i.title][0]

        assert dd_ins.severity == InsightSeverity.POSITIVE
        assert "Mild Drawdown" in dd_ins.evidence["classification"]
        assert dd_ins.evidence["max_drawdown"] == 0.0

    def test_rolling_volatility_regime_evaluation(self, synthetic_sample_df):
        analyzer = StockInsightAnalyzer(synthetic_sample_df)
        insights = analyzer.generate_risk_insights()
        rvol_ins = [i for i in insights if "Rolling Risk Regime" in i.title]

        if rvol_ins:
            ins = rvol_ins[0]
            assert "latest_rolling_vol_21" in ins.evidence
            assert "mean_rolling_vol_21" in ins.evidence
            assert ins.evidence["regime_trend"] in ["expanding", "compressing", "stable"]


# =============================================================================
# 6. Volume Insights Tests
# =============================================================================


class TestVolumeInsights:
    """Tests for trading volume surge, dry-up, and baseline checks."""

    def test_volume_surge_detected(self):
        dates = pd.date_range("2026-01-01", periods=25, freq="B").strftime("%Y-%m-%d")
        # Baseline volume = 1,000,000; latest session = 3,000,000 (3.0x surge)
        volumes = [1000000] * 24 + [3000000]
        df = pd.DataFrame(
            {
                "Date": dates,
                "Open": [100.0] * 25,
                "High": [105.0] * 25,
                "Low": [95.0] * 25,
                "Close": [102.0] * 25,
                "Volume": volumes,
            }
        )
        analyzer = StockInsightAnalyzer(df)
        insights = analyzer.generate_volume_insights()

        assert len(insights) == 1
        vol_ins = insights[0]
        assert "Elevated Trading Volume" in vol_ins.title
        assert "higher-than-average trading activity" in vol_ins.observation
        assert "increased market turnover" in vol_ins.observation
        assert vol_ins.severity == InsightSeverity.WARNING
        assert vol_ins.evidence["volume_ratio"] > 1.5

    def test_volume_dryup_detected(self):
        dates = pd.date_range("2026-01-01", periods=25, freq="B").strftime("%Y-%m-%d")
        # Baseline volume = 1,000,000; latest session = 200,000 (0.2x dry-up)
        volumes = [1000000] * 24 + [200000]
        df = pd.DataFrame(
            {
                "Date": dates,
                "Open": [100.0] * 25,
                "High": [105.0] * 25,
                "Low": [95.0] * 25,
                "Close": [102.0] * 25,
                "Volume": volumes,
            }
        )
        analyzer = StockInsightAnalyzer(df)
        insights = analyzer.generate_volume_insights()

        assert len(insights) == 1
        vol_ins = insights[0]
        assert "Reduced Trading Volume" in vol_ins.title
        assert "reduced trading volume" in vol_ins.observation
        assert "subdued market activity" in vol_ins.observation
        assert vol_ins.evidence["volume_ratio"] < 0.5

    def test_no_institutional_attribution_in_volume_insights(self):
        """Verify that ordinary OHLCV volume does not attribute behavior to institutions."""
        dates = pd.date_range("2026-01-01", periods=25, freq="B").strftime("%Y-%m-%d")
        # Test surge, dryup, typical, and empty volume
        for latest_vol in [3000000, 200000, 1000000]:
            df = pd.DataFrame(
                {
                    "Date": dates,
                    "Open": [100.0] * 25,
                    "High": [105.0] * 25,
                    "Low": [95.0] * 25,
                    "Close": [102.0] * 25,
                    "Volume": [1000000] * 24 + [latest_vol],
                }
            )
            analyzer = StockInsightAnalyzer(df)
            insights = analyzer.generate_volume_insights()
            for ins in insights:
                full_text = f"{ins.title} {ins.observation} {ins.description} {ins.limitations}".lower()
                assert "institutional" not in full_text, f"Found institutional attribution in: {full_text}"

    def test_insufficient_or_zero_volume_handled_gracefully(self):
        dates = ["2026-01-01", "2026-01-02", "2026-01-03"]
        df_zero = pd.DataFrame(
            {
                "Date": dates,
                "Open": [100.0] * 3,
                "High": [105.0] * 3,
                "Low": [95.0] * 3,
                "Close": [102.0] * 3,
                "Volume": [0, 0, 0],
            }
        )
        analyzer = StockInsightAnalyzer(df_zero)
        insights = analyzer.generate_volume_insights()

        assert len(insights) == 1
        assert "Unavailable / Insufficient" in insights[0].title
        assert "institutional" not in (insights[0].limitations or "").lower()


# =============================================================================
# 7. Correlation Insights Tests
# =============================================================================


class TestCorrelationInsights:
    """Tests for correlation interpretations and non-causation boundaries."""

    def test_correlation_disclaimer_and_strength(self, synthetic_sample_df):
        analyzer = StockInsightAnalyzer(synthetic_sample_df)
        insights = analyzer.generate_correlation_insights()

        assert len(insights) == 1
        corr_ins = insights[0]
        assert corr_ins.category == InsightCategory.CORRELATION
        assert "correlation_r" in corr_ins.evidence
        # Verified feature identification
        assert corr_ins.evidence["features"] == ["Close", "Volume"]
        assert corr_ins.evidence["variable_x"] == "Close (raw price level)"
        assert corr_ins.evidence["variable_y"] == "Volume (daily share turnover)"
        assert corr_ins.evidence["correlation_method"] == "pearson"
        assert corr_ins.evidence["asset_scope"] == "single_ticker_intra_asset"
        # Crucial requirement: correlation does not establish causation
        assert "does not establish causation" in corr_ins.observation
        assert "does not imply causation" in corr_ins.limitations
        # Verified non-stationarity and single-asset limitation disclosures
        assert "non-stationary" in corr_ins.limitations.lower()
        assert "single asset" in corr_ins.limitations.lower()

    def test_no_cross_stock_or_causal_claims_in_correlation_insights(self, synthetic_sample_df):
        """Verify correlation output disclaims cross-stock claims and causal buying/selling pressure."""
        analyzer = StockInsightAnalyzer(synthetic_sample_df)
        insights = analyzer.generate_correlation_insights()

        assert len(insights) == 1
        ins = insights[0]

        # Verify that observation explicitly disclaims inferring buying or selling pressure
        assert "does not" in ins.observation.lower()
        assert "infer buying or selling pressure" in ins.observation.lower()
        # Verify that it does NOT make affirmative claims of buying/selling pressure
        assert "indicates buying pressure" not in ins.observation.lower()
        assert "indicates selling pressure" not in ins.observation.lower()
        assert "reflects buying pressure" not in ins.observation.lower()
        assert "reflects selling pressure" not in ins.observation.lower()
        # Single asset, no multi-stock claims
        assert "cross-stock" not in ins.observation.lower()
        assert ins.evidence["asset_scope"] == "single_ticker_intra_asset"


# =============================================================================
# 8. Summary, Safeguards & Regulatory Boundaries
# =============================================================================


class TestSummaryAndIntegrity:
    """Tests verifying absence of predictive claims, buy/sell advice, and output determinism."""

    def test_generate_summary_structure_and_categorization(self, rising_trend_df):
        analyzer = StockInsightAnalyzer(rising_trend_df)
        summary = analyzer.generate_summary()

        assert isinstance(summary, InsightSummary)
        assert summary.ticker == "RISING"
        assert summary.observation_count == len(rising_trend_df)
        assert len(summary.positive_observations) > 0
        assert len(summary.data_limitations) > 0
        assert len(summary.insights) > 0

    def test_synthetic_data_labeling_in_summary(self, synthetic_sample_df):
        analyzer = StockInsightAnalyzer(synthetic_sample_df)
        summary = analyzer.generate_summary()

        assert summary.is_synthetic is True
        # Verify explicit synthetic warning in limitations
        assert any("DATASET IS SYNTHETIC" in lim for lim in summary.data_limitations)

    def test_strict_absence_of_unsupported_investment_advice(self, synthetic_sample_df):
        """Strict verification: No buy, sell, or target price recommendations generated."""
        analyzer = StockInsightAnalyzer(synthetic_sample_df)
        summary = analyzer.generate_summary()

        forbidden_phrases = [
            "buy now",
            "sell now",
            "strong buy",
            "strong sell",
            "recommend buying",
            "recommend selling",
            "target price",
            "will outperform",
            "guaranteed return",
            "price will rise",
            "price will fall",
        ]

        all_text = " ".join(
            [ins.observation for ins in summary.insights]
            + summary.positive_observations
            + summary.negative_observations
        ).lower()

        for phrase in forbidden_phrases:
            assert phrase not in all_text, f"Forbidden financial advice phrase '{phrase}' detected!"

    def test_deterministic_repeated_execution(self, rising_trend_df):
        analyzer1 = StockInsightAnalyzer(rising_trend_df)
        summary1 = analyzer1.generate_summary().to_dict()

        analyzer2 = StockInsightAnalyzer(rising_trend_df)
        summary2 = analyzer2.generate_summary().to_dict()

        assert summary1 == summary2

    def test_functional_convenience_wrapper(self, rising_trend_df):
        summary = generate_stock_insights(rising_trend_df, ticker="TEST")
        assert isinstance(summary, InsightSummary)
        assert summary.ticker == "TEST"

    def test_backward_compatible_insights_engine_adapter(self, rising_trend_df):
        adapter = InsightsEngine(rising_trend_df)
        trend_texts = adapter.generate_trend_insights()
        risk_texts = adapter.generate_risk_insights()

        assert len(trend_texts) > 0
        assert len(risk_texts) > 0
        assert isinstance(trend_texts[0], str)
        assert isinstance(risk_texts[0], str)
