import pandas as pd
import os
import glob

def process_benchmarks(root_dir, output_dir):
    # Ensure output directory exists
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
        print("No files found.")
        return

    full_df = pd.concat(all_data, ignore_index=True)
    full_df['display_val'] = (
        full_df['Mean_Accuracy (10 runs)'].round(2).astype(str) + 
        " (" + full_df['StdDev_Accuracy (10 runs)'].round(2).astype(str) + ")"
    )

    # Export Loop
    criteria = full_df['Criterion_Value'].unique()
    for criterion in criteria:
        subset = full_df[full_df['Criterion_Value'] == criterion]
        pivot_table = subset.pivot(index='model', columns='size', values='display_val')
        
        # Create a safe filename by replacing dots/spaces
        safe_name = criterion.replace(".", "_").replace(" ", "_")
        output_path = os.path.join(output_dir, f"table_{safe_name}.md")
        
        with open(output_path, "w") as f:
            f.write(f"# Table for {criterion}\n\n")
            f.write(pivot_table.to_markdown())
            
        print(f"Generated: {output_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python generate_tables_to_file.py <path_to_averaged_dir> <output_dir>")
    else:
        process_benchmarks(sys.argv[1], sys.argv[2])