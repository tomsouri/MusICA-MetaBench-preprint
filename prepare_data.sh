#!/bin/bash
set -euo pipefail

DATA_ROOT="$(pwd)/data"
ORIG_ROOT="$DATA_ROOT/original/chorale-bricks"
TARGET_ROOT="$DATA_ROOT/chorale-bricks"
MASTER_MIX_DIR="$ORIG_ROOT/master-mixes"
ZIP_URL="https://zenodo.org/records/15081741/files/01_AudioAndAnnotations.zip"
ZIP_FILE="$ORIG_ROOT/01_AudioAndAnnotations.zip"
EXTRACT_DIR="$ORIG_ROOT/01_AudioAndAnnotations"

trap 'echo "Error: command '\''${BASH_COMMAND}'\'' failed at line ${LINENO}" >&2' ERR

log() {
    echo "[prepare] $*"
}

mkdir -p "$MASTER_MIX_DIR"
mkdir -p "$TARGET_ROOT"

cd "$ORIG_ROOT"
if [[ -d "$EXTRACT_DIR" ]]; then
    log "Archive already extracted at $EXTRACT_DIR; skipping unzip."
else
    if [[ -f "$ZIP_FILE" ]]; then
        log "Zip already downloaded; skipping wget."
    else
        log "Downloading 01_AudioAndAnnotations.zip..."
        wget -nc "$ZIP_URL"
    fi
    log "Unzipping file..."
    unzip -q "$ZIP_FILE"
    log "Extraction complete!"
fi

cd "$MASTER_MIX_DIR"
LIST_FILE="../list-of-master-mix-links.txt"
if [[ -f "$LIST_FILE" ]]; then
    log "Downloading master mixes..."
    wget -nc -i "$LIST_FILE"
else
    echo "Warning: master mix list not found at $LIST_FILE" >&2
fi

log "Converting .m4a master mixes to .wav..."
shopt -s nullglob
for file in *.m4a; do
    wav_output="${file%.m4a}.wav"
    if [[ -f "$wav_output" ]]; then
        log "Skipping conversion for $file (already have $wav_output)."
    else
        log "Converting $file..."
        ffmpeg -i "$file" "$wav_output"
    fi
done
shopt -u nullglob

cd "$EXTRACT_DIR"
for dir in */; do
    subdir_name="${dir%/}"
    tgt_dir="$TARGET_ROOT/$subdir_name"
    log "Preparing $subdir_name..."
    mkdir -p "$tgt_dir"

    src_csv="$dir/$subdir_name.csv"
    if [[ -f "$src_csv" ]]; then
        cp "$src_csv" "$tgt_dir/symbolic.midi.csv"
    else
        echo "Warning: missing $src_csv" >&2
    fi

    src_mid="$dir/$subdir_name.mid"
    if [[ -f "$src_mid" ]]; then
        cp "$src_mid" "$tgt_dir/symbolic.midi"
    else
        echo "Warning: missing $src_mid" >&2
    fi

    src_musicxml="$dir/$subdir_name.musicxml"
    if [[ -f "$src_musicxml" ]]; then
        cp "$src_musicxml" "$tgt_dir/symbolic.musicxml"
    else
        echo "Warning: missing $src_musicxml" >&2
    fi

    src_mei="$dir/$subdir_name.mei"
    if [[ -f "$src_mei" ]]; then
        cp "$src_mei" "$tgt_dir/symbolic.mei"
    else
        echo "Warning: missing $src_mei" >&2
    fi

    audio_file=$(find "$MASTER_MIX_DIR" -maxdepth 1 -type f -name "${subdir_name}*.wav" -print -quit || true)
    if [[ -z "$audio_file" ]]; then
        echo "Warning: no master-mix WAV found for $subdir_name" >&2
    elif [[ -f "$tgt_dir/audio.mastermix.wav" ]]; then
        log "Master mix already copied for $subdir_name; skipping."
    else
        cp "$audio_file" "$tgt_dir/audio.mastermix.wav"
    fi
done

log "Data preparation complete."