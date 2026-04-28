# Energy Anomaly Detection — Project Overview

## What are we doing?

We're building an anomaly detection system for home energy monitoring. We have a bunch of smart plugs and power monitors tracking devices around the house — things like desk setups, entertainment centers, and data equipment. The goal is to automatically flag unusual power usage that might indicate something is wrong — a device left on, a malfunction, or unexpected consumption patterns.

## The approach: Isolation Forest

We're using an algorithm called Isolation Forest. The basic idea is simple: normal data points are "dense" (they look like their neighbors), while anomalies are "isolated" (they're unusual and easy to separate). The algorithm builds random decision trees and measures how quickly each data point gets isolated. If a reading gets isolated fast, it's probably anomalous.

We set the contamination rate at 5%, meaning we expect roughly 5% of readings per device to be flagged as anomalies. This is a tunable parameter we can adjust as we learn more about the data.

## Why per-device models?

Our first attempt ran a single model across all devices, and it flagged about 30% of readings as anomalies — way too many. The problem was that a desk lamp at 2W and an entertainment center at 80W have completely different "normal" ranges. A single model couldn't tell them apart.

Now we train a separate Isolation Forest for each device. Each device learns its own normal range, so a 2W reading on a desk lamp is normal, while a 2W reading on an entertainment center might be suspicious.

## What the data looks like

We pull readings from a PostgreSQL database. Each row has:
- **device_label** — which device (e.g. `living_room_data_corner`, `kens_desk`)
- **power_watts** — the power reading
- **datetime** — when it was recorded (readings come in roughly every few seconds)

Currently we're looking at a few days of data (Jan 11–15, 2026), which gives us around 100k+ rows.

## What we've built so far

The project is split into clean modules:

- **`main.py`** — The entrypoint. Fetches data from the DB, runs detection, prints a summary, and generates charts.
- **`detection.py`** — Per-device Isolation Forest training and prediction. Trains a separate model for each device, scales the features, and saves the trained models to disk.
- **`visualization.py`** — Generates two charts per run: a histogram showing the power distribution (normal vs anomaly) and a scatter plot of power by hour of day.
- **`cleaning.py`** — (coming soon) Data cleaning before modeling.
- **`features.py`** — (coming soon) Feature engineering pipeline.
- **`db/`** — SQLAlchemy models and async database session management.

## Current features used by the model

Right now, the model uses three features per reading:
- **`power_watts`** — the raw power value
- **`hour_sin`** / **`hour_cos`** — cyclically encoded hour of day (so midnight and 11pm are treated as close together, not 23 apart)

We also use a StandardScaler to normalize features before training, so power values (~0–90W) and sin/cos values (-1 to 1) are weighted equally.

## What's coming next

We have a three-phase plan to make the model smarter:

### Phase 1: Data Cleaning

Before we do anything with the data, we need to clean it. Right now we're feeding raw readings straight into the model. We're going to add a cleaning step that:
- Removes negative watt readings (physically impossible, likely sensor errors)
- Caps extreme spikes that are beyond what a device could realistically produce
- Deduplicates rows where the same device has multiple readings at the same timestamp
- Flags gaps in the data — if a device stops reporting for more than 5 minutes, we mark it so the model knows the context is broken
- Snaps near-zero noise (below 0.5W) to exactly 0, since that's just sensor noise on an idle device

### Phase 2: Core Feature Engineering

Right now we only give the model power and time-of-day. We're going to add several features that capture the *behavior* of the device over time:
- **`is_weekend`** — weekend vs weekday patterns are different (people are home more)
- **`rolling_mean_30m`** — the average power over the last 30 minutes for that device
- **`rolling_std_30m`** — how much the power has been fluctuating in the last 30 minutes
- **`zscore_30m`** — how far the current reading is from the 30-minute average, in standard deviations
- **`delta_from_previous`** — the change in watts from the last reading
- **`percent_change`** — same thing but as a percentage

These features help the model understand context. A reading of 80W on its own might be fine, but 80W when the 30-minute average is 5W is suspicious.

### Phase 3: Advanced Features

Once the core features are in place, we'll add more nuanced signals:
- **`rolling_mean_5m`** — a shorter 5-minute rolling average for catching quick changes
- **`time_since_last_nonzero`** — how long since the device last had a non-zero reading (helps detect devices that should be off but aren't)
- **`duration_current_state`** — how long the device has been in its current on/off state
- **`device_percentile_rank`** — where this reading falls in the device's overall distribution (is this a high or low reading for this device?)

## How models are saved

Each time we run, the trained model and scaler for every device get saved to a `models/` directory as `.joblib` files. This means we could later reload a model to score new data without retraining, or compare how models change over time.

## Visualizations

Every run produces two charts saved to `output/`:
- A **histogram** per device showing the distribution of normal vs anomalous readings
- A **scatter plot** per device showing power by hour of day, with anomalies highlighted in red

These are useful for quickly eyeballing whether the model is making sensible calls.

## Tech stack

- **Python 3.12** with async/await for database operations
- **PostgreSQL** via SQLAlchemy (async) for data storage
- **scikit-learn** for Isolation Forest and preprocessing
- **pandas** for data manipulation
- **matplotlib / seaborn** for visualization
- **joblib** for model persistence
