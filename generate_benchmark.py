"""
Sample run:

.venv/bin/python3 generate_benchmark.py --config benchmark-generation-config.yaml 

--- Starting Pipeline ---
Step  1  [Product & Extraction]                    Items:       10  Errors:    0
Step  2  [Sort Distractors]                        Items:       10  Errors:    0
Step  3  [Submodalities Product]                   Items:       30  Errors:    0
Step  4  [Generate Initial Final Options]          Items:       30  Errors:    0
Step  5  [Add NOTA-correct items]                  Items:       38  Errors:    0
Step  6  [Labels & Sorting Options]                Items:       38  Errors:    0

Step 7 [Final Save] complete. File saved to: final_benchmark.tsv

--- Step 8: Final Statistics ---
Total Benchmark Items : 38
NOTA Correct Items    : 8 (21.05%)
Total Errors Recorded : 0
--------------------------------

Prompt used to generate the script (also describes quite accurately what the script does):

Generate a python script and provide a sample config yaml file. The script should integrate the logic of the script below as a first step, and then add additional
steps, as described below. After each step, the script should print the intermediate benchmark into a tsv file in
subdirectory "intermediate_benchmarks" with a name that reflects the step that was just completed. The final output
should be a tsv file in the root directory with the name specified by the user in the --output argument.
Also, the script should take notes on error statistics and counts of items in the benchmark after each step, and print
the statistics after each step, and at the end of the script.

The steps to be implemented are as follows:
- 0.step: load a config file in yaml format that specifies further settings of the benchmark:
    - name of the method to be used for sorting the distractor pool by difficulty (to be applied in step 2)
    - number of options to be included in each question
    - NOTA text ("none of the other options is correct")
    - whether to add NOTA as one of the options
    - list of submodalities to be included in the current version of the benchmark, specified by the name of the file
      ("audio.mastermix.wav", "image.pdf", "symbolic.musicxml")
    - desired percentage of NOTA-correct questions in the benchmark
    - labels to be added to the options (e.g., "(A)", "(B)", "(C)", "(D)")
    - seed for random sorting (to ensure reproducibility, use the seed right at the beginning of the script)
    - the cmdline args of the script below, to be used for step 1 (e.g., paths to the meta-questions and pieces files, and the python file containing the methods for ground truth and distractor pool extraction)
- 1.step: generate the product of meta-questions and pieces, and compute the ground truth and distractor pool for each
question-piece pair using the methods specified in the meta-questions file. This is the logic that is currently
implemented in the script below.
- 2.step: apply a method as specified in the config to sort the distractor pool for each question-piece pair (with
preliminary dummy implementation of the method that just shuffles the distractor pool, to be replaced later with a real
implementation). This method should be applied to each question-piece pair in the benchmark generated in step 1, the
distractors sorted should be added to a new column "sorted_distractors" and
the output should be saved in an intermediate benchmark file named "benchmark_distractors_sorted.tsv".
- 3.step: generate a product of the benchmark from the 2. step with the list of submodalities specified in the config
(excluding submodalities that are not part of any modality that is supported for the given question, as specified in
`modality_in_question` column in the meta-questions file), adding the submodality name as a new column "submodality", and the column "path_to_question_context_file", which would
be the concatenation of the piece directory (column "path" from pieces.tsv) and the submodality name. The output should
be saved in an intermediate benchmark file named "benchmark_with_submodalities.tsv".
- 4.step: for each question-piece-submodality triplet, generate the final options to be included in the benchmark:
    - if NOTA is to be included, take it (the text specified in config) as one of the options,
    - take the ground truth as one of the options,
    - and take the desired number of remaining options from the sorted distractor pool, in order of difficulty (e.g., if
      the desired number of options is 5 and both NOTA and ground truth are included, take the top 3 most difficult distractors from the
      sorted distractor pool, and if NOTA is not included, take the top 4 most difficult distractors from the sorted
      distractor pool).
    - add the ground truth to a new column "final_correct_option"
    - The final options should be added in a new column "final_options" as a JSON string (list of options), and the output should be saved in an intermediate benchmark file named "benchmark_with_final_options.tsv".
- 5.step: add questions where ground-truth is excluded from the options (NOTA is correct answer) - only if the
  percentage of such desired questions is non-zero:
    - compute the probability that a random item should be added with NOTA as the correct option, such that the final
      percentage of NOTA-correct questions in the benchmark is as specified in the config (e.g., if the desired
      percentage is 20%, the probability would be 25%, because if we add an item with NOTA as the correct option with
      25% probability, we would have 25% NOTA-correct items among the newly added items, and if we add these items to
      the existing benchmark where 0% of items are NOTA-correct, we would end up with 20% NOTA-correct items in the
      final benchmark).
    - for each item from the benchmark after step 4, witch probability computed in the previous step, add a new item to
      the benchmark where the options are:
        - NOTA text
        - the top (N-1) most difficult distractors from the sorted distractor pool 
    - the column "final_correct_option" is set to NOTA text. The output should be saved in an intermediate benchmark file named
      "benchmark_with_NOTA_correct_items_added.tsv".
- 6.step: 
    - first, sort the options alphabetically, and then sort them randomly
    - add labels to the options (e.g., "(A)", "(B)", "(C)", "(D)") as specified in the config
    - add column all_choices (Type: list of str): A list containing all valid choice identifiers (usually letters
      or numbers). Example: ['A', 'B', 'C', 'D']
    - add column index2ans (Type: Dict[str, str]): A dictionary mapping the choice identifiers to their actual textual
      content. Example: {'A': '10 cm', 'B': '15 cm', 'C': '20 cm', 'D': '25cm', 'E': 'none of the other options is
      correct'}
    - The options should be in a new column "labeled_final_options" as a JSON string (list of options with labels), and the
  correct option should be in a new column "labeled_final_correct_option".
    - save the output as the intermediate bechmark file named "benchmark_with_labeled_sorted_final_options.tsv".
- 7.step:
    - save the final output (the same) in a tsv file in the root directory with the name specified in the config (e.g.,
      "final_benchmark.tsv").
- 8.step:
    - print the  final statistics of the benchmark, including the total number of items, the number and percentage of NOTA-correct
  items, and any errors encountered during the process.
"""


