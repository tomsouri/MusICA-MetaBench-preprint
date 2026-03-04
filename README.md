# multimodal-music-understanding-benchmark
Multimodal music understanding benchmark for LLMs on music in audio (recording), image (scan/render of sheet music), symbolic music (musicXML, MIDI, ABC, MEI, ...), and text (lyrics).


## Quickstart
- you need:
	- ffmpeg, pdftoppm, MuseScore, display access (e.g. by ssh -Y user@account)
	- musescore path needs to be passed to src/musicxml2pdf.py converter (as default value of the path to musescore)

`bash prepare_venv.sh`
`bash prepare_data.sh`

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


