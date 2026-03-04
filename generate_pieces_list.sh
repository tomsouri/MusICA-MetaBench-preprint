#!/bin/bash

find data -type f -name "symbolic.musicxml" | sort | awk -F'/' 'BEGIN {OFS="\t"; print "piece_id", "dataset", "name", "musicxml_path"} {print $(NF-1), $(NF-2), $(NF-1), $0}' > pieces.tsv
