# Changelog

All notable changes to GumShoe Report will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] — 2026-04-26

### Added
- Initial release of GumShoe Report
- Active Directory / SIEM connector (`ADConnector`) with live API + mock mode
- Web proxy / CASB connector (`ProxyConnector`) with category-based flagging
- Physical access / badge connector (`BadgeConnector`) with restricted-area detection
- Print management connector (`PrinterConnector`) with sensitive-filename keyword matching
- Rule-based risk engine (`RiskEngine`) with 13 weighted indicators across 4 categories
- ReportLab PDF report with cover page, risk summary, event tables, and analyst notes
- JSON export (`--json`) for SIEM ingestion
- `--mock` flag for demo/training/CI use without live APIs
- `--no-color` flag for plain-text log redirection
- `pip install -e .` support via `setup.py` with `gumshoe` console script entry point
- MIT license