import argparse
import csv
import datetime
import importlib.util
import json
import os
import random
import sys
from pathlib import Path
import yaml
import uuid
from utils import load_methods_module

stats = {
    "errors": 0,
    "step_counts": {}
}


PROJECT_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "benchmark-generation")
INTERMEDIATE_DIR = None

def deterministic_uuid(data):
    """Generates a deterministic UUID based on the input data dictionary."""
    normalized = json.dumps(data, sort_keys=True)
    return uuid.uuid5(PROJECT_NAMESPACE, normalized)



def save_intermediate(data, filename, fieldnames):
    filepath = os.path.join(INTERMEDIATE_DIR, filename)
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(data)
    stats["step_counts"][filename] = len(data)

def print_checkpoint(step_num, title, filename):
    count = stats["step_counts"].get(filename, 0)
    title_with_brackets = f"[{title}]"
    print(
        f"Step {step_num:>2}  "
        f"{title_with_brackets:<40}  "
        f"Items: {count:>8}  "
        f"Errors: {stats['errors']:>4}"
    )
    # print(f"Step {step_num} [{title}] complete. Current items: {count}. Errors so far: {stats['errors']}.")

def step_1_generate_product(config):
    args = config['cmdline_args']
    methods_module = load_methods_module(args['methods_path'])

    with open(args['meta'], 'r', encoding='utf-8') as f_meta:
        meta_questions = list(csv.DictReader(f_meta, delimiter='\t'))
    with open(args['pieces'], 'r', encoding='utf-8') as f_pieces:
        pieces = list(csv.DictReader(f_pieces, delimiter='\t'))

    output_data = []
    
    for meta in meta_questions:
        method_name = meta['method_for_ground_truth_extraction']
        if not hasattr(methods_module, method_name):
            print(f"Error: Method '{method_name}' not found.")
            stats["errors"] += 1
            continue
        
        extraction_func = getattr(methods_module, method_name)

        for piece in pieces:
            try:
                ground_truth, distractor_pool = extraction_func(piece['path'])
                if ground_truth is not None:
                    row = {**meta, **piece}
                    row['ground_truth'] = ground_truth
                    row['distractor_pool'] = json.dumps(distractor_pool)
                    output_data.append(row)
            except Exception as e:
                print(f"Error on Q '{meta.get('question_id', '')}' / Piece '{piece.get('piece_id', '')}': {e}")
                stats["errors"] += 1

    fields = list(meta_questions[0].keys()) + list(pieces[0].keys()) + ['ground_truth', 'distractor_pool']
    save_intermediate(output_data, "01_benchmark_step1_product.tsv", fields)
    print_checkpoint(1, "Product & Extraction", "01_benchmark_step1_product.tsv")
    return output_data, fields

