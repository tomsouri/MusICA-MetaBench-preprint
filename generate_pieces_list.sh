#!/bin/bash
# Copyright (C) 2026  Tomáš Sourada, Katia Vendrame, Jan Hajič, jr.
#
# This file is part of the MusICA MetaBench source code, licensed under
# the GNU General Public License v3.0 or later (SPDX: GPL-3.0-or-later).
# See the LICENSE-SOURCE-CODE file in the repository root for the full
# license text, or <https://www.gnu.org/licenses/>.

# Define the output TSV file
OUTPUT_FILE="pieces.tsv"
DATA_DIR="data"

# Write the header to the TSV file
printf "%s\t%s\t%s\t%s\n" "piece_id" "dataset" "name" "path" > "$OUTPUT_FILE"

# Make sure the data directory exists
if [ ! -d "$DATA_DIR" ]; then
    echo "Error: Directory '$DATA_DIR' does not exist."
    exit 1
fi

# Iterate over all dataset directories inside data/
for dataset_path in "$DATA_DIR"/*/; do
    # Skip if it's not a directory (in case data/ is empty)
    [ -d "$dataset_path" ] || continue

    # Extract the base name of the dataset directory
    dataset_name=$(basename "$dataset_path")

    # Skip the "original" directory
    if [ "$dataset_name" = "original" ]; then
        continue
    fi
    # Skip the "white_noise" directory
    if [ "$dataset_name" = "white_noise" ]; then
        continue
    fi

    # Iterate over all piece directories inside the current dataset
    for piece_path in "$dataset_path"*/; do
        # Skip if it's not a directory (in case the dataset dir is empty except for files)
        [ -d "$piece_path" ] || continue

        # Extract the base name of the piece directory
        piece_name=$(basename "$piece_path")
        
        # Format the relative path without a trailing slash
        clean_path="$DATA_DIR/$dataset_name/$piece_name"

        # Write the entry to the TSV file
        printf "%s\t%s\t%s\t%s\n" "$piece_name" "$dataset_name" "$piece_name" "$clean_path" >> "$OUTPUT_FILE"
    done
done

echo "Successfully generated $OUTPUT_FILE"