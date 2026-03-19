#!/bin/bash
#SBATCH -J run      # name of job
#SBATCH -p cpu-ms       # name of partition or queue (default=cpu-troja)
#SBATCH -o run.out  # name of output file for this submission script
#SBATCH -e run.err  # name of error file for this submission script

# to submit the job, you need to be ssh-ed at one of the lrc or sol machines. (from geri/freki/blackbird, ssh lrc1 or sol1)
# Then use: sbatch --dependency=afterany:<JOB_ID>
# sbatch -p cpu-ms -c2 --mem=4G --dependency=afterany:6358156 run_multiple.sh

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
# seeds=({42..43})
seeds=({42..52})


benchmarks=() # Initialize an empty array

for seed in "${seeds[@]}"; do
    benchmark_file="benchmark_count_${qpersubcategory}_${seed}.tsv"
    benchmarks+=("$benchmark_file")

    echo "Generating a benchmark with random seed: $seed"

    run .venv/bin/python3 generate_benchmark.py --config benchmark-generation-config.yaml \
        --benchmark_file "$benchmark_file" \
        --questions_per_subcategory_count "$qpersubcategory" \
        --seed "$seed" \
        --submodalities "audio.mastermix.wav" "symbolic.musicxml" "visual.short.png" \
        --allowed_metaq_ids 0 1 2 3 4 5 6 7 8 9

    echo "================================================================================"
done

.venv/bin/python3 compare_benchmark_files.py --list_of_tsvs "${benchmarks[@]}" | tee "benchmark_comparison_${qpersubcategory}qs.txt"



for model in "${models[@]}"; do
    echo "Running the benchmarks for model ${model}..."

    # 1. Replace all forward slashes / with underscores
    safe_model="${model//\//_}"

    # 2. Replace spaces with underscores
    safe_model="${safe_model// /_}"


    resfiles=()
    textonlyresfiles=()


    for seed in "${seeds[@]}"; do
        benchmark_file="benchmark_count_${qpersubcategory}_${seed}.tsv"

        echo "Running on a benchmark with random seed: $seed"
    
        resfile="${seed}_${qpersubcategory}_${safe_model}.res.tsv"
        resfiles+=("$resfile")
    

        run .venv/bin/python3 run_benchmark.py --config eval-config.yaml \
            --models "${model}" \
            --url "https://openrouter.ai/api/v1/chat/completions" \
            --api-key-env "OPENROUTER_API_KEY" \
            --benchmark_file "$benchmark_file" \
            --modalities "audio" "symbolic" "visual" \
            --run_id "Nrs${seed}"  \
            --max_waiting_time_per_request 300 \
            --verbose \
            --evaluation_output_file "${resfile}" \
            --generate_new_list_with_logs \

        echo "================================================================================"

        toresfile="${seed}_${qpersubcategory}_to_${safe_model}.res.tsv"
        textonlyresfiles+=("$toresfile")

        run .venv/bin/python3 run_benchmark.py --config eval-config.yaml \
            --models "${model}" \
            --url "https://openrouter.ai/api/v1/chat/completions" \
            --api-key-env "OPENROUTER_API_KEY" \
            --benchmark_file "$benchmark_file" \
            --modalities "audio" "symbolic" "visual" \
            --run_id "Nto_rs${seed}"  \
            --max_waiting_time_per_request 300 \
            --text_only_baseline \
            --verbose \
            --evaluation_output_file "${toresfile}" \
            --generate_new_list_with_logs \

        echo "================================================================================"
    done

    dir="averaged/${safe_model}/${qpersubcategory}"
    mkdir -p $dir

    .venv/bin/python3 compute_mean_stddev.py --list_of_tsvs "${resfiles[@]}" --output_file "${dir}/res.tsv"
    .venv/bin/python3 compute_mean_stddev.py --list_of_tsvs "${textonlyresfiles[@]}" --output_file "${dir}/textonly.tsv"

    cp "benchmark_comparison_${qpersubcategory}qs.txt" $dir/

done