# def step_2_sort_distractors(data, config, fields):
#     out_fields = fields + ['sorted_distractors']
#     for row in data:
#         pool = json.loads(row['distractor_pool'])
#         # Dummy sorting method: shuffle
#         if config['sorting_method'] == "dummy_shuffle":
#             random.shuffle(pool)
#         row['sorted_distractors'] = json.dumps(pool)
    
#     save_intermediate(data, "02_benchmark_distractors_sorted.tsv", out_fields)
#     print_checkpoint(2, "Sort Distractors", "02_benchmark_distractors_sorted.tsv")
#     return data, out_fields

def step_2_sort_distractors(data, config, fields):
    # TODO: if the sorting of distractors depends on the modality of the content file in the question, this should be
    # moved after step 3.

    out_fields = fields + ['sorted_distractors']
    method_name = config.get('sorting_method')
    methods_path = config.get('sorting_methods_path')

    if not method_name or not methods_path:
        print("Error: 'sorting_method' or 'sorting_methods_path' missing in config.")
        stats["errors"] += 1
        return data, out_fields

    try:
        sorting_module = load_methods_module(methods_path)
        if not hasattr(sorting_module, method_name):
            raise AttributeError(f"Method '{method_name}' not found in '{methods_path}'")
        sort_func = getattr(sorting_module, method_name)
    except Exception as e:
        print(f"Error loading sorting method: {e}")
        stats["errors"] += 1
        return data, out_fields

    for row in data:
        pool = json.loads(row['distractor_pool'])
        try:
            # We pass the pool and the current row data to the sorting method context
            sorted_pool = sort_func(pool, row)
            row['sorted_distractors'] = json.dumps(sorted_pool)
        except Exception as e:
            print(f"Error sorting distractors for item: {e}")
            stats["errors"] += 1
            row['sorted_distractors'] = json.dumps(pool) # Fallback to unsorted if error occurs
    
    save_intermediate(data, "02_benchmark_distractors_sorted.tsv", out_fields)
    print_checkpoint(2, "Sort Distractors", "02_benchmark_distractors_sorted.tsv")
    return data, out_fields

def is_submodality_part_of_modality(submodality, modality):
    """Each submodality should have the modality in the name"""
    # TODO: Return true if modality is the substring of submodality
    return modality in submodality

def step_3_submodalities(data, config, fields):

    out_fields = fields + ['submodality', 'path_to_question_context_file']
    out_data = []
    for row in data:
        question_modalities = row['modality_in_question'].split(',') # Assuming modalities are comma-separated in the input
        
        for sub in config['submodalities']:
            # Only include the submodality, if it is a part of a modality that is supported by the question.
            if any(is_submodality_part_of_modality(sub, mod) for mod in question_modalities):
                new_row = dict(row)
                new_row['submodality'] = sub
                new_row['path_to_question_context_file'] = os.path.join(row['path'], sub)
                out_data.append(new_row)

    save_intermediate(out_data, "03_benchmark_with_submodalities.tsv", out_fields)
    print_checkpoint(3, "Submodalities Product", "03_benchmark_with_submodalities.tsv")
    return out_data, out_fields

def step_4_final_options(data, config, fields):
    out_fields = fields + ['final_correct_option', 'final_options', 'random_guess_performance_accuracy', 'is_nota_correct']
    num_opt = config['num_options']
    nota_text = config['nota_text']
    add_nota = config['add_nota']

    for row in data:
        distractors = json.loads(row['sorted_distractors'])
        gt = row['ground_truth']
        
        options = [gt]
        if add_nota:
            options.append(nota_text)
            distractors_needed = num_opt - 2
        else:
            distractors_needed = num_opt - 1
            
        options.extend(distractors[:distractors_needed])

        if len(options) < num_opt:
            print(f"Warning: Not enough distractors for item. Needed {num_opt - 1} distractors, but only {len(distractors)} available.")
            stats["errors"] += 1
        
        row['final_correct_option'] = gt
        row['final_options'] = json.dumps(options)
        row['random_guess_performance_accuracy'] = 1.0 / len(options) if options else 0.0
        row['is_nota_correct'] = 0

    save_intermediate(data, "04_benchmark_with_final_options.tsv", out_fields)
    print_checkpoint(4, "Generate Initial Final Options", "04_benchmark_with_final_options.tsv")
    return data, out_fields

