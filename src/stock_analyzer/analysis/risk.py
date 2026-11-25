"""Risk and volatility analysis module.

Responsibility:
    Calculate daily return volatility, annualized volatility (configurable scaling factor),
    drawdown time series, and peak-to-trough maximum drawdown (MDD) with date identification.

Architecture Boundaries (Phase 7):
    - Risk profiling: standard deviation, annualization, wealth index, and drawdown.
    - NO automated trading signals or buy/sell execution logic.
    - NO Plotly interactive charts (Phase 8).
    - NO Streamlit dashboard functionality (Phase 9).
    - NO report generation (Phase 11).
"""

from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from stock_analyzer.data.exceptions import (
    DataValidationError,
    EmptyDataError,
    MissingColumnError,
)

DEFAULT_TRADING_DAYS: int = 252


class RiskAnalyzer:
    """Computes historical return volatility, wealth drawdowns, and maximum drawdown metrics.

    Supports initialization with either a daily returns pd.Series or an OHLCV pd.DataFrame.
    Enforces input immutability, date alignment, and robust statistical safeguards.
    """

    def __init__(
        self,
        data: Union[pd.Series, pd.DataFrame],
        price_column: str = "Close",
        dates: Optional[Union[pd.Series, List[Any]]] = None,
    ) -> None:
        """Initialize the risk analyzer with a return series or stock DataFrame.

        Args:
            data: A pandas Series of daily returns or a DataFrame containing price data.
            price_column: Column name to compute returns from if a DataFrame is provided.
                          Defaults to 'Close'.
            dates: Optional date series or list matching observation timestamps when passing Series.

        Raises:
            TypeError: If data is neither a pandas Series nor DataFrame.
            EmptyDataError: If data is empty.
            MissingColumnError: If a DataFrame is provided and lacks price_column.
            DataValidationError: If prices or returns are non-numeric.
        """
        if not isinstance(data, (pd.Series, pd.DataFrame)):
            raise TypeError(
                f"Expected pandas Series or DataFrame for risk analysis, received {type(data).__name__}."
            )
        if data.empty:
            raise EmptyDataError("Cannot perform risk calculations on empty data.")

        self.price_column = price_column
        self.prices: Optional[pd.Series] = None
        self.dates: Optional[pd.Series] = None

        if isinstance(data, pd.DataFrame):
            if price_column not in data.columns:
                raise MissingColumnError(
                    f"Specified price column '{price_column}' not found in DataFrame columns: {list(data.columns)}."
                )
            if not pd.api.types.is_numeric_dtype(data[price_column]):
                raise DataValidationError(
                    f"Price column '{price_column}' must have numeric data type, found {data[price_column].dtype}."
                )

            # Defensive deep copy to preserve input immutability
            working_df = data.copy(deep=True)
            if "Date" in working_df.columns:
                try:
                    date_dt = pd.to_datetime(working_df["Date"])
                    sort_indices = np.argsort(date_dt.values)
                    working_df = working_df.iloc[sort_indices].reset_index(drop=True)
                except Exception:
                    working_df = working_df.sort_values(by="Date", ascending=True).reset_index(drop=True)
                self.dates = working_df["Date"]
            elif dates is not None:
                self.dates = pd.Series(dates).reset_index(drop=True)

            self.prices = working_df[price_column].copy()
            # Calculate returns with first observation preserved as NaN
            self.returns = self.prices.pct_change()
            self.returns.name = "Daily_Return"
        else:
            # Series input
            if not pd.api.types.is_numeric_dtype(data):
                raise DataValidationError(
                    f"Return series must have numeric data type, found {data.dtype}."
                )
            self.returns = data.copy(deep=True)
            if dates is not None:
                self.dates = pd.Series(dates).reset_index(drop=True)
            elif isinstance(data.index, pd.DatetimeIndex):
                self.dates = pd.Series(data.index).reset_index(drop=True)
            elif "Date" in getattr(data, "attrs", {}):
                self.dates = pd.Series(data.attrs["Date"]).reset_index(drop=True)

    def calculate_daily_volatility(self, ddof: int = 1) -> float:
        """Calculate sample standard deviation of daily percentage returns.

        Formula:
            sigma_daily = sqrt( (1 / (N - ddof)) * sum_{t=1}^N (R_t - R_mean)^2 )

        Args:
            ddof: Delta Degrees of Freedom. Defaults to 1 (unbiased sample standard deviation).

        Returns:
            Daily volatility as float, or np.nan if fewer than 2 valid observations exist.
        """
        valid_returns = self.returns.dropna()
        if len(valid_returns) <= ddof:
            return float("nan")

        return float(valid_returns.std(ddof=ddof))

    def calculate_annualized_volatility(
        self, annualization_factor: int = DEFAULT_TRADING_DAYS, ddof: int = 1
    ) -> float:
        """Calculate annualized volatility scaled from daily return standard deviation.

        Formula:
            sigma_annual = sigma_daily * sqrt(annualization_factor)

        Annualization Assumption:
            Assumes daily returns are independently and identically distributed (i.i.d.)
            over trading sessions per calendar year (typically 252 days for equity markets).

        Args:
            annualization_factor: Number of trading periods per year (defaults to 252).
                                  Must be a positive integer >= 1.
            ddof: Delta Degrees of Freedom (defaults to 1).

        Returns:
            Annualized volatility as float, or np.nan if insufficient observations.

        Raises:
            ValueError: If annualization_factor is less than 1.
        """
        if not isinstance(annualization_factor, (int, np.integer)) or annualization_factor < 1:
            raise ValueError(
                f"Annualization factor must be a positive integer >= 1, got {annualization_factor}."
            )

        daily_vol = self.calculate_daily_volatility(ddof=ddof)
        if np.isnan(daily_vol):
            return float("nan")

        return float(daily_vol * np.sqrt(annualization_factor))

    def calculate_volatility(
        self, annualized: bool = True, trading_days: int = DEFAULT_TRADING_DAYS, ddof: int = 1
    ) -> float:
        """General volatility calculation wrapper matching starter interface."""
        if annualized:
            return self.calculate_annualized_volatility(
                annualization_factor=trading_days, ddof=ddof
            )
        return self.calculate_daily_volatility(ddof=ddof)

    def calculate_rolling_volatility(
        self,
        window: int = 21,
        annualization_factor: int = DEFAULT_TRADING_DAYS,
        ddof: int = 1,
    ) -> pd.Series:
        """Calculate rolling annualized return volatility over a sliding window.

        Formula:
            sigma_{rolling, t} = std(R_{t-window+1:t}, ddof=ddof) * sqrt(annualization_factor)

        Args:
            window: Rolling window size in trading periods (defaults to 21, ~1 month).
                    Must be an integer >= 2.
            annualization_factor: Number of trading periods per year (defaults to 252).
                                  Must be a positive integer >= 1.
            ddof: Delta Degrees of Freedom (defaults to 1).

        Returns:
            A pandas Series of annualized rolling volatility in decimal (e.g. 0.25 = 25%),
            indexed identically to the returns series. Lookback warm-up observations
            contain NaN.

        Raises:
            ValueError: If window < 2, annualization_factor < 1, or ddof < 0.
        """
        if not isinstance(window, (int, np.integer)) or window < 2:
            raise ValueError(f"Rolling window must be an integer >= 2, got {window}.")
        if not isinstance(annualization_factor, (int, np.integer)) or annualization_factor < 1:
            raise ValueError(
                f"Annualization factor must be a positive integer >= 1, got {annualization_factor}."
            )
        if not isinstance(ddof, (int, np.integer)) or ddof < 0:
            raise ValueError(f"ddof must be a non-negative integer, got {ddof}.")

        rolling_std = self.returns.rolling(window=window, min_periods=window).std(ddof=ddof)
        rolling_annual = rolling_std * np.sqrt(annualization_factor)
        rolling_annual.name = f"Rolling_Vol_{window}"
        return rolling_annual

    def calculate_drawdown_series(self) -> pd.Series:
        """Calculate historical peak-to-trough drawdown time series.

        Formula:
            Wealth_t = Product_{i=1}^t (1 + Daily Return_i)  [Wealth_0 = 1.0]
            Peak_t = max_{0 <= s <= t} Wealth_s              [High-Water Mark]
            Drawdown_t = (Wealth_t / Peak_t) - 1.0

        Conventions & Boundary Rules:
            - Drawdown is always non-positive (DD_t <= 0.0).
            - At all-time highs / new peaks, Drawdown_t = 0.0.
            - Baseline wealth begins at 1.0 at index 0.

        Returns:
            A named pandas Series of drawdowns representing percentage decline from peak.
        """
        if self.prices is not None:
            # Direct wealth ratio from prices
            wealth = self.prices / self.prices.iloc[0]
        else:
            # Wealth accumulated from return stream
            growth_factors = 1.0 + self.returns.fillna(0.0)
            wealth = growth_factors.cumprod()

        running_peak = wealth.cummax()
        # Avoid division by zero if peak is 0
        running_peak_safe = np.where(running_peak > 0, running_peak, np.nan)
        drawdown = pd.Series(
            (wealth / running_peak_safe) - 1.0, index=self.returns.index, name="Drawdown"
        )
        return drawdown

    def calculate_max_drawdown(self) -> Dict[str, Any]:
        """Compute maximum peak-to-trough drawdown and identify critical dates.

        Formula:
            Maximum Drawdown (MDD) = min_t Drawdown_t
            trough_idx = argmin_t Drawdown_t
            peak_idx = argmax_{0 <= s <= trough_idx} Wealth_s

        Returns:
            Dictionary containing:
                - `max_drawdown`: Minimum drawdown value (<= 0.0).
                - `max_drawdown_pct`: MDD expressed as percentage (e.g. -25.0).
                - `peak_date`: Timestamp string when the prior high-water mark occurred.
                - `trough_date`: Timestamp string when the deepest drawdown occurred.
                - `peak_wealth`: Wealth level at the high-water mark.
                - `trough_wealth`: Wealth level at the deepest drawdown trough.
                - `peak_index`: Observation index of prior peak.
                - `trough_index`: Observation index of maximum drawdown trough.
        """
        if self.prices is not None:
            wealth = self.prices / self.prices.iloc[0]
        else:
            growth_factors = 1.0 + self.returns.fillna(0.0)
            wealth = growth_factors.cumprod()

        running_peak = wealth.cummax()
        running_peak_safe = np.where(running_peak > 0, running_peak, np.nan)
        drawdown = pd.Series(
            (wealth / running_peak_safe) - 1.0, index=self.returns.index, name="Drawdown"
        )

        valid_dd = drawdown.dropna()
        if valid_dd.empty:
            return {
                "max_drawdown": float("nan"),
                "max_drawdown_pct": float("nan"),
                "peak_date": None,
                "trough_date": None,
                "peak_wealth": float("nan"),
                "trough_wealth": float("nan"),
                "peak_index": None,
                "trough_index": None,
            }

        mdd = float(valid_dd.min())
        trough_idx = int(valid_dd.idxmin())

        # The prior peak corresponds to the highest wealth achieved up to the trough
        prior_wealth_slice = wealth.iloc[: trough_idx + 1]
        peak_idx = int(prior_wealth_slice.idxmax())

        peak_date = None
        trough_date = None
        if self.dates is not None and len(self.dates) > max(peak_idx, trough_idx):
            peak_date = str(self.dates.iloc[peak_idx])
            trough_date = str(self.dates.iloc[trough_idx])

        return {
            "max_drawdown": mdd,
            "max_drawdown_pct": mdd * 100.0,
            "peak_date": peak_date,
            "trough_date": trough_date,
            "peak_wealth": float(wealth.iloc[peak_idx]),
            "trough_wealth": float(wealth.iloc[trough_idx]),
            "peak_index": peak_idx,
            "trough_index": trough_idx,
        }


