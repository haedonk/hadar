# Isolation Forest — Energy Anomaly Detection

Per-device anomaly detection on energy readings using scikit-learn's Isolation Forest.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your database credentials (or create `.env` directly):

```
DB_DRIVER=postgresql+asyncpg
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_db
```

## Usage

```bash
python main.py
```

This will:
1. Fetch energy readings from the database
2. Run a separate Isolation Forest per device
3. Print anomaly summary to the console
4. Save visualizations to `output/` and display them interactively

## Project Structure

| Path | Purpose |
|---|---|
| `main.py` | Entrypoint — fetch, clean, detect, visualize |
| `config.py` | Environment-based configuration |
| `pipeline/` | Core data science pipeline |
| `pipeline/cleaning.py` | Data cleaning & preprocessing |
| `pipeline/detection.py` | Per-device Isolation Forest logic |
| `pipeline/visualization.py` | Bar chart & scatter plot generation |
| `utils/` | Shared utilities |
| `utils/logger.py` | Logging setup & configuration |
| `tests/` | Test utilities |
| `tests/test_cleaning.py` | Data cleaning validation |
| `db/` | SQLAlchemy models & async session |
| `db/models/` | Database model definitions |
| `data/` | Plans, reference files |
| `models/` | Saved .joblib model artifacts (gitignored) |
| `logs/` | Timestamped run logs (gitignored) |
| `output/` | Generated charts & CSVs (gitignored) |
