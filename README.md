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
