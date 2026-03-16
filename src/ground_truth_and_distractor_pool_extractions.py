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

    perfect_numbers = [1,4,5,8]
    major_numbers = [2,3,6,7]

    ontology = {}

    # perfect-type intervals
    for n in perfect_numbers:
        for q in ["P","A","d"]:
            name = f"{q}{n}"
            try:
                iv = interval.Interval(name)
                #possible also to use iv.niceName or iv.name, but simpleName is more concise and still recognizable
                ontology[name] = iv.niceName
            except:
                pass

    # major/minor-type intervals
    for n in major_numbers:
        for q in ["M","m","A","d"]:
            name = f"{q}{n}"
            try:
                iv = interval.Interval(name)
                ontology[name] = iv.niceName
            except:
                pass

    return ontology
   
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
        # print(self.config)
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
        # if self.config.get('use_all_inds', None) and self.ontology.get('target_index') is not None:
        #     print("Warning: Both 'target_index' and 'use_all_inds' are specified in the config. 'use_all_inds' will take precedence and 'target_index' will be ignored.")
        # if if target_index is not specified in the config, or if use_all_inds is set to True, then we will sample from all possible indices in the piece for each question, instead of using a fixed index across all pieces. This allows for more variability in the questions and answers across different pieces.
        if self.ontology.get('target_index') is None or self.config.get('use_all_inds', None):
            self.use_all_inds = True
    
        else:
            self.use_all_inds = False 
        self.min_num_distractors = self.config['min_num_distractors']
        
    
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
            note_index = int(np.random.choice(range(len(notes)-1)))
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
        if note_index >= len(notes) or int(note_index) < -len(notes):
            raise IndexError(f"Requested note target_index '{note_index}' is out of bounds. The part has {len(notes)} notes.")
        
        # Get the target note and return its scientific pitch notation
        target_note = notes[note_index]
        #ground_truth_pool = [np.random.choice([n.name for n in notes if n.name != target_note.name]) for _ in range(self.distractor_pool_size)]
        
        # Build a set of candidate distractor notes (exclude the true note)
        distractor_pool_set = set(n.name for n in notes) 
        distractor_pool_set.discard(target_note.name)
        distractor_pool = list(distractor_pool_set)

        #...sampling from the ontology instead of the notes in the piece
        #distractor_pool_set.remove(target_note)
        # distractor_pool_list= [a for a in distractor_pool_set if a in self.dict_note_ontology.keys()]
        
        # # if len(distractor_pool_list) < self.distractor_pool_size:
        # #     #while len(distractor_pool_list) < self.distractor_pool_size:
        # #     distractor_pool = np.random.choice(list(self.dict_note_ontology.keys()), self.distractor_pool_size-len(distractor_pool_list), replace=False).tolist()
        # #     distractor_pool = np.random.choice(distractor_pool_list, len(distractor_pool_list), replace=False).tolist() + distractor_pool
        # # else:
        #     distractor_pool = np.random.choice(distractor_pool_list, self.distractor_pool_size, replace=False).tolist()
        distractor_pool = [self.dict_note_ontology[sample] for sample in distractor_pool]
        
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

        if target_pitch not in self.dict_note_ontology.keys():
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
        
        # Count occurrences of the target pitch in the selected part
        count = int(sum(1 for n in notes if n.name == target_pitch))
        notes_set = set(n.name for n in notes)
        tmp_pool = [int(sum(1 for n in notes if n.name == nn)) for nn in notes_set]

        # Build a set of candidate distractor counts (exclude the true count)
        distractor_pool_set = set(tmp_pool)
        distractor_pool_set.discard(count)
        distractor_pool = list(distractor_pool_set)
        # if len(distractor_pool_set) < self.distractor_pool_size:
        #     distractor_pool = np.random.choice(list(distractor_pool_set), len(distractor_pool_set), replace=False).tolist()
        #     len_diff = self.distractor_pool_size-len(distractor_pool_set)
        #    # if (max(distractor_pool_set)-min(distractor_pool_set) ) < len_diff:
        #     distractor_pool += np.random.choice([_ for _ in range(min(distractor_pool_set)//2, max(distractor_pool_set)*2 )], len_diff, replace=True).tolist()
        #    # else:
                
        #     #     distractor_pool += np.random.choice(distractor_pool_set, self.distractor_pool_size-len(distractor_pool), replace=True).tolist()
        # else:
        #     distractor_pool = np.random.choice(list(distractor_pool_set), self.distractor_pool_size, replace=False).tolist()

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
        # breakpoint()
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
            note_index = int(np.random.choice(range(len(notes)-1)))
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

        all_interval_keys = []
        for vv in self.voice_mapping.keys():
            other_part = score.parts[self.voice_mapping[vv]]
            other_notes = list(other_part.flatten().getElementsByClass(note.Note))
            for note_idx in range(len(other_notes)-1):
                n1 = other_notes[note_idx]
                n2 = other_notes[note_idx + 1]
                iv = interval.Interval(n1, n2)
                interval_name = iv.simpleName
                all_interval_keys.append(interval_name)
        # all_interval_keys = [interval.Interval(notes[i], notes[i + 1]).simpleName for i in range(len(notes)-1)]

        distractor_pool_set = set(all_interval_keys)
        distractor_pool_set.discard(interval_name)
        distractor_pool = list(distractor_pool_set)
    
        # if len(distractor_pool_list) < self.distractor_pool_size:
        #     #while len(distractor_pool_list) < self.distractor_pool_size:
        #     distractor_pool = np.random.choice(list(all_possible_interval_keys), self.distractor_pool_size-len(distractor_pool_list), replace=True).tolist()
            
        #     distractor_pool = np.random.choice(distractor_pool_list, len(distractor_pool_list), replace=False).tolist() + distractor_pool
        # else:
        #     distractor_pool = np.random.choice(distractor_pool_list, self.distractor_pool_size, replace=False).tolist()
        # print(self.dict_interval_ontology[interval_name], distractor_pool, question_values)
        distractor_pool = [self.dict_interval_ontology[sample] for sample in distractor_pool]
        
        return self.dict_interval_ontology[interval_name], distractor_pool, question_values


    def get_interval_quantity(self, path: str, question_values: dict) -> tuple[str, list[str]]:
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
        # breakpoint()
                # Get the path to the MusicXML file
        musicxml_path = get_musicxml_file_path(path)

        if not os.path.exists(musicxml_path):
            raise FileNotFoundError(f"Could not find file: {musicxml_path}")
        
        # Parse the MusicXML file into a music21 Stream
        score = converter.parse(musicxml_path)
        target_interval = question_values.get('interval')
       
        if target_interval not in self.dict_interval_ontology.keys():
            raise ValueError(f"Invalid pitch specified: {target_interval}. Expected one of {self.dict_interval_ontology}.")

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
        for note_idx in range(len(notes)-1):
            n1 = notes[note_idx]
            n2 = notes[note_idx + 1]
            iv = interval.Interval(n1, n2)
            interval_name = iv.simpleName
            intervals.append(interval_name)

        count = int(sum(1 for n in intervals if n == target_interval))
        
        tmp_pool = []
      
        for vv in self.voice_mapping.keys():
            other_part = score.parts[self.voice_mapping[vv]]
            other_notes = list(other_part.flatten().getElementsByClass(note.Note))
            for note_idx in range(len(other_notes)-1):
                n1 = other_notes[note_idx]
                n2 = other_notes[note_idx + 1]
                iv = interval.Interval(n1, n2)
                interval_name = iv.simpleName
                intervals.append(interval_name)
        intervals_set = set(intervals)
        intervals_set.discard(target_interval)
        for nn in intervals_set:
            tmp_pool.append(int(sum(1 for _ in intervals if _ == nn)))
        
        # distractor_pool = []
        # while True:
        #     sample = int(np.random.choice(tmp_pool, None))
        #     if sample != count and sample not in distractor_pool:
        #         distractor_pool.append(int(sample))
        #     if len(distractor_pool) > self.distractor_pool_size:
        #         break

        return count, tmp_pool, question_values

    
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
        # print(method)

        ground_truth, ground_truth_pool, new_values = method(path, question_values) # self.get_nth_note_ground_truth(path, question_values)
        #distractor_pool = self.get_distractors(distractor_keys, ground_truth_pool)
       # breakpoint()
        # additional, just safety reasons: Ensure the ground truth is not in the distractor pool
        if ground_truth in ground_truth_pool:
            ground_truth_pool.remove(ground_truth)
        if len(set(ground_truth_pool))< self.min_num_distractors:
            #TODO: implement smarter distractor generation in this case, e.g., by using the ontology to find similar notes/intervals to the ground truth and sampling from those.
            print(f"Warning: Only {len(set(ground_truth_pool))} unique distractors generated for question {path}.")
            
            ground_truth_pool = list(set(ground_truth_pool))
            len_diff = self.min_num_distractors - len(ground_truth_pool)
            
            method_name = method.__name__
            if "interval" in method_name:
                sample_space = copy.deepcopy(set(self.dict_interval_ontology.values()))
                sample_space.discard(ground_truth)
                additional_distractors = np.random.choice(list(sample_space), len_diff, replace=False).tolist()
            elif "note" in method_name:
                sample_space = copy.deepcopy(set(self.dict_note_ontology.values()))
                sample_space.discard(ground_truth)
                additional_distractors = np.random.choice(list(sample_space), len_diff, replace=False).tolist()
            ground_truth_pool += additional_distractors
        else:
            ground_truth_pool = list(set(ground_truth_pool))
        return ground_truth, ground_truth_pool, new_values
