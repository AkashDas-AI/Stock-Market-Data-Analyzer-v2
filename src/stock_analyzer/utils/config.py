"""Global configuration and project path definitions.

Responsibility:
    Provide centralized access to directory paths, default parameters, and constants.
"""

from pathlib import Path

# Project Root Directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Data Directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
SAMPLE_STOCK_CSV = SAMPLE_DATA_DIR / "sample_stock.csv"

# Output Directories
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
CHARTS_OUTPUT_DIR = OUTPUTS_DIR / "charts"
TABLES_OUTPUT_DIR = OUTPUTS_DIR / "tables"
REPORTS_DIR = PROJECT_ROOT / "reports" / "generated"

# Default Analysis Parameters
DEFAULT_TICKER = "AAPL"
DEFAULT_BENCHMARK = "SPY"
DEFAULT_SMA_SHORT = 20
DEFAULT_SMA_LONG = 50
DEFAULT_EMA_SPAN = 20
DEFAULT_TRADING_DAYS_PER_YEAR = 252
