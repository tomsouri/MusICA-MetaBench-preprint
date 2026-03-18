#!/bin/bash
#SBATCH -J run      # name of job
#SBATCH -p cpu-ms       # name of partition or queue (default=cpu-troja)
#SBATCH -o run.out  # name of output file for this submission script
#SBATCH -e run.err  # name of error file for this submission script

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


models=(
    "google/gemini-2.0-flash-lite-001"
    # "google/gemini-2.5-flash"
    # "google/gemini-3.1-flash-lite-preview"
    # "google/gemini-3.1-pro-preview"
)

qpersubcategory=15


for seed in {42..52}; do
    benchmark_file="benchmark_count_${qpersubcategory}_${seed}.tsv"
    echo "Running with random seed: $seed"

    run .venv/bin/python3 generate_benchmark.py --config benchmark-generation-config.yaml \
        --benchmark_file "$benchmark_file" \
        --questions_per_subcategory_count "$qpersubcategory" \
        --seed "$seed" \
        --submodalities "audio.mastermix.wav" "symbolic.musicxml" "visual.short.png" \
        --allowed_metaq_ids 0 1 2 3 4 5 6 7 8 9
    
    echo "================================================================================"
    
    for model in "${models[@]}"; do

        run .venv/bin/python3 run_benchmark.py --config eval-config.yaml \
            --models "${model}" \
            --url "https://openrouter.ai/api/v1/chat/completions" \
            --api-key-env "OPENROUTER_API_KEY" \
            --benchmark_file "$benchmark_file" \
            --modalities "audio" "symbolic" "visual" \
            --run_id "rs${seed}"  \
            --max_waiting_time_per_request 300 \
            --generate_new_list_with_logs \
            --verbose

        echo "================================================================================"
        
        run .venv/bin/python3 run_benchmark.py --config eval-config.yaml \
            --models "${model}" \
            --url "https://openrouter.ai/api/v1/chat/completions" \
            --api-key-env "OPENROUTER_API_KEY" \
            --benchmark_file "$benchmark_file" \
            --modalities "audio" "symbolic" "visual" \
            --run_id "to_rs${seed}"  \
            --max_waiting_time_per_request 300 \
            --generate_new_list_with_logs \
            --text_only_baseline \
            --verbose

        echo "================================================================================"
    done
done

