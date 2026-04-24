#!/usr/bin/env python3
"""
Generate comparison plots from a results TSV file.
Produces 4 plots: OVERALL, and one per submodality (audio, symbolic, visual).
"""

import argparse
import csv
import sys
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate accuracy comparison plots from a results TSV file."
    )
    parser.add_argument("input_tsv", help="Path to the input TSV file.")
    parser.add_argument(
        "--output-prefix",
        default="plot",
        help="Prefix for output PNG files (default: 'plot').",
    )
    parser.add_argument(
        "--dpi", type=int, default=150, help="DPI for output images (default: 150)."
    )
    return parser.parse_args()


def load_data(tsv_path):
    """Load the TSV and return header + all rows as list of dicts."""
    with open(tsv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)
        columns = reader.fieldnames
    return columns, rows


def extract_model_setups(columns):
    """
    From column names, extract (model_base, setup) pairs.
    The setup is the last token after the final '_' and must be one of
    {normal, text-only, white-noise}.  Everything before that is the model base name.
    """
    setups_of_interest = {"normal", "text-only", "white-noise"}
    # columns that are not metadata
    meta_cols = {"Criterion_Type", "Criterion_Value", "Total_Items"}

    model_map = {}  # column_name -> (model_base, setup)
    models = defaultdict(dict)  # model_base -> {setup: column_name}

    for col in columns:
        if col in meta_cols:
            continue
        # Find setup suffix
        for setup in setups_of_interest:
            if col.endswith("_" + setup):
                base = col[: -(len(setup) + 1)]
                model_map[col] = (base, setup)
                models[base][setup] = col
                break

    return models, model_map


def get_row_value(row, col):
    """Safely get a float value from a row, returning None if missing."""
    val = row.get(col)
    if val is None or val == "":
        return None
    try:
        return float(val)
    except ValueError:
        return None


def make_plot(
    title,
    accuracy_dict,
    models,
    output_path,
    dpi=150,
):
    """
    accuracy_dict: {column_name: float} for the row we care about
    models: {model_base: {setup: column_name}}

    Steps:
      1. Separate models into "complete" (all 3 setups) and "incomplete".
      2. Build aggregate bars (average over all models that have a given setup).
      3. Order: aggregate group | complete models | incomplete models (right).
    """
    SETUPS = ["normal", "text-only", "white-noise"]
    COLORS = {
        "normal": "#D62828",       # red
        "text-only": "#1D3557",    # blue
        "white-noise": "#E07BE0",  # pink
    }
    LABELS = {
        "normal": "Normal (audio)",
        "text-only": "Text-only",
        "white-noise": "White-noise",
    }

    # ---- Classify models ----
    complete_models = {}
    incomplete_models = {}
    for base, setup_map in models.items():
        # Check which setups actually have data in this row
        available = {
            s for s in SETUPS if s in setup_map and get_row_value(accuracy_dict, setup_map[s]) is not None
        }
        if available == set(SETUPS):
            complete_models[base] = setup_map
        elif len(available) > 0:
            incomplete_models[base] = setup_map

    # Sort by normal accuracy descending (complete), then alphabetically (incomplete)
    def sort_key_complete(item):
        base, sm = item
        val = get_row_value(accuracy_dict, sm.get("normal", ""))
        return -(val if val is not None else 0)

    def sort_key_incomplete(item):
        base, sm = item
        # Sort by the maximum available accuracy descending
        vals = [
            get_row_value(accuracy_dict, sm[s])
            for s in SETUPS
            if s in sm and get_row_value(accuracy_dict, sm[s]) is not None
        ]
        return -(max(vals) if vals else 0)

    complete_sorted = sorted(complete_models.items(), key=sort_key_complete)
    incomplete_sorted = sorted(incomplete_models.items(), key=sort_key_incomplete)

    # ---- Compute aggregates ----
    agg = {}
    for setup in SETUPS:
        vals = []
        for base, sm in models.items():
            if setup in sm:
                v = get_row_value(accuracy_dict, sm[setup])
                if v is not None:
                    vals.append(v)
        agg[setup] = np.mean(vals) if vals else None

    # ---- Build bar groups ----
    # Each group: (label, {setup: value})
    groups = []

    # 1) Aggregate
    groups.append(("Aggregate\n(all models)", agg))

    # 2) Complete models
    for base, sm in complete_sorted:
        vals = {s: get_row_value(accuracy_dict, sm[s]) for s in SETUPS}
        label = shorten_name(base)
        groups.append((label, vals))

    # 3) Incomplete models
    for base, sm in incomplete_sorted:
        vals = {}
        for s in SETUPS:
            if s in sm:
                vals[s] = get_row_value(accuracy_dict, sm[s])
        label = shorten_name(base)
        groups.append((label, vals))

    n_complete = len(complete_sorted)
    n_incomplete = len(incomplete_sorted)

    # ---- Plotting ----
    n_groups = len(groups)
    bar_width = 0.22
    group_width = bar_width * len(SETUPS) + 0.10  # small internal padding

    fig, ax = plt.subplots(figsize=(max(14, n_groups * 1.6), 7))

    # X positions for group centers
    x_positions = []
    current_x = 0
    for i in range(n_groups):
        x_positions.append(current_x)
        # Add extra gap after aggregate and before incomplete section
        if i == 0:
            current_x += group_width + 0.45  # gap after aggregate
        elif i == n_complete:  # after last complete, before incomplete
            current_x += group_width + 0.45
        else:
            current_x += group_width + 0.15

    # Draw bars
    for i, (label, vals) in enumerate(groups):
        cx = x_positions[i]
        for j, setup in enumerate(SETUPS):
            bx = cx + (j - 1) * bar_width
            v = vals.get(setup)
            if v is not None:
                bar = ax.bar(
                    bx,
                    v,
                    width=bar_width * 0.9,
                    color=COLORS[setup],
                    edgecolor="white",
                    linewidth=0.5,
                )
                # Value label on top
                fontsize = 6.5 if n_groups > 10 else 7.5
                ax.text(
                    bx,
                    v + 0.8,
                    f"{v:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=fontsize,
                    rotation=90,
                )

    # X-axis labels
    ax.set_xticks(x_positions)
    ax.set_xticklabels(
        [g[0] for g in groups], rotation=35, ha="right", fontsize=8
    )

    # Separator lines
    if n_complete > 0:
        sep_x = (x_positions[0] + x_positions[1]) / 2
        ax.axvline(sep_x, color="grey", linewidth=0.8, linestyle="--", alpha=0.5)
    if n_incomplete > 0 and n_complete > 0:
        idx_sep = 1 + n_complete
        if idx_sep < n_groups:
            sep_x = (x_positions[idx_sep - 1] + x_positions[idx_sep]) / 2
            ax.axvline(sep_x, color="grey", linewidth=0.8, linestyle="--", alpha=0.5)

    # Baseline
    ax.axhline(20, color="black", linewidth=1.2, linestyle=":", label="Random baseline (20%)")

    # Axis formatting
    ax.set_ylim(0, 105)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(10))
    ax.set_ylabel("Accuracy (%)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    # Legend
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor=COLORS[s], label=LABELS[s]) for s in SETUPS
    ] + [
        plt.Line2D([0], [0], color="black", linewidth=1.2, linestyle=":", label="Random baseline (20%)")
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=9, framealpha=0.9)

    # Section annotations
    # "Aggregate" on the left, "All 3 setups" in the middle, "Partial setups" on the right
    y_ann = 102
    if n_complete > 0 and n_incomplete > 0:
        ax.text(x_positions[0], y_ann, "◄ Aggregate", ha="center", fontsize=7, color="grey")
        mid_c = (x_positions[1] + x_positions[n_complete]) / 2
        ax.text(mid_c, y_ann, "— All 3 setups —", ha="center", fontsize=7, color="grey")
        mid_i = (x_positions[1 + n_complete] + x_positions[-1]) / 2
        ax.text(mid_i, y_ann, "— Partial setups →", ha="center", fontsize=7, color="grey")
    elif n_complete > 0:
        ax.text(x_positions[0], y_ann, "◄ Aggregate", ha="center", fontsize=7, color="grey")
        mid_c = (x_positions[1] + x_positions[-1]) / 2
        ax.text(mid_c, y_ann, "— All 3 setups —", ha="center", fontsize=7, color="grey")

    plt.tight_layout()
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ Saved: {output_path}")


