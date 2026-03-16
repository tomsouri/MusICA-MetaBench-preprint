#!/bin/bash
#SBATCH -J run      # name of job
#SBATCH -p cpu-ms       # name of partition or queue (default=cpu-troja)
#SBATCH -o run.out  # name of output file for this submission script
#SBATCH -e run.err  # name of error file for this submission script

# to submit the job, you need to be ssh-ed at one of the lrc or sol machines. (from geri/freki/blackbird, ssh lrc1 or sol1)
# Then use:
# sbatch -p cpu-ms -c2 --mem=4G run.sh

.venv/bin/python3 generate_benchmark.py --config benchmark-generation-config.yaml \
    --benchmark_file "benchmark_v3.tsv" \
    --submodalities "audio.mastermix.wav" "symbolic.musicxml" "visual.pdf" \
    --questions_per_subcategory_count 10 \
    --seed 42

.venv/bin/python3 run_benchmark.py --config eval-config.yaml \
    --models "google/gemini-2.0-flash-lite-001" \
    --url "https://openrouter.ai/api/v1/chat/completions" \
    --api-key-env "OPENROUTER_API_KEY" \
    --benchmark_file "benchmark_v3.tsv" \
    --sheet_name "trial" \
    --modalities "audio" "symbolic" "visual" \
    --run_id "trial01" \
    # --text_only_baseline

