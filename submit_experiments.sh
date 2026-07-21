#!/usr/bin/env bash
# Copyright (C) 2026  Tomáš Sourada, Katia Vendrame, Jan Hajič, jr.
#
# This file is part of the MusICA MetaBench source code, licensed under
# the GNU General Public License v3.0 or later (SPDX: GPL-3.0-or-later).
# See the LICENSE-SOURCE-CODE file in the repository root for the full
# license text, or <https://www.gnu.org/licenses/>.

# submit_experiments.sh
#
# Submits one SLURM job per model. Each job evaluates every combination of
# size × seed × setup × repetition for that model.
#
# Usage:
#   ./submit_experiments.sh \
#       --models "google/gemini-2.0-flash-lite-001" "aggregate-gpt-4o" \
#       --setups normal text-only \
#       --sizes 20 \
#       --seeds 55 \
#       --repetitions 1 \
#       --expid 10xExps \
#       [--partition cpu-ms] \
#       [--cpus 2] \
#       [--mem 4G]

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
declare -a models=()
declare -a setups=()
declare -a sizes=()
declare -a seeds=()
repetitions=1
expid="experiment"
partition="cpu-ms"
cpus=2
mem="4G"

# ── Argument parsing ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --models)
            shift
            while [[ $# -gt 0 && ! "$1" == --* ]]; do
                models+=("$1"); shift
            done
            ;;
        --setups)
            shift
            while [[ $# -gt 0 && ! "$1" == --* ]]; do
                setups+=("$1"); shift
            done
            ;;
        --sizes)
            shift
            while [[ $# -gt 0 && ! "$1" == --* ]]; do
                sizes+=("$1"); shift
            done
            ;;
        --seeds)
            shift
            while [[ $# -gt 0 && ! "$1" == --* ]]; do
                seeds+=("$1"); shift
            done
            ;;
        --repetitions)
            repetitions="$2"; shift 2
            ;;
        --expid)
            expid="$2"; shift 2
            ;;
        --partition)
            partition="$2"; shift 2
            ;;
        --cpus)
            cpus="$2"; shift 2
            ;;
        --mem)
            mem="$2"; shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2; exit 1
            ;;
    esac
done

for var in models setups sizes seeds; do
    declare -n arr="$var"
    if [[ ${#arr[@]} -eq 0 ]]; then
        echo "Error: --${var} is required and must not be empty." >&2
        exit 1
    fi
done

# ── Submission ───────────────────────────────────────────────────────────────
mkdir -p runs

for model in "${models[@]}"; do
    model_name="${model//\//_}"
    echo "Submitting job for model: ${model}"

    sbatch --parsable \
        -p "$partition" \
        -c "$cpus" \
        --mem="$mem" \
        --job-name="${expid}_${model_name}" \
        --output="runs/${expid}_${model_name}_%j.out" \
        --error="runs/${expid}_${model_name}_%j.err" \
        run-model-multiple-times.sh \
            --model  "$model" \
            --sizes  "${sizes[@]}" \
            --seeds  "${seeds[@]}" \
            --setups "${setups[@]}" \
            --repetitions "$repetitions"
done