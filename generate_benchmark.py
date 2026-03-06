#!/usr/bin/env python3

"""
example usage:

python generate_benchmark.py \
    --meta meta-questions.tsv \
    --pieces pieces.tsv \
    --methods_path extraction_methods.py \
    --output final_benchmark.tsv


.venv/bin/python3 generate_benchmark.py --meta meta-questions.tsv --pieces pieces.tsv --methods_path src/ground_truth_extractions.py --output benchmark_v1.tsv
"""


import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path

def load_methods_module(file_path: str):
    """Dynamically loads a python module from a given file path."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Methods file not found: {file_path}")
    
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def main():
    parser = argparse.ArgumentParser(description="Generate benchmark product from meta-questions and pieces.")
    parser.add_argument("--meta", required=True, help="Path to meta-questions TSV")
    parser.add_argument("--pieces", required=True, help="Path to pieces TSV")
    parser.add_argument("--methods_path", required=True, help="Path to the python script containing extraction methods")
    parser.add_argument("--output", required=True, help="Path for the output TSV")

    args = parser.parse_args()

    # Load the python file containing the ground truth extraction methods
    methods_module = load_methods_module(args.methods_path)

    # Read the TSV files
    with open(args.meta, 'r', encoding='utf-8') as f_meta:
        meta_reader = csv.DictReader(f_meta, delimiter='\t')
        meta_questions = list(meta_reader)
        meta_fields = meta_reader.fieldnames

    with open(args.pieces, 'r', encoding='utf-8') as f_pieces:
        pieces_reader = csv.DictReader(f_pieces, delimiter='\t')
        pieces = list(pieces_reader)
        pieces_fields = pieces_reader.fieldnames

    # Prepare output fields
    output_fields = meta_fields + pieces_fields + ['ground_truth'] + ['distractor_pool']

    with open(args.output, 'w', encoding='utf-8', newline='') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=output_fields, delimiter='\t')
        writer.writeheader()

        error_count = 0

        # Compute the product
        for meta in meta_questions:
            method_name = meta['method_for_ground_truth_extraction']
            
            # Retrieve the function object dynamically
            if not hasattr(methods_module, method_name):
                raise AttributeError(f"Method '{method_name}' not found in {args.methods_path}")
            
            extraction_func = getattr(methods_module, method_name)

            for piece in pieces:
                piece_dir_path = piece['path']
                
                ground_truth = None

                # Execute the extraction method
                try:
                    ground_truth, distractor_pool = extraction_func(piece_dir_path)

                except Exception as e:
                    print(f"Error computing GT for question '{meta['question_id']}' on piece '{piece['piece_id']}': {e}. Skipping the question-piece pair.")
                    error_count += 1

                if ground_truth is not None:
                    output_row = {**meta, **piece}
                    output_row['ground_truth'] = ground_truth
                    output_row['distractor_pool'] = json.dumps(distractor_pool)  # Convert list to JSON string for TSV storage
                    writer.writerow(output_row)


    if error_count > 0:
        print(f"WARNING: Encountered {error_count} errors during ground truth extraction. Check the logs for details.")

    print(f"Finished generating benchmark with {error_count} errors.")
    print(f"Benchmark saved to: {args.output}")
    # print(f"Successfully generated benchmark at {args.output}")

if __name__ == "__main__":
    main()