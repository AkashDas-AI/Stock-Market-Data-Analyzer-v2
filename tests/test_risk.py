"""Unit tests for risk, volatility, and maximum drawdown (MDD) module."""

import numpy as np
import pandas as pd
import pytest

from stock_analyzer.analysis.risk import (
    RiskAnalyzer,
    calculate_daily_volatility,
    calculate_annualized_volatility,
    calculate_rolling_volatility,
    calculate_drawdown_series,
    calculate_max_drawdown,
)
from stock_analyzer.data.exceptions import (
    DataValidationError,
    EmptyDataError,
    MissingColumnError,
)


@pytest.fixture
def sample_known_risk_df() -> pd.DataFrame:
    """Fixture with known price peak, drawdown trough, and recovery trajectory.

    Day 1: 100.0 (Starting baseline)
    Day 2: 120.0 (Peak! HWM = 120.0, DD = 0.0)
    Day 3: 90.0  (Trough! Wealth = 90/100 = 0.9, HWM = 1.2, DD = (90 - 120)/120 = -0.25 -> -25%)
    Day 4: 110.0 (Partial recovery, DD = (110 - 120)/120 = -0.083333)
    Day 5: 130.0 (New Peak! HWM = 130.0, DD = 0.0)

    Returns:
    R_1: NaN
    R_2: (120 - 100)/100 = 0.20
    R_3: (90 - 120)/120 = -0.25
    R_4: (110 - 90)/90 = 0.222222...
    R_5: (130 - 110)/110 = 0.181818...
    """
    return pd.DataFrame(
        {
            "Date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"],
            "Close": [100.0, 120.0, 90.0, 110.0, 130.0],
            "Open": [99.0, 119.0, 100.0, 95.0, 120.0],
            "High": [101.0, 125.0, 105.0, 112.0, 132.0],
            "Low": [98.0, 118.0, 89.0, 92.0, 119.0],
            "Volume": [1000, 2000, 3000, 2500, 3500],
        }
    )


class TestRiskAnalyzerValidation:
    """Tests input validation, type safety, and defensive copies."""

    def test_invalid_input_type_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected pandas Series or DataFrame"):
            RiskAnalyzer(12345)  # type: ignore

    def test_empty_dataframe_raises_empty_data_error(self):
        with pytest.raises(EmptyDataError, match="Cannot perform risk calculations on empty data"):
            RiskAnalyzer(pd.DataFrame())

    def test_empty_series_raises_empty_data_error(self):
        with pytest.raises(EmptyDataError, match="Cannot perform risk calculations on empty data"):
            RiskAnalyzer(pd.Series([], dtype=float))

    def test_missing_price_column_raises_missing_column_error(self, sample_known_risk_df):
        with pytest.raises(MissingColumnError, match="Specified price column 'NonExistent' not found"):
            RiskAnalyzer(sample_known_risk_df, price_column="NonExistent")

    def test_non_numeric_prices_raise_data_validation_error(self, sample_known_risk_df):
        df = sample_known_risk_df.copy()
        df["Close"] = ["100", "120", "90", "110", "130"]
        with pytest.raises(DataValidationError, match="must have numeric data type"):
            RiskAnalyzer(df, price_column="Close")

    def test_invalid_annualization_factor_raises_value_error(self, sample_known_risk_df):
        analyzer = RiskAnalyzer(sample_known_risk_df)
        with pytest.raises(ValueError, match="Annualization factor must be a positive integer"):
            analyzer.calculate_annualized_volatility(annualization_factor=0)
        with pytest.raises(ValueError, match="Annualization factor must be a positive integer"):
            analyzer.calculate_annualized_volatility(annualization_factor=-10)


