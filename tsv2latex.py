#!/usr/bin/env python3
# Copyright (C) 2026  Tomáš Sourada, Katia Vendrame, Jan Hajič, jr.
#
# This file is part of the MusICA MetaBench source code, licensed under
# the GNU General Public License v3.0 or later (SPDX: GPL-3.0-or-later).
# See the LICENSE-SOURCE-CODE file in the repository root for the full
# license text, or <https://www.gnu.org/licenses/>.

"""Convert a TSV file to a LaTeX booktabs table."""

import sys
import csv

def tsv_to_latex(input_file, output_file=None):
    with open(input_file, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        rows = list(reader)

    if not rows:
        print("Empty file.", file=sys.stderr)
        return

    header, *body = rows
    ncols = len(header)
    col_spec = "l" * ncols  # left-aligned; tweak as needed

    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        rf"  \begin{{tabular}}{{{col_spec}}}",
        r"    \toprule",
        "    " + " & ".join(header) + r" \\",
        r"    \midrule",
    ]

    for row in body:
        # Pad or trim row to match header length
        row = (row + [""] * ncols)[:ncols]
        lines.append("    " + " & ".join(row) + r" \\")

    lines += [
        r"    \bottomrule",
        r"  \end{tabular}",
        r"  \caption{TODO}",
        r"  \label{tab:TODO}",
        r"\end{table}",
    ]

    output = "\n".join(lines)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output + "\n")
    else:
        print(output)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} input.tsv [output.tex]", file=sys.stderr)
        sys.exit(1)

    tsv_to_latex(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
