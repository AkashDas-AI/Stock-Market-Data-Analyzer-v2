"""Data ingestion and processing manager for Streamlit dashboard.

Responsibility:
    Coordinate data retrieval from Live Yahoo Finance, user-uploaded CSV,
    or synthetic sample fallback. Cleans and validates data using existing
    Phase 3 and Phase 4 pipelines. Caches retrieval using st.cache_data.
"""

from datetime import date, timedelta
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Optional, Tuple, Union

import pandas as pd
import streamlit as st

from stock_analyzer.data.cleaner import StockDataCleaner
from stock_analyzer.data.exceptions import (
    DataFetchError,
    DataValidationError,
    EmptyDataError,
    InvalidDateRangeError,
    MissingColumnError,
    StockDataError,
    TickerNotFoundError,
)
from stock_analyzer.data.fetcher import StockDataFetcher
from stock_analyzer.data.loader import StockDataLoader, load_stock_csv

SAMPLE_CSV_PATH = Path("data/sample/sample_stock.csv")


@st.cache_data(show_spinner=False, ttl=300)
def fetch_cached_live_data(
    ticker: str, start_date_str: str, end_date_str: str
) -> pd.DataFrame:
    """Fetch historical stock data via Yahoo Finance with caching.

    Args:
        ticker: Uppercase stock ticker symbol (e.g. 'AAPL').
        start_date_str: ISO start date string ('YYYY-MM-DD').
        end_date_str: ISO end date string ('YYYY-MM-DD').

    Returns:
        Raw fetched pandas DataFrame.

    Raises:
        StockDataError: If yfinance retrieval fails, returns empty, or encounters an invalid date range.
    """
    fetcher = StockDataFetcher(ticker)
    return fetcher.fetch_history(
        start_date=start_date_str,
        end_date=end_date_str,
    )


@st.cache_data(show_spinner=False)
def load_cached_sample_data(sample_path: str = str(SAMPLE_CSV_PATH)) -> pd.DataFrame:
    """Load the pre-packaged offline synthetic sample stock CSV with caching.

    Args:
        sample_path: Path to sample CSV file.

    Returns:
        Raw loaded pandas DataFrame with is_synthetic=True.
    """
    return load_stock_csv(sample_path)


def load_uploaded_csv(uploaded_file: Any) -> pd.DataFrame:
    """Load user-uploaded CSV file from Streamlit file uploader.

    Args:
        uploaded_file: Streamlit UploadedFile object or file-like buffer.

    Returns:
        Loaded pandas DataFrame.

    Raises:
        DataValidationError: If CSV parsing fails or is empty.
    """
    try:
        # Seek to beginning if stream
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file)
        if df.empty:
            raise EmptyDataError("The uploaded CSV file contains no data rows.")
        return df
    except Exception as exc:
        if isinstance(exc, (EmptyDataError, DataValidationError)):
            raise
        raise DataValidationError(f"Failed to parse uploaded CSV file: {str(exc)}") from exc


def filter_date_range(
    df: pd.DataFrame,
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
) -> pd.DataFrame:
    """Filter DataFrame between inclusive start and end dates without timezone shift.

    Normalizes timestamps to ISO 'YYYY-MM-DD' calendar strings, ensuring consistent
    date-boundary inclusion across timezones and providers.

    Args:
        df: DataFrame containing a 'Date' column.
        start_date: Inclusive start date (string 'YYYY-MM-DD' or date object).
        end_date: Inclusive end date (string 'YYYY-MM-DD' or date object).

    Returns:
        Filtered DataFrame copy with original metadata attributes preserved.
    """
    if "Date" not in df.columns or (start_date is None and end_date is None):
        return df.copy(deep=True)

    s_str = start_date if isinstance(start_date, str) else start_date.strftime("%Y-%m-%d") if start_date else None
    e_str = end_date if isinstance(end_date, str) else end_date.strftime("%Y-%m-%d") if end_date else None

    # Strict calendar date normalization avoiding timezone shift
    date_series = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

    mask = pd.Series(True, index=df.index)
    if s_str:
        mask &= (date_series >= s_str)
    if e_str:
        mask &= (date_series <= e_str)

    filtered = df.loc[mask].copy(deep=True)
    filtered.attrs = df.attrs.copy()
    return filtered


