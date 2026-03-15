"""
Methods for automatic extraction of ground truth answers and pools of distractors for the benchmark questions.
Each meta-question in the benchmark should be associated with a function in this file that implements the logic for
extracting the ground truth answer and distractor pool from the symbolic score of a piece (or some other way). The generate_benchmark.py
script will dynamically load this file and call the appropriate function for each question-piece pair to populate the
benchmark with ground truth answers and distractors.
"""

# TODO: create a directory for these methods, have single file per question, add dynamic loading of all methods in the directory, and add a template file for new questions to be added easily by future contributors.

from operator import index

from operator import index

from music21 import converter, note, chord, stream, interval, pitch
import os
from utils import get_musicxml_file_path
import yaml
import numpy as np

import copy
# def get_num_ontology(path_to_xml: str) -> dict[str, list[int]]:
#     musicxml_path = get_musicxml_file_path(path_to_xml)
#     if not os.path.exists(musicxml_path):
#         raise FileNotFoundError(f"Could not find file: {musicxml_path}")
#     score = converter.parse(musicxml_path)
#     num_ontology = {
#         'note_count': [],
#         'inerval_count': []
#     }
def get_tonal_intervals():

    intervals = {
            "P1": "perfect unison",
            "m2": "minor second",
            "M2": "major second",
            "m3": "minor third",
            "M3": "major third",
            "P4": "perfect fourth",
            "A4": "augmented fourth",
            "d5": "diminished fifth",
            "P5": "perfect fifth",
            "m6": "minor sixth",
            "M6": "major sixth",
            "m7": "minor seventh",
            "M7": "major seventh",
            "P8": "perfect octave"
        }

    return intervals

def get_tonal_notes():
    notes = {}
    for pc in range(12):
        p = pitch.Pitch()
        p.pitchClass = pc
        notes[p.name] = p.name
        notes[p.getEnharmonic().name] = p.getEnharmonic().name
    return notes
    # labels = ["C", "C sharp", "D flat","D", "D sharp","E flat","E", "F flat", "E sharp","F", "F sharp","G flat","G", "G sharp","A flat", "A","A sharp","B flat","B","C flat","B sharp"]
    # music21_keys = []
    # for midi in range(12):  # pitch classes
    #     p = pitch.Pitch()
    #     p.midi = 60 + midi  # C4 + offset
    #     music21_keys.append(p.name)
    #     music21_keys.append(p.getEnharmonic().name)
    
    # notes = {k:v for k,v in zip(music21_keys, labels)}
    
    # return notes

