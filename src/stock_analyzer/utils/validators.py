"""Data and parameter validation helpers.

Responsibility:
    Validate ticker symbols, date ranges, DataFrame schemas, and input boundaries.
"""

from typing import List, Tuple
import pandas as pd

REQUIRED_OHLCV_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]


def validate_ohlcv_schema(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Validate that DataFrame has required OHLCV columns.

    Args:
        df: Input DataFrame to inspect.

    Returns:
        Tuple of (is_valid, list_of_missing_columns).
    """
    missing = [col for col in REQUIRED_OHLCV_COLUMNS if col not in df.columns]
    return (len(missing) == 0, missing)


def validate_price_boundaries(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Validate that High >= max(Open, Close) and Low <= min(Open, Close).

    Args:
        df: Input DataFrame with numeric price columns.

    Returns:
        Tuple of (is_valid, list_of_error_descriptions).
    """
    errors = []
    if not ((df["High"] >= df["Open"]).all() and (df["High"] >= df["Close"]).all()):
        errors.append("Found rows where High < Open or High < Close.")
    if not ((df["Low"] <= df["Open"]).all() and (df["Low"] <= df["Close"]).all()):
        errors.append("Found rows where Low > Open or Low > Close.")
    if (df["Low"] <= 0).any():
        errors.append("Found non-positive price values in Low column.")
    return (len(errors) == 0, errors)
