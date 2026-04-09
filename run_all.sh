#!/usr/bin/env bash
# run_all.sh
#
# THIS IS THE ENTRY POINT FOR RUNNING ALL THE EXPERIMENTS.
#
# Convenience wrapper: generates benchmarks first, then submits experiment jobs.
# Edit the variables below (or override them from the command line in a future
# iteration) to configure a full experiment run.

set -euo pipefail

# ══════════════════════════════════════════════════════════════════════════════
# Configuration — edit these as needed
# ══════════════════════════════════════════════════════════════════════════════

seeds=({43..54}) # 12 different seeds for benchmark generation
sizes=(
    5
    10
    20
    50
    100
)

# ══════════════════════════════════════════════════════════════════════════════
# Step 1 — Generate benchmarks (idempotent; skips existing files)
# ══════════════════════════════════════════════════════════════════════════════
# TODO: be careful: the benchmark generates only once!!
echo "=== Generating benchmarks ==="
bash generate_benchmarks.sh \
    --sizes  "${sizes[@]}" \
    --seeds  "${seeds[@]}"

# ══════════════════════════════════════════════════════════════════════════════
# Step 2a — 10 times experiments, size=5, compare normal vs. text-only
# ══════════════════════════════════════════════════════════════════════════════

repetitions=1
seeds=({43..52}) # just 10 seeds for the experiments (not all 12 benchmark seeds)
setups=(
    "normal"
    "text-only"
)
expid="10xExps-n-vs-to"
sizes=(
    5
    # 10
    # 20
    # 50
)

models=(
    "google/gemini-2.0-flash-lite-001"
    # "aggregate-gpt-4o"
    "aggregate-mistral"
    # "aggregate-gpt-5"
    # "google/gemini-2.5-flash-lite"
    # "xiaomi/mimo-v2-omni"
    "google/gemini-3.1-flash-lite-preview"
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
# Step 2b — 10 times experiments, size=10 to 50, normal setup only (no text-only)
# ══════════════════════════════════════════════════════════════════════════════

repetitions=1
seeds=({43..52}) # just 10 seeds for the experiments (not all 12 benchmark seeds)
setups=(
    "normal"
    # "text-only"
)
expid="10xExps"
sizes=(
    # 5
    10
    20
    50
    # 100
)

models=(
    "google/gemini-2.0-flash-lite-001"
    # "aggregate-gpt-4o"
    "aggregate-mistral"
    # "aggregate-gpt-5"
    # "google/gemini-2.5-flash-lite"
    # "xiaomi/mimo-v2-omni"
    "google/gemini-3.1-flash-lite-preview"
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
# Step 3 — 10 times experiments for other models - normal setup only (no text-only)
# ══════════════════════════════════════════════════════════════════════════════
sizes=(
    5
    10
)

models=(
    # "google/gemini-2.0-flash-lite-001"
    "aggregate-gpt-4o"
    # "aggregate-mistral"
    # "aggregate-gpt-5"
    "google/gemini-2.5-flash-lite"
    # "xiaomi/mimo-v2-omni"
    # "google/gemini-3.1-flash-lite-preview"
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
# Step 4...: TODO: run 10 times on the same benchmark instance (for flash 3.1 only, normal setup, different sizes)
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# Step 5...: TODO: select one size of the benchmark and run all models (add more models such that it would make more sense) once on it: all setups (now we should have noisy setup ready).
# Then, aggregate the results using generate_aggregated_table.py.
# ══════════════════════════════════════════════════════════════════════════════


