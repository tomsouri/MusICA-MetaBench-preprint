#!/bin/bash
# Copyright (C) 2026  Tomáš Sourada, Katia Vendrame, Jan Hajič, jr.
#
# This file is part of the MusICA MetaBench source code, licensed under
# the GNU General Public License v3.0 or later (SPDX: GPL-3.0-or-later).
# See the LICENSE-SOURCE-CODE file in the repository root for the full
# license text, or <https://www.gnu.org/licenses/>.

# Default values
model="Qwen/Qwen3-Omni-30B-A3B-Thinking"
sizes=(1 5 10 20 50 100 200 500)
seeds=({42..51})
setups=("normal" "text-only")
repetitions=1

# Argument Parsing
# while [[ "$#" -gt 0 ]]; do
#     case $1 in
#         --model) model="$2"; shift ;;
#         --sizes) 
#             shift
#             while [[ "$#" -gt 0 && ! "$1" =~ ^-- ]]; do
#                 sizes+=("$1")
#                 shift
#             done
#             continue ;;
#         --seeds) 
#             shift
#             while [[ "$#" -gt 0 && ! "$1" =~ ^-- ]]; do
#                 seeds+=("$1")
#                 shift
#             done
#             continue ;;
#         --setups) 
#             shift
#             while [[ "$#" -gt 0 && ! "$1" =~ ^-- ]]; do
#                 setups+=("$1")
#                 shift
#             done
#             continue ;;
#         --repetitions) repetitions="$2"; shift ;;
#         *) echo "Unknown parameter passed: $1"; exit 1 ;;
#     esac
#     shift
# done

# Logic execution
echo "Running Model: $model"
echo "Sizes: ${sizes[@]}"
echo "Setups: ${setups[@]}"
echo "Seeds: ${seeds[@]}"
echo "Repetitions: $repetitions"

safe_model="${model//\//_}"
safe_model="${safe_model// /_}"

# check if either there is a single seed or the number of repetitions is 1, otherwise print warning.
if [[ ${#seeds[@]} -eq 1 || $repetitions -eq 1 ]]; then
    echo "OK: either there is a single seed or the number of repetitions is 1."
else
    echo "WARNING: there are multiple seeds and more than 1 repetition. This will lead to multiple runs for the same seed, which may not be what you intended."
fi

for size in "${sizes[@]}"; do
    for setup in "${setups[@]}"; do 
        # save the resfile paths to a list to then perform aggregation.
        # To be used for comparisons between seeds.
        current_setup_size_resfiles=() # reset the list of resfiles for the current setup and size

        for seed in "${seeds[@]}"; do
            # save the resfile paths to a list to then perform aggregation.
            # To be used for comparisons between repetitions of the same seed.
            current_setup_size_seed_resfiles=() # reset the list of resfiles for the current setup, size, and seed

            for ((i=1; i<=repetitions; i++)); do
                
                
                echo "Executing: model=$model, size=$size, seed=$seed, setup=$setup, iteration=$i"
                # TODO: how to include iteration number?
                
                mkdir -p "results/${safe_model}/${size}/${setup}/"
                # TODO: use the slurm job id in the resfile name, to avoid overwriting results when running multiple jobs in parallel.

                resfile="results/${safe_model}/${size}/${setup}/jobid_${SLURM_JOB_ID:-local}.rs${seed}.rep${i}.res.tsv"
                
                current_setup_size_seed_resfiles+=("$resfile")
                current_setup_size_resfiles+=("$resfile")

                run bash run-qwen.sh -m "${model}" -s "${size}" -e "${seed}" -t "${setup}" -r "${resfile}"
            done
            
            # if there were multiple repetitions, do the aggregation of results for this seed
            if [[ $repetitions -gt 1 ]]; then
                dir="aggregated/10repetitions_on_same_bench/${safe_model}/${size}/${setup}/seed_${seed}"
                mkdir -p $dir

                tabname="10repetitions.${safe_model}.${size}.${setup}.seed${seed}"

                .venv/bin/python3 compute_mean_stddev.py --list_of_tsvs "${current_setup_size_seed_resfiles[@]}" --output_file "${dir}/res.tsv" --gsheet_tab_name "${tabname}"
                
                echo "Results written to $dir"
            fi

        done
        # do the aggregation of results for the given setup and size, across seeds
        if [[ ${#seeds[@]} -gt 1 ]]; then
            dir="aggregated/comparison_between_seeds/${safe_model}/${size}"
            mkdir -p $dir

            tabname="comparison_between_seeds.${safe_model}.${size}.${setup}"

            .venv/bin/python3 compute_mean_stddev.py --list_of_tsvs "${current_setup_size_resfiles[@]}" --output_file "${dir}/${setup}.tsv" --gsheet_tab_name "${tabname}"
            
            echo "Results written to $dir"

            .venv/bin/python3 generate_averaged_tables.py --input_dir "aggregated/comparison_between_seeds/"
        fi

    done
done

