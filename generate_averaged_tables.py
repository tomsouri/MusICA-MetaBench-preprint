import pandas as pd
import os
import glob
import argparse

def process_benchmarks(root_dir, output_dir, target_criteria):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    all_data = []
    search_path = os.path.join(root_dir, "*", "*", "res.tsv")
    
    for file_path in glob.glob(search_path):
        parts = file_path.split(os.sep)
        model_name = parts[-3]
        benchmark_size = parts[-2]
        
        df = pd.read_csv(file_path, sep='\t')
        df['model'] = model_name
        df['size'] = benchmark_size
        all_data.append(df)

    if not all_data:
        print("No files found in the specified directory.")
        return

    full_df = pd.concat(all_data, ignore_index=True)
    full_df['display_val'] = (
        full_df['Mean_Accuracy (10 runs)'].apply(lambda x: f"{x:.2f}") + 
        " (" + full_df['StdDev_Accuracy (10 runs)'].apply(lambda x: f"{x:.2f}") + ")"
    )

    # Filter by user provided criteria
    unique_criteria = full_df['Criterion_Value'].unique()
    criteria_to_process = [c for c in target_criteria if c in unique_criteria]

    if not criteria_to_process:
        print(f"None of the provided criteria found: {target_criteria}")
        print(f"Available criteria: {list(unique_criteria)}")
        return

    for criterion in criteria_to_process:
        subset = full_df[full_df['Criterion_Value'] == criterion]
        pivot_table = subset.pivot(index='model', columns='size', values='display_val')
        
        safe_name = criterion.replace(".", "_").replace(" ", "_")
        output_path = os.path.join(output_dir, f"table_{safe_name}.md")
        
        with open(output_path, "w") as f:
            f.write(f"# Table for {criterion}\n\n")
            f.write(pivot_table.to_markdown())
            
        print(f"Generated: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate benchmark tables from TSV files.")
    parser.add_argument("input_dir", help="Path to the directory containing averaged data")
    parser.add_argument("output_dir", help="Directory where tables will be saved")
    parser.add_argument("--criteria", nargs='+', default=["ALL", "audio.mastermix.wav", "symbolic.musicxml", "visual.short.png"], 
                        help="List of Criterion_Values to generate tables for (e.g., ALL submodality)")

    args = parser.parse_args()
    process_benchmarks(args.input_dir, args.output_dir, args.criteria)