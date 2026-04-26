# 🔍 GumShoe Report

**Automated Insider Threat Triage — 24-Hour User Activity Aggregator**

GumShoe Report is a Python CLI tool built for security analysts. Given a username, it instantly pulls and correlates the last 24 hours of activity across four data sources, scores the user's behavior with a rule-based risk engine, and produces a color-coded terminal summary alongside a formatted PDF investigation report.

---

## Features

- **Multi-source correlation** — Active Directory logins, web proxy history, badge swipes, and print jobs in a single command
- **Risk scoring engine** — 12 configurable rules covering authentication, data transfer, physical access, and printing anomalies
- **Color-coded terminal output** — Suspicious entries highlighted at a glance
- **PDF investigation report** — ReportLab-generated case file with cover page, risk summary, indicator table, and analyst notes section
- **JSON export** — Raw collected data exportable for SIEM ingestion or further analysis
- **Mock mode** — Realistic synthetic dataset for demos, training, and CI testing without live API access
- **Live API ready** — Connector stubs for AD/SIEM, CASB/proxy, badge access control, and PaperCut/print management

---

## Quickstart

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/gumshoe-report.git
cd gumshoe-report

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run against simulated data
python gumshoe.py jsmith --mock

# 4. Save report to a custom directory and also export JSON
python gumshoe.py jsmith --mock --output ./cases --json
```

---

## Installation

Python 3.10+ is required.

### 1) Create and activate a virtual environment

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

#### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

#### Windows (cmd.exe)

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
```

### 2) Install project dependencies

```bash
python -m pip install -r requirements.txt
```

### 3) (Optional) Install as a CLI command in your environment

```bash
python -m pip install -e .
gumshoe jsmith --mock
```

---

## Usage

```
usage: gumshoe [-h] [--mock] [--output OUTPUT] [--json] [--no-color] username

positional arguments:
  username         AD username to investigate (e.g. jsmith)

options:
  --mock           Use simulated data instead of live APIs
  --output OUTPUT  Directory for output files (default: ./reports)
  --json           Also export raw collected data as a JSON file
  --no-color       Disable ANSI colour output (useful for log redirection)
```

### Examples

```bash
# Demo with built-in simulated data
python gumshoe.py jsmith --mock

# Investigate a real user (requires API env vars — see below)
python gumshoe.py jdoe

# Save to a specific case folder and export JSON
python gumshoe.py jdoe --mock --output ./cases/2024-10-jdoe --json

# Plain text output (for piping to a log file)
python gumshoe.py jdoe --mock --no-color > jdoe_triage.txt
```

---

## Connecting Live APIs

Set environment variables before running. GumShoe falls back to mock data if any variable is missing.

| Variable | Description |
|---|---|
| `AD_API_BASE` | Base URL for your SIEM / AD event log API |
| `AD_API_KEY` | API key or bearer token for AD/SIEM |
| `PROXY_API_BASE` | Base URL for your web proxy / CASB API |
| `PROXY_API_KEY` | API key for proxy/CASB |
| `BADGE_API_BASE` | Base URL for your physical access control API |
| `BADGE_API_KEY` | API key for badge/access system |
| `PRINT_API_BASE` | Base URL for PaperCut / PrintAudit / CUPS API |
| `PRINT_API_KEY` | API key for print management server |

```bash
export AD_API_BASE=https://siem.yourorg.com/api/v1
export AD_API_KEY=your-token
python gumshoe.py jdoe
```

Each connector's `_live_fetch()` method documents the expected API response schema. Adapt field mapping in `_normalise()` to match your vendor's output.

---

## Project Structure

```
gumshoe-report/
├── gumshoe.py                   # CLI entry point
├── connectors/
│   ├── ad_connector.py          # Active Directory / SIEM logins
│   ├── proxy_connector.py       # Web proxy / CASB browsing history
│   ├── badge_connector.py       # Physical access control system
│   └── printer_connector.py     # Print management server
├── engine/
│   └── risk_engine.py           # Rule-based risk scoring (0–100)
├── reports/
│   └── pdf_report.py            # ReportLab PDF generator
├── tests/
│   └── test_risk_engine.py      # Unit tests for scoring rules
├── requirements.txt
├── setup.py
├── .gitignore
└── README.md
```

---

## Risk Scoring Rules

Scores are additive and capped at 100. Risk levels: **LOW** (0–24) · **MEDIUM** (25–49) · **HIGH** (50–74) · **CRITICAL** (75+)

| Category | Rule | Points |
|---|---|---|
| Authentication | Successful login without MFA | +15 |
| Authentication | Login from external/public IP | +20 |
| Authentication | 3+ failed login attempts | +20 |
| Authentication | 1–2 failed login attempts | +8 |
| Temporal | Login outside business hours | +10 |
| Web Activity | Visited exfil-category site (Mega, Tor, etc.) | +15 |
| Data Transfer | Outbound upload >50 MB via proxy | +25 |
| Physical Access | Attempted restricted-area badge swipe | +15 |
| Physical Access | Swipe at classified/restricted location | +5 |
| Physical Access | Badge event outside business hours | +10 |
| Printing | Sensitive keyword in document name | +20 |
| Printing | Total pages printed >200 | +15 |
| Temporal | Print job submitted outside business hours | +10 |

---

## Output

### Terminal
Color-coded tables for each data source, followed by a risk score bar and triggered indicator list.

### PDF Report (`gumshoe_<username>_<timestamp>.pdf`)
- **Cover page** — subject, investigation window, classification label
- **Executive summary** — risk score, risk level, full indicator table
- **AD login events** — workstation, IP, result, MFA status
- **Web proxy history** — domain, category, bytes transferred (flagged if >50 MB)
- **Badge swipes** — location, direction, access result (restricted areas highlighted)
- **Print jobs** — document name, printer, page count (sensitive filenames flagged)
- **Analyst notes** — blank lined section for investigator comments

### JSON (`gumshoe_<username>_<timestamp>.json`)
Full structured dump including all raw events and the risk report, suitable for SIEM ingestion.

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/new-rule`
3. Add your rule in `engine/risk_engine.py` and a test in `tests/`
4. Open a pull request

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

> **Disclaimer:** GumShoe Report is a security operations tool intended for authorized use only. Always ensure investigations comply with your organization's policies, applicable law, and employee privacy regulations.