def step_5_nota_correct(data, config, fields):
    T = config.get('nota_correct_percentage', 0.0)
    out_data = []
    
    if T > 0:
        P = T / (1.0 - T)
        N = config['num_options']
        nota_text = config['nota_text']
        
        for row in data:
            out_data.append(dict(row)) # Keep original item
            
            # Inject NOTA Correct randomly
            if random.random() < P:
                new_row = dict(row)
                distractors = json.loads(row['sorted_distractors'])
                
                # Top N-1 distractors + NOTA
                options = [nota_text] + distractors[:N-1]
                new_row['final_correct_option'] = nota_text
                new_row['final_options'] = json.dumps(options)
                new_row['is_nota_correct'] = 1
                
                out_data.append(new_row)
    else:
        out_data = data

    save_intermediate(out_data, "05_benchmark_with_NOTA_correct_items_added.tsv", fields)
    print_checkpoint(5, "Add NOTA-correct items", "05_benchmark_with_NOTA_correct_items_added.tsv")
    return out_data, fields

def step_6_formatting(data, config, fields):
    out_fields = ['item_id'] + fields + ['all_choices', 'index2ans', 'labeled_final_options', 'labeled_final_correct_option']
    labels = config['labels']
    
    for row in data:
        options = json.loads(row['final_options'])
        correct_opt = row['final_correct_option']
        
        # Sort alphabetically, then randomly
        options.sort()
        random.shuffle(options)
        
        all_choices = labels[:len(options)]
        index2ans = {}
        labeled_final_options = []
        labeled_correct = None
        
        for i, opt in enumerate(options):
            label = all_choices[i]
            index2ans[label] = opt
            labeled_final_options.append(f"({label}) {opt}")
            if opt == correct_opt:
                labeled_correct = label # Assign label letter as correct answer (e.g., 'C')
                
        row['all_choices'] = json.dumps(all_choices)
        row['index2ans'] = json.dumps(index2ans)
        row['labeled_final_options'] = json.dumps(labeled_final_options)
        row['labeled_final_correct_option'] = labeled_correct

        # For item_id, use a unique string identifier
        row['item_id'] = str(deterministic_uuid(row))

    save_intermediate(data, "06_benchmark_with_labeled_sorted_final_options.tsv", out_fields)
    print_checkpoint(6, "Labels & Sorting Options", "06_benchmark_with_labeled_sorted_final_options.tsv")
    return data, out_fields


def step_7_final_save(data, config, fields):
    out_path = config['cmdline_args']['output']
    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter='\t')
        writer.writeheader()
        writer.writerows(data)
    print(f"\nStep 7 [Final Save] complete. File saved to: {out_path}")

def main():
    parser = argparse.ArgumentParser(description="Benchmark Generator Pipeline")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    args = parser.parse_args()

    # Step 0: Load Config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    global INTERMEDIATE_DIR
    INTERMEDIATE_DIR = "logs/intermediate_benchmarks/" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        
    random.seed(config.get('seed', 42))
    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)

    # Pipeline Execution
    print("--- Starting Pipeline ---")
    data, fields = step_1_generate_product(config)
    data, fields = step_2_sort_distractors(data, config, fields)
    data, fields = step_3_submodalities(data, config, fields)
    data, fields = step_4_final_options(data, config, fields)
    data, fields = step_5_nota_correct(data, config, fields)
    data, fields = step_6_formatting(data, config, fields)
    step_7_final_save(data, config, fields)

    # Step 8: Final Statistics
    total_items = len(data)
    nota_correct_count = sum(1 for row in data if row.get('final_correct_option') == config['nota_text'])
    nota_percent = (nota_correct_count / total_items * 100) if total_items > 0 else 0

    print("\n--- Step 8: Final Statistics ---")
    print(f"Total Benchmark Items : {total_items}")
    print(f"NOTA Correct Items    : {nota_correct_count} ({nota_percent:.2f}%)")
    print(f"Total Errors Recorded : {stats['errors']}")
    print("--------------------------------")

if __name__ == "__main__":
    main()