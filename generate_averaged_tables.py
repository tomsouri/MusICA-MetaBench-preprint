"""
Generates TSV tables for the results of 10-times-experiments (10 different instances of the same-size benchmark):
- For each criterion (e.g., "ALL", "audio.mastermix.wav", etc.), it creates a table:
- rows = models;
- columns = benchmark sizes, 
- cell = "mean_acc (stddev)".
"""

import pandas as pd
import os
import glob
import argparse
import re

from utils import upload_tsv_to_gsheet, create_gsheet_tabs

def extract_numeric(size_str):
    """Extracts the numeric part of a size string for sorting (e.g., '10k' -> 10000)."""
    match = re.match(r"(\d+)", size_str)
    num = int(match.group(1)) if match else 0
    if 'k' in size_str.lower():
        num *= 1000
    if 'm' in size_str.lower():
        num *= 1000000
    return num

def process_benchmarks(root_dir, output_dir, target_criteria, config, filename="res.tsv"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    all_data = []
    search_path = os.path.join(root_dir, "*", "*", filename)
    
    for file_path in glob.glob(search_path):
        parts = file_path.split(os.sep)
        model_name = parts[-3]
        benchmark_size = parts[-2]
        
        df = pd.read_csv(file_path, sep='\t')
        df['model'] = model_name
        df['size'] = benchmark_size
        all_data.append(df)

    if not all_data:
        print("No files found.")
        return

    full_df = pd.concat(all_data, ignore_index=True)

    # in the full_df, find a column with the name "Mean_Accuracy ({integer} runs)", and a column with the name "StdDev_Accuracy ({integer} runs)". Use these to create a new column "display_val" with the format "mean (stddev)". This will be the value displayed in the final tables.
    # Find columns matching "Mean_Accuracy ({n} runs)" and "StdDev_Accuracy ({n} runs)"
    mean_cols = [c for c in full_df.columns if c.startswith("Mean_Accuracy")]
    std_cols = [c for c in full_df.columns if c.startswith("StdDev_Accuracy")]

    default_mean_col = "Mean_Accuracy (10 runs)"
    default_std_col = "StdDev_Accuracy (10 runs)"

    if default_mean_col not in full_df.columns or default_std_col not in full_df.columns:
        # Fallback for the case that it was not run for 10 runs.
        print(f"Expected columns '{default_mean_col}' and '{default_std_col}' not found. Available mean columns: {mean_cols}, stddev columns: {std_cols}, using the first ones found.")
        mean_col = mean_cols[0] if mean_cols else None
        std_col = std_cols[0] if std_cols else None
    else:
        mean_col = default_mean_col
        std_col = default_std_col
    
    print(f"Using mean column: {mean_col}, stddev column: {std_col}")

    full_df['display_val'] = (
        full_df[mean_col].apply(lambda x: f"{x:.2f}") + 
        " (" + full_df[std_col].apply(lambda x: f"{x:.2f}") + ")"
    )

    # 1. Custom sorting for sizes
    available_sizes = sorted(full_df['size'].unique(), key=extract_numeric)

    criteria_to_process = [c for c in target_criteria if c in full_df['Criterion_Value'].unique()]

    for criterion in criteria_to_process:
        subset = full_df[full_df['Criterion_Value'] == criterion]
        pivot_table = subset.pivot(index='model', columns='size', values='display_val')
        
        # Apply the sorted order to the columns
        pivot_table = pivot_table.reindex(columns=available_sizes)
        
        safe_name = criterion.replace(".", "_").replace(" ", "_")
        output_path = os.path.join(output_dir, f"table_{safe_name}.tsv")
        
        # 2. Export to TSV
        pivot_table.to_csv(output_path, sep='\t')
        print(f"Generated: {output_path}")
        upload_tsv_to_gsheet(config=config, tab_name=criterion, tsv_file=output_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate TSV benchmark tables.")
    parser.add_argument("--input_dir", default="averaged/", help="Path to the directory containing averaged data")
    parser.add_argument("--output_dir", default="tables/", help="Directory where TSV tables will be saved")
    parser.add_argument("--criteria", nargs='+', default=["ALL", "audio.mastermix.wav", "symbolic.musicxml", "visual.short.png"], 
                        help="List of Criterion_Values to generate tables for (e.g., ALL submodality)")
    parser.add_argument("--gsheet_id_to_upload", type=str, default=None,
                        help="Google Sheet ID to upload results to")
    parser.add_argument("--gspread_credentials_location", type=str, default="logs/protobenchmark-logging-aa9418338494.json",
                        help="Path to gspread credentials JSON file")
    parser.add_argument("--results_filename", type=str, default=None, choices=[None, "normal.tsv", "text-only.tsv"],
                        help="From which files take the input results?")
    
    args = parser.parse_args()

    sheet_ids_to_upload = {
        "normal.tsv": "1QDJj7BP074IjWv9jAzjWHT4a2bjWCqtqbTeZJ6jWVPA",
        "text-only.tsv": "1U0D2MLGffnxcHTe-WPWpUCXnRIdo4dlmnFyHWyePNGQ"
    }  

    if args.results_filename is None:
        for filename in ["normal.tsv", "text-only.tsv"]:
            args.results_filename = filename
            args.gsheet_id_to_upload = sheet_ids_to_upload[filename]
            config = {
                'credentials_location': args.gspread_credentials_location,
                'sheet_id': args.gsheet_id_to_upload
            }
            process_benchmarks(args.input_dir, args.output_dir, args.criteria, config, filename=args.results_filename)





