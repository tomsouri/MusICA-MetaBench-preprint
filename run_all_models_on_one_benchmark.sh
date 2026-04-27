#!/usr/bin/env bash
# run_all_models_on_one_benchmark.sh
#
# THIS IS THE ENTRY POINT FOR RUNNING THE EXPERIMENTS ON ALL MODELS ON ONE BENCHMARK INSTANCE.
#
# Convenience wrapper: generates benchmarks first, then submits experiment jobs.
# Edit the variables below (or override them from the command line in a future
# iteration) to configure a full experiment run.

set -euo pipefail

# ══════════════════════════════════════════════════════════════════════════════
# Configuration — edit these as needed
# ══════════════════════════════════════════════════════════════════════════════

seeds=({52..52}) # single benchmark instance with seed 52
sizes=(
    20
)

# ══════════════════════════════════════════════════════════════════════════════
# Step 1 — Generate benchmarks (idempotent; skips existing files)
# ══════════════════════════════════════════════════════════════════════════════
echo "=== Generating benchmarks ==="
bash generate_benchmarks.sh \
    --sizes  "${sizes[@]}" \
    --seeds  "${seeds[@]}"


# ══════════════════════════════════════════════════════════════════════════════
# MULTIMODAL MODELS, IN 3 SETUPS (WHITE NOISE, NORMAL, TEXT-ONLY)
# ══════════════════════════════════════════════════════════════════════════════


repetitions=1
setups=(
    "normal"
    "text-only"
    "white-noise"
)
expid="ChSAllSetups"

models=(
    "google/gemini-2.0-flash-lite-001"
    "google/gemini-3.1-flash-lite-preview"
    "aggregate-gpt-4o"
    "aggregate-mistral"
    "google/gemini-2.5-flash-lite"
    "aggregate-gpt-5"
    "aggregate-gpt-5-full"
    # "xiaomi/mimo-v2-omni"
)


echo "=== Submitting experiment jobs ==="
bash submit_experiments.sh \
    --models      "${models[@]}" \
    --setups      "${setups[@]}" \
    --sizes       "${sizes[@]}" \
    --seeds       "${seeds[@]}" \
    --repetitions "$repetitions" \
    --expid       "$expid"



# ══════════════════════════════════════════════════════════════════════════════
# COSTLY MULTIMODAL MODELS, JUST NORMAL SETUP# 
# ══════════════════════════════════════════════════════════════════════════════


repetitions=1
setups=(
    "normal"
)
expid="ChS"

models=(
    "google/gemini-3.1-pro-preview"
)




echo "=== Submitting experiment jobs ==="
bash submit_experiments.sh \
    --models      "${models[@]}" \
    --setups      "${setups[@]}" \
    --sizes       "${sizes[@]}" \
    --seeds       "${seeds[@]}" \
    --repetitions "$repetitions" \
    --expid       "$expid"


# ══════════════════════════════════════════════════════════════════════════════
# TEXT-ONLY MODELS, IN TEXT-ONLY SETUP
# ══════════════════════════════════════════════════════════════════════════════

setups=(
    "text-only"
)
expid="ChSTextOnly"

models=(
    "google/gemma-3-27b-it"
    "meta-llama/llama-4-scout"
    "deepseek/deepseek-v3.2"
)



echo "=== Submitting experiment jobs ==="
bash submit_experiments.sh \
    --models      "${models[@]}" \
    --setups      "${setups[@]}" \
    --sizes       "${sizes[@]}" \
    --seeds       "${seeds[@]}" \
    --repetitions "$repetitions" \
    --expid       "$expid"

