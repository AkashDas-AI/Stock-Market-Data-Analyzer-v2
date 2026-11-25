"""Data cleaning, integrity validation, and preprocessing module.

Responsibility:
    Validate stock-market time series against financial sanity checks,
    distinguish exact duplicate records from conflicting duplicate timestamps,
    handle missing values and anomalies deterministically,
    and produce comprehensive, auditable cleaning reports.

Boundaries:
    This module performs structural cleaning and data validation. Exploratory
    data analysis (EDA), moving averages, indicators, returns, and visualizations
    are strictly deferred to later phases.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, NamedTuple, Any, Union
import pandas as pd

from stock_analyzer.data.exceptions import (
    EmptyDataError,
    MissingColumnError,
    DataValidationError,
)
from stock_analyzer.utils.config import PROCESSED_DATA_DIR

# Mandatory columns required for analytical pipelines
MANDATORY_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]
VALID_CONFLICT_POLICIES = ("reject", "retain", "keep_last", "keep_first")


@dataclass
class CleaningReport:
    """Comprehensive, auditable summary of data cleaning and validation."""

    original_row_count: int
    final_row_count: int
    missing_values_by_column: Dict[str, int] = field(default_factory=dict)
    exact_duplicates_count: int = 0
    conflicting_duplicates_count: int = 0
    duplicate_dates_count: int = 0
    duplicate_policy: str = "reject"
    conflict_policy: str = "reject"
    invalid_records_count: int = 0
    records_removed: int = 0
    removal_reasons: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    is_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary representation."""
        return {
            "original_row_count": self.original_row_count,
            "final_row_count": self.final_row_count,
            "missing_values_by_column": self.missing_values_by_column,
            "exact_duplicates_count": self.exact_duplicates_count,
            "conflicting_duplicates_count": self.conflicting_duplicates_count,
            "duplicate_dates_count": self.duplicate_dates_count,
            "duplicate_policy": self.duplicate_policy,
            "conflict_policy": self.conflict_policy,
            "invalid_records_count": self.invalid_records_count,
            "records_removed": self.records_removed,
            "removal_reasons": self.removal_reasons,
            "warnings": self.warnings,
            "is_valid": self.is_valid,
        }

    def summary(self) -> str:
        """Produce formatted string summary of the cleaning execution."""
        lines = [
            "=== Data Cleaning Report ===",
            f"Original Rows: {self.original_row_count}",
            f"Final Rows:    {self.final_row_count}",
            f"Rows Removed:  {self.records_removed}",
            f"Exact Duplicates: {self.exact_duplicates_count}",
            f"Conflicting Duplicates: {self.conflicting_duplicates_count}",
            f"Conflict Policy: {self.conflict_policy}",
            f"Invalid OHLC:  {self.invalid_records_count}",
            f"Status:        {'VALID' if self.is_valid else 'INVALID'}",
        ]
        if self.removal_reasons:
            lines.append("Removal Reasons:")
            for reason, count in self.removal_reasons.items():
                lines.append(f"  - {reason}: {count}")
        if self.warnings:
            lines.append("Warnings:")
            for warn in self.warnings:
                lines.append(f"  - {warn}")
        return "\n".join(lines)


class CleaningResult(NamedTuple):
    """Container holding cleaned DataFrame and associated audit report."""

    data: pd.DataFrame
    report: CleaningReport


