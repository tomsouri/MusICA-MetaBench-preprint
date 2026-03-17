#!/bin/bash
#SBATCH -J run-m      # name of job
#SBATCH -p cpu-ms       # name of partition or queue (default=cpu-troja)
#SBATCH -o run_m.out  # name of output file for this submission script
#SBATCH -e run_m.err  # name of error file for this submission script

# to submit the job, you need to be ssh-ed at one of the lrc or sol machines. (from geri/freki/blackbird, ssh lrc1 or sol1)
# Then use:
# sbatch -p cpu-ms -c2 --mem=4G run_multiple.sh

# - "google/gemini-3.1-pro-preview"
# - "google/gemini-3.1-flash-lite-preview"
# - "llama-4-scout-17b-16e-instruct"
# - "openai/gpt-4o-audio-preview"
# - "openai/gpt-4o-mini"
# - "google/gemini-2.5-flash"
# - "google/gemini-2.0-flash-lite-001"

benchmark_file="benchmark_v5.tsv"
models=(
    "google/gemini-2.0-flash-lite-001"
    "google/gemini-2.5-flash"
    # "google/gemini-3.1-flash-lite-preview"
    # "google/gemini-3.1-pro-preview"
)

.venv/bin/python3 generate_benchmark.py --config benchmark-generation-config.yaml \
    --benchmark_file "$benchmark_file" \
    --questions_per_subcategory_count 10 \
    --seed 41 \
    --submodalities "audio.mastermix.wav" "symbolic.musicxml" "visual.pdf" \
    --allowed_metaq_ids 0 1 2 3


.venv/bin/python3 run_benchmark.py --config eval-config.yaml \
    --models ${models[*]} \
    --url "https://openrouter.ai/api/v1/chat/completions" \
    --api-key-env "OPENROUTER_API_KEY" \
    --benchmark_file "$benchmark_file" \
    --sheet_name "gemini-all-10" \
    --run_id "gemini-all-10" 
    # --text_only_baseline
    # --modalities "symbolic" \

