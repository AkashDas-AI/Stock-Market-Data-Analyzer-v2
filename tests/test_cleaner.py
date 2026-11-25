"""Unit tests for stock data cleaning and validation module."""

import pytest
import pandas as pd
import numpy as np

from stock_analyzer.data.cleaner import (
    StockDataCleaner,
    clean_stock_data,
    save_processed_data,
    CleaningReport,
)
from stock_analyzer.data.exceptions import (
    EmptyDataError,
    MissingColumnError,
    DataValidationError,
)


def _create_sample_df():
    """Create a pristine, valid 5-row OHLCV DataFrame."""
    return pd.DataFrame(
        {
            "Date": ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"],
            "Open": [150.0, 151.0, 152.0, 153.0, 154.0],
            "High": [155.0, 156.0, 157.0, 158.0, 159.0],
            "Low": [149.0, 150.0, 151.0, 152.0, 153.0],
            "Close": [154.0, 155.0, 156.0, 157.0, 158.0],
            "Adj Close": [153.5, 154.5, 155.5, 156.5, 157.5],
            "Volume": [1000000, 1200000, 1100000, 1300000, 1250000],
        }
    )


class TestStockDataCleaner:
    """Test suite for StockDataCleaner and cleaning pipeline."""

    def test_clean_valid_dataframe(self):
        raw = _create_sample_df()
        raw.attrs["ticker"] = "AAPL"
        cleaner = StockDataCleaner(raw)
        result = cleaner.clean()

        assert not result.data.empty
        assert len(result.data) == 5
        assert result.report.original_row_count == 5
        assert result.report.final_row_count == 5
        assert result.report.records_removed == 0
        assert result.report.is_valid is True
        assert result.data.attrs["ticker"] == "AAPL"
        assert result.data.attrs["cleaned"] is True

    def test_raw_input_immutability(self):
        raw = _create_sample_df()
        raw_copy = raw.copy(deep=True)
        cleaner = StockDataCleaner(raw)
        _ = cleaner.clean()

        pd.testing.assert_frame_equal(raw, raw_copy)

    def test_empty_dataframe_raises_error(self):
        empty_df = pd.DataFrame()
        cleaner = StockDataCleaner(empty_df)
        with pytest.raises(EmptyDataError, match="empty DataFrame"):
            cleaner.clean()

    def test_missing_required_columns_raises_error(self):
        df = pd.DataFrame({"Date": ["2026-01-05"], "Open": [150.0], "High": [155.0]})
        cleaner = StockDataCleaner(df)
        with pytest.raises(MissingColumnError, match="missing mandatory columns"):
            cleaner.clean()

    def test_invalid_type_raises_error(self):
        with pytest.raises(TypeError, match="must be a pandas DataFrame"):
            StockDataCleaner("not a dataframe")

    def test_invalid_duplicate_policy_raises_error(self):
        raw = _create_sample_df()
        with pytest.raises(ValueError, match="policy"):
            StockDataCleaner(raw, duplicate_policy="invalid_policy")

    def test_missing_required_numerical_values(self):
        raw = _create_sample_df()
        # Insert NaN in Close of row 1, and Volume of row 3
        raw.loc[1, "Close"] = np.nan
        raw.loc[3, "Volume"] = np.nan

        cleaner = StockDataCleaner(raw, drop_missing=True)
        result = cleaner.clean()

        assert len(result.data) == 3
        assert result.report.records_removed == 2
        assert result.report.removal_reasons["missing_required_values"] == 2
        assert result.report.missing_values_by_column["Close"] == 1
        assert result.report.missing_values_by_column["Volume"] == 1

    def test_optional_adj_close_with_missing_values(self):
        raw = _create_sample_df()
        # Insert NaN into Adj Close only
        raw.loc[2, "Adj Close"] = np.nan

        cleaner = StockDataCleaner(raw)
        result = cleaner.clean()

        # All 5 rows should be retained since Adj Close is optional
        assert len(result.data) == 5
        assert result.report.records_removed == 0
        assert any("Optional 'Adj Close' contains 1 missing values" in w for w in result.report.warnings)

    def test_invalid_dates_handling(self):
        raw = _create_sample_df()
        raw.loc[1, "Date"] = "not-a-date"
        raw.loc[3, "Date"] = None

        cleaner = StockDataCleaner(raw)
        result = cleaner.clean()

        assert len(result.data) == 3
        assert result.report.removal_reasons["invalid_or_missing_date"] == 2

    def test_exact_duplicate_records(self):
        """Exact duplicates (identical across all columns) must be safely removed under default policy."""
        raw = _create_sample_df()
        # Duplicate row 1 exactly (same date, same OHLCV)
        raw = pd.concat([raw, raw.iloc[[1]]], ignore_index=True)
        assert len(raw) == 6

        cleaner = StockDataCleaner(raw)  # default policy
        result = cleaner.clean()

        assert len(result.data) == 5
        assert result.report.exact_duplicates_count == 1
        assert result.report.conflicting_duplicates_count == 0
        assert result.report.records_removed == 1
        assert result.report.removal_reasons["exact_duplicate_record"] == 1
        assert result.report.is_valid is True

    def test_conflicting_duplicates_default_reject(self):
        """Conflicting duplicates (same date, different OHLCV) must raise DataValidationError by default."""
        raw = _create_sample_df()
        # Add duplicate date with different price
        conflict_row = raw.iloc[[1]].copy()
        conflict_row["Close"] = 199.0
        conflict_row["High"] = 200.0
        raw = pd.concat([raw, conflict_row], ignore_index=True)

        cleaner = StockDataCleaner(raw)  # default policy is 'reject'
        with pytest.raises(DataValidationError, match="conflicting duplicate records"):
            cleaner.clean()

    def test_conflicting_duplicates_retain_policy(self):
        """Conflicting duplicates with 'retain' policy must be kept for review and flagged in report."""
        raw = _create_sample_df()
        conflict_row = raw.iloc[[1]].copy()
        conflict_row["Close"] = 199.0
        conflict_row["High"] = 200.0
        raw = pd.concat([raw, conflict_row], ignore_index=True)

        cleaner = StockDataCleaner(raw, conflict_policy="retain")
        result = cleaner.clean()

        # Both conflicting rows retained
        assert len(result.data) == 6
        assert result.report.conflicting_duplicates_count == 1
        assert result.report.records_removed == 0
        assert result.report.is_valid is False  # Flagged invalid due to unresolved conflicts
        assert any("Retained 1 conflicting duplicate records" in w for w in result.report.warnings)

    def test_conflicting_duplicates_explicit_keep_last(self):
        """Explicit 'keep_last' policy resolves conflicts deterministically."""
        raw = _create_sample_df()
        # Row 1 is 2026-01-06 with Close=155.0
        conflict_row = raw.iloc[[1]].copy()
        conflict_row["Close"] = 199.0
        conflict_row["High"] = 200.0
        raw = pd.concat([raw, conflict_row], ignore_index=True)

        cleaner = StockDataCleaner(raw, duplicate_policy="keep_last")
        result = cleaner.clean()

        assert len(result.data) == 5
        assert result.report.conflicting_duplicates_count == 1
        assert result.report.records_removed == 1
        assert result.report.removal_reasons["conflicting_duplicate_date"] == 1
        assert 199.0 in result.data["Close"].values  # Kept the last one
        assert result.report.conflict_policy == "keep_last"

    def test_conflicting_duplicates_explicit_keep_first(self):
        """Explicit 'keep_first' policy resolves conflicts deterministically."""
        raw = _create_sample_df()
        conflict_row = raw.iloc[[1]].copy()
        conflict_row["Close"] = 199.0
        conflict_row["High"] = 200.0
        raw = pd.concat([raw, conflict_row], ignore_index=True)

        cleaner = StockDataCleaner(raw, duplicate_policy="keep_first")
        result = cleaner.clean()

        assert len(result.data) == 5
        assert result.report.conflicting_duplicates_count == 1
        assert result.report.records_removed == 1
        assert result.report.removal_reasons["conflicting_duplicate_date"] == 1
        assert 199.0 not in result.data["Close"].values  # Dropped the second, kept 155.0

    def test_mixed_exact_and_conflicting_duplicates(self):
        """Exact duplicates are removed first, and conflicting duplicates are resolved per policy."""
        raw = _create_sample_df()
        # Exact duplicate of row 0
        exact_dup = raw.iloc[[0]].copy()
        # Conflicting duplicate of row 1
        conflict_dup = raw.iloc[[1]].copy()
        conflict_dup["Close"] = 199.0
        conflict_dup["High"] = 200.0

        raw = pd.concat([raw, exact_dup, conflict_dup], ignore_index=True)
        assert len(raw) == 7

        cleaner = StockDataCleaner(raw, duplicate_policy="keep_last")
        result = cleaner.clean()

        assert len(result.data) == 5
        assert result.report.exact_duplicates_count == 1
        assert result.report.conflicting_duplicates_count == 1
        assert result.report.records_removed == 2
        assert result.report.removal_reasons["exact_duplicate_record"] == 1
        assert result.report.removal_reasons["conflicting_duplicate_date"] == 1

    def test_non_positive_prices(self):
        raw = _create_sample_df()
        raw.loc[1, "Close"] = 0.0   # Zero price
        raw.loc[3, "Low"] = -5.0    # Negative price

        cleaner = StockDataCleaner(raw)
        result = cleaner.clean()

        assert len(result.data) == 3
        assert result.report.removal_reasons["non_positive_price"] == 2

    def test_negative_volume(self):
        raw = _create_sample_df()
        raw.loc[2, "Volume"] = -100

        cleaner = StockDataCleaner(raw)
        result = cleaner.clean()

        assert len(result.data) == 4
        assert result.report.removal_reasons["negative_volume"] == 1

    def test_invalid_ohlc_relationships(self):
        raw = _create_sample_df()
        # Row 1: High < Open
        raw.loc[1, "High"] = 140.0
        raw.loc[1, "Open"] = 150.0

        # Row 2: Low > Close
        raw.loc[2, "Low"] = 160.0
        raw.loc[2, "Close"] = 155.0

        # Row 3: High < Low
        raw.loc[3, "High"] = 145.0
        raw.loc[3, "Low"] = 155.0

        cleaner = StockDataCleaner(raw)
        result = cleaner.clean()

        assert len(result.data) == 2
        assert result.report.invalid_records_count == 3
        assert result.report.removal_reasons["invalid_ohlc_relationship"] == 3

    def test_chronological_sorting(self):
        raw = _create_sample_df()
        # Reverse row order
        raw = raw.iloc[::-1].reset_index(drop=True)
        assert raw["Date"].iloc[0] == "2026-01-09"

        cleaner = StockDataCleaner(raw)
        result = cleaner.clean()

        assert result.data["Date"].iloc[0] == pd.Timestamp("2026-01-05")
        assert result.data["Date"].iloc[-1] == pd.Timestamp("2026-01-09")
        assert (result.data["Date"].diff().dropna() > pd.Timedelta(0)).all()

    def test_cleaning_report_accuracy_and_summary(self):
        raw = _create_sample_df()
        raw.loc[1, "Close"] = np.nan
        raw.loc[2, "High"] = 120.0  # Invalid High < Open
        raw.loc[4, "Date"] = raw.loc[3, "Date"]  # Duplicate date

        cleaner = StockDataCleaner(raw, duplicate_policy="keep_last")
        result = cleaner.clean()

        report = result.report
        assert report.original_row_count == 5
        assert report.final_row_count == 2
        assert report.records_removed == 3
        assert len(report.warnings) > 0

        summary_text = report.summary()
        assert "Data Cleaning Report" in summary_text
        assert "Original Rows: 5" in summary_text
        assert "Final Rows:    2" in summary_text

        report_dict = report.to_dict()
        assert isinstance(report_dict, dict)
        assert report_dict["original_row_count"] == 5

    def test_convenience_functions(self, tmp_path):
        raw = _create_sample_df()
        result = clean_stock_data(raw)
        assert isinstance(result, tuple)
        cleaned_df, report = result
        assert len(cleaned_df) == 5
        assert isinstance(report, CleaningReport)

        # Test save_processed_data
        output_file = save_processed_data(cleaned_df, "TEST_TICKER")
        assert output_file.exists()
        loaded = pd.read_csv(output_file)
        assert len(loaded) == 5
