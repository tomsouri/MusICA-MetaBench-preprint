# Copyright (C) 2026  Tomáš Sourada, Katia Vendrame, Jan Hajič, jr.
#
# This file is part of the MusICA MetaBench source code, licensed under
# the GNU General Public License v3.0 or later (SPDX: GPL-3.0-or-later).
# See the LICENSE-SOURCE-CODE file in the repository root for the full
# license text, or <https://www.gnu.org/licenses/>.

# =========================================================================
# Evaluation Stats Calculation
# =========================================================================
from typing import Dict, Tuple, List, Any
import os
import argparse
import csv
import datetime
import json
import sys
import time

from pathlib import Path

import requests
import yaml

def safe_float(val: Any) -> float:
    """Safely convert string log entries to float, returning 0.0 on failure/empty."""
    try:
        if val is None or val == "":
            return 0.0
        return float(val)
    except ValueError:
        return 0.0

def print_stat_line(name: str, total_items: int, correct_items: int, incorrect_items: int, unparsable_items: int, indent: int = 2, model_errors: int = 0, total_time: float = 0.0, total_price: float = 0.0):
    """Helper to format and print exactly mathematical statistics per criteria"""
    ind = " " * indent
    acc_percent = (correct_items / total_items * 100) if total_items > 0 else 0.0
    
    # Unparsable rate is explicitly (unparsable / incorrect)
    unp_percent = (unparsable_items / incorrect_items * 100) if incorrect_items > 0 else 0.0
    model_error_percent = (model_errors / incorrect_items * 100) if incorrect_items > 0 else 0.0
    
    print(f"{ind}- {name}:")
    print(f"{ind}    Items: {total_items}")
    print(f"{ind}    Accuracy: {acc_percent:.2f}% ({correct_items}/{total_items})")
    print(f"{ind}    Unparsable Rate (of incorrect items): {unp_percent:.2f}% ({unparsable_items}/{incorrect_items})")
    print(f"{ind}    Model Errors Rate (of incorrect items): {model_error_percent:.2f}% ({model_errors}/{incorrect_items})")
    print(f"{ind}    Time Taken: {total_time:.2f}s")
    print(f"{ind}    Price: ${total_price:.6f}")

def generate_stat_dict(model_name: str, crit_name: str, crit_value: str, total: int, correct: int, incorrect: int, unparsable: int, model_errors: int, total_time: float, total_price: float) -> dict:
    """Creates a flat dictionary for tabular TSV export."""
    acc_percent = (correct / total * 100) if total > 0 else 0.0
    unp_percent = (unparsable / incorrect * 100) if incorrect > 0 else 0.0
    model_error_percent = (model_errors / incorrect * 100) if incorrect > 0 else 0.0
    return {
        "Model": model_name,
        "Criterion_Type": crit_name,
        "Criterion_Value": crit_value,
        "Total_Items": total,
        "Correct_Items": correct,
        "Incorrect_Items": incorrect,
        "Unparsable_Items": unparsable,
        "Model_Error_Items": model_errors,
        "Accuracy_Percent": round(acc_percent, 2),
        "Unparsable_Percent": round(unp_percent, 2),
        "Model_Error_Percent": round(model_error_percent, 2),
        "Total_Time_s": round(total_time, 2),
        "Total_Price": round(total_price, 6)
    }

