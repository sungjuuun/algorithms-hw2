#!/usr/bin/env python3
"""Compare separate chaining and linear probing across load factors."""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import TextIO

from src.hash_table import HashTable
from src.linear_probing_hash_table import LinearProbingHashTable


TABLE_SIZE = 4093
LOAD_FACTORS = tuple(index / 10 for index in range(1, 10))
FAILED_SEARCH_COUNT = 5000
EXPERIMENT_REPETITIONS = 5
RANDOM_SEED = 20261123
ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "experiments" / "comparison.csv"
SVG_PATH = ROOT / "experiments" / "comparison.svg"


@dataclass(frozen=True)
class MethodResult:
    successful_average: float
    successful_theory: float
    unsuccessful_average: float
    unsuccessful_theory: float


@dataclass(frozen=True)
class ExperimentResult:
    target_load_factor: float
    inserted_keys: int
    actual_load_factor: float
    repetitions: int
    chaining: MethodResult
    linear_probing: MethodResult


def generate_urls(rng: random.Random, count: int, namespace: str) -> list[str]:
    """Generate reproducible, unique HTTP(S) URL keys."""
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


def generate_keys(rng: random.Random, count: int, namespace: str) -> list[str]:
    """Generate reproducible string keys with independently mixed suffixes."""
    keys = []
    for index in range(count):
        keys.append(f"{namespace}-{index}-{rng.getrandbits(128):032x}")
    return keys


def separate_chaining_theory(load_factor: float) -> tuple[float, float]:
    return 1 + load_factor / 2, load_factor


def linear_probing_theory(load_factor: float) -> tuple[float, float]:
    if not 0 <= load_factor < 1:
        raise ValueError("linear probing theory requires 0 <= load_factor < 1")
    successful = 0.5 * (1 + 1 / (1 - load_factor))
    unsuccessful = 0.5 * (1 + 1 / ((1 - load_factor) ** 2))
    return successful, unsuccessful


def _average_probe_count(table, keys: list[str]) -> float:
    total = 0
    for key in keys:
        total += table.probe_count(key)
    return total / len(keys)


def run_comparison(seed: int = RANDOM_SEED) -> list[ExperimentResult]:
    rng = random.Random(seed)
    results = []
    for target_load_factor in LOAD_FACTORS:
        inserted_count = int(target_load_factor * TABLE_SIZE + 0.5)
        chaining_success_total = 0.0
        chaining_failure_total = 0.0
        linear_success_total = 0.0
        linear_failure_total = 0.0
        for _ in range(EXPERIMENT_REPETITIONS):
            inserted_keys = generate_keys(rng, inserted_count, "shared")
            unsuccessful_keys = generate_keys(rng, FAILED_SEARCH_COUNT, "missing")

            chaining = HashTable(M=TABLE_SIZE, max_load=None)
            linear_probing = LinearProbingHashTable(M=TABLE_SIZE, max_load=None)
            for key in inserted_keys:
                chaining.put(key, None)
                linear_probing.put(key, None)

            chaining_success_total += _average_probe_count(chaining, inserted_keys)
            chaining_failure_total += _average_probe_count(
                chaining, unsuccessful_keys
            )
            linear_success_total += _average_probe_count(
                linear_probing, inserted_keys
            )
            linear_failure_total += _average_probe_count(
                linear_probing, unsuccessful_keys
            )

        actual_load_factor = inserted_count / TABLE_SIZE
        chaining_success_theory, chaining_failure_theory = (
            separate_chaining_theory(actual_load_factor)
        )
        linear_success_theory, linear_failure_theory = linear_probing_theory(
            actual_load_factor
        )
        results.append(
            ExperimentResult(
                target_load_factor=target_load_factor,
                inserted_keys=inserted_count,
                actual_load_factor=actual_load_factor,
                repetitions=EXPERIMENT_REPETITIONS,
                chaining=MethodResult(
                    successful_average=chaining_success_total / EXPERIMENT_REPETITIONS,
                    successful_theory=chaining_success_theory,
                    unsuccessful_average=chaining_failure_total
                    / EXPERIMENT_REPETITIONS,
                    unsuccessful_theory=chaining_failure_theory,
                ),
                linear_probing=MethodResult(
                    successful_average=linear_success_total / EXPERIMENT_REPETITIONS,
                    successful_theory=linear_success_theory,
                    unsuccessful_average=linear_failure_total
                    / EXPERIMENT_REPETITIONS,
                    unsuccessful_theory=linear_failure_theory,
                ),
            )
        )
    return results


def _write_csv(results: list[ExperimentResult], output: TextIO) -> None:
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        (
            "target_load_factor",
            "inserted_keys",
            "actual_load_factor",
            "repetitions",
            "chaining_success_experimental",
            "chaining_success_theoretical",
            "chaining_failure_experimental",
            "chaining_failure_theoretical",
            "linear_success_experimental",
            "linear_success_theoretical",
            "linear_failure_experimental",
            "linear_failure_theoretical",
        )
    )
    for result in results:
        writer.writerow(
            (
                f"{result.target_load_factor:.2f}",
                result.inserted_keys,
                f"{result.actual_load_factor:.6f}",
                result.repetitions,
                f"{result.chaining.successful_average:.6f}",
                f"{result.chaining.successful_theory:.6f}",
                f"{result.chaining.unsuccessful_average:.6f}",
                f"{result.chaining.unsuccessful_theory:.6f}",
                f"{result.linear_probing.successful_average:.6f}",
                f"{result.linear_probing.successful_theory:.6f}",
                f"{result.linear_probing.unsuccessful_average:.6f}",
                f"{result.linear_probing.unsuccessful_theory:.6f}",
            )
        )


