#!/bin/bash

# Create data directory if not present
mkdir -p data/original/chorale-bricks
mkdir -p data/chorale-bricks

# Download and unzip the file
cd data/original/chorale-bricks
# echo "Downloading 01_AudioAndAnnotations.zip..."
# wget https://zenodo.org/records/15081741/files/01_AudioAndAnnotations.zip
# echo "Unzipping file..."
# unzip -q 01_AudioAndAnnotations.zip
# echo "Done!"

mkdir -p master-mixes
cd master-mixes
# echo "Downloading master mixes..."
# wget -i ../list-of-master-mix-links.txt

# Using ffmpeg, convert each .m4a file in master-mixes to .wav format, and save it in the same directory with the same name (but .wav extension)
for file in *.m4a; do
    ffmpeg -i "$file" "${file%.m4a}.wav"
done
cd ../

# for every directory inside 01_AudioAndAnnotations, create a subdirectory in data/chorale-bricks (with the same
# name) and copy each file from the original directory to the new one, for those:
# - subdir_name/subdir_name.csv, copy to data/chorale-bricks/subdir_name/symbolic.midi.csv
# - subdir_name/subdir_name.mid, copy to data/chorale-bricks/subdir_name/symbolic.midi
# - subdir_name/subdir_name.musicxml, copy to data/chorale-bricks/subdir_name/symbolic.musicxml
# - subdir_name/subdir_name.mei, copy to data/chorale-bricks/subdir_name/symbolic.mei

cd 01_AudioAndAnnotations
for dir in */; do
    subdir_name=$(basename "$dir")
    tgt_dir="../../../chorale-bricks/$subdir_name"
    cp "$dir/$subdir_name.csv" "$tgt_dir/symbolic.midi.csv"
    cp "$dir/$subdir_name.mid" "$tgt_dir/symbolic.midi"
    cp "$dir/$subdir_name.musicxml" "$tgt_dir/symbolic.musicxml"
    cp "$dir/$subdir_name.mei" "$tgt_dir/symbolic.mei"
    cp "../master-mixes/$subdir_name*.wav" "$tgt_dir/audio.mastermix.wav"
done











