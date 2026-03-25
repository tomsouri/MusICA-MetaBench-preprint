#!/bin/bash

# For specified list of models, setups, seeds, and sizes, generate benchmarks and submit jobs to run the benchmarks on a
# cluster using sbatch.


models=(
    "google/gemini-2.0-flash-lite-001"
    "aggregate-gpt-4o"
    "aggregate-mistral"
    "aggregate-gpt-5"
    "google/gemini-2.5-flash-lite"
    "xiaomi/mimo-v2-omni"
    "google/gemini-3.1-flash-lite-preview"
)
setups=(
    "normal"
    "text-only"
)
seeds=({55..55}) # just a single seed
# sizes=({1..1}) # just 20 questions per subcategory
sizes=({20..20}) # just 20 questions per subcategory

for seed in "${seeds[@]}"; do
    for size in ${sizes[@]} ; do

        benchmark_file="benchmark_count_${size}_${seed}.tsv"
        # benchmarks+=("$benchmark_file")

        echo "Generating a benchmark with random seed: $seed"

        run .venv/bin/python3 generate_benchmark.py --config benchmark-generation-config.yaml \
            --benchmark_file "$benchmark_file" \
            --questions_per_subcategory_count "$size" \
            --seed "$seed" \
            --submodalities "audio.mastermix.wav" "symbolic.musicxml" "visual.short.png" \
            --allowed_metaq_ids 0 1 2 3 4 5 6 7 8 9

        echo "================================================================================"
        

        echo "Submitting jobs for benchmark with seed ${seed} and size ${size}..."
        for model in "${models[@]}" ; do
            echo "          Submitting jobs for model: ${model}"
            model_name="${model//\//_}"
            for setup in "${setups[@]}" ; do
                echo "              Submitting job for setup: ${setup}"
                sbatch --parsable \
                    -p cpu-ms -c2 --mem=4G \
                   --job-name="${model_name}_${setup}" \
                   --output="runs/${model_name}_${setup}_%j.out" \
                   --error="runs/${model_name}_${setup}_%j.err" \
                    run-model.sh -m "${model}" -s "${size}" -e "${seed}" -t "${setup}"
            done
        done
    done
done