class TestVolatilityCalculations:
    """Tests daily volatility, sample ddof=1, and annualization scaling."""

    def test_daily_volatility_known_sequence(self):
        # 5 returns: [0.01, -0.02, 0.03, -0.01, 0.02]
        returns = pd.Series([np.nan, 0.01, -0.02, 0.03, -0.01, 0.02])
        analyzer = RiskAnalyzer(returns)

        # Expected sample std (ddof=1) of [0.01, -0.02, 0.03, -0.01, 0.02]
        valid_vals = [0.01, -0.02, 0.03, -0.01, 0.02]
        expected_std = float(np.std(valid_vals, ddof=1))

        daily_vol = analyzer.calculate_daily_volatility(ddof=1)
        assert daily_vol == pytest.approx(expected_std)

    def test_annualized_volatility_scaling(self):
        returns = pd.Series([np.nan, 0.01, -0.02, 0.03, -0.01, 0.02])
        analyzer = RiskAnalyzer(returns)

        daily_vol = analyzer.calculate_daily_volatility(ddof=1)
        # Default 252 days
        expected_annual_252 = daily_vol * np.sqrt(252)
        assert analyzer.calculate_annualized_volatility(annualization_factor=252) == pytest.approx(expected_annual_252)

        # Custom annualization factor (e.g. 365 days)
        expected_annual_365 = daily_vol * np.sqrt(365)
        assert analyzer.calculate_annualized_volatility(annualization_factor=365) == pytest.approx(expected_annual_365)

    def test_insufficient_observations_returns_nan(self):
        # Only 1 observation -> cannot compute sample std with ddof=1
        returns_single = pd.Series([np.nan, 0.05])
        analyzer_single = RiskAnalyzer(returns_single)

        assert np.isnan(analyzer_single.calculate_daily_volatility(ddof=1))
        assert np.isnan(analyzer_single.calculate_annualized_volatility())


class TestDrawdownCalculations:
    """Tests drawdown series and maximum drawdown (MDD) against ground truth."""

    def test_drawdown_series_known_values(self, sample_known_risk_df):
        analyzer = RiskAnalyzer(sample_known_risk_df)
        dd = analyzer.calculate_drawdown_series()

        assert len(dd) == 5
        assert dd.name == "Drawdown"

        # Day 1: 100/100 - 1 = 0.0
        assert dd.iloc[0] == pytest.approx(0.0)
        # Day 2: 120/120 - 1 = 0.0 (New peak)
        assert dd.iloc[1] == pytest.approx(0.0)
        # Day 3: 90/120 - 1 = -30/120 = -0.25 (-25.0%)
        assert dd.iloc[2] == pytest.approx(-0.25)
        # Day 4: 110/120 - 1 = -10/120 = -0.08333333333333337
        assert dd.iloc[3] == pytest.approx(-10.0 / 120.0)
        # Day 5: 130/130 - 1 = 0.0 (New peak)
        assert dd.iloc[4] == pytest.approx(0.0)

    def test_maximum_drawdown_metrics_and_dates(self, sample_known_risk_df):
        analyzer = RiskAnalyzer(sample_known_risk_df)
        mdd_res = analyzer.calculate_max_drawdown()

        assert mdd_res["max_drawdown"] == pytest.approx(-0.25)
        assert mdd_res["max_drawdown_pct"] == pytest.approx(-25.0)

        # Prior peak occurred on 2026-01-02 (Price = 120)
        assert mdd_res["peak_date"] == "2026-01-02"
        assert mdd_res["peak_index"] == 1
        assert mdd_res["peak_wealth"] == pytest.approx(1.2)

        # Drawdown trough occurred on 2026-01-03 (Price = 90)
        assert mdd_res["trough_date"] == "2026-01-03"
        assert mdd_res["trough_index"] == 2
        assert mdd_res["trough_wealth"] == pytest.approx(0.9)