def get_and_clean_data(
    source_type: str,
    ticker: str = "AAPL",
    start_date: Optional[Union[date, str]] = None,
    end_date: Optional[Union[date, str]] = None,
    uploaded_file: Optional[Any] = None,
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Retrieve, clean, and validate stock data according to source selection.

    Enforces inclusive end-date behavior for live Yahoo Finance fetches (querying yfinance
    with end_date + 1 day because yfinance end dates are exclusive) as well as consistent
    inclusive filtering across CSV uploads and synthetic sample datasets.

    Args:
        source_type: One of 'Live Yahoo Finance', 'Upload CSV', 'Sample Dataset (Synthetic)'.
        ticker: Ticker symbol (used for live fetch and metadata labelling).
        start_date: Inclusive start date for observation window.
        end_date: Inclusive end date for observation window.
        uploaded_file: File-like buffer if source_type is 'Upload CSV'.

    Returns:
        Tuple of (Cleaned DataFrame or None, Error message string or None).
    """
    clean_ticker = ticker.strip().upper() if ticker else ""

    # Universal date validation: reject invalid ranges before fetching or filtering
    if start_date is not None and end_date is not None:
        s_date_val = start_date if isinstance(start_date, str) else start_date.strftime("%Y-%m-%d")
        e_date_val = end_date if isinstance(end_date, str) else end_date.strftime("%Y-%m-%d")
        if s_date_val >= e_date_val:
            return None, f"Start date ({s_date_val}) must be strictly before end date ({e_date_val})."

    try:
        if source_type == "Live Yahoo Finance":
            if not clean_ticker:
                return None, "Please enter a valid stock ticker symbol (e.g. AAPL, MSFT, SPY)."

            if start_date is None or end_date is None:
                return None, "Start date and end date must both be specified."

            s_date = start_date if isinstance(start_date, str) else start_date.strftime("%Y-%m-%d")
            e_date = end_date if isinstance(end_date, str) else end_date.strftime("%Y-%m-%d")

            # Yahoo Finance's end_date parameter is EXCLUSIVE.
            # To include the user's selected end_date, query yfinance with end_date + 1 day:
            e_date_obj = end_date if isinstance(end_date, date) else pd.to_datetime(end_date).date()
            fetch_end_str = (e_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")

            try:
                raw_df = fetch_cached_live_data(clean_ticker, s_date, fetch_end_str)
            except EmptyDataError as exc:
                return None, f"No market data returned for '{clean_ticker}': {str(exc)}"
            except InvalidDateRangeError as exc:
                return None, f"Invalid date range for '{clean_ticker}': {str(exc)}"
            except DataFetchError as exc:
                return None, f"Live Data Fetch Error: {str(exc)}"
            except StockDataError as exc:
                return None, f"Market Data Error: {str(exc)}"
            except ValueError as exc:
                return None, f"Invalid Ticker: {str(exc)}"
            except Exception as exc:
                return None, f"Failed to retrieve data for '{clean_ticker}': {str(exc)}"

            cleaner = StockDataCleaner(raw_df)
            clean_res = cleaner.clean()
            cleaned_df = clean_res.data
            cleaned_df.attrs["ticker"] = clean_ticker
            cleaned_df.attrs["is_synthetic"] = False
            cleaned_df.attrs["cleaning_report"] = clean_res.report.to_dict()

            # Bound strictly to user's requested inclusive date interval
            bounded_df = filter_date_range(cleaned_df, start_date=s_date, end_date=e_date)
            if bounded_df.empty:
                return None, f"No market observations found for '{clean_ticker}' within {s_date} to {e_date}."
            return bounded_df, None

        elif source_type == "Upload CSV":
            if uploaded_file is None:
                return None, "Please upload a CSV file containing Date, Open, High, Low, Close, and Volume columns."

            raw_df = load_uploaded_csv(uploaded_file)
            cleaner = StockDataCleaner(raw_df)
            clean_res = cleaner.clean()
            cleaned_df = clean_res.data

            csv_ticker = clean_ticker if clean_ticker and clean_ticker != "AAPL" else "UPLOADED"
            cleaned_df.attrs["ticker"] = csv_ticker
            cleaned_df.attrs["is_synthetic"] = False
            cleaned_df.attrs["cleaning_report"] = clean_res.report.to_dict()

            if start_date is not None or end_date is not None:
                cleaned_df = filter_date_range(cleaned_df, start_date=start_date, end_date=end_date)
                if cleaned_df.empty:
                    s_desc = str(start_date) if start_date else "start"
                    e_desc = str(end_date) if end_date else "end"
                    return None, f"No observations found in uploaded CSV within {s_desc} to {e_desc}."

            return cleaned_df.copy(deep=True), None

        elif source_type == "Sample Dataset (Synthetic)":
            if not SAMPLE_CSV_PATH.exists():
                return None, f"Sample stock dataset file not found at '{SAMPLE_CSV_PATH}'."

            raw_df = load_cached_sample_data(str(SAMPLE_CSV_PATH))
            cleaner = StockDataCleaner(raw_df)
            clean_res = cleaner.clean()
            cleaned_df = clean_res.data
            cleaned_df.attrs["ticker"] = "SAMPLE"
            cleaned_df.attrs["is_synthetic"] = True
            cleaned_df.attrs["cleaning_report"] = clean_res.report.to_dict()

            if start_date is not None or end_date is not None:
                cleaned_df = filter_date_range(cleaned_df, start_date=start_date, end_date=end_date)
                if cleaned_df.empty:
                    s_desc = str(start_date) if start_date else "start"
                    e_desc = str(end_date) if end_date else "end"
                    return None, f"No observations found in sample dataset within {s_desc} to {e_desc}."

            return cleaned_df.copy(deep=True), None

        else:
            return None, f"Unrecognized data source selection: '{source_type}'."

    except (MissingColumnError, EmptyDataError, DataValidationError, StockDataError) as exc:
        return None, f"Data Validation Error: {str(exc)}"
    except Exception as exc:
        return None, f"Unexpected error processing dataset: {str(exc)}"
