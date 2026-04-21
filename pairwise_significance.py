#!/usr/bin/env python3
"""
Pairwise statistical significance analysis for LLM benchmark subsets.

For each benchmark size, produces a model×model matrix indicating whether
model A is statistically significantly worse than model B, using a paired
t-test on the 10 seed-based subset evaluations.

Usage:
    python pairwise_significance.py --results-dir ./results --effect-size 5.0 --alpha 0.05

    # Power-analysis mode: shift means to differ by exactly E
    python pairwise_significance.py --results-dir ./results --effect-size 5.0 --shift-to-ensure-difference

    # With Bonferroni correction for multiple comparisons
    python pairwise_significance.py --results-dir ./results --effect-size 5.0 --shift-to-ensure-difference --bonferroni

    # Sweep over multiple effect sizes
    python pairwise_significance.py --results-dir ./results --effect-sizes 1.0 2.0 3.0 5.0 7.0 10.0 --shift-to-ensure-difference --bonferroni
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def load_model_results(results_dir: str) -> dict[str, pd.DataFrame]:
    """
    Load all TSV files from the results directory.

    Each TSV file is expected to have:
      - A 'size' column (or first column) indicating benchmark size
      - Columns named 'seed_<N>' with accuracy values in [0, 100]

    Returns:
        Dictionary mapping model_name -> DataFrame indexed by size,
        with seed columns containing accuracy values.
    """
    models = {}
    results_path = Path(results_dir)

    for filepath in sorted(results_path.glob("*.tsv")):
        model_name = filepath.stem
        df = pd.read_csv(filepath, sep="\t")

        # Identify the size column: either named 'size' or the first column
        if "size" in df.columns:
            df = df.set_index("size")
        else:
            # Assume the first column is the size
            df = df.set_index(df.columns[0])
            df.index.name = "size"

        # Keep only seed columns
        seed_cols = [c for c in df.columns if c.startswith("seed_")]
        if not seed_cols:
            print(f"Warning: No seed columns found in {filepath.name}, skipping.")
            continue

        df = df[seed_cols].apply(pd.to_numeric, errors="coerce")
        models[model_name] = df

    return models


def get_available_sizes(models: dict[str, pd.DataFrame]) -> list:
    """Get all unique sizes across all models, sorted."""
    all_sizes = set()
    for df in models.values():
        all_sizes.update(df.index.tolist())
    return sorted(all_sizes)


def get_models_for_size(models: dict[str, pd.DataFrame], size) -> list[str]:
    """Get list of model names that have results for a given size."""
    available = []
    for model_name, df in models.items():
        if size in df.index:
            available.append(model_name)
    return sorted(available)


def build_output_dir(base_output_dir: str, effect_size: float | None,
                     shift: bool, bonferroni: bool,
                     is_sweep: bool = False) -> Path:
    """
    Build a structured output directory path encoding the configuration.

    Example: ./output/effect_5.0pp/shifted/bonferroni/
             ./output/sweep/shifted/bonferroni/
    """
    parts = [base_output_dir]

    if is_sweep:
        parts.append("sweep")
    else:
        parts.append(f"effect_{effect_size}pp")

    parts.append("shifted" if shift else "standard")
    parts.append("bonferroni" if bonferroni else "no_bonferroni")

    return Path(*parts)


def compute_pairwise_table(
    models: dict[str, pd.DataFrame],
    size,
    effect_size: float = 5.0,
    alpha: float = 0.05,
    shift_to_ensure_difference: bool = False,
    bonferroni: bool = False,
) -> tuple[pd.DataFrame | None, float, int | None]:
    """
    Compute the pairwise significance table for a given benchmark size.

    Cell (A, B) answers: "Is model A significantly worse than model B?"

    When shift_to_ensure_difference is True, model B's values are shifted so
    that mean(B_shifted) = mean(A) + effect_size, preserving B's variance.

    When bonferroni is True, the significance threshold is divided by the
    number of tests actually performed.

    Returns:
        Tuple of (DataFrame, alpha_corrected, n_tests).
        DataFrame has models as both index and columns, cells containing
        strings like 'SKIP', 'N (p=0.123)', 'S (p=0.004)', or '-' on diagonal.
    """
    available_models = get_models_for_size(models, size)

    # Find common seed columns across all available models for this size
    common_seeds = None
    for model_name in available_models:
        df = models[model_name]
        row_seeds = set(df.columns)
        if common_seeds is None:
            common_seeds = row_seeds
        else:
            common_seeds = common_seeds & row_seeds
    common_seeds = sorted(common_seeds)

    if len(common_seeds) < 2:
        return None, alpha, None

    # Extract accuracy arrays for each model (over common seeds)
    accuracies = {}
    for model_name in available_models:
        df = models[model_name]
        accuracies[model_name] = df.loc[size, common_seeds].values.astype(float)

    n_models = len(available_models)

    # Determine number of tests for Bonferroni correction
    if bonferroni:
        if shift_to_ensure_difference:
            n_tests = n_models * (n_models - 1)
        else:
            n_tests = 0
            for i, model_a in enumerate(available_models):
                for j, model_b in enumerate(available_models):
                    if i == j:
                        continue
                    mean_a = np.mean(accuracies[model_a])
                    mean_b = np.mean(accuracies[model_b])
                    if mean_a < mean_b and (mean_b - mean_a) >= effect_size:
                        n_tests += 1
            if n_tests == 0:
                n_tests = 1

        alpha_corrected = alpha / n_tests
    else:
        alpha_corrected = alpha
        n_tests = None

    result = pd.DataFrame(
        "", index=available_models, columns=available_models
    )

    for i, model_a in enumerate(available_models):
        for j, model_b in enumerate(available_models):
            if i == j:
                result.loc[model_a, model_b] = "-"
                continue

            acc_a = accuracies[model_a].copy()
            acc_b = accuracies[model_b].copy()
            mean_a = np.mean(acc_a)
            mean_b = np.mean(acc_b)

            if shift_to_ensure_difference:
                shift = mean_a + effect_size - mean_b
                acc_b = acc_b + shift
            else:
                if mean_a >= mean_b:
                    result.loc[model_a, model_b] = "SKIP"
                    continue

                diff = mean_b - mean_a
                if diff < effect_size:
                    result.loc[model_a, model_b] = "SKIP"
                    continue

            t_stat, p_two_sided = stats.ttest_rel(acc_b, acc_a)

            if t_stat > 0:
                p_value = p_two_sided / 2
            else:
                p_value = 1.0 - p_two_sided / 2

            if p_value < alpha_corrected:
                result.loc[model_a, model_b] = f"S (p={p_value:.4f})"
            else:
                result.loc[model_a, model_b] = f"N (p={p_value:.4f})"

    return result, alpha_corrected, n_tests


def count_significance(table: pd.DataFrame) -> tuple[int, int, int, int]:
    """
    Count the number of S, N, SKIP, and total tested cells in a pairwise table.

    Returns:
        (n_significant, n_not_significant, n_skip, n_tested)
        where n_tested = n_significant + n_not_significant
    """
    n_s = 0
    n_n = 0
    n_skip = 0
    for i in range(len(table)):
        for j in range(len(table.columns)):
            cell = table.iloc[i, j]
            if cell == "-" or cell == "":
                continue
            elif cell == "SKIP":
                n_skip += 1
            elif cell.startswith("S "):
                n_s += 1
            elif cell.startswith("N "):
                n_n += 1
    n_tested = n_s + n_n
    return n_s, n_n, n_skip, n_tested


def save_table(table: pd.DataFrame, filepath: Path,
               bonferroni: bool, alpha_corrected: float):
    """
    Save the pairwise table as a TSV file.

    If bonferroni is enabled, the corrected alpha is stored in the
    top-left corner cell (index name position) for reference.
    """
    if bonferroni:
        table = table.copy()
        table.index.name = f"alpha={alpha_corrected:.6f}"

    table.to_csv(filepath, sep="\t")


def save_summary(output_path: Path, summary_rows: list[dict],
                 effect_size: float, alpha: float,
                 shift: bool, bonferroni: bool):
    """
    Save a summary TSV file with per-size statistics and experiment metadata.
    """
    min_all_significant = None
    for row in summary_rows:
        if row["n_tested"] > 0 and row["n_not_significant"] == 0:
            min_all_significant = row["size"]
            break

    summary_filepath = output_path / "summary.tsv"
    with open(summary_filepath, "w") as f:
        header_cols = [
            "size", "n_models", "n_significant", "n_not_significant",
            "n_skip", "n_tested", "all_significant"
        ]
        if bonferroni:
            header_cols.append("alpha_corrected")
        f.write("\t".join(header_cols) + "\n")

        for row in summary_rows:
            all_sig = "YES" if (row["n_tested"] > 0 and row["n_not_significant"] == 0) else "NO"
            values = [
                str(row["size"]),
                str(row["n_models"]),
                str(row["n_significant"]),
                str(row["n_not_significant"]),
                str(row["n_skip"]),
                str(row["n_tested"]),
                all_sig,
            ]
            if bonferroni:
                alpha_val = row.get("alpha_corrected")
                values.append(f"{alpha_val:.6f}" if alpha_val is not None else "N/A")
            f.write("\t".join(values) + "\n")

        f.write("\n")

        desc_parts = [
            f"effect_size={effect_size}pp",
            f"alpha={alpha}",
            f"mode={'shifted' if shift else 'standard'}",
            f"bonferroni={'yes' if bonferroni else 'no'}",
        ]
        f.write("# " + "  |  ".join(desc_parts) + "\n")

        if min_all_significant is not None:
            f.write(f"# minimum_size_all_significant={min_all_significant}\n")
        else:
            f.write("# minimum_size_all_significant=NONE (no size has all pairs significant)\n")

    return summary_filepath, min_all_significant


def run_single_effect_size(
    models: dict[str, pd.DataFrame],
    sizes_to_analyze: list,
    effect_size: float,
    alpha: float,
    shift: bool,
    bonferroni: bool,
    output_path: Path | None,
    verbose: bool = True,
) -> list[dict]:
    """
    Run the full pairwise analysis for a single effect size.

    Returns:
        List of summary row dicts (one per size).
    """
    summary_rows = []

    for size in sizes_to_analyze:
        available = get_models_for_size(models, size)

        if verbose:
            print(f"{'='*70}")
            print(f"SIZE = {size}  ({len(available)} models: {', '.join(available)})")
            print(f"{'='*70}")

        if len(available) < 2:
            if verbose:
                print("  Fewer than 2 models available, skipping.\n")
            summary_rows.append({
                "size": size,
                "n_models": len(available),
                "n_significant": 0,
                "n_not_significant": 0,
                "n_skip": 0,
                "n_tested": 0,
                "alpha_corrected": None,
            })
            continue

        if verbose:
            print("\n  Mean accuracies (across seeds):")
            means = {}
            for model_name in available:
                df = models[model_name]
                seed_cols = [c for c in df.columns if c.startswith("seed_")]
                mean_acc = df.loc[size, seed_cols].astype(float).mean()
                means[model_name] = mean_acc
            for model_name in sorted(means, key=means.get, reverse=True):
                print(f"    {model_name:30s}  {means[model_name]:.2f}")

        table, alpha_used, n_tests = compute_pairwise_table(
            models, size,
            effect_size=effect_size,
            alpha=alpha,
            shift_to_ensure_difference=shift,
            bonferroni=bonferroni,
        )

        if table is not None:
            n_s, n_n, n_skip, n_tested = count_significance(table)
            all_sig = n_tested > 0 and n_n == 0

            if verbose:
                if shift:
                    print(f"\n  Pairwise table (row A, col B): "
                          f"'With forced diff of {effect_size}pp, "
                          f"can we detect A < B?'")
                else:
                    print(f"\n  Pairwise table (row A, col B): "
                          f"'Is A significantly worse than B?'")

                if bonferroni:
                    print(f"  Bonferroni: {n_tests} tests, "
                          f"α_corrected = {alpha}/{n_tests} = {alpha_used:.6f}")
                print()

                with pd.option_context(
                    "display.max_columns", None,
                    "display.max_colwidth", 20,
                    "display.width", 200,
                ):
                    print(table.to_string())
                print()

                print(f"  Summary: {n_s} significant, {n_n} not significant, "
                      f"{n_skip} skipped, {n_tested} tested"
                      f"  {'✓ ALL SIGNIFICANT' if all_sig else ''}")

            summary_rows.append({
                "size": size,
                "n_models": len(available),
                "n_significant": n_s,
                "n_not_significant": n_n,
                "n_skip": n_skip,
                "n_tested": n_tested,
                "alpha_corrected": alpha_used,
            })

            if output_path:
                out_filepath = output_path / f"pairwise_size_{size}.tsv"
                save_table(table, out_filepath, bonferroni, alpha_used)
                if verbose:
                    print(f"  Saved to: {out_filepath}")
        else:
            summary_rows.append({
                "size": size,
                "n_models": len(available),
                "n_significant": 0,
                "n_not_significant": 0,
                "n_skip": 0,
                "n_tested": 0,
                "alpha_corrected": None,
            })

        if verbose:
            print()

    return summary_rows


def print_single_summary(summary_rows: list[dict], bonferroni: bool):
    """Print the summary table for a single effect size run."""
    header = (f"  {'Size':>6s}  {'Models':>6s}  {'S':>4s}  {'N':>4s}  "
              f"{'Skip':>5s}  {'Tested':>6s}  {'All sig?':>8s}")
    if bonferroni:
        header += f"  {'α_corrected':>12s}"
    print(header)
    print(f"  {'-'*len(header.strip())}")
    for row in summary_rows:
        all_sig = "YES" if (row["n_tested"] > 0 and row["n_not_significant"] == 0) else "NO"
        line = (f"  {row['size']:>6}  {row['n_models']:>6}  {row['n_significant']:>4}  "
                f"{row['n_not_significant']:>4}  {row['n_skip']:>5}  "
                f"{row['n_tested']:>6}  {all_sig:>8s}")
        if bonferroni:
            alpha_val = row.get("alpha_corrected")
            line += f"  {alpha_val:>12.6f}" if alpha_val is not None else f"  {'N/A':>12s}"
        print(line)


def find_min_all_significant(summary_rows: list[dict]) -> int | None:
    """Find the minimum size where all tested pairs are significant."""
    for row in summary_rows:
        if row["n_tested"] > 0 and row["n_not_significant"] == 0:
            return row["size"]
    return None


def run_sweep(
    models: dict[str, pd.DataFrame],
    sizes_to_analyze: list,
    effect_sizes: list[float],
    alpha: float,
    shift: bool,
    bonferroni: bool,
    output_path: Path | None,
):
    """
    Run the analysis for multiple effect sizes, then produce:
      1. Per-effect-size detailed output (tables + summaries)
      2. A cross-effect-size summary: effect_size -> min benchmark size
      3. A cross-size summary: benchmark size -> min detectable effect size
    """
    # ── Per-effect-size runs ──────────────────────────────────────────────
    # Maps effect_size -> summary_rows
    all_summaries: dict[float, list[dict]] = {}

    for es in effect_sizes:
        print(f"\n{'#'*70}")
        print(f"# EFFECT SIZE = {es} pp")
        print(f"{'#'*70}\n")

        # Per-effect-size output subdirectory
        if output_path:
            es_output_path = output_path / f"effect_{es}pp"
            os.makedirs(es_output_path, exist_ok=True)
        else:
            es_output_path = None

        summary_rows = run_single_effect_size(
            models, sizes_to_analyze, es, alpha, shift, bonferroni,
            es_output_path, verbose=True,
        )

        all_summaries[es] = summary_rows

        # Save per-effect-size summary
        if es_output_path:
            save_summary(es_output_path, summary_rows, es, alpha, shift, bonferroni)

        # Print per-effect-size summary
        print(f"  {'─'*60}")
        print(f"  Summary for effect_size = {es} pp:")
        print()
        print_single_summary(summary_rows, bonferroni)
        min_size = find_min_all_significant(summary_rows)
        print()
        if min_size is not None:
            print(f"  ► Minimum size (all significant): {min_size}")
        else:
            print(f"  ► No size has all tested pairs significant.")
        print()

    # ── Cross-effect-size summary table ───────────────────────────────────
    # For each effect size: what is the minimum benchmark size?
    print(f"\n{'='*70}")
    print(f"CROSS-SUMMARY: Effect Size → Minimum Benchmark Size")
    print(f"{'='*70}\n")

    es_to_min_size: dict[float, int | None] = {}
    for es in effect_sizes:
        es_to_min_size[es] = find_min_all_significant(all_summaries[es])

    print(f"  {'Effect Size (pp)':>16s}  {'Min Benchmark Size':>18s}")
    print(f"  {'─'*36}")
    for es in effect_sizes:
        min_size = es_to_min_size[es]
        size_str = str(min_size) if min_size is not None else "—"
        print(f"  {es:>16.1f}  {size_str:>18s}")
    print()

    # ── Cross-size summary table ──────────────────────────────────────────
    # For each benchmark size: what is the minimum detectable effect size?
    print(f"{'='*70}")
    print(f"CROSS-SUMMARY: Benchmark Size → Minimum Detectable Effect Size")
    print(f"{'='*70}\n")

    # For each size, find the smallest effect size where all pairs are significant
    size_to_min_es: dict[int, float | None] = {}
    for size in sizes_to_analyze:
        min_es = None
        for es in effect_sizes:  # already sorted by caller or we sort here
            summary_rows = all_summaries[es]
            # Find the row for this size
            row = None
            for r in summary_rows:
                if r["size"] == size:
                    row = r
                    break
            if row is not None and row["n_tested"] > 0 and row["n_not_significant"] == 0:
                if min_es is None or es < min_es:
                    min_es = es
        size_to_min_es[size] = min_es

    print(f"  {'Benchmark Size':>14s}  {'Min Detectable Effect (pp)':>26s}")
    print(f"  {'─'*42}")
    for size in sizes_to_analyze:
        min_es = size_to_min_es[size]
        es_str = f"{min_es:.1f}" if min_es is not None else "—"
        n_models = len(get_models_for_size(models, size))
        print(f"  {size:>14}  {es_str:>26s}   ({n_models} models)")
    print()

    # ── Combined matrix: sizes × effect sizes ─────────────────────────────
    print(f"{'='*70}")
    print(f"MATRIX: All Significant? (Size × Effect Size)")
    print(f"{'='*70}\n")

    sorted_effect_sizes = sorted(effect_sizes)

    # Header
    header = f"  {'Size':>6s}"
    for es in sorted_effect_sizes:
        header += f"  {es:>7.1f}pp"
    print(header)
    print(f"  {'─' * (8 + 9 * len(sorted_effect_sizes))}")

    for size in sizes_to_analyze:
        line = f"  {size:>6}"
        for es in sorted_effect_sizes:
            summary_rows = all_summaries[es]
            row = None
            for r in summary_rows:
                if r["size"] == size:
                    row = r
                    break
            if row is None or row["n_tested"] == 0:
                cell = "—"
            elif row["n_not_significant"] == 0:
                cell = "✓"
            else:
                # Show fraction: n_significant / n_tested
                cell = f"{row['n_significant']}/{row['n_tested']}"
            line += f"  {cell:>9s}"
        print(line)
    print()
    print(f"  ✓ = all tested pairs significant")
    print(f"  n/m = n out of m tested pairs significant")
    print(f"  — = no pairs tested")
    print()

    # ── Save cross-summaries ──────────────────────────────────────────────
    if output_path:
        # Save effect_size -> min_size table
        cross_es_path = output_path / "cross_summary_effect_to_size.tsv"
        with open(cross_es_path, "w") as f:
            f.write("effect_size_pp\tmin_benchmark_size\n")
            for es in effect_sizes:
                min_size = es_to_min_size[es]
                f.write(f"{es}\t{min_size if min_size is not None else 'NONE'}\n")
            f.write("\n")
            desc_parts = [
                f"alpha={alpha}",
                f"mode={'shifted' if shift else 'standard'}",
                f"bonferroni={'yes' if bonferroni else 'no'}",
            ]
            f.write("# " + "  |  ".join(desc_parts) + "\n")
        print(f"  Saved: {cross_es_path}")

        # Save size -> min_effect table
        cross_size_path = output_path / "cross_summary_size_to_effect.tsv"
        with open(cross_size_path, "w") as f:
            f.write("benchmark_size\tn_models\tmin_detectable_effect_pp\n")
            for size in sizes_to_analyze:
                min_es = size_to_min_es[size]
                n_models = len(get_models_for_size(models, size))
                f.write(f"{size}\t{n_models}\t{min_es if min_es is not None else 'NONE'}\n")
            f.write("\n")
            desc_parts = [
                f"alpha={alpha}",
                f"mode={'shifted' if shift else 'standard'}",
                f"bonferroni={'yes' if bonferroni else 'no'}",
                f"effect_sizes_tested={','.join(str(e) for e in effect_sizes)}",
            ]
            f.write("# " + "  |  ".join(desc_parts) + "\n")
        print(f"  Saved: {cross_size_path}")

        # Save the full matrix
        matrix_path = output_path / "cross_summary_matrix.tsv"
        with open(matrix_path, "w") as f:
            # Header
            f.write("size")
            for es in sorted_effect_sizes:
                f.write(f"\t{es}pp")
            f.write("\n")
            # Rows
            for size in sizes_to_analyze:
                f.write(str(size))
                for es in sorted_effect_sizes:
                    summary_rows = all_summaries[es]
                    row = None
                    for r in summary_rows:
                        if r["size"] == size:
                            row = r
                            break
                    if row is None or row["n_tested"] == 0:
                        f.write("\t—")
                    elif row["n_not_significant"] == 0:
                        f.write("\tALL")
                    else:
                        f.write(f"\t{row['n_significant']}/{row['n_tested']}")
                f.write("\n")
            f.write("\n")
            desc_parts = [
                f"alpha={alpha}",
                f"mode={'shifted' if shift else 'standard'}",
                f"bonferroni={'yes' if bonferroni else 'no'}",
            ]
            f.write("# " + "  |  ".join(desc_parts) + "\n")
        print(f"  Saved: {matrix_path}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Pairwise significance analysis for LLM benchmark subsets."
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        required=True,
        help="Directory containing one TSV file per model.",
    )

    # Effect size: either single or multiple
    es_group = parser.add_mutually_exclusive_group(required=True)
    es_group.add_argument(
        "--effect-size",
        type=float,
        default=None,
        help="Single minimum mean difference (in percentage points) to consider "
        "for significance testing.",
    )
    es_group.add_argument(
        "--effect-sizes",
        type=float,
        nargs="+",
        default=None,
        help="Multiple effect sizes (in percentage points) to sweep over. "
        "Produces cross-summary tables mapping effect sizes to minimum "
        "benchmark sizes and vice versa.",
    )

    parser.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Significance level for the paired t-test. Default: 0.05",
    )
    parser.add_argument(
        "--shift-to-ensure-difference",
        action="store_true",
        default=False,
        help="If set, shift model B's values so that mean(A) + effect_size = "
        "mean(B_shifted), preserving B's variance. This tests whether the "
        "benchmark size has enough power to detect a difference of exactly "
        "effect_size, regardless of the actual observed difference. "
        "All model pairs are tested (no SKIP).",
    )
    parser.add_argument(
        "--bonferroni",
        action="store_true",
        default=False,
        help="If set, apply Bonferroni correction to the significance threshold "
        "to control family-wise error rate across all pairwise tests within "
        "each benchmark size.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="If provided, save tables as TSV files in this directory. "
        "Subdirectories are created to encode configuration.",
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="*",
        default=None,
        help="If provided, only analyze these sizes. Otherwise, analyze all.",
    )
    args = parser.parse_args()

    # Load all model results
    print(f"Loading results from: {args.results_dir}")
    models = load_model_results(args.results_dir)
    if not models:
        print("No model result files found. Exiting.")
        sys.exit(1)

    print(f"Loaded {len(models)} models: {', '.join(sorted(models.keys()))}")
    print(f"Significance level (alpha): {args.alpha}")
    if args.bonferroni:
        print(f"Bonferroni correction: ENABLED")
    if args.shift_to_ensure_difference:
        print(f"Mode: SHIFTED (power analysis)")
    else:
        print(f"Mode: STANDARD")

    # Determine sizes to analyze
    all_sizes = get_available_sizes(models)
    if args.sizes:
        sizes_to_analyze = [s for s in args.sizes if s in all_sizes]
        if not sizes_to_analyze:
            print(f"None of the requested sizes {args.sizes} found in data.")
            sys.exit(1)
    else:
        sizes_to_analyze = all_sizes

    # ── Sweep mode (multiple effect sizes) ────────────────────────────────
    if args.effect_sizes is not None:
        effect_sizes = sorted(args.effect_sizes)
        print(f"Effect sizes to sweep: {', '.join(f'{e}pp' for e in effect_sizes)}")
        print()

        if args.output_dir:
            output_path = build_output_dir(
                args.output_dir, None,
                args.shift_to_ensure_difference, args.bonferroni,
                is_sweep=True,
            )
            os.makedirs(output_path, exist_ok=True)
            print(f"Output directory: {output_path}")
        else:
            output_path = None

        run_sweep(
            models, sizes_to_analyze, effect_sizes,
            args.alpha, args.shift_to_ensure_difference, args.bonferroni,
            output_path,
        )
        return

    # ── Single effect size mode ───────────────────────────────────────────
    effect_size = args.effect_size
    print(f"Effect size threshold: {effect_size} pp")
    print()

    if args.output_dir:
        output_path = build_output_dir(
            args.output_dir, effect_size,
            args.shift_to_ensure_difference, args.bonferroni,
        )
        os.makedirs(output_path, exist_ok=True)
        print(f"Output directory: {output_path}")
        print()
    else:
        output_path = None

    summary_rows = run_single_effect_size(
        models, sizes_to_analyze, effect_size, args.alpha,
        args.shift_to_ensure_difference, args.bonferroni,
        output_path, verbose=True,
    )

    # Save and print summary
    if output_path and summary_rows:
        save_summary(output_path, summary_rows, effect_size,
                     args.alpha, args.shift_to_ensure_difference, args.bonferroni)

    print(f"{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print()
    print_single_summary(summary_rows, args.bonferroni)
    min_size = find_min_all_significant(summary_rows)
    print()
    if min_size is not None:
        print(f"  ► Minimum size where all pairs are significant: {min_size}")
    else:
        print(f"  ► No size has all tested pairs significant.")
    print()


if __name__ == "__main__":
    main()