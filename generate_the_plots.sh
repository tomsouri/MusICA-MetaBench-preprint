#!/bin/bash
BASE_DIR=$(dirname "$0")

SRC_DIR=$(dirname "$0")

TGT_DIR="$SRC_DIR/aggregated/results-for-paper/chorale-bricks"

SCRIPTS_DIR="$BASE_DIR/src/plotting"


font_size=15

echo "Generating submodality spider chart for selected models from $SRC_DIR/aggregated/models_comparison/size_20/seed_52/normal/accuracy_only.tsv to $TGT_DIR/plots/spiders/submodality-chorale-bricks_s20_seed52_selected-models.png"
.venv/bin/python $SCRIPTS_DIR/generate_spider_chart.py $SRC_DIR/aggregated/models_comparison/size_20/seed_52/normal/accuracy_only.tsv \
      --include google_gemini-3.1-pro-preview aggregate-gpt-4o aggregate-mistral Qwen_Qwen3-Omni-30B-A3B-Thinking \
      --criterion_type submodality \
      --baseline \
      --font_size $font_size \
      --output_file $TGT_DIR/plots/spiders/submodality-chorale-bricks_s20_seed52_selected-models.png

echo "Generating subcategory spider chart from $SRC_DIR/aggregated/models_comparison/size_20/seed_52/normal/accuracy_only.tsv"
.venv/bin/python $SCRIPTS_DIR/generate_spider_chart.py $SRC_DIR/aggregated/models_comparison/size_20/seed_52/normal/accuracy_only.tsv \
      --include google_gemini-3.1-pro-preview aggregate-gpt-4o aggregate-mistral Qwen_Qwen3-Omni-30B-A3B-Thinking \
      --criterion_type subcategory \
      --baseline \
      --font_size $font_size \
      --output_file $TGT_DIR/plots/spiders/subcategory-chorale-bricks_s20_seed52_selected-models.png


# .venv/bin/python3 generate_plot_with_comparison_of_normal_textonly_noise.py $SRC_DIR/aggregated/models_comparison/size_20/seed_52/normal/accuracy_only.tsv --output-prefix $TGT_DIR/plots/size-20-seed-52-normal --y-max 70 --no-hatch --font-size 15 --height 7


# .venv/bin/python3 generate_comparison_table.py --base_path $SRC_DIR/results --size 20 --seed 52 --criterion OVERALL ALL --output $TGT_DIR/tables/s20_seed52_comparison.tsv --tex_output $TGT_DIR/tables/s20_seed52_comparison.tex --exclude_errors --multiline_setup

echo "Generating comparison table for size 20, seed 52 from $SRC_DIR/results to $TGT_DIR/tables/s20_seed52_comparison.tsv and $TGT_DIR/tables/s20_seed52_comparison.tex"
.venv/bin/python3 $SCRIPTS_DIR/generate_comparison_table.py --base_path $SRC_DIR/results --size 20 --seed 52 --criterion OVERALL ALL --output $TGT_DIR/tables/s20_seed52_comparison.tsv --tex_output $TGT_DIR/tables/s20_seed52_comparison.tex --exclude_errors --omit_setup

echo "Generating plot with comparison of normal and text-only noise for a single benchmark instance (size 20, seed 52) from $SRC_DIR/aggregated/models_comparison/size_20/seed_52/comparison_normal_vs_textonly.tsv"
.venv/bin/python3 $SCRIPTS_DIR/generate_plot_with_comparison_of_normal_textonly_noise.py $SRC_DIR/aggregated/models_comparison/size_20/seed_52/comparison_normal_vs_textonly.tsv --output-prefix $TGT_DIR/plots/size-20-seed-52-normal-vs-textonly-vs-white-noise --y-max 70 --no-hatch --font-size 15 --height 7


echo "Generating plot with comparison of normal and text-only noise averaged over seeds for size 20 and size 50 from $SRC_DIR/aggregated/models_comparison/size_20/mean_over_seeds/comparison_normal_vs_textonly.tsv and $SRC_DIR/aggregated/models_comparison/size_50/mean_over_seeds/comparison_normal_vs_textonly.tsv"
.venv/bin/python3 $SCRIPTS_DIR/generate_plot_with_comparison_of_normal_textonly_noise.py $SRC_DIR/aggregated/models_comparison/size_50/mean_over_seeds/comparison_normal_vs_textonly.tsv --output-prefix $TGT_DIR/plots/size-50-mean-over-seeds-normal-vs-textonly-vs-white-noise --ignore-incomplete --y-max 51 --no-hatch --font-size 15 --print-only-average --height 3.5

.venv/bin/python3 $SCRIPTS_DIR/generate_plot_with_comparison_of_normal_textonly_noise.py $SRC_DIR/aggregated/models_comparison/size_20/mean_over_seeds/comparison_normal_vs_textonly.tsv --output-prefix $TGT_DIR/plots/size-20-mean-over-seeds-normal-vs-textonly-vs-white-noise --ignore-incomplete --y-max 51 --no-hatch --font-size 15 --print-only-average --height 3.5


echo "Generating plot with standard deviations across sizes from $SRC_DIR/tables/normal/stddev-only/table_ALL.tsv"
.venv/bin/python3 $SCRIPTS_DIR/plot_stddev_with_benchmark_size.py $SRC_DIR/tables/normal/stddev-only/table_ALL.tsv --output $TGT_DIR/plots/stddevs3.png --log-x --exclude-size-one --multiply-sizes-by 15 --fontsize 12
