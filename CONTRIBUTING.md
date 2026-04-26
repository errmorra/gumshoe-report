# Contributing to GumShoe Report

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/gumshoe-report.git
cd gumshoe-report
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

### Windows (cmd.exe)

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Adding a Risk Rule

1. Open `engine/risk_engine.py`
2. Add your rule inside `RiskEngine.score()` — increment `total` and append to `indicators`
3. Add a corresponding test in `tests/test_risk_engine.py`
4. Update the scoring table in `README.md`

## Adding a Connector

1. Create `connectors/your_connector.py`, implementing `fetch(username, since) -> list[dict]`
2. Add `_live_fetch()` (calls your API) and `_mock_data()` (returns synthetic data)
3. Wire it into `gumshoe.py`
4. Document required env vars in `README.md`

## Pull Request Checklist

- [ ] Tests pass locally (`pytest tests/ -v`)
- [ ] Mock mode still works end-to-end (`python gumshoe.py testuser --mock`)
- [ ] No API keys or real usernames committed
- [ ] CHANGELOG.md updated under `[Unreleased]`
