# Plan: Production-Level Project Reorganization

**Date:** 2026-04-26

---

## Problem

All Python modules (`cleaning.py`, `detection.py`, `visualization.py`, `logger.py`, `test.py`, `config.py`) live at the project root alongside `main.py`. This is flat and doesn't scale. The `.gitignore` is also missing several common entries. We need to reorganize into a proper package structure per the coding standards.

---

## Current Structure

```
isolation-forest/
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── main.py           # entrypoint
├── config.py         # configuration
├── cleaning.py       # data cleaning
├── detection.py      # isolation forest logic
├── visualization.py  # plotting
├── logger.py         # logging setup
├── test.py           # dedup test utility
├── db/
│   ├── __init__.py
│   ├── session.py
│   └── models/
│       ├── __init__.py
│       ├── base.py
│       ├── device.py
│       └── energy_reading.py
├── data/             # plans & docs
├── logs/             # run logs (timestamped)
├── models/           # saved .joblib files
└── output/           # charts & CSVs (timestamped)
```

---

## Target Structure

```
isolation-forest/
├── .env
├── .gitignore              # ← expanded
├── README.md               # ← updated with new structure
├── requirements.txt
├── main.py                 # entrypoint — stays at root
├── config.py               # ← stays at root (imported everywhere)
├── pipeline/               # NEW package for pipeline modules
│   ├── __init__.py
│   ├── cleaning.py         # ← moved from root
│   ├── detection.py        # ← moved from root
│   └── visualization.py    # ← moved from root
├── utils/                  # NEW package for utilities
│   ├── __init__.py
│   └── logger.py           # ← moved from root
├── tests/                  # NEW package for tests
│   ├── __init__.py
│   └── test_cleaning.py    # ← moved & renamed from test.py
├── db/                     # unchanged
│   ├── __init__.py
│   ├── session.py
│   └── models/
│       ├── __init__.py
│       ├── base.py
│       ├── device.py
│       └── energy_reading.py
├── data/                   # plans & docs (unchanged)
├── logs/                   # gitignored
├── models/                 # gitignored (.joblib artifacts)
└── output/                 # gitignored
```

---

## Steps

### Step 1 — Create new package directories with `__init__.py`

- `pipeline/__init__.py` — export `clean_data`, `run_per_device_isolation`, visualization functions
- `utils/__init__.py` — export `setup_logging`, `get_logger`
- `tests/__init__.py` — empty

### Step 2 — Move files into packages

| From | To |
|---|---|
| `cleaning.py` | `pipeline/cleaning.py` |
| `detection.py` | `pipeline/detection.py` |
| `visualization.py` | `pipeline/visualization.py` |
| `logger.py` | `utils/logger.py` |
| `test.py` | `tests/test_cleaning.py` |

### Step 3 — Update all internal imports

Every moved file's internal imports change:
- `from logger import ...` → `from utils.logger import ...`
- `from config import ...` → stays the same (config at root)
- `from cleaning import ...` → `from pipeline.cleaning import ...`
- `from detection import ...` → `from pipeline.detection import ...`
- `from test import ...` → `from tests.test_cleaning import ...`
- `from visualization import ...` → `from pipeline.visualization import ...`

Files to update:
- **`main.py`** — all pipeline/utils imports
- **`pipeline/cleaning.py`** — logger import, test import
- **`pipeline/detection.py`** — logger import
- **`db/session.py`** — config import (already correct)

### Step 4 — Fix `.gitignore`

Add missing entries:
- `logs/` — run logs directory
- `.vscode/` — editor settings
- `*.egg-info/` — packaging artifacts
- `dist/`, `build/` — build artifacts
- `.pytest_cache/` — pytest cache
- `.mypy_cache/` — mypy cache
- `*.log` — stray log files
- `.DS_Store` — macOS artifacts

### Step 5 — Update `README.md`

Reflect new project structure table and any import path changes.

### Step 6 — Delete old root-level files

Remove the moved files from the project root:
- `cleaning.py`
- `detection.py`
- `visualization.py`
- `logger.py`
- `test.py`

### Step 7 — Verify

- `python main.py` runs without import errors (or at minimum `python -c "from pipeline.cleaning import clean_data"` etc.)
- `.gitignore` covers all generated artifacts

---

## Notes

- `config.py` stays at root — it's the central config imported by everything.
- `main.py` stays at root — it's the entrypoint.
- `db/` stays as-is — already properly structured per coding standards.
- `models/` (joblib artifacts) and `output/` remain gitignored at root.
- `requirements.txt` needs `joblib` added (currently implicitly available via scikit-learn but good to be explicit).