# =============================================================================
# Functional Convenience Wrappers
# =============================================================================


def calculate_daily_volatility(
    data: Union[pd.Series, pd.DataFrame],
    price_column: str = "Close",
    ddof: int = 1,
) -> float:
    """Convenience function to compute daily volatility."""
    analyzer = RiskAnalyzer(data, price_column=price_column)
    return analyzer.calculate_daily_volatility(ddof=ddof)


def calculate_annualized_volatility(
    data: Union[pd.Series, pd.DataFrame],
    annualization_factor: int = DEFAULT_TRADING_DAYS,
    price_column: str = "Close",
    ddof: int = 1,
) -> float:
    """Convenience function to compute annualized volatility."""
    analyzer = RiskAnalyzer(data, price_column=price_column)
    return analyzer.calculate_annualized_volatility(
        annualization_factor=annualization_factor, ddof=ddof
    )


def calculate_drawdown_series(
    data: Union[pd.Series, pd.DataFrame],
    price_column: str = "Close",
) -> pd.Series:
    """Convenience function to compute peak-to-trough drawdown series."""
    analyzer = RiskAnalyzer(data, price_column=price_column)
    return analyzer.calculate_drawdown_series()


def calculate_max_drawdown(
    data: Union[pd.Series, pd.DataFrame],
    price_column: str = "Close",
) -> Dict[str, Any]:
    """Convenience function to compute maximum drawdown and peak/trough dates."""
    analyzer = RiskAnalyzer(data, price_column=price_column)
    return analyzer.calculate_max_drawdown()


def calculate_rolling_volatility(
    data: Union[pd.Series, pd.DataFrame],
    window: int = 21,
    annualization_factor: int = DEFAULT_TRADING_DAYS,
    price_column: str = "Close",
    ddof: int = 1,
) -> pd.Series:
    """Convenience function to compute rolling annualized volatility series."""
    analyzer = RiskAnalyzer(data, price_column=price_column)
    return analyzer.calculate_rolling_volatility(
        window=window, annualization_factor=annualization_factor, ddof=ddof
    )
