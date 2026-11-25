# Contribution Guidelines

**Project:** Stock Market Data Analyzer  
**Maintainer:** Akash Das  

Thank you for contributing to the Stock Market Data Analyzer project. To ensure high code quality and consistency across all 12 implementation phases, please follow these guidelines:

## Development Standards
1. **Virtual Environment**: All development must use the project-local `.venv` environment located in the project root.
2. **Modular Architecture**: Code should be placed within the appropriate subpackage in `src/stock_analyzer/` according to its domain:
   - Data collection and ingestion: `src/stock_analyzer/data/`
   - Statistical and technical analysis: `src/stock_analyzer/analysis/`
   - Plotting and visualizers: `src/stock_analyzer/visualization/`
   - Report generation: `src/stock_analyzer/reporting/`
   - Shared utilities: `src/stock_analyzer/utils/`
3. **Type Hinting**: All new functions and methods must include explicit Python type annotations.
4. **Testing**: Add automated test cases under `tests/` for any new analytical functions. Ensure all tests pass with `pytest`.
5. **Phase Discipline**: Only implement features authorized for the current roadmap phase.
