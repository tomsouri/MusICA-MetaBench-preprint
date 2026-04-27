# Music I Care About Meta-Benchmark (MusICA MetaBench)

A comprehensive benchmark suite for evaluating Multimodal Large Language Models (MLLMs) on music perception tasks across multiple modalities (Audio, Symbolic, and Visual).

## Overview

This project provides a systematic framework to assess how well MLLMs understand classical music. It generates music theory questions covering pitch, rhythm, and harmony using various modalities:
- **Audio**: WAV files (mastermixes).
- **Symbolic**: MusicXML and ABC notation.
- **Visual**: PNG images of scores.

The benchmark includes a flexible generation pipeline, an inference engine via the OpenRouter API, and a suite of evaluation and aggregation tools.

## Key Features

- **8-Step Generation Pipeline**: Controlled generation of questions, ground truth, and distractors.
- **Multi-Modality**: Support for evaluating models on different representations of the same musical content.
- **NOTA Support**: Includes "None of the above" as a correct answer for ~20% of questions to test for hallucination/over-confidence.
- **Extensible Configuration**: YAML-based setup for benchmarks, evaluations, and music theory ontologies.
- **Statistical Analysis**: Tools for significance testing (pairwise comparison) and aggregate reporting.

## Table of Contents
1. [Setup](#setup)
2. [Quick Start](#quick-start)
3. [Technical Guidelines](#technical-guidelines)
4. [Dataset Information](#dataset-information)
5. [Inference & Parsing](#inference--parsing)
6. [Evaluation & Results](#evaluation--results)
7. [Logs & Reproducibility](#logs--reproducibility)

## Setup

### Environment
```bash
# Create a virtual environment and install dependencies
bash prepare_venv.sh
```

### API Configuration
Set your OpenRouter API key:
```bash
export OPENROUTER_API_KEY="your-api-key"
```

### Data Preparation
```bash
# Download ChoraleBricks and process it to the required format
bash prepare_data.sh
```

## Quick Start

### Step A: Generate a Benchmark
```bash
.venv/bin/python3 generate_benchmark.py \
    --config benchmark-generation-config.yaml \
    --benchmark_file test_benchmark.tsv \
    --size 10 
```
*The `size` parameter specifies questions per category-modality combination.*

### Step B: Run Inference
```bash
.venv/bin/python3 run_benchmark.py \
    --config eval-config.yaml \
    --benchmark_file test_benchmark.tsv \
    --models "openai/gpt-4o"
```

## Technical Guidelines

### Custom Datasets
To apply MusICA MetaBench to a custom dataset:
1. **Prepare Pieces**: Organize your musical pieces in a directory structure. Each piece should have its own folder.
2. **Metadata**: Create a `pieces.tsv` file listing the paths to these directories.
3. **Format Support**: Ensure the desired modalities (Audio, Symbolic, Visual) are available in each piece directory (e.g., `symbolic.musicxml`, `audio.mastermix.wav`, `image.png`).

### Custom Formats
To add support for a new musical format:
1. Update `musical_piece_format_info` in `run_benchmark.py` or your config file to include the new extension and its description.
2. Ensure the generation pipeline (`generate_benchmark.py`) is aware of the new submodality by adding it to the `benchmark-generation-config.yaml`.

### New Question Templates
Adding a new question template involves:
1. **Define Meta-Question**: Add a new row to [meta-questions.tsv](meta-questions.tsv) with a unique ID, category, and text template (using `{wildcards}`).
2. **Implement Extraction**: Add a corresponding function in [src/ground_truth_and_distractor_pool_extractions.py](src/ground_truth_and_distractor_pool_extractions.py). This function must:
   - Accept arguments matching the wildcards.
   - Return a `(ground_truth, distractor_pool)` tuple.
3. **Ontology**: If needed, update [ontology.yaml](ontology.yaml) to include new musical concepts.

## Dataset Information

### ChoraleBricks
A collection of Bach chorale fragments.
- **Benchmark Instance:** [A-pre-generated_full_benchmark.tsv](benchmarks/A-pre-generated_full_benchmark.tsv)

### ChoralSynth
ChoralSynth is a synthetic dataset for testing specific music understanding capabilities, available in a separate branch.
- **Switch to branch:** `git checkout choralsynth`
- **Setup:** Follow the `prepare_data.sh` script in that branch to synthesize or download the audio files.
- **Benchmark Instance:** [benchmark_viena4x22.tsv](benchmark_viena4x22.tsv) (Example instance)

## Inference & Parsing

### User Prompt Template
The prompt template defines how the question and musical context are presented to the LLM. It can be customized in [eval-config.yaml](eval-config.yaml).
- **Template Variable:** `user_prompt_template`
- **Placeholder Replacement:** `<FORMAT>`, `<QUESTION>`, `<OPTIONS_TEXT>`, and `<OPTION_LABELS>` are dynamically replaced during runtime.

### Response Parsing
Responses are parsed to extract the final letter choice. The logic is:
1. **Extraction**: `run_benchmark.py` uses methods loaded from `src/extraction_methods.py` (configured via `path_to_extraction_file`).
2. **Format**: The model is instructed to end with `Final Answer: <answer>`.
3. **Regex**: A regex typically searches for the last occurrence of a single letter enclosed in parentheses or following "Final Answer:".

## Evaluation & Results

### Per-Category Analysis
Generate detailed plots with evaluation across categories (pitch, rhythm, harmony, etc.):
```bash
bash generate_the_plots.sh
```
The script processes `results.tsv` and generates visualizations in the `aggregated/` folder.

### Technical Setup of Running LLMs
- **Environment:** Tested on Linux (Ubuntu 22.04) using Python 3.10+.
- **LLM Configuration:** Controlled via [eval-config.yaml](eval-config.yaml).
  - **Seed:** Set to `42` for reproducibility.
  - **API:** Primarily uses OpenRouter for access to various models.
  - **Parameters:** Default settings for temperature and max tokens are managed by the API provider unless specified in the payload.

## Logs & Reproducibility

### LLM Inference Logs
Full logs of LLM inference (prompts and raw JSON responses) are stored for selected models:
- [Link to Logs Directory](logs/) <!-- TODO: Add more specific links if available -->

### Reproducing Results
... <!-- TODO: Instructions for reproducing paper results -->

## Project Structure
| Path | Description |
| :--- | :--- |
| `benchmarks/` | Pre-generated and custom benchmark TSV files. |
| `data/` | Source musical pieces (ChoraleBricks, Vienna piano corpus, etc.). |
| `src/` | Core logic for ground truth extraction and distractor generation. |
| `results/` | Raw results from inference runs. |
| `aggregated/` | Processed results and significance tests. |
| `tables/` | LaTeX and TSV tables for paper results. |