class TestEdgeCasesAndSeriesInput:
    """Tests edge cases: flat prices, rising prices, falling prices, and series inputs."""

    def test_flat_prices_zero_drawdown_and_volatility(self):
        prices = pd.Series([100.0, 100.0, 100.0, 100.0])
        analyzer = RiskAnalyzer(prices.to_frame(name="Close"))

        assert analyzer.calculate_daily_volatility() == pytest.approx(0.0)
        assert analyzer.calculate_annualized_volatility() == pytest.approx(0.0)

        dd = analyzer.calculate_drawdown_series()
        assert (dd == 0.0).all()

        mdd_res = analyzer.calculate_max_drawdown()
        assert mdd_res["max_drawdown"] == pytest.approx(0.0)

    def test_strictly_rising_prices_zero_drawdown(self):
        prices = pd.Series([100.0, 105.0, 110.0, 120.0])
        analyzer = RiskAnalyzer(prices.to_frame(name="Close"))

        dd = analyzer.calculate_drawdown_series()
        assert (dd == 0.0).all()

        mdd_res = analyzer.calculate_max_drawdown()
        assert mdd_res["max_drawdown"] == pytest.approx(0.0)

    def test_strictly_falling_prices_maximum_drawdown(self):
        dates = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]
        prices = pd.Series([100.0, 90.0, 80.0, 70.0])
        df = pd.DataFrame({"Date": dates, "Close": prices})
        analyzer = RiskAnalyzer(df)

        mdd_res = analyzer.calculate_max_drawdown()
        # Fall from 100 to 70 = -30%
        assert mdd_res["max_drawdown"] == pytest.approx(-0.30)
        assert mdd_res["peak_date"] == "2026-01-01"
        assert mdd_res["trough_date"] == "2026-01-04"

    def test_series_input_with_explicit_dates(self):
        returns = pd.Series([np.nan, 0.20, -0.25, 0.222222, 0.181818])
        dates = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"]
        analyzer = RiskAnalyzer(returns, dates=dates)

        mdd_res = analyzer.calculate_max_drawdown()
        assert mdd_res["max_drawdown"] == pytest.approx(-0.25)
        assert mdd_res["peak_date"] == "2026-01-02"
        assert mdd_res["trough_date"] == "2026-01-03"

    def test_functional_wrappers(self, sample_known_risk_df):
        d_vol = calculate_daily_volatility(sample_known_risk_df)
        a_vol = calculate_annualized_volatility(sample_known_risk_df, annualization_factor=252)
        r_vol = calculate_rolling_volatility(sample_known_risk_df, window=2)
        dd = calculate_drawdown_series(sample_known_risk_df)
        mdd = calculate_max_drawdown(sample_known_risk_df)

        assert isinstance(d_vol, float)
        assert isinstance(a_vol, float)
        assert isinstance(r_vol, pd.Series)
        assert isinstance(dd, pd.Series)
        assert isinstance(mdd, dict)
        assert mdd["max_drawdown"] == pytest.approx(-0.25)


class TestRollingVolatilityCalculations:
    """Tests rolling annualized return volatility across sliding windows."""

    def test_invalid_rolling_window_raises_value_error(self, sample_known_risk_df):
        analyzer = RiskAnalyzer(sample_known_risk_df)
        with pytest.raises(ValueError, match="Rolling window must be an integer >= 2"):
            analyzer.calculate_rolling_volatility(window=1)
        with pytest.raises(ValueError, match="Rolling window must be an integer >= 2"):
            analyzer.calculate_rolling_volatility(window=0)
        with pytest.raises(ValueError, match="Rolling window must be an integer >= 2"):
            analyzer.calculate_rolling_volatility(window="invalid")  # type: ignore

    def test_invalid_annualization_factor_raises_value_error(self, sample_known_risk_df):
        analyzer = RiskAnalyzer(sample_known_risk_df)
        with pytest.raises(ValueError, match="Annualization factor must be a positive integer >= 1"):
            analyzer.calculate_rolling_volatility(window=2, annualization_factor=0)

    def test_rolling_volatility_warmup_and_calculation(self):
        # 6 prices: [100.0, 102.0, 101.0, 104.0, 103.0, 106.0]
        # returns:
        # idx 0: NaN
        # idx 1: 0.02
        # idx 2: -0.00980392
        # idx 3: 0.02970297
        # idx 4: -0.00961538
        # idx 5: 0.02912621
        prices = pd.Series([100.0, 102.0, 101.0, 104.0, 103.0, 106.0])
        df = pd.DataFrame({"Date": [f"2026-01-0{i+1}" for i in range(6)], "Close": prices})
        analyzer = RiskAnalyzer(df)

        # Window = 2:
        # returns at idx 0 is NaN
        # idx 1 has only 1 valid return in lookback [NaN, 0.02] -> rolling_std is NaN
        # idx 2 has 2 valid returns [0.02, -0.00980392] -> valid rolling_std
        roll_vol = analyzer.calculate_rolling_volatility(window=2, annualization_factor=252)

        assert len(roll_vol) == 6
        assert np.isnan(roll_vol.iloc[0])
        assert np.isnan(roll_vol.iloc[1])
        assert not np.isnan(roll_vol.iloc[2])

        r1 = (102.0 - 100.0) / 100.0
        r2 = (101.0 - 102.0) / 102.0
        expected_std = float(np.std([r1, r2], ddof=1))
        expected_annual_vol = expected_std * np.sqrt(252)
        assert roll_vol.iloc[2] == pytest.approx(expected_annual_vol)
