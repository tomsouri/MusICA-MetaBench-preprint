#!/bin/bash

# Usage: ./run-model.sh -m "model_name" -s 5 -e 42 -t "normal"

while getopts m:s:e:t: flag
do
    case "${flag}" in
        m) model=${OPTARG};;
        s) size=${OPTARG};;
        e) seed=${OPTARG};;
        t) setup=${OPTARG};; # "normal" or "text-only"
    esac
done

# echo "Running model: $model | Size: $size | Seed: $seed | Setup: $setup"

safe_model="${model//\//_}"
safe_model="${safe_model// /_}"
clean_string="${model//[^a-zA-Z0-9]/_}"
apikey="${clean_string}_${size}"

benchmark_file="benchmark_count_${size}_${seed}.tsv"
setup_dir="normal"
text_only_flag=""

if [ "$setup" == "text-only" ]; then
    setup_dir="to"
    text_only_flag="--text_only_baseline"
    apikey="${apikey}_to"
fi

mkdir -p "results/${safe_model}/${size}/${setup_dir}/"
resfile="results/${safe_model}/${size}/${setup_dir}/rs${seed}.res.tsv"


# echo "${apikey}" 

# For now, disable ZDR, to allow running all models

# Run the benchmark
run .venv/bin/python3 run_benchmark.py --config eval-config.yaml \
    --models "${model}" \
    --url "https://openrouter.ai/api/v1/chat/completions" \
    --api-key-env "${apikey}" \
    --benchmark_file "$benchmark_file" \
    --modalities "audio" "symbolic" "visual" \
    --run_id "${setup}-${safe_model}-${size}-${seed}"  \
    --max_waiting_time_per_request 30 \
    --verbose \
    --evaluation_output_file "${resfile}" \
    --generate_new_list_with_logs \
    --disable_zdr \
    $text_only_flag \