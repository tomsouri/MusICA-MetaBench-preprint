#!/usr/bin/env python3
"""
Convert MusicXML files to PDF using music21.

Usage:
    python musicxml_to_pdf.py -i input.musicxml -o output.pdf
"""

import subprocess
import os
import platform
import argparse, sys

def get_musescore_path():
    """Returns the default MuseScore executable path based on the OS."""
    system = platform.system()
    if system == "Windows":
        # Check standard installation paths for MuseScore 4 and 3
        paths = [
            r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe",
            r"C:\Program Files\MuseScore 3\bin\MuseScore3.exe"
        ]
        for p in paths:
            if os.path.exists(p): return p
        raise FileNotFoundError("MuseScore executable not found. Please specify the path.")
    
    elif system == "Darwin": # macOS
        paths = [
            "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
            "/Applications/MuseScore 3.app/Contents/MacOS/mscore"
        ]
        for p in paths:
            if os.path.exists(p): return p
        raise FileNotFoundError("MuseScore not found in macOS Applications.")
    
    elif system == "Linux":
        # Usually just 'mscore' in the PATH on Linux
        return "mscore3"

def convert_musicxml_to_pdf(input_mxml, output_pdf=None, musescore_path=None):
    """
    Converts a MusicXML file to PDF using MuseScore.
    Returns True if successful, False otherwise.
    """
    if not os.path.exists(input_mxml):
        print(f"Input file does not exist: {input_mxml}", file=sys.stderr)
        return False

    if output_pdf is None:
        # Default output name: same as input but with .pdf extension
        base_name = os.path.splitext(input_mxml)[0]
        output_pdf = f"{base_name}.pdf"

    if musescore_path is None:
        musescore_path = get_musescore_path()

    # The command line argument structure for MuseScore conversion
    command = [
        musescore_path,
        input_mxml,
        "-o", output_pdf
    ]

    print(f"Converting '{input_mxml}' to '{output_pdf}'...")
    
    try:
        # Run the command and wait for it to finish
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Verify the file was actually created
        if not os.path.exists(output_pdf):
            print(f"Error: MuseScore exited normally but the output file '{output_pdf}' was not created.", file=sys.stderr)
            return False
            
        print("Conversion successful!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(f"Could not find the MuseScore executable at: {musescore_path}", file=sys.stderr)
        return False

def main():
    """Main function to handle command-line arguments and conversion."""
    parser = argparse.ArgumentParser(
        description="Convert MusicXML files to PDF using music21",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Input MusicXML file path"
    )
    
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output PDF file path"
    )

    parser.add_argument(
        "-m", "--musescore",
        required=False,
        default="/opt/tools/musescore/MuseScore-Studio-4.6.4.253351238-x86_64.AppImage",
        help="Path to the MuseScore executable (optional, will try to auto-detect if not provided)"
    )
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()

    if not args.musescore:
        try:
            args.musescore = get_musescore_path()
            print(f"Auto-detected MuseScore path: {args.musescore}")
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
    
    # Perform the conversion
    success = convert_musicxml_to_pdf(input_mxml=args.input, output_pdf=args.output, musescore_path=args.musescore)
    
    # If conversion failed, exit with error code so the bash script registers a failure
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()



# import sys
# import argparse
# import music21

# import os
# from music21 import environment

# mscore_path = os.environ.get("MUSESCORE_PATH", None)
# if mscore_path:
#     us = environment.UserSettings()
#     us['musescoreDirectPNGPath'] = mscore_path
#     us['musicxmlPath'] = mscore_path
# else:
#     print("Warning: MUSESCORE_PATH not set — MuseScore features will not work.")



# def convert_musicxml_to_pdf(input_path, output_path):
#     """
#     Convert a MusicXML file to PDF.
    
#     Args:
#         input_path (str): Path to the input MusicXML file
#         output_path (str): Path for the output PDF file
#     """
#     try:
#         # Parse the MusicXML file
#         score = music21.converter.parse(input_path)
        
#         # Clear all title/composer related fields that MuseScore might use
#         if score.metadata:
#             score.metadata.title = ""
#             score.metadata.composer = ""
#             score.metadata.movementName = ""
        
#         # Also set the movement title attribute which MuseScore uses for display
#         score.movementName = ""
        
#         # Write as PDF
#         score.write("musicxml.pdf", fp=output_path)
#         # TODO: for some reason, this also writes to a file output_path-'.pdf'+'.musicxml', need to investigate
        
#         print(f"Successfully converted '{input_path}' to '{output_path}'")
        
#     except FileNotFoundError:
#         print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
#         sys.exit(1)
#     except music21.converter.ConverterException as e:
#         print(f"Error: Unable to parse MusicXML file: {e}", file=sys.stderr)
#         sys.exit(1)
#     except Exception as e:
#         print(f"Error: An unexpected error occurred: {e}", file=sys.stderr)
#         sys.exit(1)

# def main():
#     """Main function to handle command-line arguments and conversion."""
#     parser = argparse.ArgumentParser(
#         description="Convert MusicXML files to PDF using music21",
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#         epilog=__doc__
#     )
    
#     parser.add_argument(
#         "-i", "--input",
#         required=True,
#         help="Input MusicXML file path"
#     )
    
#     parser.add_argument(
#         "-o", "--output",
#         required=True,
#         help="Output PDF file path"
#     )
    
#     # If no arguments provided, show help
#     if len(sys.argv) == 1:
#         parser.print_help()
#         sys.exit(1)
    
#     args = parser.parse_args()
    
#     # Perform the conversion
#     convert_musicxml_to_pdf(args.input, args.output)

# if __name__ == "__main__":
#     main()
