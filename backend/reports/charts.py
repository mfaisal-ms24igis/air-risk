"""
Chart generation utilities using matplotlib.
"""

import io
import base64
from datetime import date
from typing import List

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

from air_quality.constants import AQI_COLORS


def create_aqi_trend_chart(
    dates: List[date], values: List[float], pollutant: str, title: str = None
) -> str:
    """
    Create AQI trend line chart.

    Args:
        dates: List of dates
        values: List of AQI values
        pollutant: Pollutant code
        title: Optional chart title

    Returns:
        Base64 encoded PNG image
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot line
    ax.plot(dates, values, "b-", linewidth=2, marker="o", markersize=4)

    # Add AQI threshold lines
    thresholds = [
        (50, "Good"),
        (100, "Moderate"),
        (150, "USG"),
        (200, "Unhealthy"),
        (300, "Very Unhealthy"),
    ]

    for threshold, label in thresholds:
        ax.axhline(y=threshold, color="gray", linestyle="--", alpha=0.5)
        ax.text(
            dates[-1], threshold, f" {label}", va="center", fontsize=8, color="gray"
        )

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
    plt.xticks(rotation=45)

    # Labels
    ax.set_xlabel("Date")
    ax.set_ylabel("AQI")
    ax.set_title(title or f"{pollutant} AQI Trend")

    # Grid
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=150)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()

    return f"data:image/png;base64,{image_base64}"


def create_population_pie_chart(
    categories: List[str], populations: List[int], title: str = None
) -> str:
    """
    Create population distribution pie chart by AQI category.

    Args:
        categories: List of category names
        populations: List of population values
        title: Optional chart title

    Returns:
        Base64 encoded PNG image
    """
    fig, ax = plt.subplots(figsize=(8, 8))

    # Filter out zero values
    non_zero = [(c, p) for c, p in zip(categories, populations) if p > 0]
    if not non_zero:
        return None

    cats, pops = zip(*non_zero)

    # Colors for AQI categories
    colors = AQI_COLORS[: len(cats)]

    # Create pie chart
    wedges, texts, autotexts = ax.pie(
        pops,
        labels=cats,
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        explode=[0.02] * len(pops),
    )

    # Style
    for autotext in autotexts:
        autotext.set_fontsize(10)
        autotext.set_fontweight("bold")

    ax.set_title(title or "Population by AQI Category")

    plt.tight_layout()

    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=150)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()

    return f"data:image/png;base64,{image_base64}"


def create_district_bar_chart(
    districts: List[str],
    values: List[float],
    metric: str = "AQI",
    title: str = None,
    color_by_value: bool = True,
) -> str:
    """
    Create horizontal bar chart for district comparison.

    Args:
        districts: List of district names
        values: List of metric values
        metric: Name of the metric
        title: Optional chart title
        color_by_value: Whether to color bars by AQI level

    Returns:
        Base64 encoded PNG image
    """
    fig, ax = plt.subplots(figsize=(10, max(6, len(districts) * 0.4)))

    y_pos = np.arange(len(districts))

    # Color bars by value if AQI
    if color_by_value and metric == "AQI":
        colors = []
        for v in values:
            if v <= 50:
                colors.append(AQI_COLORS[0])
            elif v <= 100:
                colors.append(AQI_COLORS[1])
            elif v <= 150:
                colors.append(AQI_COLORS[2])
            elif v <= 200:
                colors.append(AQI_COLORS[3])
            elif v <= 300:
                colors.append(AQI_COLORS[4])
            else:
                colors.append(AQI_COLORS[5])
    else:
        colors = ["#3498db"] * len(values)

    # Create bars
    bars = ax.barh(y_pos, values, color=colors)

    # Add value labels
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_width() + 1,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}",
            va="center",
            fontsize=9,
        )

    # Labels
    ax.set_yticks(y_pos)
    ax.set_yticklabels(districts)
    ax.set_xlabel(metric)
    ax.set_title(title or f"Districts by {metric}")
    ax.invert_yaxis()

    plt.tight_layout()

    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=150)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()

    return f"data:image/png;base64,{image_base64}"


def create_multi_pollutant_chart(
    dates: List[date],
    data: dict,  # {pollutant: [values]}
    title: str = None,
) -> str:
    """
    Create multi-line chart comparing multiple pollutants.

    Args:
        dates: List of dates
        data: Dictionary mapping pollutant to values
        title: Optional chart title

    Returns:
        Base64 encoded PNG image
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6", "#f39c12"]

    for i, (pollutant, values) in enumerate(data.items()):
        ax.plot(
            dates,
            values,
            label=pollutant,
            color=colors[i % len(colors)],
            linewidth=2,
            marker="o",
            markersize=3,
        )

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
    plt.xticks(rotation=45)

    # Labels
    ax.set_xlabel("Date")
    ax.set_ylabel("AQI")
    ax.set_title(title or "Multi-Pollutant AQI Comparison")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=150)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()

    return f"data:image/png;base64,{image_base64}"


def create_heatmap(
    districts: List[str],
    pollutants: List[str],
    values: List[List[float]],
    title: str = None,
) -> str:
    """
    Create heatmap of districts vs pollutants.

    Args:
        districts: List of district names
        pollutants: List of pollutant codes
        values: 2D list of values [districts][pollutants]
        title: Optional chart title

    Returns:
        Base64 encoded PNG image
    """
    fig, ax = plt.subplots(figsize=(10, max(6, len(districts) * 0.3)))

    data = np.array(values)

    # Create heatmap
    im = ax.imshow(data, cmap="RdYlGn_r", aspect="auto")

    # Labels
    ax.set_xticks(np.arange(len(pollutants)))
    ax.set_yticks(np.arange(len(districts)))
    ax.set_xticklabels(pollutants)
    ax.set_yticklabels(districts)

    # Add colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("AQI", rotation=-90, va="bottom")

    # Add text annotations
    for i in range(len(districts)):
        for j in range(len(pollutants)):
            ax.text(
                j,
                i,
                f"{values[i][j]:.0f}",
                ha="center",
                va="center",
                color="white" if values[i][j] > 150 else "black",
                fontsize=8,
            )

    ax.set_title(title or "AQI Heatmap")

    plt.tight_layout()

    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=150)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()

    return f"data:image/png;base64,{image_base64}"
