"""Stock Market Data Analyzer - Command Line Entry Point.

Author: Akash Das
Phase: 9 of 12 (Streamlit Dashboard Integration)
"""

import sys
from pathlib import Path

# Ensure src/ directory is on sys.path for direct script execution
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from stock_analyzer import __version__, __author__


def main() -> None:
    """CLI entry point for Stock Market Data Analyzer."""
    print("=" * 60)
    print(f"Stock Market Data Analyzer (v{__version__})")
    print(f"Project Author: {__author__}")
    print("=" * 60)
    print("Phase 9: Streamlit Dashboard Integration complete and operational.")
    print("To launch the interactive dashboard, run:")
    print("    streamlit run app/dashboard.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
