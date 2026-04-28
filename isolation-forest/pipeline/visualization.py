from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def plot_anomaly_bar_chart(df: pd.DataFrame, output_dir: Path) -> None:
    """Histogram of temperature distribution per device, colored by normal vs anomaly.

    Saves PNG to output_dir and displays interactively.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    devices = df["device_label"].unique()
    n_devices = len(devices)
    fig, axes = plt.subplots(n_devices, 1, figsize=(10, 4 * n_devices), squeeze=False)

    for ax, device in zip(axes.flat, devices):
        subset = df[df["device_label"] == device]
        normal = subset[subset["anomaly"] == 1]["temperature"].astype(float)
        anomalies = subset[subset["anomaly"] == -1]["temperature"].astype(float)

        sns.histplot(normal, color="steelblue", label="Normal", bins=30, ax=ax, kde=True)
        sns.histplot(anomalies, color="crimson", label="Anomaly", bins=30, ax=ax, kde=True)

        ax.set_title(f"{device} — Temperature Distribution")
        ax.set_xlabel("Temperature (\u00b0C)")
        ax.set_ylabel("Count")
        ax.legend()

    fig.tight_layout()
    fig.savefig(output_dir / "anomaly_bar_chart.png", dpi=150)
    plt.show()


def plot_anomaly_scatter(df: pd.DataFrame, output_dir: Path) -> None:
    """Scatter plot of hour_of_day vs temperature per device, colored by anomaly.

    Saves PNG to output_dir and displays interactively.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    devices = df["device_label"].unique()
    n_devices = len(devices)
    fig, axes = plt.subplots(n_devices, 1, figsize=(12, 4 * n_devices), squeeze=False)

    for ax, device in zip(axes.flat, devices):
        subset = df[df["device_label"] == device].copy()

        normal = subset[subset["anomaly"] == 1]
        anomalies = subset[subset["anomaly"] == -1]

        ax.scatter(
            pd.to_datetime(normal["datetime"]).dt.hour,
            normal["temperature"].astype(float),
            color="steelblue",
            label="Normal",
            alpha=0.5,
            s=10,
        )
        ax.scatter(
            pd.to_datetime(anomalies["datetime"]).dt.hour,
            anomalies["temperature"].astype(float),
            color="crimson",
            label="Anomaly",
            alpha=0.7,
            s=15,
        )

        ax.set_title(f"{device} — Temperature by Hour of Day")
        ax.set_xlabel("Hour of Day")
        ax.set_ylabel("Temperature (\u00b0C)")
        ax.set_xticks(range(24))
        ax.legend()
        ax.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_dir / "anomaly_scatter_plot.png", dpi=150)
    plt.show()
