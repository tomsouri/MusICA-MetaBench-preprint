#!/usr/bin/env python3
"""
Run:
.venv/bin/python3 extract_results.py --all

Extract and aggregate benchmark results from a nested directory structure.

Directory structure expected:
results/<model-name>/<benchmark-size>/<setup>/jobid_<jobid>.rs<seed>.rep1.res.tsv

Output: One TSV file per model-setup combination with benchmark sizes as rows
and seeds as columns.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
import pandas as pd
from collections import defaultdict
import argparse

# Predefined seeds (adjust if needed)
DEFAULT_SEEDS = [42,43,44,45,46,47,48,49,50,51]

# Predefined models and setups (modify as needed)
DEFAULT_MODELS = [
	"aggregate-gpt-4o",
	"aggregate-mistral",
	"google_gemini-2.0-flash-lite-001",
	"google_gemini-2.5-flash-lite",
	"google_gemini-3.1-flash-lite-preview",
	"Qwen_Qwen3-Omni-30B-A3B-Thinking",
]

DEFAULT_SETUPS = [
    "normal",
    "text-only",
    "white-noise"
]


def parse_filename(filename: str) -> Optional[Tuple[Union[int, str], int]]:
    """
    Parse filename to extract jobid and seed.
    
    Expected format: jobid_<jobid>.rs<seed>.rep1.res.tsv
    where <jobid> can be a number or "local"
    
    Returns:
        Tuple of (jobid, seed) where jobid is int or "local", or None if parsing fails
    """
    pattern = r'jobid_(\d+|local)\.rs(\d+)\.rep1\.res\.tsv'
    match = re.match(pattern, filename)
    if match:
        jobid_str = match.group(1)
        jobid = int(jobid_str) if jobid_str != "local" else "local"
        seed = int(match.group(2))
        return (jobid, seed)
    return None


def compare_jobids(jobid1: Union[int, str], jobid2: Union[int, str]) -> int:
    """
    Compare two jobids. Returns positive if jobid1 > jobid2, negative if jobid1 < jobid2, 0 if equal.
    
    Rules:
    - Numeric jobids are compared numerically
    - "local" is considered less than any numeric jobid
    - If both are "local", they are equal
    """
    if jobid1 == "local" and jobid2 == "local":
        return 0
    elif jobid1 == "local":
        return -1
    elif jobid2 == "local":
        return 1
    else:
        return jobid1 - jobid2


def extract_numeric_prefix(benchmark_size: str) -> Tuple[float, str]:
    """
    Extract numeric prefix from benchmark size for sorting.
    
    Args:
        benchmark_size: String like "100", "1000", "10k", "1.5M", etc.
    
    Returns:
        Tuple of (numeric_value, original_string) for sorting
    """
    # Try to extract a number from the beginning
    match = re.match(r'^(\d+\.?\d*)\s*([kKmMgGtT]?)', benchmark_size)
    if match:
        number = float(match.group(1))
        suffix = match.group(2).upper()
        
        # Apply multipliers for suffixes
        multipliers = {
            'K': 1e3,
            'M': 1e6,
            'G': 1e9,
            'T': 1e12,
        }
        
        if suffix in multipliers:
            number *= multipliers[suffix]
        
        return (number, benchmark_size)
    
    # If no number found, try to convert the whole string to a number
    try:
        return (float(benchmark_size), benchmark_size)
    except ValueError:
        # If all else fails, return a very large number to sort non-numeric values at the end
        return (float('inf'), benchmark_size)


def extract_accuracy(file_path: Path) -> Optional[float]:
    """
    Extract Accuracy_Percent value from TSV file where Criterion_Type is 'OVERALL'.
    
    Args:
        file_path: Path to the TSV file
        
    Returns:
        Accuracy percentage as float or None if not found
    """
    try:
        df = pd.read_csv(file_path, sep='\t')
        
        # Check if required columns exist
        if 'Criterion_Type' not in df.columns or 'Accuracy_Percent' not in df.columns:
            print(f"Warning: Required columns not found in {file_path}", file=sys.stderr)
            return None
        
        # Filter for OVERALL row
        overall_row = df[df['Criterion_Type'] == 'OVERALL']
        
        if overall_row.empty:
            print(f"Warning: No OVERALL row found in {file_path}", file=sys.stderr)
            return None
        
        if len(overall_row) > 1:
            print(f"Warning: Multiple OVERALL rows found in {file_path}, using first", file=sys.stderr)
        
        accuracy = overall_row.iloc[0]['Accuracy_Percent']
        return float(accuracy)
    
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return None


def scan_results_directory(
    results_dir: Path,
    model: str,
    setup: str
) -> Dict[str, Dict[int, Tuple[Union[int, str], Path]]]:
    """
    Scan the results directory for a given model and setup.
    
    Returns:
        Dictionary mapping benchmark_size -> seed -> (jobid, file_path)
    """
    model_setup_dir = results_dir / model
    
    if not model_setup_dir.exists():
        print(f"Warning: Model directory not found: {model_setup_dir}", file=sys.stderr)
        return {}
    
    results = defaultdict(dict)
    
    # Iterate through benchmark sizes
    for benchmark_dir in model_setup_dir.iterdir():
        if not benchmark_dir.is_dir():
            continue
        
        benchmark_size = benchmark_dir.name
        setup_dir = benchmark_dir / setup
        
        if not setup_dir.exists():
            continue
        
        # Iterate through result files
        for result_file in setup_dir.glob("jobid_*.rs*.rep1.res.tsv"):
            parsed = parse_filename(result_file.name)
            
            if parsed is None:
                print(f"Warning: Could not parse filename: {result_file}", file=sys.stderr)
                continue
            
            jobid, seed = parsed
            
            # Check if we already have a result for this seed
            if seed in results[benchmark_size]:
                existing_jobid, existing_path = results[benchmark_size][seed]
                comparison = compare_jobids(jobid, existing_jobid)
                
                if comparison > 0:
                    print(f"Warning: Multiple files for {model}/{benchmark_size}/{setup}/seed{seed}. "
                          f"Using jobid {jobid} over {existing_jobid}", file=sys.stderr)
                    results[benchmark_size][seed] = (jobid, result_file)
                else:
                    print(f"Warning: Multiple files for {model}/{benchmark_size}/{setup}/seed{seed}. "
                          f"Keeping jobid {existing_jobid} over {jobid}", file=sys.stderr)
            else:
                results[benchmark_size][seed] = (jobid, result_file)
    
    return results


def create_aggregated_tsv(
    results_dir: Path,
    model: str,
    setup: str,
    seeds: List[int],
    output_file: Optional[Path] = None
) -> Optional[pd.DataFrame]:
    """
    Create aggregated TSV file for a model-setup combination.
    
    Args:
        results_dir: Path to results directory
        model: Model name
        setup: Setup name
        seeds: List of expected seeds
        output_file: Optional output file path. If None, auto-generate
        
    Returns:
        DataFrame with aggregated results or None if no data found
    """
    # Scan directory
    results = scan_results_directory(results_dir, model, setup)
    
    if not results:
        print(f"No results found for model={model}, setup={setup}", file=sys.stderr)
        return None
    
    # Build the aggregated dataframe
    rows = []
    
    # Sort benchmark sizes numerically
    sorted_benchmark_sizes = sorted(results.keys(), key=extract_numeric_prefix)
    
    for benchmark_size in sorted_benchmark_sizes:
        row = {'benchmark_size': benchmark_size}

        some_seed_missing = False
        
        for seed in seeds:
            col_name = f'seed_{seed}'
            
            if seed in results[benchmark_size]:
                jobid, file_path = results[benchmark_size][seed]
                accuracy = extract_accuracy(file_path)
                row[col_name] = accuracy
            else:
                print(f"Warning: Missing data for {model}/{benchmark_size}/{setup}/seed{seed}", 
                      file=sys.stderr)
                row[col_name] = None
                some_seed_missing = True

        if not some_seed_missing:
            rows.append(row)
        else:
            print(f"Skipping benchmark_size={benchmark_size} for model={model}, setup={setup} due to missing seeds", 
                  file=sys.stderr)
    
    if not rows:
        print(f"No data extracted for model={model}, setup={setup}", file=sys.stderr)
        return None
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Reorder columns: benchmark_size first, then seeds in order
    column_order = ['benchmark_size'] + [f'seed_{seed}' for seed in seeds]
    df = df[column_order]
    
    # Save to file
    if output_file is None:
        output_file = results_dir / f"{model}.{setup}.tsv"
    
    # if df is empty, skip saving
    if df.empty:
        print(f"No valid data to save for model={model}, setup={setup}", file=sys.stderr)
        return None
    

    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, sep='\t', index=False)
    print(f"Created: {output_file}")
    
    return df


def process_multiple_combinations(
    results_dir: Path,
    models: List[str],
    setups: List[str],
    seeds: List[int],
    output_dir: Optional[Path] = None
):
    """
    Process multiple model-setup combinations.
    
    Args:
        results_dir: Path to results directory
        models: List of model names
        setups: List of setup names
        seeds: List of expected seeds
        output_dir: Optional output directory. If None, use results_dir
    """
    if output_dir is None:
        output_dir = results_dir
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    summary = []
    
    for model in models:
        for setup in setups:
            print(f"\nProcessing model={model}, setup={setup}...")
            output_file = output_dir / f"{setup}" / f"{model}.tsv"
            
            df = create_aggregated_tsv(results_dir, model, setup, seeds, output_file)
            
            if df is not None:
                summary.append({
                    'model': model,
                    'setup': setup,
                    'output_file': output_file,
                    'num_benchmark_sizes': len(df),
                    'total_cells': len(df) * len(seeds),
                    'missing_cells': df.isna().sum().sum() - df.isna()['benchmark_size'].sum()
                })
    
    # Print summary
    if summary:
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        summary_df = pd.DataFrame(summary)
        print(summary_df.to_string(index=False))
        
        #  summary
        # summary_file = output_dir / "processing_summary.tsv"
        # summary_df.to_csv(summary_file, sep='\t', index=False)
        # print(f"\nSummary saved to: {summary_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract and aggregate benchmark results from nested directory structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single model-setup combination
  python script.py --model model1 --setup setup1
  
  # Process multiple models and setups
  python script.py --models model1 model2 --setups setup1 setup2
  
  # Use all predefined models and setups
  python script.py --all
  
  # Specify custom seeds
  python script.py --all --seeds 0 1 2 3 4
        """
    )
    
    parser.add_argument(
        '--results-dir',
        type=Path,
        default=Path('results'),
        help='Path to results directory (default: results/)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default="aggregated/10-times-runs/",
        help='Path to output directory (default: aggregated/10-times-runs/)'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        help='Single model name to process'
    )
    
    parser.add_argument(
        '--setup',
        type=str,
        help='Single setup name to process'
    )
    
    parser.add_argument(
        '--models',
        type=str,
        nargs='+',
        help='List of model names to process'
    )
    
    parser.add_argument(
        '--setups',
        type=str,
        nargs='+',
        help='List of setup names to process'
    )
    
    parser.add_argument(
        '--seeds',
        type=int,
        nargs='+',
        default=DEFAULT_SEEDS,
        help=f'List of seeds (default: {DEFAULT_SEEDS})'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all predefined models and setups'
    )
    
    args = parser.parse_args()
    
    # Determine which models and setups to process
    if args.all:
        models = DEFAULT_MODELS
        setups = DEFAULT_SETUPS
    elif args.models and args.setups:
        models = args.models
        setups = args.setups
    elif args.model and args.setup:
        models = [args.model]
        setups = [args.setup]
    else:
        parser.error("Must specify either --all, (--model and --setup), or (--models and --setups)")
    
    # Check if results directory exists
    if not args.results_dir.exists():
        print(f"Error: Results directory not found: {args.results_dir}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Results directory: {args.results_dir}")
    print(f"Output directory: {args.output_dir or args.results_dir}")
    print(f"Models: {models}")
    print(f"Setups: {setups}")
    print(f"Seeds: {args.seeds}")
    
    # Process combinations
    process_multiple_combinations(
        args.results_dir,
        models,
        setups,
        args.seeds,
        args.output_dir
    )


if __name__ == "__main__":
    main()
