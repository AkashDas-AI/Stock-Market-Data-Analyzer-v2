"""CSV data loading and local file ingestion module.

Responsibility:
    Load local CSV stock datasets, synthetic demonstration data, and user-uploaded files,
    standardizing column names and date parsing while providing comprehensive error reporting.

Boundaries:
    This module performs structural ingestion and validation. Full data cleaning
    (missing-value imputation, outlier removal, deduplication) is deferred to Phase 4.
"""

from pathlib import Path
from typing import Union, List, Optional
import pandas as pd

from stock_analyzer.data.exceptions import (
    DataLoadingError,
    EmptyDataError,
    MissingColumnError,
    InvalidDateError,
)
from stock_analyzer.utils.config import SAMPLE_STOCK_CSV

# Mandatory OHLCV columns required for downstream analysis
REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]


class StockDataLoader:
    """Loader for tabular stock market data stored in CSV files."""

    def __init__(self, file_path: Union[str, Path]) -> None:
        """Initialize loader with file path.

        Args:
            file_path: Path to CSV data file.

        Raises:
            ValueError: If file_path is empty or None.
        """
        if not file_path:
            raise ValueError("File path must be provided.")
        self.file_path = Path(file_path)

    def load_csv(self) -> pd.DataFrame:
        """Load and normalize CSV data into a standardized DataFrame.

        Returns:
            Normalized pandas DataFrame containing ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            and optionally 'Adj Close', sorted chronologically by Date.

        Raises:
            DataLoadingError: If file is not found or cannot be read.
            EmptyDataError: If CSV file is empty.
            MissingColumnError: If required OHLCV columns are missing.
            InvalidDateError: If date values cannot be parsed.
        """
        if not self.file_path.exists():
            raise DataLoadingError(f"File not found: '{self.file_path}'")
        if not self.file_path.is_file():
            raise DataLoadingError(f"Specified path is not a file: '{self.file_path}'")

        try:
            df = pd.read_csv(self.file_path)
        except pd.errors.EmptyDataError:
            raise EmptyDataError(f"The CSV file '{self.file_path}' is completely empty.")
        except Exception as exc:
            raise DataLoadingError(f"Failed to read CSV file '{self.file_path}': {exc}") from exc

        if df.empty:
            raise EmptyDataError(f"The CSV file '{self.file_path}' contains zero data rows.")

        normalized_df = self._normalize_columns(df)
        validated_df = self._validate_and_parse_dates(normalized_df)

        # Attach metadata
        validated_df.attrs["source_file"] = str(self.file_path.resolve())
        validated_df.attrs["source"] = "Local CSV"
        validated_df.attrs["is_synthetic"] = self._check_if_synthetic()

        return validated_df

    def _check_if_synthetic(self) -> bool:
        """Determine if loaded file corresponds to the synthetic sample dataset."""
        try:
            return self.file_path.resolve() == SAMPLE_STOCK_CSV.resolve()
        except Exception:
            return False

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names to canonical casing."""
        working_df = df.copy()

        # Build column map handling common variations and whitespace
        col_map = {}
        for col in working_df.columns:
            cleaned = str(col).strip()
            lower_col = cleaned.lower()
            if lower_col in ("date", "datetime", "timestamp", "time"):
                col_map[col] = "Date"
            elif lower_col == "open":
                col_map[col] = "Open"
            elif lower_col == "high":
                col_map[col] = "High"
            elif lower_col == "low":
                col_map[col] = "Low"
            elif lower_col == "close":
                col_map[col] = "Close"
            elif lower_col in ("adj close", "adj_close", "adjusted close", "adjclose"):
                col_map[col] = "Adj Close"
            elif lower_col in ("volume", "vol", "shares"):
                col_map[col] = "Volume"

        working_df = working_df.rename(columns=col_map)

        # Check for presence of required columns
        missing_cols = [c for c in REQUIRED_COLUMNS if c not in working_df.columns]
        if missing_cols:
            raise MissingColumnError(
                f"CSV file '{self.file_path.name}' is missing mandatory columns: {missing_cols}. "
                f"Available columns are: {list(working_df.columns)}"
            )

        # Retain standard market columns in canonical order
        selected_cols = ["Date", "Open", "High", "Low", "Close"]
        if "Adj Close" in working_df.columns:
            selected_cols.append("Adj Close")
        selected_cols.append("Volume")

        working_df = working_df[selected_cols]

        # Convert numeric columns
        for col in ["Open", "High", "Low", "Close"]:
            working_df[col] = pd.to_numeric(working_df[col], errors="coerce")
        if "Adj Close" in working_df.columns:
            working_df["Adj Close"] = pd.to_numeric(working_df["Adj Close"], errors="coerce")
        working_df["Volume"] = pd.to_numeric(working_df["Volume"], errors="coerce")

        return working_df

    def _validate_and_parse_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse Date column into datetime and verify validity."""
        working_df = df.copy()

        # Attempt date conversion
        try:
            parsed_dates = pd.to_datetime(working_df["Date"], errors="coerce")
        except Exception as exc:
            raise InvalidDateError(
                f"Failed to parse dates in CSV file '{self.file_path.name}': {exc}"
            ) from exc

        # If any non-null raw date string resulted in NaT, signal invalid date values
        invalid_mask = working_df["Date"].notna() & parsed_dates.isna()
        if invalid_mask.any():
            invalid_samples = working_df.loc[invalid_mask, "Date"].head(3).tolist()
            raise InvalidDateError(
                f"CSV file '{self.file_path.name}' contains invalid date values that cannot be parsed: {invalid_samples}"
            )

        working_df["Date"] = parsed_dates

        # Remove timezone if present
        if hasattr(working_df["Date"].dt, "tz") and working_df["Date"].dt.tz is not None:
            working_df["Date"] = working_df["Date"].dt.tz_localize(None)

        # Sort chronologically and reset index
        working_df = working_df.sort_values(by="Date", ascending=True).reset_index(drop=True)

        return working_df

    @classmethod
    def load_sample(cls) -> pd.DataFrame:
        """Load the built-in synthetic sample dataset with explicit synthetic labelling.

        Returns:
            DataFrame populated from data/sample/sample_stock.csv with is_synthetic=True.
        """
        loader = cls(SAMPLE_STOCK_CSV)
        df = loader.load_csv()
        df.attrs["is_synthetic"] = True
        df.attrs["source"] = "Synthetic Sample Dataset (data/sample/sample_stock.csv)"
        return df


def load_stock_csv(file_path: Union[str, Path]) -> pd.DataFrame:
    """Convenience function to load and validate a stock CSV file.

    Args:
        file_path: Path to CSV data file.

    Returns:
        Standardized DataFrame.
    """
    loader = StockDataLoader(file_path)
    return loader.load_csv()


def load_sample_stock_data() -> pd.DataFrame:
    """Convenience function to load the synthetic sample dataset.

    Returns:
        DataFrame with sample data and synthetic metadata flag.
    """
    return StockDataLoader.load_sample()
