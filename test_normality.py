import os
import argparse
import pandas as pd
import numpy as np
from scipy import stats
import sys

def test_normality(file_path, alpha=0.05, output_file=None):
    def log(message):
        if output_file:
            output_file.write(message + "\n")
        else:
            print(message)

    log(f"Testing normality for: {os.path.basename(file_path)}")
    try:
        # Load the TSV file
        df = pd.read_csv(file_path, sep='\t')
        
        # The first column is 'benchmark_size', the rest are seeds (10 of them)
        # We want to test the distribution of the 10 accuracy numbers in each row.
        
        # Iterate over each row
        results = []
        for index, row in df.iterrows():
            benchmark_size = row['benchmark_size']
            # Get the 10 accuracy numbers (assuming they start from the second column)
            data = row.iloc[1:].values
            
            # Perform Shapiro-Wilk test
            # The Shapiro-Wilk test tests the null hypothesis that the data was drawn from a normal distribution.
            stat, p_value = stats.shapiro(data)
            
            # If p-value > alpha, we fail to reject the null hypothesis (assume normal distribution)
            is_normal = p_value > alpha
            
            results.append({
                'benchmark_size': benchmark_size,
                'stat': stat,
                'p_value': p_value,
                'alpha': alpha,
                'is_normal': is_normal
            })
            
            status = "PASS" if is_normal else "FAIL"
            log(f"  Size {benchmark_size:3}: p-value = {p_value:.4f} (alpha={alpha:.5f}) -> {status}")
            
        return results
    except Exception as e:
        log(f"  Error processing {file_path}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Test normality of aggregated results using Shapiro-Wilk test.')
    parser.add_argument('setup', help='The setup to process (e.g., normal, text-only, white-noise)')
    parser.add_argument('--base_dir', default='aggregated/10-times-runs', help='Base directory for aggregated results')
    parser.add_argument('--bonferroni', action='store_true', help='Apply Bonferroni correction to alpha')
    parser.add_argument('--output_dir', default="aggregated/pairwise-significance/normality-tests/",help='File to write detailed results to')
    parser.add_argument('--pool_and_normalize_first', action='store_true', help='Normalize each row and pool all values for a single normality test')
    
    args = parser.parse_args()
    
    setup_dir = os.path.join(args.base_dir, args.setup)
    output_file = os.path.join(args.output_dir, f"{args.setup}_normality_results.txt")
    
    if not os.path.isdir(setup_dir):
        print(f"Error: Setup directory not found: {setup_dir}")
        sys.exit(1)
        
    files = sorted([f for f in os.listdir(setup_dir) if f.endswith('.tsv')])
    
    if not files:
        print(f"No TSV files found in {setup_dir}")
        return

    # Phase 1: Count total tests for Bonferroni
    total_tests = 0
    all_files_data = []
    for file_name in files:
        file_path = os.path.join(setup_dir, file_name)
        try:
            df = pd.read_csv(file_path, sep='\t')
            total_tests += len(df)
            all_files_data.append((file_path, df))
        except Exception as e:
            print(f"Warning: Could not read {file_name} for counting: {e}")

    alpha = 0.05
    if args.bonferroni and total_tests > 0:
        alpha = 0.05 / total_tests

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Open output file if specified
    out_f = open(output_file, 'w') if output_file else None
    
    def log_both(message):
        if out_f:
            out_f.write(message + "\n")
        print(message)

    if args.pool_and_normalize_first:
        log_both("Mode: Pooling and normalizing all data first.")
        standardized = []
        for file_path, df in all_files_data:
            for index, row in df.iterrows():
                experiment = row.iloc[1:].values.astype(float)
                # Check for zero variance to avoid division by zero
                if np.std(experiment) == 0:
                    continue
                z = (experiment - np.mean(experiment)) / np.std(experiment, ddof=1)
                standardized.extend(z)
        
        if not standardized:
            print("Error: No data to process.")
            if out_f: out_f.close()
            sys.exit(1)

        stat, p_value = stats.shapiro(standardized)
        is_normal = p_value > alpha
        
        summary = (
            f"\nPOOLED NORMALITY TEST RESULTS\n"
            f"Total samples: {len(standardized)}\n"
            f"Total experiments (rows) pooled: {len(standardized)//10}\n"
            f"Shapiro-Wilk Statistic: {stat:.4f}\n"
            f"p-value: {p_value:.4f} (alpha={alpha:.5f})\n"
            f"Result: {'PASS (Normal)' if is_normal else 'FAIL (Not Normal)'}"
        )
        log_both(summary)
        if out_f: out_f.close()
        return

    if args.bonferroni and total_tests > 0:
        log_both(f"Applying Bonferroni correction: total_tests = {total_tests}, adjusted alpha = {alpha:.5f}")
    else:
        log_both(f"Using standard alpha = {0.05}")

    if out_f:
        out_f.write("-" * 40 + "\n")
    else:
        print("-" * 40)

    # Phase 2: Run tests and collect stats
    total_passed = 0
    total_failed = 0

    for file_path, df in all_files_data:
        file_results = test_normality(file_path, alpha=alpha, output_file=out_f)
        if file_results:
            for res in file_results:
                if res['is_normal']:
                    total_passed += 1
                else:
                    total_failed += 1
        if out_f:
            out_f.write("-" * 40 + "\n")
        else:
            print("-" * 40)

    # Final Summary
    summary = (
        f"\nOVERALL RESULTS\n"
        f"Total tests performed: {total_tests}\n"
        f"Normalities NOT REJECTED (PASS): {total_passed}\n"
        f"Normalities REJECTED (FAIL):     {total_failed}"
    )
    
    if out_f:
        out_f.write(summary + "\n")
        out_f.close()
        print(f"Detailed results written to {output_file}")

    print(summary)

if __name__ == "__main__":
    main()