def write_csv(results: list[ExperimentResult], path: Path = CSV_PATH) -> None:
    with path.open("w", newline="", encoding="utf-8") as output:
        _write_csv(results, output)


def _svg_polyline(
    results: list[ExperimentResult],
    value_getter,
    maximum: float,
    plot: tuple[float, float, float, float],
) -> str:
    left, top, width, height = plot
    points = []
    for result in results:
        x = left + (result.target_load_factor - LOAD_FACTORS[0]) / (
            LOAD_FACTORS[-1] - LOAD_FACTORS[0]
        ) * width
        y = top + height - value_getter(result) / maximum * height
        points.append(f"{x:.2f},{y:.2f}")
    return " ".join(points)


def write_svg(results: list[ExperimentResult], path: Path = SVG_PATH) -> None:
    width = 1120
    height = 600
    plot = (75.0, 40.0, 700.0, 450.0)
    left, top, plot_width, plot_height = plot
    largest_value = max(
        max(
            result.chaining.unsuccessful_average,
            result.chaining.unsuccessful_theory,
            result.linear_probing.unsuccessful_average,
            result.linear_probing.unsuccessful_theory,
        )
        for result in results
    )
    maximum = float(max(10, ceil(largest_value / 10) * 10))
    series = (
        ("Chaining success: measured", lambda r: r.chaining.successful_average, "#1769aa", ""),
        ("Chaining success: theory", lambda r: r.chaining.successful_theory, "#1769aa", "7 4"),
        ("Linear success: measured", lambda r: r.linear_probing.successful_average, "#11825b", ""),
        ("Linear success: theory", lambda r: r.linear_probing.successful_theory, "#11825b", "7 4"),
        ("Chaining failure: measured", lambda r: r.chaining.unsuccessful_average, "#c43b3b", ""),
        ("Chaining failure: theory", lambda r: r.chaining.unsuccessful_theory, "#c43b3b", "7 4"),
        ("Linear failure: measured", lambda r: r.linear_probing.unsuccessful_average, "#9a4f96", ""),
        ("Linear failure: theory", lambda r: r.linear_probing.unsuccessful_theory, "#9a4f96", "7 4"),
    )
    output = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="sans-serif" font-size="12" fill="#222">',
    ]

    for tick in range(0, int(maximum) + 1, 10):
        y = top + plot_height - tick / maximum * plot_height
        output.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" '
            f'y2="{y:.2f}" stroke="#ddd"/>'
        )
        output.append(
            f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end">'
            f"{tick}</text>"
        )
    for result in results:
        x = left + (result.target_load_factor - LOAD_FACTORS[0]) / (
            LOAD_FACTORS[-1] - LOAD_FACTORS[0]
        ) * plot_width
        output.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" '
            f'y2="{top + plot_height}" stroke="#eee"/>'
        )
        output.append(
            f'<text x="{x:.2f}" y="{top + plot_height + 22}" '
            f'text-anchor="middle">{result.target_load_factor:.1f}</text>'
        )
    output.extend(
        (
            f'<line x1="{left}" y1="{top + plot_height}" '
            f'x2="{left + plot_width}" y2="{top + plot_height}" stroke="#222"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" '
            f'y2="{top + plot_height}" stroke="#222"/>',
            f'<text x="{left + plot_width / 2}" y="{height - 28}" '
            'text-anchor="middle" font-size="15">Load factor (α)</text>',
            f'<text x="20" y="{top + plot_height / 2}" '
            'text-anchor="middle" font-size="15" '
            f'transform="rotate(-90 20 {top + plot_height / 2})">'
            'Average probes</text>',
        )
    )
    for label, getter, color, dash in series:
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        output.append(
            f'<polyline points="{_svg_polyline(results, getter, maximum, plot)}" '
            f'fill="none" stroke="{color}" stroke-width="2"{dash_attribute}/>'
        )
        for result in results:
            x = left + (result.target_load_factor - LOAD_FACTORS[0]) / (
                LOAD_FACTORS[-1] - LOAD_FACTORS[0]
            ) * plot_width
            y = top + plot_height - getter(result) / maximum * plot_height
            output.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{color}"/>'
            )

    legend_x = 820.0
    for index, (label, _, color, dash) in enumerate(series):
        y = 55.0 + index * 25
        dash_attribute = f' stroke-dasharray="{dash}"' if dash else ""
        output.append(
            f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 28}" '
            f'y2="{y}" stroke="{color}" stroke-width="2"{dash_attribute}/>'
        )
        output.append(f'<text x="{legend_x + 36}" y="{y + 4}">{label}</text>')
    output.extend(("</g>", "</svg>"))
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def _print_results(results: list[ExperimentResult]) -> None:
    print(
        "α   | Chaining success (meas/theory) | Chaining failure (meas/theory) "
        "| Linear success (meas/theory) | Linear failure (meas/theory)"
    )
    print("-" * 136)
    for result in results:
        print(
            f"{result.actual_load_factor:.4f} | "
            f"{result.chaining.successful_average:.4f}/"
            f"{result.chaining.successful_theory:.4f} | "
            f"{result.chaining.unsuccessful_average:.4f}/"
            f"{result.chaining.unsuccessful_theory:.4f} | "
            f"{result.linear_probing.successful_average:.4f}/"
            f"{result.linear_probing.successful_theory:.4f} | "
            f"{result.linear_probing.unsuccessful_average:.4f}/"
            f"{result.linear_probing.unsuccessful_theory:.4f}"
        )


def main() -> None:
    results = run_comparison()
    write_csv(results)
    write_svg(results)
    _print_results(results)
    print(f"\nFixed seed: {RANDOM_SEED}; table size: {TABLE_SIZE}")
    print(f"Wrote {CSV_PATH.relative_to(ROOT)} and {SVG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
