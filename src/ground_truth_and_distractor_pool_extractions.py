"""
Methods for automatic extraction of ground truth answers and pools of distractors for the benchmark questions.
Each meta-question in the benchmark should be associated with a function in this file that implements the logic for
extracting the ground truth answer and distractor pool from the symbolic score of a piece (or some other way). The generate_benchmark.py
script will dynamically load this file and call the appropriate function for each question-piece pair to populate the
benchmark with ground truth answers and distractors.
"""

# TODO: create a directory for these methods, have single file per question, add dynamic loading of all methods in the directory, and add a template file for new questions to be added easily by future contributors.

from music21 import converter, note, chord, stream
import os
from utils import get_musicxml_file_path

def first_soprano_note_scientific_pitch_get_distractor_pool(path: str) -> list[str]:
    """
    Dummy implementation for generating a pool of distractor pitches.
    """
    return ["A4", "B4", "G4", "F4", "E4", "D4", "C4"]



def first_soprano_note_scientific_pitch_get_ground_truth(path: str) -> str:
    """
    Parses a MusicXML file and returns the scientific pitch notation 
    of the first note in the Soprano part.
    
    Args:
        path (str): The path to the directory of the piece, which contains the MusicXML file.
        
    Returns:
        str: The pitch in scientific notation (e.g., "G5", "Eb4").
    """

    # Get the path to the MusicXML file
    musicxml_path = get_musicxml_file_path(path)

    if not os.path.exists(musicxml_path):
        raise FileNotFoundError(f"Could not find file: {musicxml_path}")

    # 1. Parse the symbolic score
    score = converter.parse(musicxml_path)
    
    # 2. Identify the Soprano part
    soprano_part = None
    for p in score.parts:
        part_name = (p.partName or "").lower()
        
        # Sometimes the name is stored in the instrument metadata instead
        inst = p.getInstrument()
        inst_name = (inst.instrumentName or "").lower() if inst else ""
        
        if "soprano" in part_name or "soprano" in inst_name:
            soprano_part = p
            break
            
    # Fallback: Default to the first (top) part if "Soprano" isn't explicitly labeled
    if soprano_part is None:
        if not score.parts:
            raise ValueError("The parsed score contains no parts.")
        soprano_part = score.parts[0]
        
    # 3. Extract all sounded notes (ignores measure boundaries and rests)
    # .flatten() removes nested structures like measures
    # .notes filters out rests and empty elements
    sounded_events = soprano_part.flatten().notes
    
    if not sounded_events:
        raise ValueError("No notes were found in the identified Soprano part.")
        
    first_event = sounded_events[0]
    
    # 4. Extract the Pitch
    target_pitch = None
    if isinstance(first_event, note.Note):
        target_pitch = first_event.pitch
    elif isinstance(first_event, chord.Chord):
        # If the first event is a chord (e.g., divisi), the soprano sings the top note
        # .sortAscending() ensures the highest pitch is the last element
        target_pitch = first_event.sortAscending()[-1].pitch
    else:
        raise TypeError(f"Unexpected element type: {type(first_event)}")
        
    # 5. Format to Standard ASCII Scientific Pitch Notation
    # music21 defaults to '-' for flats (e.g., 'E-5'). We replace it with 'b' for 'Eb5'
    scientific_notation = target_pitch.nameWithOctave.replace('-', 'b')
    
    return scientific_notation


def first_soprano_note_scientific_pitch(path: str) -> tuple[str, list[str]]:
    """
    question_id: 2xxx
    question: What is the scientific pitch notation of the initial soprano note in the provided excerpt?

    Logic: Parses a MusicXML file and returns the scientific pitch notation 
    of the first note in the Soprano part.
    
    Args:
        path (str): The path to the directory of the piece, which contains the MusicXML file.
        
    Returns:
        str: The pitch in scientific notation (e.g., "G5", "Eb4").
        list[str]: A list of distractor pitches in scientific notation with ground truth excluded.
    """
    ground_truth = first_soprano_note_scientific_pitch_get_ground_truth(path)
    distractor_pool = first_soprano_note_scientific_pitch_get_distractor_pool(path)
    
    # Ensure the ground truth is not in the distractor pool
    if ground_truth in distractor_pool:
        distractor_pool.remove(ground_truth)
    
    return ground_truth, distractor_pool

# --- Example Usage --- #
if __name__ == "__main__":
    # import sys
    # # Example: 
    # path_to_musicxml = sys.argv[1] if len(sys.argv) > 1 else "path/to/bach_chorale.musicxml"
    # answer = first_soprano_note_scientific_pitch(path_to_musicxml)
    # print(f"The first soprano note is: {answer}")
    pass