def shorten_name(base):
    """Shorten model base names for readability on the x-axis."""
    # Replace common prefixes
    name = base
    replacements = [
        ("google_", ""),
        ("Qwen_", ""),
        ("meta-llama_", ""),
        ("deepseek_", ""),
        ("aggregate-", "agg-"),
    ]
    for old, new in replacements:
        name = name.replace(old, new)
    # Wrap long names
    if len(name) > 25:
        # Try to break at a hyphen or underscore near the middle
        mid = len(name) // 2
        for offset in range(10):
            for pos in [mid + offset, mid - offset]:
                if 0 < pos < len(name) and name[pos] in "-_":
                    name = name[:pos] + "\n" + name[pos:]
                    return name
        name = name[:mid] + "\n" + name[mid:]
    return name


def main():
    args = parse_args()
    columns, rows = load_data(args.input_tsv)
    models, model_map = extract_model_setups(columns)

    print(f"Loaded {len(rows)} rows, {len(models)} distinct model bases.")
    print(f"Model bases: {list(models.keys())}\n")

    # ---- Identify the rows we need ----
    # 1) OVERALL row: Criterion_Type == "OVERALL"
    # 2) submodality rows: Criterion_Type == "submodality"
    target_rows = {}
    for row in rows:
        ctype = row.get("Criterion_Type", "")
        cval = row.get("Criterion_Value", "")
        if ctype == "OVERALL":
            target_rows["OVERALL"] = row
        elif ctype == "submodality":
            target_rows[f"submodality: {cval}"] = row

    if not target_rows:
        print("ERROR: Could not find OVERALL or submodality rows.", file=sys.stderr)
        sys.exit(1)

    # ---- Generate plots ----
    for label, row in sorted(target_rows.items()):
        # Build accuracy_dict from this row
        accuracy_dict = {}
        for col in columns:
            if col in {"Criterion_Type", "Criterion_Value", "Total_Items"}:
                continue
            accuracy_dict[col] = row.get(col)

        safe_label = label.replace(" ", "_").replace(":", "").replace("/", "-")
        output_path = f"{args.output_prefix}_{safe_label}.png"

        total = row.get("Total_Items", "?")
        plot_title = f"Model Accuracy — {label}  (N = {total})"
        print(f"Generating plot: {plot_title}")
        make_plot(plot_title, accuracy_dict, models, output_path, dpi=args.dpi)

    print("\nDone!")


if __name__ == "__main__":
    main()
