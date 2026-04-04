#!/bin/bash

# For specified list of models, setups, seeds, and sizes, generate benchmarks and submit jobs to run the benchmarks on a
# cluster using sbatch.


# TODO: refactor this, such that the generation of benchmarks is done in a separate script, 
# and only once per size and seed.
# Also, the list of models should be passed as an argument to the script, and not hardcoded in the script. 
# Same for the list of setups, seeds, sizes, and repetitions.
#
# Then, provide a script that would run this script with the desired arguments.

# TODO: where to perform the aggregation of results across all models? (for single runs on single benchmark instance?)
# to je ted jedno, to ted behat nebudeme


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
sizes=({20..20}) # just 20 questions per subcategory
repetitions=1 # just one repetition per model, setup, seed, and size combination
expid="10xExps"

mkdir -p runs

# TODO: this should be done only once per size and seed.

for size in ${sizes[@]} ; do
    benchmarks=() # reset the benchmarks list for each size

    for seed in "${seeds[@]}"; do
    

        mkdir -p "benchmarks/qs_per_subcat_${size}/"
        benchmark_file="benchmarks/qs_per_subcat_${size}/seed_${seed}.tsv"

        benchmarks+=("$benchmark_file")

        echo "Generating a benchmark with random seed: $seed"

        run .venv/bin/python3 generate_benchmark.py --config benchmark-generation-config.yaml \
            --benchmark_file "$benchmark_file" \
            --questions_per_subcategory_count "$size" \
            --seed "$seed" \
            --submodalities "audio.mastermix.wav" "symbolic.musicxml" "visual.short.png" \
            --allowed_metaq_ids 0 1 2 3 4 5 6 7 8 9
        
        # TODO: remove the time signature meta-questions
        echo "================================================================================"
        
    done

    mkdir -p benchmark-comparisons
    .venv/bin/python3 src/results_aggregation/compare_benchmark_files.py --list_of_tsvs "${benchmarks[@]}" | tee "benchmark-comparisons/${size}qs.txt"
    
    echo "Comparison of benchmarks with ${size} questions per subcategory written to benchmark-comparisons/${size}qs.txt"
    echo "================================================================================"
    echo "================================================================================"
done





# For each model, submit an independent job: that would run all sizes, all setups, all seeds, 
# and all repetitions for that model. The results would be written to a file named according 
# to the model, size, setup, seed, and repetition number. If there are multiple repetitions, 
# then the results would be aggregated at the end of the job and written to a separate file 
# named according to the model, size, setup, and seed (without the repetition number).
for model in "${models[@]}" ; do
    echo "Submitting job for model: ${model}"
    model_name="${model//\//_}"

    sbatch --parsable \
        -p cpu-ms -c2 --mem=4G \
        --job-name="${expid}_${model_name}" \
        --output="runs/${expid}_${model_name}_%j.out" \
        --error="runs/${expid}_${model_name}_%j.err" \
        run-model-multiple-times.sh --model "${model}" --sizes "${sizes[@]}" --seeds "${seeds[@]}" --setups "${setups[@]}" --repetitions "$repetitions"
done