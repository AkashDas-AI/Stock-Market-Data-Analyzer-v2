"""Custom exception hierarchy for stock data collection, ingestion, and cleaning."""


class StockDataError(Exception):
    """Base exception for all stock data errors in Stock Market Data Analyzer."""
    pass


class DataFetchError(StockDataError):
    """Raised when data acquisition from an external provider fails."""
    pass


class TickerNotFoundError(DataFetchError):
    """Raised when a ticker symbol is invalid or has no data available on the provider."""
    pass


class EmptyDataError(StockDataError):
    """Raised when a data query or file returns zero observations."""
    pass


class InvalidDateRangeError(StockDataError):
    """Raised when the specified date range is mathematically or logically invalid."""
    pass


class DataLoadingError(StockDataError):
    """Raised when loading local tabular stock data fails."""
    pass


class MissingColumnError(DataLoadingError):
    """Raised when an ingested dataset is missing mandatory OHLCV columns."""
    pass


class InvalidDateError(DataLoadingError):
    """Raised when date values in a dataset cannot be parsed into valid timestamps."""
    pass


class DataValidationError(StockDataError):
    """Raised when data validation fails during cleaning or integrity assertions."""
    pass
