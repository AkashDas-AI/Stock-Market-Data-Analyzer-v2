# Documentation Suite & Master Directory Index

**Project:** Stock Market Data Analyzer  
**Author:** Akash Das  
**Project Status:** All 12 of 12 Phases Completed & Verified (Officially Published)  
**Public Repository:** [https://github.com/AkashDas-AI/Stock-Market-Data-Analyzer-v2](https://github.com/AkashDas-AI/Stock-Market-Data-Analyzer-v2)  

---

## 1. Documentation Map & Repository Structure

All documents in this directory follow an unnumbered, capital-case naming convention designed for clarity, discoverability, and long-term project maintenance:

| Document | Purpose & Scope | Target Audience | GitHub Status |
| :--- | :--- | :--- | :---: |
| [**`PROJECT_ARCHITECTURE.md`**](PROJECT_ARCHITECTURE.md) | Comprehensive 4-tier architectural blueprint, class hierarchies, mathematical definitions, and design patterns. | Developers / Architects | **Yes (Public)** |
| [**`DATA_FLOW_AND_PIPELINE.md`**](DATA_FLOW_AND_PIPELINE.md) | End-to-end data lifecycle: Ingestion $\rightarrow$ Invariant Cleaning $\rightarrow$ Analytics $\rightarrow$ Insights $\rightarrow$ Reporting. | Developers / Data Engineers | **Yes (Public)** |
| [**`MODULE_REFERENCE.md`**](MODULE_REFERENCE.md) | Technical reference of all packages, modules, classes, and public API methods. | Developers / Integrators | **Yes (Public)** |
| [**`DATA_DICTIONARY.md`**](DATA_DICTIONARY.md) | Strict schemas, formulas, units, constraints, and exported CSV layouts. | Analysts / Developers | **Yes (Public)** |
| [**`USER_GUIDE.md`**](USER_GUIDE.md) | End-user manual for starting the app, selecting data sources, toggling indicators, and exporting reports. | End Users / Analysts | **Yes (Public)** |
| [**`TESTING_GUIDE.md`**](TESTING_GUIDE.md) | Guide to running Pytest, module test inventory (268 tests), fixtures, and API mocking strategy. | QA / Developers | **Yes (Public)** |
| [**`SCREENSHOT_GUIDE.md`**](SCREENSHOT_GUIDE.md) | Visual design manual documenting UI layouts, KPI cards, dark theme contrast, and chart subplots. | Designers / Users | **Yes (Public)** |
| [**`DEVELOPMENT_ROADMAP.md`**](DEVELOPMENT_ROADMAP.md) | Official 12-phase permanent development plan and completion milestones. | Project Reviewers | **Yes (Public)** |
| [**`EXECUTION_AND_VALIDATION_LOG.md`**](EXECUTION_AND_VALIDATION_LOG.md) | Chronological audit trail of all 23 execution entries across all 12 completed development phases. | Auditors / Reviewers | **Yes (Public)** |
| **`INTERVIEW_PREPARATION_GUIDE.md`** *(Local Only)* | Exhaustive technical interview preparation manual, architectural defenses, math formulas, and bug solutions. | Author (Private Study) | **Excluded from Git** |

---

## 2. GitHub Exclusion Policy for Preparation Notes

In accordance with project security and personal study guidelines:
- **Public Documentation:** Architectural, pipeline, user, testing, and schema guides are formatted to accompany the codebase in the public GitHub repository. They provide transparent technical clarity to prospective collaborators and code reviewers.
- **Private Interview Preparation:** `INTERVIEW_PREPARATION_GUIDE.md` is strictly excluded from Git tracking via `.gitignore` (`docs/*INTERVIEW*`). It remains on your local workstation as a personal study and defense reference.