def evaluate_results(logs: List[Dict[str, Any]], criteria: List[str], output_tsvs: list[str] = []):
    """Processes full logs and calculates overall & partial accuracy/unparsable-rate per criteria."""
    print("\n" + "="*50)
    print("📈 EVALUATION STATISTICS")
    print("="*50)
    
    if not logs:
        print("No logs to evaluate.")
        return

    models = set(row.get("model", "UNKNOWN_MODEL") for row in logs)
    tabular_data = []
    
    for model in models:
        print(f"\n🚀 MODEL: {model}")
        print("-" * 40)
        model_logs = [row for row in logs if row.get("model") == model]
        
        # Overall
        total = len(model_logs)
        correct = sum(1 for r in model_logs if r.get("is_correct") is True)
        incorrect = total - correct
        unparsable = sum(1 for r in model_logs if r.get("is_correct") is False and r.get("label_of_answer", "") == "UNPARSABLE")
        model_error = sum(1 for r in model_logs if r.get("is_correct") is False and r.get("label_of_answer", "") == "MODEL_ERROR")
        
        # Calculate time and price across the entire model run
        total_time = sum(safe_float(r.get("time_taken")) for r in model_logs)
        total_price = sum(safe_float(r.get("price")) for r in model_logs)
        
        print_stat_line("OVERALL", total, correct, incorrect, unparsable, indent=0, model_errors=model_error, total_time=total_time, total_price=total_price)
        tabular_data.append(generate_stat_dict(model, "OVERALL", "ALL", total, correct, incorrect, unparsable, model_error, total_time, total_price))
        
        # Calculate per-criteria
        for criterion in criteria:
            print(f"\n  By Criterion: [{criterion}]")
            unique_vals = set(row.get(criterion, "N/A") for row in model_logs)
            
            for val in sorted(list(unique_vals)):
                val_logs = [row for row in model_logs if row.get(criterion) == val]
                v_total = len(val_logs)
                v_correct = sum(1 for r in val_logs if r.get("is_correct") is True)
                v_incorrect = v_total - v_correct
                v_unparsable = sum(1 for r in val_logs if r.get("is_correct") is False and r.get("label_of_answer", "") == "UNPARSABLE")
                v_model_error = sum(1 for r in val_logs if r.get("is_correct") is False and r.get("label_of_answer", "") == "MODEL_ERROR")
                
                # Calculate time and price specifically for this criterion slice
                v_time = sum(safe_float(r.get("time_taken")) for r in val_logs)
                v_price = sum(safe_float(r.get("price")) for r in val_logs)

                print_stat_line(f"{val}", v_total, v_correct, v_incorrect, v_unparsable, indent=4, model_errors=v_model_error, total_time=v_time, total_price=v_price)
                tabular_data.append(generate_stat_dict(model, criterion, val, v_total, v_correct, v_incorrect, v_unparsable, v_model_error, v_time, v_price))

    # Save to TSV Table
    if tabular_data:
        for output_tsv in output_tsvs:
            try:
                # os.makedirs(os.path.dirname(output_tsv), exist_ok=True)
                with open(output_tsv, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=tabular_data[0].keys(), delimiter='\t')
                    writer.writeheader()
                    writer.writerows(tabular_data)
                print(f"\n✓ Saved evaluation tabular stats to: {output_tsv}")
            except Exception as e:
                print(f"\n⚠ Could not save evaluation stats to {output_tsv}. Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Evaluate benchmark runs.")
    parser.add_argument('--run_uuids', nargs='+', required=True)
    parser.add_argument('--logdir', default="logs")
    parser.add_argument('--config', required=True, help="Path to config.yaml")
    parser.add_argument('--output', required=True, help="Path for output tsv")
    
    args = parser.parse_args()

    # 1. Load criteria from YAML
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
        criteria = config.get("evaluation_criteria", [])

    # 2. Find matching subdirectories and collect TSV data
    all_logs = []
    log_path = Path(args.logdir)
    
    if log_path.exists():
        # Iterate over subdirectories
        for subdir in [d for d in log_path.iterdir() if d.is_dir()]:
            # Check if any UUID is in the directory name
            if any(uuid in subdir.name for uuid in args.run_uuids):
                tsv_file = subdir / "benchmark_logs.tsv"
                
                if tsv_file.exists():
                    with open(tsv_file, mode='r', encoding='utf-8') as f:
                        reader = csv.DictReader(f, delimiter='\t')
                        
                        # Convert boolean-like strings properly for standard log reading
                        for row in reader:
                            # Ensuring is_correct is actually boolean typed if your script assumes so
                            raw_correct = row.get("is_correct", "")
                            if raw_correct.lower() == "true":
                                row["is_correct"] = True
                            elif raw_correct.lower() == "false":
                                row["is_correct"] = False
                            all_logs.append(row)

    # 3. Pass to evaluation function
    evaluate_results(all_logs, criteria, output_tsvs=[args.output])

if __name__ == "__main__":
    main()


# Example run:
# .venv/bin/python3 eval.py --config eval-config.yaml --output res.tsv --run_uuids 184930_068a164a-de63-4339-8b1a-df40377cdebb