class StockDataCleaner:
    """Validator and cleaner for raw financial stock market time-series."""

    def __init__(
        self,
        df: pd.DataFrame,
        duplicate_policy: Optional[str] = None,
        conflict_policy: str = "reject",
        drop_missing: bool = True,
    ) -> None:
        """Initialize cleaner with input DataFrame and configuration.

        Args:
            df: Input DataFrame produced by Phase 3 ingestion.
            duplicate_policy: Optional policy for handling duplicates ('reject', 'retain', 'keep_last', 'keep_first').
                Maintained for backward compatibility; takes precedence if specified.
            conflict_policy: Policy for handling conflicting duplicate timestamps
                ('reject', 'retain', 'keep_last', 'keep_first'). Defaults to 'reject'.
            drop_missing: Whether to drop rows missing mandatory OHLCV values.

        Raises:
            TypeError: If df is not a pandas DataFrame.
            ValueError: If conflict_policy or duplicate_policy is unrecognized.
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame.")

        # Determine effective conflict policy
        effective_policy = duplicate_policy if duplicate_policy is not None else conflict_policy
        if effective_policy not in VALID_CONFLICT_POLICIES:
            raise ValueError(
                f"Invalid policy '{effective_policy}'. "
                f"Allowed policies are: {VALID_CONFLICT_POLICIES}"
            )

        # Defensive deep copy to guarantee raw data remains immutable
        self.raw_df = df.copy(deep=True)
        self.effective_policy = effective_policy
        self.drop_missing = drop_missing
        self._report: Optional[CleaningReport] = None

    @property
    def report(self) -> Optional[CleaningReport]:
        """Access the latest cleaning report."""
        return self._report

    def clean(self) -> CleaningResult:
        """Execute the complete data cleaning and validation pipeline.

        Returns:
            CleaningResult containing the cleaned DataFrame and CleaningReport.

        Raises:
            EmptyDataError: If the input DataFrame is empty.
            MissingColumnError: If mandatory columns are absent.
            DataValidationError: If conflicting duplicate records exist under 'reject' policy.
        """
        if self.raw_df.empty:
            raise EmptyDataError("Cannot clean an empty DataFrame.")

        # 1. Validate mandatory schema
        missing_cols = [c for c in MANDATORY_COLUMNS if c not in self.raw_df.columns]
        if missing_cols:
            raise MissingColumnError(
                f"DataFrame is missing mandatory columns: {missing_cols}. "
                f"Available columns: {list(self.raw_df.columns)}"
            )

        working_df = self.raw_df.copy(deep=True)
        original_count = len(working_df)
        removal_reasons: Dict[str, int] = {}
        warnings: List[str] = []

        # 2. Date parsing and invalid date detection
        raw_dates = working_df["Date"]
        parsed_dates = pd.to_datetime(raw_dates, errors="coerce")
        invalid_dates_mask = raw_dates.notna() & parsed_dates.isna()
        null_dates_mask = raw_dates.isna()
        bad_date_mask = invalid_dates_mask | null_dates_mask

        if bad_date_mask.any():
            bad_date_count = int(bad_date_mask.sum())
            removal_reasons["invalid_or_missing_date"] = bad_date_count
            warnings.append(f"Removed {bad_date_count} rows with invalid or missing date timestamps.")
            working_df = working_df[~bad_date_mask].copy()
            parsed_dates = parsed_dates[~bad_date_mask]

        working_df["Date"] = parsed_dates
        if hasattr(working_df["Date"].dt, "tz") and working_df["Date"].dt.tz is not None:
            working_df["Date"] = working_df["Date"].dt.tz_localize(None)

        # 3. Exact Duplicate Records Handling (Identical values across ALL columns)
        exact_dup_mask = working_df.duplicated(keep="first")
        exact_dup_count = int(exact_dup_mask.sum())

        if exact_dup_count > 0:
            removal_reasons["exact_duplicate_record"] = exact_dup_count
            warnings.append(
                f"Removed {exact_dup_count} exact duplicate records (identical values across all fields)."
            )
            working_df = working_df[~exact_dup_mask].copy()

        # 4. Conflicting Duplicate Records Handling (Same timestamp, differing values)
        conflict_dup_mask_excess = working_df.duplicated(subset=["Date"], keep="first")
        conflicting_count = int(conflict_dup_mask_excess.sum())

        if conflicting_count > 0:
            conflict_all_mask = working_df.duplicated(subset=["Date"], keep=False)
            conflicting_dates = sorted(
                working_df.loc[conflict_all_mask, "Date"].dt.strftime("%Y-%m-%d").unique().tolist()
            )

            if self.effective_policy == "reject":
                raise DataValidationError(
                    f"Found {conflicting_count} conflicting duplicate records on date(s): {conflicting_dates}. "
                    "Records share the same timestamp but have conflicting price or volume values. "
                    "To resolve, explicitly configure conflict_policy='keep_last', 'keep_first', or 'retain'."
                )
            elif self.effective_policy == "retain":
                warnings.append(
                    f"Retained {conflicting_count} conflicting duplicate records for date(s): {conflicting_dates} for manual review."
                )
            elif self.effective_policy == "keep_last":
                drop_mask = working_df.duplicated(subset=["Date"], keep="last")
                working_df = working_df[~drop_mask].copy()
                removal_reasons["conflicting_duplicate_date"] = conflicting_count
                warnings.append(
                    f"Resolved {conflicting_count} conflicting duplicate records on date(s) {conflicting_dates} "
                    "using explicit 'keep_last' policy."
                )
            elif self.effective_policy == "keep_first":
                drop_mask = working_df.duplicated(subset=["Date"], keep="first")
                working_df = working_df[~drop_mask].copy()
                removal_reasons["conflicting_duplicate_date"] = conflicting_count
                warnings.append(
                    f"Resolved {conflicting_count} conflicting duplicate records on date(s) {conflicting_dates} "
                    "using explicit 'keep_first' policy."
                )

        total_duplicates_tracked = exact_dup_count + conflicting_count

        # 5. Numeric type conversion
        numeric_cols = ["Open", "High", "Low", "Close", "Volume"]
        has_adj_close = "Adj Close" in working_df.columns
        if has_adj_close:
            numeric_cols.append("Adj Close")

        for col in numeric_cols:
            working_df[col] = pd.to_numeric(working_df[col], errors="coerce")

        # Record missing values by column
        missing_by_col = {col: int(working_df[col].isna().sum()) for col in working_df.columns}

        # 6. Missing required value handling (OHLCV)
        missing_required_mask = working_df[MANDATORY_COLUMNS].isna().any(axis=1)
        if missing_required_mask.any():
            missing_req_count = int(missing_required_mask.sum())
            if self.drop_missing:
                removal_reasons["missing_required_values"] = missing_req_count
                warnings.append(
                    f"Removed {missing_req_count} rows missing mandatory price or volume values."
                )
                working_df = working_df[~missing_required_mask].copy()
            else:
                warnings.append(
                    f"Retained {missing_req_count} rows with missing values as drop_missing=False."
                )

        # Handle optional Adj Close missing values separately
        if has_adj_close:
            adj_nulls = int(working_df["Adj Close"].isna().sum())
            if adj_nulls > 0:
                warnings.append(
                    f"Optional 'Adj Close' contains {adj_nulls} missing values; rows were retained."
                )

        # 7. Non-positive price and negative volume validation
        price_cols = ["Open", "High", "Low", "Close"]
        non_positive_price_mask = (working_df[price_cols] <= 0).any(axis=1)
        if has_adj_close:
            non_positive_adj = working_df["Adj Close"].notna() & (working_df["Adj Close"] <= 0)
            non_positive_price_mask = non_positive_price_mask | non_positive_adj

        negative_vol_mask = working_df["Volume"] < 0

        invalid_value_mask = non_positive_price_mask | negative_vol_mask
        if invalid_value_mask.any():
            price_err_count = int(non_positive_price_mask.sum())
            vol_err_count = int(negative_vol_mask.sum())
            if price_err_count > 0:
                removal_reasons["non_positive_price"] = price_err_count
                warnings.append(f"Removed {price_err_count} rows with non-positive price values (<= 0).")
            if vol_err_count > 0:
                removal_reasons["negative_volume"] = vol_err_count
                warnings.append(f"Removed {vol_err_count} rows with negative volume (< 0).")
            working_df = working_df[~invalid_value_mask].copy()

        # 8. OHLC relationship consistency validation
        high_low_invalid = working_df["High"] < working_df["Low"]
        high_open_close_invalid = (working_df["High"] < working_df["Open"]) | (
            working_df["High"] < working_df["Close"]
        )
        low_open_close_invalid = (working_df["Low"] > working_df["Open"]) | (
            working_df["Low"] > working_df["Close"]
        )

        ohlc_inconsistent_mask = high_low_invalid | high_open_close_invalid | low_open_close_invalid
        ohlc_invalid_count = int(ohlc_inconsistent_mask.sum())

        if ohlc_invalid_count > 0:
            removal_reasons["invalid_ohlc_relationship"] = ohlc_invalid_count
            warnings.append(
                f"Removed {ohlc_invalid_count} rows where OHLC boundaries were violated "
                "(High must be >= max(Open, Close) and Low <= min(Open, Close))."
            )
            working_df = working_df[~ohlc_inconsistent_mask].copy()

        # 9. Chronological sorting
        working_df = working_df.sort_values(by="Date", ascending=True).reset_index(drop=True)

        # 10. Finalize counts and report
        final_count = len(working_df)
        total_removed = original_count - final_count
        is_dataset_valid = (final_count > 0) and not (
            conflicting_count > 0 and self.effective_policy == "retain"
        )

        self._report = CleaningReport(
            original_row_count=original_count,
            final_row_count=final_count,
            missing_values_by_column=missing_by_col,
            exact_duplicates_count=exact_dup_count,
            conflicting_duplicates_count=conflicting_count,
            duplicate_dates_count=total_duplicates_tracked,
            duplicate_policy=self.effective_policy,
            conflict_policy=self.effective_policy,
            invalid_records_count=ohlc_invalid_count,
            records_removed=total_removed,
            removal_reasons=removal_reasons,
            warnings=warnings,
            is_valid=is_dataset_valid,
        )

        # Preserve metadata from raw dataframe
        working_df.attrs = dict(self.raw_df.attrs)
        working_df.attrs["cleaned"] = True
        working_df.attrs["cleaning_records_removed"] = total_removed

        return CleaningResult(data=working_df, report=self._report)


def clean_stock_data(
    df: pd.DataFrame,
    duplicate_policy: Optional[str] = None,
    conflict_policy: str = "reject",
    drop_missing: bool = True,
) -> CleaningResult:
    """Convenience function to clean and validate a stock DataFrame.

    Args:
        df: Input DataFrame.
        duplicate_policy: Optional duplicate policy ('reject', 'retain', 'keep_last', 'keep_first').
        conflict_policy: Policy for conflicting duplicates (defaults to 'reject').
        drop_missing: Whether to drop rows with missing required values.

    Returns:
        CleaningResult(data=cleaned_df, report=cleaning_report).
    """
    cleaner = StockDataCleaner(
        df,
        duplicate_policy=duplicate_policy,
        conflict_policy=conflict_policy,
        drop_missing=drop_missing,
    )
    return cleaner.clean()


def save_processed_data(df: pd.DataFrame, file_name: str) -> Path:
    """Save cleaned and validated stock DataFrame into data/processed/.

    Args:
        df: Cleaned pandas DataFrame.
        file_name: Target filename (e.g. 'AAPL_cleaned.csv').

    Returns:
        Path to the saved processed CSV file.
    """
    if not file_name.endswith(".csv"):
        file_name = f"{file_name}.csv"

    output_path = PROCESSED_DATA_DIR / file_name
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path
