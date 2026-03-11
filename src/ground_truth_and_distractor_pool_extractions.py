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

def nth_voice_note_scientific_pitch_get_ground_truth(path: str, values: dict) -> str:
    """
    Logic: Parses a MusicXML file and returns the scientific pitch notation 
    of the order-th note in the specified voice part.
    
    Args:
        path (str): The path to the directory of the piece, which contains the MusicXML file.
        values (dict): A dictionary containing the value for {order} and {voice}, e.g., {"order": 1, "voice": "S"}
    """
    # Get the path to the MusicXML file
    musicxml_path = get_musicxml_file_path(path)

    if not os.path.exists(musicxml_path):
        raise FileNotFoundError(f"Could not find file: {musicxml_path}")
    
    # Parse the MusicXML file into a music21 Stream
    score = converter.parse(musicxml_path)
    
    # Map the requested voice to the corresponding part index
    voice_mapping = {
        'S': 0, # Soprano
        'A': 1, # Alto
        'T': 2, # Tenor
        'B': 3  # Bass
    }
    
    voice_key = values.get('voice')
    if voice_key not in voice_mapping:
        raise ValueError(f"Invalid voice specified: {voice_key}. Expected one of 'S', 'A', 'T', 'B'.")
        
    part_index = voice_mapping[voice_key]
    
    # Check if the score has the expected number of parts
    if part_index >= len(score.parts):
        raise IndexError(f"The parsed score does not contain a part for voice '{voice_key}'.")
        
    target_part = score.parts[part_index]
    
    # Flatten the part (to remove measure hierarchies) and extract only the notes (ignoring rests/chords)
    notes = list(target_part.flatten().getElementsByClass(note.Note))
    
    if not notes:
        raise ValueError(f"No valid notes found in part '{voice_key}'.")
        
    # Determine the index based on the 'order'
    order = values.get('order')
    if order == 'end':
        note_index = -1
    else:
        try:
            # Subtract 1 because standard list indices are 0-indexed, but the prompt uses 1-indexed (1: first)
            note_index = int(order) - 1
        except (ValueError, TypeError):
            raise ValueError(f"Invalid order specified: {order}. Expected integer or 'end'.")
            
    # Check if the index is out of bounds
    if note_index >= len(notes) or note_index < -len(notes):
        raise IndexError(f"Requested note order '{order}' is out of bounds. The part has {len(notes)} notes.")
        
    # Get the target note and return its scientific pitch notation
    target_note = notes[note_index]
    
    return target_note.nameWithOctave


def nth_voice_note_scientific_pitch(path: str, values: dict) -> tuple[str, list[str]]:
    """
    meta-question_id: 0
    meta-question: What is the scientific pitch notation of the {order} {voice} note in the provided excerpt?
    
    Logic: Parses a MusicXML file and returns the scientific pitch notation 
    of the order-th note in the specified voice part.
    
    Args:
        path (str): The path to the directory of the piece, which contains the MusicXML file.
        values (dict): A dictionary containing the value for {order} and {voice}, e.g., {"order": 1, "voice": "S"}
        
    Returns:
        str: The pitch in scientific notation (e.g., "G5", "Eb4").
        list[str]: A list of distractor pitches in scientific notation with ground truth excluded.
    """
    ground_truth = nth_voice_note_scientific_pitch_get_ground_truth(path, values)
    distractor_pool = ["A4", "B4", "G4", "F4", "E4", "D4", "C4"]
    
    # Ensure the ground truth is not in the distractor pool
    if ground_truth in distractor_pool:
        distractor_pool.remove(ground_truth)
    
    return ground_truth, distractor_pool

# def get_musicxml_file_path(piece_dir: str) -> str:
#     """
#     Given the directory of a piece, returns the path to the MusicXML file.
    
#     Args:
#         piece_dir (str): The directory containing the piece's files.
        
#     Returns:
#         str: The path to the MusicXML file.
#     """
#     return os.path.join(piece_dir, "symbolic.musicxml")



# --- Example Usage --- #
if __name__ == "__main__":
    # import sys
    # # Example: 
    # path = sys.argv[1] if len(sys.argv) > 1 else "path/to/bach_chorale"

    # for voice in ['S', 'A', 'T', 'B']:
    #     for order in [3,4,5]:
    #         values = {"order": order, "voice": voice}
    #         answer, distractors = nth_voice_note_scientific_pitch(path, values)
    #         print(f"The {order}-th {voice} note is: {answer}")
    pass

