# multimodal-music-understanding-benchmark
Multimodal music understanding benchmark for LLMs on music in audio (recording), image (scan/render of sheet music), symbolic music (musicXML, MIDI, ABC, MEI, ...), and text (lyrics).


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
