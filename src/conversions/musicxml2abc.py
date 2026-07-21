#!/usr/bin/env python3
# Copyright (C) 2026  Tomáš Sourada, Katia Vendrame, Jan Hajič, jr.
#
# This file is part of the MusICA MetaBench source code, licensed under
# the GNU General Public License v3.0 or later (SPDX: GPL-3.0-or-later).
# See the LICENSE-SOURCE-CODE file in the repository root for the full
# license text, or <https://www.gnu.org/licenses/>.

import sys
import os

def convert_file(input_path: str, output_path: str) -> None:
    """Convert a MusicXML file to ABC and write the result."""
    # Prevent abc_xml_converter from parsing our command-line
    #import sys as _sys
    #old_argv = _sys.argv[:]
    #_sys.argv = [_sys.argv[0]]
    output_path = determine_output_path(input_path, output_path)

    from abc_xml_converter import convert_xml2abc

    #_sys.argv = old_argv

    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    try:
        abc_text = convert_xml2abc(file_to_convert=input_path)
    except Exception as e:
        raise RuntimeError(f"Conversion failed: {e}") from e

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(abc_text)
    except Exception as e:
        raise RuntimeError(f"Failed to write output file '{output_path}': {e}") from e

def determine_output_path(input_path: str, explicit_output: str | None) -> str:
    """Determine the output .abc filename."""
    if explicit_output:
        return explicit_output

    base, ext = os.path.splitext(input_path)
    if ext.lower() not in [".musicxml", ".xml"]:
        raise ValueError(
            "Input file must have extension .musicxml or .xml "
            "when --output is not provided."
        )
    return base + ".abc"


def main():
    if len(sys.argv) < 2:
        print("Usage: xxx.py INPUT_FILE OUTPUT_FILE")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv)>2 else None

    try:
        convert_file(input_file, output_file)
        print(f"Converted successfully: {output_file}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
