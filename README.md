# multimodal-music-understanding-benchmark
Multimodal music understanding benchmark for LLMs on music in audio (recording), image (scan/render of sheet music), symbolic music (musicXML, MIDI, ABC, MEI, ...), and text (lyrics).

## TODOs
Implement  further results aggregation script (for single benchmark instance) (#79)
- one that gets specified size (qs per category count) and seed, and for this, goes over the results directory, extracts all corresponding "normal" files and extracts a selected column from it (by default, accuracy, but also unparsable, model error, time and price are relevant), and generate a large table with 1 column per model with the accuracy for each of the criterion values

- and one that gets specified the same but compare text-only and normal setup: for every model, print the whole column for text-only and for normal setup



## To run
- adjust the script `submit-jobs.sh` to fit your needs (e.g., the usage of `sbatch` command)
- to use it as it is, you need to have an API key defined in your `~/.bashrc` file for each model-size-setup tuple, in
  the following format: `<model_name_with_underscores>_<count>[_to]`
    - e.g., among many others, I have the following lines in my `~/.bashrc` file:
    export xiaomi_mimo_v2_omni_20_to="sk-or-v1..."
    export google_gemini_3_1_flash_lite_preview_20="sk-or-v1..."
    export google_gemini_3_1_flash_lite_preview_20_to="sk-or-v1..."


## Quickstart
- you need:
	- ffmpeg, pdftoppm, MuseScore, display access (e.g. by ssh -Y user@account)
	- musescore path needs to be passed to src/musicxml2pdf.py converter (as default value of the path to musescore)

Prepare virtual env:
`bash prepare_venv.sh`

Prepare data to the desired format:
`bash prepare_data.sh`

Generate the benchmark items:
`.venv/bin/python3 generate_benchmark.py --config benchmark-generation-config.yaml`

Run LLMs on the benchmark:
`.venv/bin/python3 run_benchmark.py --config eval-config.yaml`
- print logs to `logs/run_<datetime>/benchmark_results.tsv` and appends them to Google sheet

Evaluate:
- is performed already by `run_benchmark.py`, with output in `evaluation_summary.tsv`

Then, the data is in
data/$DATASET/$PIECE_ID/{audio.mastermix.wav, image.pdf, image.png, symbolic.musicxml, symbolic.abc.txt, symbolic.mei, symbolic.midi}

The interesting ones in the preliminary experiments are audio.mastermix.wav, image.pdf, and symbolic.abc.txt.

## Your own data
- provide the data in data/$DATASET/$PIECE_ID/<music-file>.[pdf/wav/png/musicxml/...]
- the file `symbolic.musicxml` for every piece is required for automatic benchmark generation
- run `generate_pieces_list.sh` to obtain the list of pieces, which is required for automatic benchmark generation

## Your own questions
- you may define your own questions
- for that, provide the questions in `meta-questions.tsv` file (see example for the format), and implement a python
  method (inside `src/ground_truth_extractions.py`) that automatically extracts the ground truth for given musicxml file
  (and link it from the `meta-questions.tsv` file)




## Our approach
- come up with a question, e.g. "what is the pitch of the first note in the soprano part, expressed in scientific
  notation?"
- get Gemini 3.1 Pro Preview to improve the wording: "Reformulate this question and suggest pool of options to be used
  in a benchmark for evaluating multimodal LLMs on understanding audio, image sheet music and symbolic scores:
  <QUESTION>"
- get the same model to generate the python method that would extract the ground truth: "And now, carefully implement a
  python method, that would receive musicxml as the input file representing the music excerpt, and using music21 library
  would extract the correct answer to this question (that is, extract the pitch of the first note in the soprano part in
  scientific notation)."
- decide to which modalities is it applicable
- decide which distractors to include in the pool
- and put the question as a single row to the meta-questions.tsv


## Guidelines for Custom Datasets

1.  **Repository Setup**: Download the project's repository.
2.  **Environment**: Install the required dependencies:
    `bash prepare_venv.sh`
3.  **Data Structure**: Place your data in the `data/` directory using the following structure:
    `data/<dataset-name>/<piece-name>/<modality>.<format>`
    *   *Example*: `data/asap/bwv846/symbolic.musicxml`
    *   **Required**: A `symbolic.musicxml` file is mandatory, as the ground truth is extracted from it.
    *   **Optional**: Additional modalities (e.g., `audio.wav`, `visual.png`) are optional. Note that modalities not provided cannot be used in evaluation.
4.  **Configuration (Optional)**: Edit `generation-config.yaml` to customize generation parameters (such as benchmark size). If skipped, the default configuration is used.
5.  **Define Ontology (Optional)**: Update the ontology of possible values for the wildcards used in prompts.
6.  **Index Pieces**: Run `generate_pieces_list.sh` to generate the list of available pieces.
    `bash generate_pieces_list.sh`
7.  **Generate Benchmark**: Run the `generate_benchmark.py` script to execute the benchmark generation pipeline.
    `.venv/bin/python generate_benchmark.py`
8.  **Setup Evaluation**: Configure `eval-config.yaml` to specify which models to evaluate, including their API endpoint URLs and API keys.
9.  **Run Evaluation**: Run the `run_benchmark.py` script to execute the selected models on the generated benchmark.
    `.venv/bin/python run_benchmark.py`
10. **Analyze**: Inspect the generated fine-grained results.

