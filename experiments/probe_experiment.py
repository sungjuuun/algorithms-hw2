#!/usr/bin/env python3
"""Measure separate chaining probe counts across several load factors."""

from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from src.hash_table import HashTable


TABLE_SIZE = 4093
LOAD_FACTORS = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)
FAILED_SEARCH_COUNT = 2000
RANDOM_SEED = 20261123
ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "experiments" / "results.csv"
SVG_PATH = ROOT / "experiments" / "chaining.svg"


@dataclass(frozen=True)
class ExperimentResult:
    target_load_factor: float
    inserted_keys: int
    actual_load_factor: float
    successful_average: float
    successful_theory: float
    unsuccessful_average: float
    unsuccessful_theory: float


def generate_urls(rng: random.Random, count: int, namespace: str) -> list[str]:
    """Generate reproducible, unique HTTP(S) URLs in a separate key namespace."""
    urls = []
    for index in range(count):
        scheme = ("http", "https")[rng.randrange(2)]
        hostname_token = rng.randrange(1_000_000_000)
        path_token = rng.randrange(1_000_000_000)
        urls.append(
            f"{scheme}://{namespace}-{index}-{hostname_token}.example/"
            f"item/{path_token}?sample={rng.randrange(1_000_000_000)}"
        )
    return urls


def _average_probe_count(table: HashTable, keys: list[str]) -> float:
    total = 0
    for key in keys:
        total += table.probe_count(key)
    return total / len(keys)


def run_experiment(
    target_load_factor: float, rng: random.Random
) -> ExperimentResult:
    inserted_count = int(target_load_factor * TABLE_SIZE + 0.5)
    inserted_keys = generate_urls(rng, inserted_count, "insert")
    unsuccessful_keys = generate_urls(rng, FAILED_SEARCH_COUNT, "missing")

    table = HashTable(M=TABLE_SIZE, max_load=None)
    for key in inserted_keys:
        table.put(key, None)

    actual_load_factor = table.load_factor
    successful_average = _average_probe_count(table, inserted_keys)
    unsuccessful_average = _average_probe_count(table, unsuccessful_keys)

    return ExperimentResult(
        target_load_factor=target_load_factor,
        inserted_keys=inserted_count,
        actual_load_factor=actual_load_factor,
        successful_average=successful_average,
        successful_theory=1 + actual_load_factor / 2,
        unsuccessful_average=unsuccessful_average,
        unsuccessful_theory=actual_load_factor,
    )


def _write_csv(results: list[ExperimentResult], output: TextIO) -> None:
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        (
            "target_load_factor",
            "inserted_keys",
            "actual_load_factor",
            "successful_experimental_average",
            "successful_theoretical_value",
            "unsuccessful_experimental_average",
            "unsuccessful_theoretical_value",
        )
    )
    for result in results:
        writer.writerow(
            (
                f"{result.target_load_factor:.2f}",
                result.inserted_keys,
                f"{result.actual_load_factor:.6f}",
                f"{result.successful_average:.6f}",
                f"{result.successful_theory:.6f}",
                f"{result.unsuccessful_average:.6f}",
                f"{result.unsuccessful_theory:.6f}",
            )
        )


def write_csv(results: list[ExperimentResult], path: Path = CSV_PATH) -> None:
    with path.open("w", newline="", encoding="utf-8") as output:
        _write_csv(results, output)


def _svg_polyline(
    values: list[float],
    maximum_load_factor: float,
    maximum_probe_count: float,
    plot: tuple[float, float, float, float],
) -> str:
    left, top, width, height = plot
    points = []
    for result, value in zip(LOAD_FACTORS, values):
        x = left + result / maximum_load_factor * width
        y = top + height - value / maximum_probe_count * height
        points.append(f"{x:.2f},{y:.2f}")
    return " ".join(points)


