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
import yaml
import numpy as np
import functools

# def get_num_ontology(path_to_xml: str) -> dict[str, list[int]]:
#     musicxml_path = get_musicxml_file_path(path_to_xml)
#     if not os.path.exists(musicxml_path):
#         raise FileNotFoundError(f"Could not find file: {musicxml_path}")
#     score = converter.parse(musicxml_path)
#     num_ontology = {
#         'note_count': [],
#         'inerval_count': []
#     }


class AnswerDistractorExtractors:
    def __init__(self, path_to_ontology: str, distractor_pool_size: int = 3):
        self.ontology = yaml.load(open(path_to_ontology, 'r'))
        self.distractor_pool_size = distractor_pool_size

    def get_nth_note(path: str, values: dict) -> str:
        """
        Logic: Parses a MusicXML file and returns the scientific pitch notation 
        of the order-th note in the specified voice part.
        
        Args:
            path (str): The path to the directory of the piece, which contains the MusicXML file.
            values (dict): A dictionary containing the value for {order} and {voice}, e.g., {"order": 1, "voice": "S"}
            
        Returns:
            str: return NOTE NAME ONLY (e.g., "G", "E flat").
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
        ground_truth_pool = [n.name for n in notes if n.name != target_note.name]

        return target_note.name, ground_truth_pool

    def get_distractors(self, distractor_keys: list[str], ground_truth_pool: list[str]) -> list[str]:
        """
        Returns a list of distractor pitches based on the provided keys.
        
        Args:
            distractor_keys (list[str]): A list of keys corresponding to distractors in the ontology.
            
        Returns:
            list[str]: A list of distractor pitches.
        """
        distractors = []
        dist_pools = {}
        for key in distractor_keys:
            if ground_truth_pool[key]:
                dist_pools[key] = np.random.choice(ground_truth_pool, size=self.distractor_pool_size, replace=False).tolist()
            else:
                dist_pools[key] = np.random.choice(self.ontology[key], size=self.distractor_pool_size, replace=False).tolist()
        distractors = ["".join(pool) for pool in zip(*dist_pools.values())]
        return distractors
    
    # def get_nth_note(self, path: str, question_values: dict, distractor_keys: list[str], ground_truth_pool: list[str]) -> tuple[str, list[str]]:
    #     """
    #         meta-question_id: 0
    #         meta-question: What is the scientific pitch notation of the {order} {voice} note in the provided excerpt?
            
    #         Logic: Parses a MusicXML file and returns the scientific pitch notation 
    #         of the order-th note in the specified voice part.
            
    #         Args:
    #             path (str): The path to the directory of the piece, which contains the MusicXML file.
    #             values (dict): A dictionary containing the value for {order} and {voice}, e.g., {"order": 1, "voice": "S"}
                
    #         Returns:
    #             str: return NOTE NAME ONLY (e.g., "G", "E flat").
    #             list[str]: A list of distractor pitcheswith ground truth excluded.
    #     """

    #     ground_truth, ground_truth_pool = self.get_nth_note_ground_truth(path, question_values)
    #     distractor_pool = self.get_distractors(distractor_keys, ground_truth_pool)
        
    #     # Ensure the ground truth is not in the distractor pool
    #     if ground_truth in distractor_pool:
    #         distractor_pool.remove(ground_truth)
        
    #     return ground_truth, distractor_pool
    
    def get_note_quantity(self, path: str, question_values: dict, distractor_keys: list[str]) -> tuple[str, list[str]]:
        """
            meta-question_id: 0
            meta-question: Which voice part has the {quantity} number of {pitch} notes in the provided excerpt?
            
            Logic: Parses a MusicXML file and returns the voice part that has the most/least number of notes of a given pitch.
            
            Args:
                path (str): The path to the directory of the piece, which contains the MusicXML file.
                values (dict): A dictionary containing the value for {quantity} and {pitch}, e.g., {"quantity": "most", "pitch": "G"}
                
            Returns:
                str: The voice part with the most/least number of the specified pitch (e.g., "Soprano").
                list[str]: A list of distractor voice parts with ground truth excluded.
        """

        # Get the path to the MusicXML file
        musicxml_path = get_musicxml_file_path(path)

        if not os.path.exists(musicxml_path):
            raise FileNotFoundError(f"Could not find file: {musicxml_path}")
        
        # Parse the MusicXML file into a music21 Stream
        score = converter.parse(musicxml_path)
        target_pitch = question_values.get('pitch')

        if target_pitch not in self.ontology['pitch']:
            raise ValueError(f"Invalid pitch specified: {target_pitch}. Expected one of {self.ontology['pitch']}.")
        voice_mapping = {
                    'S': 0, # Soprano
                    'A': 1, # Alto
                    'T': 2, # Tenor
                    'B': 3  # Bass
                }
                
        voice_key = question_values.get('voice')
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
            raise ValueError(f"No valid notes found in part '{voice_key}'")           
        
        #for test_note in score.parts[0].flatten().getElementsByClass(note.Note):
        count = sum(1 for n in notes if n.name == target_pitch)
        notes_set = set(n.name for n in notes)
        dist_pool = {}
        for nn in notes_set:
            dist_pool[nn] = sum(1 for n in notes if n.name == nn)
        
        distractor_pool = np.random.choice(list(dist_pool.keys()), size=len(distractor_keys), replace=False).tolist()
        
        return count, distractor_pool
    
    def get_interval_quantity(self, path: str, question_values: dict, distractor_keys: list[str]) -> tuple[str, list[str]]:
        """
            meta-question_id: 0
            meta-question: Which voice part has the {quantity} number of {interval} intervals in the provided excerpt?
            
            Logic: Parses a MusicXML file and returns the voice part that has the most/least number of intervals of a given type.
            
            Args:
                path (str): The path to the directory of the piece, which contains the MusicXML file.
                values (dict): A dictionary containing the value for {quantity} and {interval}, e.g., {"quantity": "most", "interval": "major third"}
                
            Returns:
                str: The voice part with the most/least number of the specified interval (e.g., "Soprano").
                list[str]: A list of distractor voice parts with ground truth excluded.
        """
        pass

    def get_nth_interval(self, path: str, question_values: dict, distractor_keys: list[str]) -> tuple[str, list[str]]:
        """
            meta-question_id: 0
            meta-question: What is the {order} {voice} interval in the provided excerpt?
            
            Logic: Parses a MusicXML file and returns the specified interval in the specified voice part.
            
            Args:
                path (str): The path to the directory of the piece, which contains the MusicXML file.
                values (dict): A dictionary containing the value for {order} and {voice}, e.g., {"order": 1, "voice": "S"}
                
            Returns:
                str: The specified interval (e.g., "major third").
                list[str]: A list of distractor intervals with ground truth excluded.
        """
        pass

    def extract_answer_and_distractors(self, method, path: str, question_values: dict, distractor_keys: list[str]) -> tuple[str, list[str]]:
        """
        A wrapper function that extracts the ground truth answer and distractor pool for a given question.
        
        Args:
            path (str): The path to the directory of the piece, which contains the MusicXML file.
            question_values (dict): A dictionary containing the values needed to extract the answer (e.g., {"order": 1, "voice": "S"}).
            distractor_keys (list[str]): A list of keys corresponding to distractors in the ontology.
        Returns:
            tuple[str, list[str]]: A tuple containing the ground truth answer and a list of
            distractors.
        """
        # This function can be extended to handle different types of questions by checking the question type and calling the appropriate extraction method.
        # For now, it directly calls get_nth_note as an example.
        ground_truth, ground_truth_pool = functools.partial(method, path, question_values, distractor_keys) # self.get_nth_note_ground_truth(path, question_values)
        distractor_pool = self.get_distractors(distractor_keys, ground_truth_pool)
        
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