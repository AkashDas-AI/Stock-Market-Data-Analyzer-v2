"""Data collection, ingestion, loading, and cleaning subpackage."""

from stock_analyzer.data.exceptions import (
    StockDataError,
    DataFetchError,
    TickerNotFoundError,
    EmptyDataError,
    InvalidDateRangeError,
    DataLoadingError,
    MissingColumnError,
    InvalidDateError,
    DataValidationError,
)
from stock_analyzer.data.fetcher import StockDataFetcher, fetch_stock_data
from stock_analyzer.data.loader import (
    StockDataLoader,
    load_stock_csv,
    load_sample_stock_data,
)
from stock_analyzer.data.cleaner import (
    StockDataCleaner,
    CleaningReport,
    CleaningResult,
    clean_stock_data,
    save_processed_data,
)

__all__ = [
    # Fetcher
    "StockDataFetcher",
    "fetch_stock_data",
    # Loader
    "StockDataLoader",
    "load_stock_csv",
    "load_sample_stock_data",
    # Cleaner
    "StockDataCleaner",
    "CleaningReport",
    "CleaningResult",
    "clean_stock_data",
    "save_processed_data",
    # Exceptions
    "StockDataError",
    "DataFetchError",
    "TickerNotFoundError",
    "EmptyDataError",
    "InvalidDateRangeError",
    "DataLoadingError",
    "MissingColumnError",
    "InvalidDateError",
    "DataValidationError",
]