def write_svg(results: list[ExperimentResult], path: Path = SVG_PATH) -> None:
    width = 900
    height = 540
    plot = (75.0, 35.0, 790.0, 415.0)
    left, top, plot_width, plot_height = plot
    maximum_load_factor = LOAD_FACTORS[-1]
    largest_value = max(
        result.unsuccessful_average for result in results
    )
    maximum_probe_count = float(max(1, math.ceil(largest_value)))
    output = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="sans-serif" font-size="12" fill="#222">',
    ]

    for tick in range(int(maximum_probe_count) + 1):
        y = top + plot_height - tick / maximum_probe_count * plot_height
        output.append(
            f'<line x1="{left}" y1="{y:.2f}" '
            f'x2="{left + plot_width}" y2="{y:.2f}" '
            'stroke="#ddd" stroke-width="1"/>'
        )
        output.append(
            f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end">'
            f"{tick}</text>"
        )

    for tick in range(5):
        load_factor = float(tick)
        x = left + load_factor / maximum_load_factor * plot_width
        output.append(
            f'<line x1="{x:.2f}" y1="{top}" '
            f'x2="{x:.2f}" y2="{top + plot_height}" '
            'stroke="#eee" stroke-width="1"/>'
        )
        output.append(
            f'<text x="{x:.2f}" y="{top + plot_height + 22}" '
            f'text-anchor="middle">{tick}</text>'
        )

    output.extend(
        (
            f'<line x1="{left}" y1="{top + plot_height}" '
            f'x2="{left + plot_width}" y2="{top + plot_height}" '
            'stroke="#222"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" '
            f'y2="{top + plot_height}" stroke="#222"/>',
            f'<text x="{left + plot_width / 2}" y="{height - 28}" '
            'text-anchor="middle" font-size="15">Load factor (α)</text>',
            f'<text x="20" y="{top + plot_height / 2}" '
            'text-anchor="middle" font-size="15" '
            'transform="rotate(-90 20 '
            f'{top + plot_height / 2})">Average probe count</text>',
        )
    )

    series = (
        (
            "Successful (theory)",
            [result.successful_theory for result in results],
            "#1769aa",
            "",
        ),
        (
            "Successful (experiment)",
            [result.successful_average for result in results],
            "#1769aa",
            "7 4",
        ),
        (
            "Unsuccessful (theory)",
            [result.unsuccessful_theory for result in results],
            "#c43b3b",
            "",
        ),
        (
            "Unsuccessful (experiment)",
            [result.unsuccessful_average for result in results],
            "#c43b3b",
            "7 4",
        ),
    )
    for label, values, color, dash in series:
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        points = _svg_polyline(
            values, maximum_load_factor, maximum_probe_count, plot
        )
        output.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-width="2"{dash_attribute}/>'
        )
        for load_factor, value in zip(LOAD_FACTORS, values):
            x = left + load_factor / maximum_load_factor * plot_width
            y = top + plot_height - value / maximum_probe_count * plot_height
            output.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" '
                f'fill="{color}"/>'
            )

    legend_x = 545.0
    legend_y = 48.0
    for index, (label, _, color, dash) in enumerate(series):
        y = legend_y + index * 21
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        output.append(
            f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 28}" '
            f'y2="{y}" stroke="{color}" stroke-width="2"{dash_attribute}/>'
        )
        output.append(
            f'<text x="{legend_x + 36}" y="{y + 4}">{label}</text>'
        )

    output.extend(("</g>", "</svg>"))
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def _print_results(results: list[ExperimentResult]) -> None:
    print(
        "target α | inserted | actual α | success exp/theory/diff "
        "| failure exp/theory/diff"
    )
    print("-" * 91)
    for result in results:
        success_difference = result.successful_average - result.successful_theory
        failure_difference = (
            result.unsuccessful_average - result.unsuccessful_theory
        )
        print(
            f"{result.target_load_factor:8.2f} | "
            f"{result.inserted_keys:8d} | "
            f"{result.actual_load_factor:8.4f} | "
            f"{result.successful_average:7.4f}/"
            f"{result.successful_theory:7.4f}/"
            f"{success_difference:+7.4f} | "
            f"{result.unsuccessful_average:7.4f}/"
            f"{result.unsuccessful_theory:7.4f}/"
            f"{failure_difference:+7.4f}"
        )


def main() -> None:
    rng = random.Random(RANDOM_SEED)
    results = [run_experiment(load_factor, rng) for load_factor in LOAD_FACTORS]
    write_csv(results)
    write_svg(results)
    _print_results(results)
    print(f"\nWrote {CSV_PATH.relative_to(ROOT)} and {SVG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