class AnswerDistractorExtractors:
    def __init__(self, config_yaml):
        self.config = config_yaml
        print(self.config)
        music_config = self.config['music_ontology_settings']
        if "harmonic_system" in self.config:
            system = self.config["harmonic_system"]
        else:
            system = "tonal"
        self.ontology = yaml.load(open(music_config['ontology_path'],'r'), Loader=yaml.FullLoader)
        if "interval" in self.ontology.keys():
            self.dict_interval_ontology = {k: v for d in self.ontology['interval'] for k, v in d.items()}
        else:
            self.dict_interval_ontology = self.build_interval_ontology(system)
            self.ontology['interval'] = [{k:v} for k,v in self.dict_interval_ontology.items()]

        if "pitch" in self.ontology.keys():
            self.dict_note_ontology = {k: v for d in self.ontology['pitch'] for k, v in d.items()}
            
        else:
            self.dict_note_ontology = self.build_note_ontology(system)
            self.ontology['pitch'] = [{k:v} for k,v in self.dict_note_ontology.items()]

        self.voice_mapping = {
                    'S': 0, # Soprano
                    'A': 1, # Alto
                    'T': 2, # Tenor
                    'B': 3  # Bass
                }
        
        if self.ontology.get('target_index', None) or self.config.get('use_all_inds',False):
            self.use_all_inds = True
    
        else:
            self.use_all_inds = False 
        self.distractor_pool_size = self.config['distractor_pool_size']
        
    
    def build_interval_ontology(self,system):

        if system=="tonal":
            return get_tonal_intervals()

        else:
            raise ValueError(f"Unknown hamonic system for harmonical recognition: {system}")
    def build_note_ontology(self, system):
        if system=="tonal":
            return get_tonal_notes()

        else:
            raise ValueError(f"Unknown hamonic system for harmonical recognition: {system}")

    def get_nth_note(self,path: str, values: dict) -> str:
        """
        Logic: Parses a MusicXML file and returns the scientific pitch notation 
        of the index-th note in the specified voice part.
        
        Args:
            path (str): The path to the directory of the piece, which contains the MusicXML file.
            values (dict): A dictionary containing the value for {index} and {voice}, e.g., {"target_index": 1, "voice": "S"}
            
        Returns:
            str: return NOTE NAME ONLY (e.g., "G", "E flat").
        """
            # Get the path to the MusicXML file
        musicxml_path = get_musicxml_file_path(path)

        if not os.path.exists(musicxml_path):
            raise FileNotFoundError(f"Could not find file: {musicxml_path}")
        
        # Parse the MusicXML file into a music21 Stream
        score = converter.parse(musicxml_path)
               
        voice_key = values.get('voice')
        if voice_key not in self.voice_mapping:
            raise ValueError(f"Invalid voice specified: {voice_key}. Expected one of 'S', 'A', 'T', 'B'.")
            
        part_index = self.voice_mapping[voice_key]
        
        # Check if the score has the expected number of parts
        if part_index >= len(score.parts):
            raise IndexError(f"The parsed score does not contain a part for voice '{voice_key}'.")
            
        target_part = score.parts[part_index]
        
        # Flatten the part (to remove measure hierarchies) and extract only the notes (ignoring rests/chords)
        notes = list(target_part.flatten().getElementsByClass(note.Note))
        
        if not notes:
            raise ValueError(f"No valid notes found in part '{voice_key}'.")
            
        if self.use_all_inds:
            note_index = np.random.choice(range(len(notes)-1))
            values['target_index'] = int(note_index)
        else:
            note_index = values.get('target_index')
        if note_index == 'end':
            note_index = -1
        
        # else:
        #     try:
        #         # Subtract 1 because standard list indices are 0-indexed, but the prompt uses 1-indexed (1: first)
        #         note_index = int(target_index) - 1
        #     except (ValueError, TypeError):
        #         raise ValueError(f"Invalid target_index specified: {target_index}. Expected integer or 'end'.")
                
        # Check if the target_index is out of bounds
        if note_index >= len(notes) or note_index < -len(notes):
            raise IndexError(f"Requested note target_index '{note_index}' is out of bounds. The part has {len(notes)} notes.")
        
        # Get the target note and return its scientific pitch notation
        target_note = notes[note_index]
        #ground_truth_pool = [np.random.choice([n.name for n in notes if n.name != target_note.name]) for _ in range(self.distractor_pool_size)]
        distractor_pool = []
        distractor_pool_set = copy.deepcopy(notes)
        distractor_pool_set.remove(target_note)
        distractor_pool = np.random.choice(distractor_pool_set, self.distractor_pool_size, replace=False)

        distractor_pool = [self.dict_note_ontology[sample.name] for sample in distractor_pool]
        
        return target_note.name, distractor_pool, values

    
    def get_note_quantity(self, path: str, question_values: dict) -> tuple[str, list[str]]:
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

        if target_pitch not in self.dict_note_ontology.values():
            raise ValueError(f"Invalid pitch specified: {target_pitch}. Expected one of {self.dict_note_ontology}.")

        voice_key = question_values.get('voice')
        if voice_key not in self.voice_mapping:
            raise ValueError(f"Invalid voice specified: {voice_key}. Expected one of 'S', 'A', 'T', 'B'.")
            
        part_index = self.voice_mapping[voice_key]
        
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
        tmp_pool = []
        for nn in notes_set:
            tmp_pool.append(sum(1 for n in notes if n.name == nn))
        
        #distractor_pool = np.random.choice([v for _,v in dist_pool.items() if v != count], size=len(distractor_keys), replace=True).tolist()
        distractor_pool_set = copy.deepcopy(tmp_pool)
        if count in distractor_pool_set:
            distractor_pool_set.remove(count)
        distractor_pool = []
        if len(distractor_pool_set) < self.distractor_pool_size:
            
            len_diff = self.distractor_pool_size-len(distractor_pool_set)
            if (max(distractor_pool_set)-min(distractor_pool_set) ) < len_diff:
                distractor_pool += np.random.choice([_ for _ in range(min(distractor_pool_set)//2, max(distractor_pool_set)*2 )], len_diff, replace=False).tolist()
            else:
                distractor_pool = np.random.choice(distractor_pool_set, len(distractor_pool_set), replace=False).tolist()
            #     distractor_pool += np.random.choice(distractor_pool_set, self.distractor_pool_size-len(distractor_pool), replace=True).tolist()
        else:
            distractor_pool = np.random.choice(distractor_pool_set, self.distractor_pool_size, replace=False).tolist()

        return count, distractor_pool, question_values
    

    def get_nth_interval(self, path: str, question_values: dict) -> tuple[str, list[str]]:
        """
            meta-question_id: 0
            meta-question: What is the {target_index} {voice} interval in the provided excerpt?
            
            Logic: Parses a MusicXML file and returns the specified interval in the specified voice part.
            
            Args:
                path (str): The path to the directory of the piece, which contains the MusicXML file.
                values (dict): A dictionary containing the value for {target_index} and {voice}, e.g., {"target_index": 1, "voice": "S"}
                
            Returns:
                str: The specified interval (e.g., "major third").
                list[str]: A list of distractor intervals with ground truth excluded.
        """
        breakpoint()
        musicxml_path = get_musicxml_file_path(path)

        if not os.path.exists(musicxml_path):
            raise FileNotFoundError(f"Could not find file: {musicxml_path}")
        
        # Parse the MusicXML file into a music21 Stream
        score = converter.parse(musicxml_path)
                
        voice_key = question_values.get('voice')

        if voice_key not in self.voice_mapping:
            raise ValueError(f"Invalid voice specified: {voice_key}. Expected one of 'S', 'A', 'T', 'B'.")
            
        part_index = self.voice_mapping[voice_key]
        
        # Check if the score has the expected number of parts
        if part_index >= len(score.parts):
            raise IndexError(f"The parsed score does not contain a part for voice '{voice_key}'.")
            
        target_part = score.parts[part_index]
        
        # Flatten the part (to remove measure hierarchies) and extract only the notes (ignoring rests/chords)
        notes = list(target_part.flatten().getElementsByClass(note.Note))

        if self.use_all_inds:
            note_index = np.random.choice(range(len(notes)-1))
            question_values['target_index'] = note_index
        else:
            note_index = question_values.get('target_index')
        if note_index == 'end':
            note_index = -1

        if note_index >= len(notes) - 1:
            raise IndexError("Interval target_index out of range")

        n1 = notes[note_index]
        n2 = notes[note_index + 1]
        iv = interval.Interval(n1, n2)
        interval_name = iv.simpleName

        distractor_pool = []
        while True:
            sample = np.random.choice([i for i in range(len(notes)-1)], None)
            if sample!= note_index and sample not in distractor_pool:
                distractor_pool.append(sample)
            if len(distractor_pool) > self.distractor_pool_size:
                break

        intervals_pool = [interval.Interval(notes[i], notes[i + 1]) for i in distractor_pool]
        interval_names_pool = [self.dict_interval_ontology[iv.simpleName] for iv in intervals_pool]
        
        try:
            return self.dict_interval_ontology[interval_name], interval_names_pool, question_values
        
        except KeyError:
            return None, interval_names_pool, question_values

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
        breakpoint()
                # Get the path to the MusicXML file
        musicxml_path = get_musicxml_file_path(path)

        if not os.path.exists(musicxml_path):
            raise FileNotFoundError(f"Could not find file: {musicxml_path}")
        
        # Parse the MusicXML file into a music21 Stream
        score = converter.parse(musicxml_path)
        target_interval = question_values.get('interval')
        if target_interval not in self.interval_ontology.values():
            raise ValueError(f"Invalid pitch specified: {target_interval}. Expected one of {self.interval_ontology}.")

        voice_key = question_values.get('voice')
        if voice_key not in self.voice_mapping:
            raise ValueError(f"Invalid voice specified: {voice_key}. Expected one of 'S', 'A', 'T', 'B'.")
        
        part_index = self.voice_mapping[voice_key]
        
        # Check if the score has the expected number of parts
        if part_index >= len(score.parts):
            raise IndexError(f"The parsed score does not contain a part for voice '{voice_key}'.")
            
        target_part = score.parts[part_index]
        
        # Flatten the part (to remove measure hierarchies) and extract only the notes (ignoring rests/chords)
        notes = list(target_part.flatten().getElementsByClass(note.Note))
        
        if not notes:
            raise ValueError(f"No valid notes found in part '{voice_key}'")           
        
        #for test_note in score.parts[0].flatten().getElementsByClass(note.Note):
        intervals = []
        for note_idx in range(len(notes)):
            n1 = notes[note_idx]
            n2 = notes[note_idx + 1]
            iv = interval.Interval(n1, n2)
            interval_name = iv.simpleName
            intervals.append(interval_name)

        count = sum(1 for n in intervals if n == target_interval)
        intervals_set = set(intervals)
        tmp_pool = []
        for nn in intervals_set:
            tmp_pool.append(sum(1 for n in intervals if n == target_interval))
        
        distractor_pool = []
        while True:
            sample = np.random.choice(tmp_pool, None)
            if sample!= count and sample not in distractor_pool:
                distractor_pool.append(int(sample))
            if len(distractor_pool) > self.distractor_pool_size:
                break

        return count, distractor_pool, question_values

            # def get_distractors(self, distractor_keys: list[str], ground_truth_pool: list[str]) -> list[str]:
            #     """
            #     Returns a list of distractor pitches based on the provided keys.
                
            #     Args:
            #         distractor_keys (list[str]): A list of keys corresponding to distractors in the ontology.
                    
            #     Returns:
            #         list[str]: A list of distractor pitches.
            #     """
            #     distractors = []
            #     dist_pools = {}
            #     for key in distractor_keys:
            #         if isinstance(ground_truth_pool, dict):
            #             if ground_truth_pool[key]:
            #                 dist_pools[key] = np.random.choice(ground_truth_pool, size=self.distractor_pool_size, replace=False).tolist()
            #         else:
            #             dist_pools[key] = np.random.choice(self.ontology[key], size=self.distractor_pool_size, replace=False).tolist()
            #     distractors = ["".join(pool) for pool in zip(*dist_pools.values())]
            #     return distractors
    
    def extract_answer_and_distractors(self, method, path: str, question_values: dict) -> tuple[str, list[str]]:
        """
        A wrapper function that extracts the ground truth answer and distractor pool for a given question.
        
        Args:
            path (str): The path to the directory of the piece, which contains the MusicXML file.
            question_values (dict): A dictionary containing the values needed to extract the answer (e.g., {"target_index": 1, "voice": "S"}).
            distractor_keys (list[str]): A list of keys corresponding to distractors in the ontology.
        Returns:
            tuple[str, list[str]]: A tuple containing the ground truth answer and a list of
            distractors.
        """
        # This function can be extended to handle different types of questions by checking the question type and calling the appropriate extraction method.
        # For now, it directly calls get_nth_note as an example.
        print(method)

        ground_truth, ground_truth_pool, new_values = method(path, question_values) # self.get_nth_note_ground_truth(path, question_values)
        #distractor_pool = self.get_distractors(distractor_keys, ground_truth_pool)
        
        # additional, just safety reasons: Ensure the ground truth is not in the distractor pool
        if ground_truth in ground_truth_pool:
            ground_truth_pool.remove(ground_truth)
        if len(set(ground_truth_pool))< 4:
            raise ValueError("less then 4 distractors generated, bug!")
        return ground_truth, ground_truth_pool, new_values
