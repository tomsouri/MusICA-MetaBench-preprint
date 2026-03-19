import os
import csv
import itertools
import fnmatch
import argparse

def calculate_tsv_overlap(file1_path, file2_path, columns_to_compare):
    """
    Standard overlap calculation between two specific TSV files.
    """
    def get_row_fingerprints(file_path, columns):
        fingerprints = []
        with open(file_path, mode='r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                fingerprint = tuple(row[col] for col in columns)
                fingerprints.append(fingerprint)
        return fingerprints

    data1 = get_row_fingerprints(file1_path, columns_to_compare)
    data2 = get_row_fingerprints(file2_path, columns_to_compare)

    if not data1: return 0.0
    
    set2 = set(data2)
    matches = sum(1 for row in data1 if row in set2)
    return (matches / len(data1)) * 100

def discover_tsv_files_from_patterns(root_path, dir_pattern, file_pattern):
    """
    Finds matching TSVs using Unix-like wildcard patterns and computes statistics.
    
    Args:
        root_path (str): Directory A.
        dir_pattern (str): Pattern B (e.g., "batch_*_data").
        file_pattern (str): Pattern C (e.g., "xy*23").
    """
    target_files = []
    
    # Ensure the file pattern handles the extension check if not provided in pattern
    if not file_pattern.endswith('.tsv'):
        file_pattern += '.tsv'

    # 1. Traversal with Pattern Matching
    for root, dirs, files in os.walk(root_path):
        # We only care about the immediate directory name for the B pattern
        folder_name = os.path.basename(root)
        
        # fnmatch provides Unix shell-style wildcards
        if fnmatch.fnmatch(folder_name, dir_pattern):
            for file in files:
                if fnmatch.fnmatch(file, file_pattern):
                    target_files.append(os.path.join(root, file))

    if len(target_files) < 2:
        print(f"Insufficient files found matching patterns (Found: {len(target_files)})")
        return None
    
def analyze_tsv_collection(target_files, columns):

    # 2. Pair-wise Comparison
    overlaps = []
    file_pairs = list(itertools.combinations(target_files, 2))
    
    print(f"Comparing {len(target_files)} files ({len(file_pairs)} unique pairs)...")

    for f1, f2 in file_pairs:
        score = calculate_tsv_overlap(f1, f2, columns)
        overlaps.append(score)

    # 3. Aggregation
    stats = {
        "avg": sum(overlaps) / len(overlaps),
        "max": max(overlaps),
        "min": min(overlaps),
        "count": len(target_files),
        "pairs": len(overlaps)
    }

    # Formatting output
    print(f"\n{'='*40}")
    # print(f"Results for pattern: {dir_pattern}/{file_pattern}")
    print(f"{'='*40}")
    print(f"Average Overlap: {stats['avg']:.2f}%")
    print(f"Maximum Overlap: {stats['max']:.2f}%")
    print(f"Minimum Overlap: {stats['min']:.2f}%")
    print(f"Total Files Compared: {stats['count']}")
    print(f"{'='*40}\n")

    return stats






def main():
    parser = argparse.ArgumentParser(description="Calculate overlap stats between TSV files matching specific patterns.")
    
    # Path arguments
    parser.add_argument("--root_path", type=str, default="logs/", 
                        help="The base directory to search in (default: logs/)")
    
    # Pattern arguments
    parser.add_argument("--dir_pattern", type=str,
                        help="Unix-like pattern for subdirectories (e.g., 'batch_*')")
    parser.add_argument("--file_pattern", type=str, default="benchmark*.tsv",
                        help="Unix-like pattern for files (e.g., 'benchmark*.tsv')")
    
    # Comparison arguments
    parser.add_argument("--columns", nargs='+', 
                        default=['meta-question_id', 'dataset', 'piece_id', 'question', 'modality'],
                        help="List of column names to compare (space separated)")
    
    # Explicit List Mode Argument
    parser.add_argument("--list_of_tsvs", nargs='+', 
                        help="Explicit list of TSV file paths to compare. Overrides discovery mode.")


    args = parser.parse_args()

    target_files = []

    # 1. File Selection Logic
    if args.list_of_tsvs:
        # Use explicitly provided files
        target_files = args.list_of_tsvs
        print(f"Using {len(target_files)} provided files.")
    else:
        # Use Discovery Mode (ensure patterns are provided)
        if not args.dir_substring or not args.file_substring:
            parser.error("Either --list_of_tsvs OR both --dir_substring and --file_substring must be provided.")

        target_files = discover_tsv_files_from_patterns(root_path=args.root_path, dir_pattern=args.dir_pattern, file_pattern=args.file_pattern)

    # Example Usage:
    # import sys
    # print(f"Comparing {sys.argv[1]} and {sys.argv[2]}")
    # columns = ['meta-question_id', 'dataset', 'piece_id', 'question', 'modality']
    # percent = calculate_tsv_overlap(sys.argv[1], sys.argv[2], columns)
    # print(f"Overlap: {percent}%")

    analyze_tsv_collection(target_files, args.columns)

# Example run:
# .venv/bin/python3 compare_benchmark_files.py --dir_pattern "run_2026-03-18_*rs*-15" --file_pattern "benchmark_cou*.tsv"


if __name__ == "__main__":
    main()