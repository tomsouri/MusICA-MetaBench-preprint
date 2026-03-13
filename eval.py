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


import requests
import yaml

def print_stat_line(name: str, total_items: int, correct_items: int, incorrect_items: int, unparsable_items: int, indent: int = 2):
    """Helper to format and print exactly mathematical statistics per criteria"""
    ind = " " * indent
    acc_percent = (correct_items / total_items * 100) if total_items > 0 else 0.0
    
    # Unparsable rate is explicitly (unparsable / incorrect)
    unp_percent = (unparsable_items / incorrect_items * 100) if incorrect_items > 0 else 0.0
    
    print(f"{ind}- {name}:")
    print(f"{ind}    Items: {total_items}")
    print(f"{ind}    Accuracy: {acc_percent:.2f}% ({correct_items}/{total_items})")
    print(f"{ind}    Unparsable Rate (of incorrect items): {unp_percent:.2f}% ({unparsable_items}/{incorrect_items})")

# def evaluate_results(logs: List[Dict[str, Any]], criteria: List[str]):
#     """Processes full logs and calculates overall & partial accuracy/unparsable-rate per criteria."""
#     print("\n" + "="*50)
#     print("📈 EVALUATION STATISTICS")
#     print("="*50)
    
#     if not logs:
#         print("No logs to evaluate.")
#         return

#     # Group records by model
#     models = set(row.get("model", "UNKNOWN_MODEL") for row in logs)
    
#     for model in models:
#         print(f"\n🚀 MODEL: {model}")
#         print("-" * 40)
#         model_logs = [row for row in logs if row.get("model") == model]
        
#         total = len(model_logs)
#         correct = sum(1 for r in model_logs if r.get("is_correct") is True)
#         incorrect = total - correct
#         unparsable = sum(1 for r in model_logs if r.get("is_correct") is False and r.get("label_of_answer", "") == "UNPARSABLE")
        
#         print_stat_line("OVERALL", total, correct, incorrect, unparsable, indent=0)
        
#         # Calculate per-criteria
#         for criterion in criteria:
#             print(f"\n  By Criterion: [{criterion}]")
#             # Discover unique values in this column
#             unique_vals = set(row.get(criterion, "N/A") for row in model_logs)
            
#             for val in sorted(list(unique_vals)):
#                 val_logs = [row for row in model_logs if row.get(criterion) == val]
#                 v_total = len(val_logs)
#                 v_correct = sum(1 for r in val_logs if r.get("is_correct") is True)
#                 v_incorrect = v_total - v_correct
#                 v_unparsable = sum(1 for r in val_logs if r.get("is_correct") is False and r.get("label_of_answer", "") == "UNPARSABLE")
                
#                 print_stat_line(f"{val}", v_total, v_correct, v_incorrect, v_unparsable, indent=4)


def generate_stat_dict(model_name: str, crit_name: str, crit_value: str, total: int, correct: int, incorrect: int, unparsable: int) -> dict:
    """Creates a flat dictionary for tabular TSV export."""
    acc_percent = (correct / total * 100) if total > 0 else 0.0
    unp_percent = (unparsable / incorrect * 100) if incorrect > 0 else 0.0
    return {
        "Model": model_name,
        "Criterion_Type": crit_name,
        "Criterion_Value": crit_value,
        "Total_Items": total,
        "Correct_Items": correct,
        "Incorrect_Items": incorrect,
        "Unparsable_Items": unparsable,
        "Accuracy_Percent": round(acc_percent, 2),
        "Unparsable_Percent": round(unp_percent, 2)
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
        
        print_stat_line("OVERALL", total, correct, incorrect, unparsable, indent=0)
        tabular_data.append(generate_stat_dict(model, "OVERALL", "ALL", total, correct, incorrect, unparsable))
        
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
                
                print_stat_line(f"{val}", v_total, v_correct, v_incorrect, v_unparsable, indent=4)
                tabular_data.append(generate_stat_dict(model, criterion, val, v_total, v_correct, v_incorrect, v_unparsable))

    # Save to TSV Table
    # if output_tsv and tabular_data:
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
