import os
import csv
import itertools
import fnmatch
import argparse


import pandas as pd
import numpy as np
import sys
from typing import List

from compare_benchmark_files import discover_tsv_files_from_patterns

# def aggregate_experiment_results(file_paths: List[str], identity_cols, outfile: str):
#     """
#     Aggregates multiple TSV experiment runs, verifies consistency across 
#     Model and Criterion columns, and computes Mean/StdDev for Accuracy_Percent.
#     """
#     if not file_paths:
#         print("No files provided.")
#         return

#     dataframes = []
    
#     target_col = "Accuracy_Percent"

#     try:
#         for path in file_paths:
#             df = pd.read_csv(path, sep='\t')
#             dataframes.append(df)

#         # 1. Check consistency across files
#         reference_df = dataframes[0][identity_cols]
#         for i, df in enumerate(dataframes[1:], start=1):
#             if not reference_df.equals(df[identity_cols]):
#                 raise ValueError(f"Consistency check failed: File '{file_paths[i]}' "
#                                  f"does not match the structure/values of the first file.")

#         # 2. Extract values for computation
#         # We stack the 'Accuracy_Percent' columns from all dataframes
#         all_accuracies = pd.concat([df[target_col] for df in dataframes], axis=1)

#         # 3. Compute Mean and StdDev
#         # ddof=1 for sample standard deviation
#         means = all_accuracies.mean(axis=1)
#         stds = all_accuracies.std(axis=1, ddof=1)

#         # 4. Prepare Output DataFrame
#         # We take the metadata from the first file and attach the results
#         output_df = dataframes[0].copy()
        
#         # We can drop the original Accuracy_Percent and replace it with Mean and Std
#         output_df.drop(columns=[target_col], inplace=True)
#         output_df["Mean_Accuracy"] = means.round(4)
#         output_df["StdDev_Accuracy"] = stds.round(4)

#         # 5. Print output as TSV
#         # Using sys.stdout to print directly to the terminal/console
#         with open(outfile, "w") as f:
#             f.write(output_df.to_csv(sep='\t', index=False))

#     except Exception as e:
#         print(f"Error processing files: {e}", file=sys.stderr)



def aggregate_experiment_results(file_paths: List[str], identity_cols, outfile: str):
    dataframes = []
    target_col = "Accuracy_Percent"

    try:
        for path in file_paths:
            # We use sep=None with engine='python' to automatically detect 
            # if the file is truly Tab or Comma separated
            df = pd.read_csv(path, sep=None, engine='python')
            
            # Clean column names (remove whitespace/hidden characters)
            df.columns = [c.strip() for c in df.columns]
            dataframes.append(df)

        # Validate that all required columns exist in the first file
        first_df_cols = dataframes[0].columns
        for col in identity_cols + [target_col]:
            if col not in first_df_cols:
                available = ", ".join(list(first_df_cols))
                raise KeyError(f"Column '{col}' not found. Available columns: [{available}]")

        # 1. Check consistency across all files
        # We ensure they have the same metadata rows in the same order
        reference_identity = dataframes[0][identity_cols]
        for i, df in enumerate(dataframes[1:], start=1):
            if not reference_identity.equals(df[identity_cols]):
                raise ValueError(f"Consistency check failed: Row values in {identity_cols} "
                                 f"in file '{file_paths[i]}' do not match the first file.")

        # 2. Extract values and compute statistics
        # Concatenate only the Accuracy_Percent column from all files side-by-side
        all_accuracies = pd.concat([df[target_col] for df in dataframes], axis=1)

        # Math: Mean (μ) and Sample StdDev (s)
        # Using ddof=1 for the unbiased estimator
        means = all_accuracies.mean(axis=1)
        stds = all_accuracies.std(axis=1, ddof=1)

        # 3. Build result DataFrame
        # Keep everything except the original accuracy column
        # result_df = dataframes[0].drop(columns=[target_col])

        # Select ONLY the identity columns from the first dataframe
        result_df = dataframes[0][identity_cols].copy()

        result_df["Mean_Accuracy"] = means.round(4)
        result_df["StdDev_Accuracy"] = stds.round(4)

        # 4. Final Output
        # Re-ordering columns to put stats next to where Accuracy was
        with open(outfile, "w") as f:
            f.write(result_df.to_csv(sep='\t', index=False))
        
        print(f"Written the aggregated results to {outfile}.")

    except Exception as e:
        print(f"Error processing files: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Calculate overlap stats between TSV files matching specific patterns.")
    
    # Path arguments
    parser.add_argument("--root_path", type=str, default="logs/", 
                        help="The base directory to search in (default: logs/)")
    
    # Pattern arguments
    parser.add_argument("--dir_pattern", type=str,
                        help="Unix-like pattern for subdirectories (e.g., 'batch_*')")
    parser.add_argument("--file_pattern", type=str, default="results.tsv",
                        help="Unix-like pattern for files (e.g., 'results.tsv')")
    
    # Comparison arguments
    parser.add_argument("--identity_columns", nargs='+', 
                        default=['Model', 'Criterion_Type', 'Criterion_Value'],
                        help="List of column names to compare (space separated)")
    
    # Explicit List Mode Argument
    parser.add_argument("--list_of_tsvs", nargs='+', 
                        help="Explicit list of TSV file paths to compare. Overrides discovery mode.")
    parser.add_argument("--output_file", type=str, required=True,
                        help="Path to output file")

    args = parser.parse_args()

    target_files = []

    # 1. File Selection Logic
    if args.list_of_tsvs:
        # Use explicitly provided files
        target_files = args.list_of_tsvs
        print(f"Using {len(target_files)} provided files.")
    else:
        # Use Discovery Mode (ensure patterns are provided)
        if not args.dir_pattern or not args.file_pattern:
            parser.error("Either --list_of_tsvs OR both --dir_pattern and --file_pattern must be provided.")

        target_files = discover_tsv_files_from_patterns(root_path=args.root_path, dir_pattern=args.dir_pattern, file_pattern=args.file_pattern)


    aggregate_experiment_results(target_files, args.identity_columns, args.output_file)


# .venv/bin/python3 compute_mean_stddev.py --dir_pattern "run_2026-03-17_2*rs*" --file_pattern "results.tsv" --output_file "a.tsv" --root_path "logs/"

if __name__ == "__main__":
    main()