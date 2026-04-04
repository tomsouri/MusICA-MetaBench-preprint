"""
For a single size and seed (that is, for a single instance of benchmark),
aggregate the results across all the models and setups.
"""

import pandas as pd
import argparse
from pathlib import Path

import pandas as pd
import argparse
from pathlib import Path

def aggregate_results(base_path, b_size, seed, fields, setup, output, compare_mode):
    root = Path(base_path)
    merge_keys = ['Criterion_Type', 'Criterion_Value', 'Total_Items']
    
    # Identify unique models
    all_models = [p.name for p in root.iterdir() if p.is_dir()]
    
    # Prepare list to hold data
    final_cols = []
    base_df = None

    for model in all_models:
        setups = ["normal", "to"] if compare_mode else [setup]
        
        for setup in setups:
            file_path = root / model / b_size / setup / f"rs{seed}.res.tsv"
            
            if not file_path.exists():
                print(f"Warning: Missing {file_path}. Skipping model {model} setup {setup}.")
                continue
            
            df = pd.read_csv(file_path, sep='\t')
            
            # Validation
            if base_df is None:
                base_df = df[merge_keys].copy()
            else:
                if not base_df.equals(df[merge_keys]):
                    raise ValueError(f"Consistency error: {file_path} does not match base keys.")

            # Add requested fields for this model/setup
            for field in fields:
                if field not in df.columns:
                    raise ValueError(f"Field '{field}' not in {file_path}")
                
                # Column naming: Model_Setup_Field (e.g., Llama_normal_Accuracy_Percent)
                
                setup_str = f"_{setup}" if len(setups) > 1 else ""
                field_str = field.replace(" ", "_")  # Replace spaces with underscores for column names
                field_str = f"_{field_str}" if len(fields) > 1 else ""
                col_name = f"{model}{setup_str}{field_str}"

                final_cols.append(df[field].rename(col_name))

    # Construct Final DataFrame
    result_df = pd.concat([base_df] + final_cols, axis=1)
    
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(output, sep='\t', index=False)
    print(f"Results saved to: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", required=True, help="Benchmark size")
    parser.add_argument("--seed", required=True, help="Seed (e.g., 42)")
    # parser.add_argument("--setup", default="normal", help="Setup name")
    # parser.add_argument("--field", nargs='+', default=["Accuracy_Percent", "Unparsable_Percent", "Model_Error_Percent", "Total_Time_s", "Total_Price"], help="List of fields to extract")
    parser.add_argument("--path", default="results", help="Root results directory")
    parser.add_argument("--output", default="aggregated_results", help="Path to save the output TSV")
    # parser.add_argument("--normal_vs_textonly_comparison", action="store_true")

    args = parser.parse_args()

    interesting_fields = ["Accuracy_Percent", "Unparsable_Percent", "Model_Error_Percent", "Total_Time_s", "Total_Price"]
    single_field = ["Accuracy_Percent"]

    for setup in ["normal", "to"]:
        print(f"Aggregating results for setup: {setup}")
        for fields in [interesting_fields, single_field]:
            print(f"Processing fields: {fields}")
            outfile = args.output + f"{setup}"
            outfile = outfile + "_all_fields.tsv" if len(fields) > 1 else outfile + "_accuracy_only.tsv"

            aggregate_results(args.path, args.size, args.seed, fields, setup, outfile, False)
    
    outfile = args.output + "comparison_normal_vs_textonly.tsv"
    aggregate_results(args.path, args.size, args.seed, single_field, None, outfile, True)

# example usage:
# .venv/bin/python3 generate_aggregated_table.py --size 20 --seed 55 --output aggregated/