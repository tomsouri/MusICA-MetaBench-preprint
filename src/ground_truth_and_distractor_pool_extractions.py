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

from music21 import converter, note, chord, stream, interval, pitch, meter,key,roman
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
        enh_name = p.getEnharmonic().name
        for note_name in [p.name, enh_name]:
            if "#" in note_name:
                if '##' in note_name:
                    notes[note_name] = note_name[0]+" double sharp"
                else:
                    notes[note_name] = note_name[0]+" sharp"
            elif "-" in note_name:
                if '--' in note_name:
                    notes[note_name] = note_name[0]+" double flat"
                else:
                    notes[note_name] = note_name[0]+" flat"
            else:
                notes[note_name] = note_name[0]
            
        #  + (" sharp" if '#' in p.name else "") + (" flat" if '-' in p.name else "") + (" double sharp" if '##' in p.name else "") + (" double flat" if '--' in p.name else "")
        # notes[p.name] = p.name
        # notes[p.getEnharmonic().name] = p.getEnharmonic().name
    
    return notes
    # labels = ["C", "C sharp", "D flat","D", "D sharp","E flat","E", "F flat", "E sharp","F", "F sharp","G flat","G", "G sharp","A flat", "A","A sharp","B flat","B","C flat","B sharp"]
    # music21_keys = []
    # for midi in range(12):  # pitch classes
    #     p = pitch.Pitch()
    #     p.midi = 60 + midi  # C4 + offset
    #     music21_keys.append(p.name)
    #     music21_keys.append(p.getEnharmonic().name)
    
    # notes = {k:v for k,v in zip(music21_keys, labels)}

def get_rhythm():
         
    return {3.0: 'triple-whole', 
            2.0: 'double-whole', 
            1.0: 'whole', 
            1.5: 'dotted-whole', 
            0.5: 'half', 0.25: 'quarter', 
            0.125: 'eighth', 0.0625: 'sixteenth',
            0.03125: 'thirty-second', 
            0.015625: 'sixty-fourth', 
            0.0078125: 'hundred-twenty-eighth', 
            0.00390625: 'two-hundred-fifty-sixth'}
def get_time_signatures():

    numerators = range(1, 13)          # 1–12 beats
    denominators = [1, 2, 4, 8, 16, 32]

    ontology = {}

    for n in numerators:
        for d in denominators:
            ts_str = f"{n}/{d}"
            try:
                ts = meter.TimeSignature(ts_str)
                ontology[ts_str] = ts.ratioString
            except:
                pass

    return ontology

def get_tonality():
    modes = ['major', 'minor']  #, 'dorian', 'phrygian', 'lydian', 'mixolydian', 'locrian']
    ontology = {}
    for pc in range(12):
        p = pitch.Pitch()
        p.pitchClass = pc
        for mode in modes:
            word = f"{p.name} {mode}"
            ontology[word] = word
            # if mode == 'major':
            #     word = f"{p.name} {mode}"
            #     ton_key = p.name.upper()
            #     #tonality = key.Key(ton_key)
            # if mode == 'minor':
            #     word = f"{p.name} {mode}"
            #     ton_key = p.name.lower()
            #     #tonality = key.Key(ton_key)
            # ontology[ton_key] = word

    return ontology
def get_ordinal_suffix(n: int) -> str:
      
    if 11 <= (n % 100) <= 13:
        return 'th'
    else:
        last_digit = n % 10
        if last_digit == 1:
            return 'st'
        elif last_digit == 2:
            return 'nd'
        elif last_digit == 3:
            return 'rd'
        else:
            return 'th'

def get_nice_target_index(self, target_index: int) -> str:

    # # Retrieve the dictionary for the target index
    # target_index_dicts = self.ontology['target_index']
    # for target_index_dict in target_index_dicts:
    #     if str(target_index) in target_index_dict:
    #         return target_index_dict[str(target_index)]

    # Fallback to generating the ordinal suffix dynamically
    return {f"{target_index}":f"{str(target_index+1)+ get_ordinal_suffix(target_index)}"}
import itertools
def get_chords():
    pitch_classes = list(range(12))  # 0–11
    ontology = set()
    max_notes = 4 #number of voices
    for r in range(2, max_notes + 1):  # dyads → tetrads
        for pcs in itertools.combinations(pitch_classes, r):

            # build chord from pitch classes
            pitches = [pitch.Pitch(midi=60 + pc) for pc in pcs]
            ch = chord.Chord(pitches)
            name = ch.commonName
            if "with" in name:  # filter out chords with added tones (e.g., "C major with added sixth")
                name = name.split(" with")[0]
                
            if name:  # filter None / empty
                ontology.add(name)
  
    ontology = {chord_name: chord_name for chord_name in ontology}
    return ontology
def get_cadences():
    pitch_classes = list(range(12))  # 0–11
    ontology = set()
    max_notes = 3 #number of voices
    
    for r in range(3, max_notes + 1):  # dyads → tetrads
        for pcs in itertools.combinations(pitch_classes, r):

            # build chord from pitch classes
            pitches = [pitch.Pitch(midi=60 + pc) for pc in pcs]
            ch = chord.Chord(pitches)
            for pcs2 in itertools.combinations(pitch_classes, r):
                pitches2 = [pitch.Pitch(midi=60 + pc) for pc in pcs2]
                ch2 = chord.Chord(pitches2)
                
                rn = str(roman.romanNumeralFromChord(ch, key.Key('A')).figure)
                rn2 = str(roman.romanNumeralFromChord(ch2, key.Key('A')).figure)
                if rn != rn2:
                    cad_name = f"{rn}: {rn2}"
            # value = f"{rn.figure}: {rn2.figure}"    
            # if name:  # filter None / empty
                    ontology.add(cad_name)
    # breakpoint()
    ontology = {cad_name: cad_name for cad_name in ontology}
    return ontology
def get_rhythm_props():
    # Define the rhythmic proportions to consider
    rhythmic_proportions = [0.5, 1.0, 2.0, 3.0, 0.25, 0.33, 4.0, 1.5]  # e.g., half, equal, double
    ontology = {str(prop) : (f"1:{int(prop)}") for prop in rhythmic_proportions if prop >=1}
    ontology.update({str(prop) : (f"1:{prop}") for prop in rhythmic_proportions if prop < 1})
    ontology.update({"other" : "other"})
    # ontology = {0:""}
    return ontology
# def get_harmonic_cadences():
    
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

        if "rhythm" in self.ontology.keys():
            self.dict_rhythm_ontology = {k: v for d in self.ontology['rhythm'] for k, v in d.items()}
        else:
            self.dict_rhythm_ontology = self.build_rhythm_ontology(system)
            self.ontology['rhythm'] = [{k:v} for k,v in self.dict_rhythm_ontology.items()]

        if "time_signature" in self.ontology.keys():
            self.dict_time_signature_ontology = {k: v for d in self.ontology['time_signature'] for k, v in d.items()}
        else:
            self.dict_time_signature_ontology = self.build_time_signature_ontology(system)
            self.ontology['time_signature'] = [{k:v} for k,v in self.dict_time_signature_ontology.items()]
        
        if "tonality" in self.ontology.keys():
            self.dict_tonality_ontology = {k: v for d in self.ontology['tonality'] for k, v in d.items()}
        else:
            self.dict_tonality_ontology = self.build_tonality_ontology(system)
            self.ontology['tonality'] = [{k:v} for k,v in self.dict_tonality_ontology.items()]
        
        if "chords" in self.ontology.keys():
            self.dict_chord_ontology = {k: v for d in self.ontology['chords'] for k, v in d.items()}
        else:
            self.dict_chord_ontology = self.build_chord_ontology(system)
            self.ontology['chords'] = [{k:v} for k,v in self.dict_chord_ontology.items()]

        if "rhythm_proportion" in self.ontology.keys():
            self.dict_rhythm_prop_ontology = {k: v for d in self.ontology['rhythm_proportion'] for k, v in d.items()}
        else:
            self.dict_rhythm_prop_ontology = self.build_rhythm_prop_ontology(system)
            self.ontology['rhythm_proportion'] = [{k:v} for k,v in self.dict_rhythm_prop_ontology.items()]
        self.voice_mapping = {
                    'S': 0, # Soprano
                    'A': 1, # Alto
                    'T': 2, # Tenor
                    'B': 3  # Bass
                }
        if "cadences" in self.ontology.keys():
            self.dict_cadence_ontology = {k: v for d in self.ontology['cadences'] for k, v in d.items()}
        #  TODO: TO SOLVE / very slow
        # else:
            # self.dict_cadence_ontology = self.build_cadence_ontology(system)
            # self.ontology['cadences'] = [{k:v} for k,v in self.dict_cadence_ontology.items()]
        self.distractor_pool_size = self.config.get('distractor_pool_size', 4)

        if self.ontology.get('target_index') is None or self.config.get('use_all_inds', None):
            self.use_all_inds = True
            self.ontology['target_index'] = [get_nice_target_index(self, idx) for idx in range(self.distractor_pool_size*10)]
            
        else:
            self.use_all_inds = False 
        
        self.min_num_distractors = self.config['min_num_distractors']
        self.random_distractors = self.config.get('random_distractors', False)
        self.verbose = self.config.get('verbose', False)
        yaml.dump(self.ontology, open('generated_ontology.yaml','w'))

    def build_cadence_ontology(self, system):
        if system=="tonal":
            
            return get_cadences()
                # "V-I": "authentic cadence",
                # "V-vi": "deceptive cadence",
                # "IV-I": "plagal cadence",
                # "V-VI": "half cadence",
                # "I-V": "retrograde authentic cadence",

                # Add more cadences as needed
            
        else:
            raise ValueError(f"Unknown hamonic system for harmonical recognition: {system}")

    def build_rhythm_prop_ontology(self, system):
        if system=="tonal":
            return get_rhythm_props()
        else:
            raise ValueError(f"Unknown hamonic system for harmonical recognition: {system}")

    def build_chord_ontology(self, system):
        if system=="tonal":
            return get_chords()

        else:
            raise ValueError(f"Unknown hamonic system for harmonical recognition: {system}")

    def build_tonality_ontology(self, system):
        if system=="tonal":
            return get_tonality()
        else:
            raise ValueError(f"Unknown hamonic system for harmonical recognition: {system}")
        
    def build_rhythm_ontology(self, system):
        if system=="tonal":
            return get_rhythm()

        else:
            raise ValueError(f"Unknown hamonic system for harmonical recognition: {system}")
    
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
    def build_time_signature_ontology(self, system):
        if system=="tonal":
            return get_time_signatures()

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
            values['target_index'] = self.ontology["target_index"][int(note_index)]
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
        if not(self.random_distractors):
            # Build a set of candidate distractor notes (exclude the true note)
            for vv in self.voice_mapping.keys():
                other_part = score.parts[self.voice_mapping[vv]]
                other_notes = list(other_part.flatten().getElementsByClass(note.Note))
                notes += other_notes

            distractor_pool_set = set(n.name for n in notes) 
            distractor_pool_set.discard(target_note.name)
            distractor_pool = list(distractor_pool_set)
            
            distractor_pool = [self.dict_note_ontology[sample] for sample in distractor_pool]

        else:
            try:
                distractor_pool = np.random.choice(list(self.dict_note_ontology.values()), self.distractor_pool_size, replace=False).tolist()
            except ValueError:
                if self.verbose:
                    print(f"Warning: Not enough unique notes in the ontology. number of distractors as number of unique notes: {len(self.dict_note_ontology.keys())}")
                distractor_pool = np.random.choice(list(self.dict_note_ontology.values()), self.distractor_pool_size, replace=False).tolist()

        #...sampling from the ontology instead of the notes in the piece
        #distractor_pool_set.remove(target_note)
        # distractor_pool_list= [a for a in distractor_pool_set if a in self.dict_note_ontology.keys()]
        
        # # if len(distractor_pool_list) < self.distractor_pool_size:
        # #     #while len(distractor_pool_list) < self.distractor_pool_size:
        # #     distractor_pool = np.random.choice(list(self.dict_note_ontology.keys()), self.distractor_pool_size-len(distractor_pool_list), replace=False).tolist()
        # #     distractor_pool = np.random.choice(distractor_pool_list, len(distractor_pool_list), replace=False).tolist() + distractor_pool
        # # else:
        #     distractor_pool = np.random.choice(distractor_pool_list, self.distractor_pool_size, replace=False).tolist()
        
        
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

        all_notes = []
        for vv in self.voice_mapping.keys():
            other_part = score.parts[self.voice_mapping[vv]]
            other_notes = list(other_part.flatten().getElementsByClass(note.Note))
            all_notes.append([n.name for n in other_notes])

        # all_notes = [n for sublist in all_notes for n in sublist]
        # notes_set = set(all_notes)
        tmp_pool = []
        for line in all_notes:
            for _n in list(set(line)):
                tmp_pool.append(int(sum(1 for n in line if n == _n)))
        
        if not self.random_distractors:
        # Build a set of candidate distractor counts (exclude the true count)
            distractor_pool = set(tmp_pool)
            distractor_pool.discard(count)
            
        else:
            try:
                max_len= max(tmp_pool)
                distractor_pool = np.random.choice(range(max_len), self.distractor_pool_size, replace=False).tolist()
            except ValueError:
                print(f"Warning: Not enough number of same notes in the piece to generate {self.distractor_pool_size} distractors. Sampling random numbers instead")
                distractor_pool = np.random.choice(range(self.distractor_pool_size), self.distractor_pool_size, replace=False).tolist()
            if count in distractor_pool:
                distractor_pool.remove(count)

        # if len(distractor_pool_set) < self.distractor_pool_size:
        #     distractor_pool = np.random.choice(list(distractor_pool_set), len(distractor_pool_set), replace=False).tolist()
        #     len_diff = self.distractor_pool_size-len(distractor_pool_set)
        #    # if (max(distractor_pool_set)-min(distractor_pool_set) ) < len_diff:
        #     distractor_pool += np.random.choice([_ for _ in range(min(distractor_pool_set)//2, max(distractor_pool_set)*2 )], len_diff, replace=True).tolist()
        #    # else:
                
        #     #     distractor_pool += np.random.choice(distractor_pool_set, self.distractor_pool_size-len(distractor_pool), replace=True).tolist()
        # else:
        #     distractor_pool = np.random.choice(list(distractor_pool_set), self.distractor_pool_size, replace=False).tolist()
        distractor_pool = list(distractor_pool)
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
            question_values['target_index'] = self.ontology['target_index'][note_index]
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

        if not self.random_distractors:
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
        else:
            try:
                distractor_pool = np.random.choice(list(self.dict_interval_ontology.values()), self.distractor_pool_size, replace=False).tolist()
            except ValueError:
                if self.verbose:
                    print(f"Warning: Not enough unique intervals in the ontology. number of distractors as number of unique intervals: {len(set(all_interval_keys))}")
                distractor_pool = np.random.choice(list(self.dict_interval_ontology.values()), self.distractor_pool_size, replace=False).tolist()


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
        voice_intervals = []
        for vv in self.voice_mapping.keys():
            other_part = score.parts[self.voice_mapping[vv]]
            other_notes = list(other_part.flatten().getElementsByClass(note.Note))
            for note_idx in range(len(other_notes)-1):
                n1 = other_notes[note_idx]
                n2 = other_notes[note_idx + 1]
                iv = interval.Interval(n1, n2)
                interval_name = iv.simpleName
                intervals.append(interval_name)
            voice_intervals.append(intervals)
        # intervals_set = set(intervals)
        # intervals_set.discard(target_interval)
        if not self.random_distractors:
            for line in voice_intervals:
                for nn in set(line):
                    tmp_pool.append(int(sum(1 for _ in line if _ == nn)))
            distractor_tool = set(tmp_pool)
            distractor_tool.discard(count)
        else:

            try:
                max_len= max(tmp_pool)
                distractor_tool = np.random.choice(range(max_len), self.distractor_pool_size, replace=False).tolist()
            except ValueError:
                print(f"Warning: Not enough distractors ({self.distractor_pool_size}). Sampling numbers in range len(intervals) ({len(intervals)}) instead.")
                distractor_tool = np.random.choice(range(self.distractor_pool_size), self.distractor_pool_size, replace=False).tolist()
            if count in distractor_tool:
                distractor_tool.remove(count)
        # distractor_pool = []
        # while True:
        #     sample = int(np.random.choice(tmp_pool, None))
        #     if sample != count and sample not in distractor_pool:
        #         distractor_pool.append(int(sample))
        #     if len(distractor_pool) > self.distractor_pool_size:
        #         break

        return count, list(distractor_tool), question_values

    
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
        #new values look like this 
        #{'target_index': 38, 'voice': 'S'}
        # i need: new_words = {"target_index": 38th, "voice": "soprano"}
        new_words = {}
      
        for var_name, value_symbol in new_values.items():
            value_symbol = str(value_symbol)
            if var_name in self.ontology:
                possible_dicts = self.ontology[var_name]
                for dict_item in possible_dicts:
                    if value_symbol in dict_item:
                        new_words[var_name] = dict_item[value_symbol]             
    
       # distractor_pool = self.get_distractors(distractor_keys, ground_truth_pool)
       # breakpoint()
       # additional, just safety reasons: Ensure the ground truth is not in the distractor pool
        if ground_truth in ground_truth_pool:
            ground_truth_pool.remove(ground_truth)
        if len(set(ground_truth_pool))< self.min_num_distractors:
            if self.config.get('verbose', False):
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
            elif "rhythm" in method_name:
                sample_space = copy.deepcopy(set(self.dict_rhythm_ontology.values()))
                sample_space.discard(ground_truth)
                additional_distractors = np.random.choice(list(sample_space), len_diff, replace=False).tolist()
            ground_truth_pool += additional_distractors
        else:
            ground_truth_pool = list(set(ground_truth_pool))
        
        return ground_truth, ground_truth_pool, new_values, new_words

    def get_nth_rhythm(self, path: str, values: dict) -> str:
        """
        Logic: Parses a MusicXML file and returns the rhythm (e.g., quarter, eighth) of the index-th note in the specified voice part.

        Args:
            path (str): The path to the directory of the piece, which contains the MusicXML file.
            values (dict): A dictionary containing the value for {index} and {voice}, e.g., {"target_index": 1, "voice": "S"}

        Returns:
            str: return RHYTHM ONLY (e.g., "quarter", "eighth").
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
            values['target_index'] = self.ontology['target_index'][note_index]
        else:
            note_index = values.get('target_index')

        if note_index == 'end':
            note_index = -1

        # Check if the target_index is out of bounds
        if note_index >= len(notes) or int(note_index) < -len(notes):
            raise IndexError(f"Requested note target_index '{note_index}' is out of bounds. The part has {len(notes)} notes.")

        # Get the target note and return its rhythm
        target_note = notes[note_index]
        target_rhythm = target_note.quarterLength

        if not self.random_distractors:
            all_notes = []
            for vv in self.voice_mapping.keys():
                other_part = score.parts[self.voice_mapping[vv]]
                other_notes = list(other_part.flatten().getElementsByClass(note.Note))
                all_notes += other_notes
            # Build a set of candidate distractor rhythms (exclude the true rhythm)

            distractor_pool_set = set(n.quarterLength for n in all_notes)
            distractor_pool_set.discard(target_rhythm)
            distractor_pool = list(distractor_pool_set)

            # Map rhythms to their ontology names
            distractor_pool = [self.dict_rhythm_ontology[sample] for sample in distractor_pool]
        else:
            try:
                distractor_pool = np.random.choice(list(self.dict_rhythm_ontology.values()), self.distractor_pool_size, replace=False).tolist()
            except ValueError:
                print(f"Warning: Not enough unique rhythms in the piece to generate {self.distractor_pool_size} distractors. Sampling from the entire ontology instead.")
                distractor_pool = np.random.choice(list(self.dict_rhythm_ontology.values()), len(list(self.dict_rhythm_ontology.values())), replace=False).tolist()
            if target_rhythm in distractor_pool:
                distractor_pool.remove(target_rhythm)
            
        return self.dict_rhythm_ontology[target_rhythm], distractor_pool, values

    def get_rhythm_pattern(self, path: str, question_values: dict) -> tuple[str, list[str]]:
        
        musicxml_path = get_musicxml_file_path(path)
        score = converter.parse(musicxml_path)
        # # target_rhythm = question_values.get('rhythm')
       
        # if target_rhythm not in self.dict_rhythm_ontology.keys():
        #     raise ValueError(f"Invalid rhythm specified: {target_rhythm}. Expected one of {self.dict_rhythm_ontology}.")
   
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

        if not os.path.exists(musicxml_path):
            raise FileNotFoundError(f"Could not find file: {musicxml_path}")
        if self.use_all_inds:
            note_index = int(np.random.choice(range(len(notes)-1)))
            question_values['target_index'] = self.ontology['target_index'][note_index]
        else:
            note_index = question_values.get('target_index')

        if note_index == 'end':
            note_index = -1
        # Check if the target_index is out of bounds
        note_index = int(note_index)
        if note_index >= len(notes) or int(note_index) < -len(notes):
            raise IndexError(f"Requested note target_index '{note_index}' is out of bounds. The part has {len(notes)} notes.")

        # Parse the MusicXML file into a music21 Stream
        
        props = []
        for note_idx in range(len(notes)-1):
            n1 = notes[note_idx].quarterLength
            n2 = notes[note_idx + 1].quarterLength
            if n1 and n2 != 0:
                rhythmic_proportion = n2/n1
    
            # rhythmic_proportion = n2/n1 if n1 != 0 else 0
            # iv = interval.Interval(n1, n2)
            # interval_name = iv.simpleName
            # intervals.append(interval_name)
            props.append(rhythmic_proportion)
        target_prop = props[note_index]#self.dict_rhythm_ontology[target_rhythm]
        # props_voices = []
        all_props = []
        for vv in self.voice_mapping.keys():
            other_part = score.parts[self.voice_mapping[vv]]
            other_notes = list(other_part.flatten().getElementsByClass(note.Note))
            for note_idx in range(len(other_notes)-1):
                n1 = other_notes[note_idx].quarterLength
                n2 = other_notes[note_idx + 1].quarterLength
                if n1 and n2 != 0:
                    rhythmic_proporton= n2/n1
                all_props.append(rhythmic_proporton)
        for _p in all_props:
            _key = str(round(_p,2))
            try:
                all_props_names = self.dict_rhythm_prop_ontology[_key]
            except KeyError:
                all_props_names = "other"
            # props_voices.append(props)
        # count = int(sum(1 for n in notes if n.quarterLength == target_rhythm))
        #breakpoint()
        
        # all_rhys = []
      
        # for vv in self.voice_mapping.keys():
        #     other_part = score.parts[self.voice_mapping[vv]]
        #     other_notes = list(other_part.flatten().getElementsByClass(note.Note))
        #     all_rhys.append([n.quarterLength for n in other_notes])
        
       # breakpoint()
        # tmp_pool = []
        # for nn in all_rhys:
        #     for length in list(set(nn)):
        #         tmp_pool.append(int(sum(1 for _ in nn if _ == length)))
        try:
            target_prop_name = self.dict_rhythm_prop_ontology[target_prop]
        except:
            target_prop_name="other"
            
        if not self.random_distractors:
             distractor_tool = set(all_props_names)
             distractor_tool.discard(target_prop_name)
        else:
            try:        
                distractor_tool = np.random.choice(list(set(all_props_names)), self.distractor_pool_size, replace=False).tolist()
            except ValueError:
                if self.verbose:
                    print(f"Warning: Not enough unique rhythm proportions in the ontology. number of distractors as number of unique rhythm proportions: {len(self.ontology['rhythm_proportion'])}")
                distractor_tool = np.random.choice(list(set(self.dict_rhythm_prop_ontology)), len(set(self.dict_rhythm_prop_ontology)), replace=False).tolist()

            if target_prop_name in distractor_tool:
                distractor_tool.remove(target_prop_name)

        return target_prop_name, list(distractor_tool), question_values

    def get_time_signature(self, path: str, question_values: dict) -> tuple[str, list[str]]:
        musicxml_path = get_musicxml_file_path(path)

        if not os.path.exists(musicxml_path):
            raise FileNotFoundError(f"Could not find file: {musicxml_path}")
        
        # Parse the MusicXML file into a music21 Stream
        score = converter.parse(musicxml_path)
        time_signatures = score.recurse().getElementsByClass('TimeSignature')
        
        if not time_signatures:
            if self.config.get('verbose', False):
                print("No time signatures found in the piece., skipping question.")
            
            return None, distractor_pool, question_values
        else:
            target_time_signature = time_signatures[0].ratioString
            target_time_signature = self.dict_time_signature_ontology[target_time_signature]
            distractor_pool = list(self.dict_time_signature_ontology.values())

            return target_time_signature, distractor_pool, question_values
   
    def get_harmonic_tonality(self, path: str, question_values: dict) -> tuple[str, list[str]]:
        musicxml_path = get_musicxml_file_path(path)

        if not os.path.exists(musicxml_path):
            raise FileNotFoundError(f"Could not find file: {musicxml_path}")
        
        # Parse the MusicXML file into a music21 Stream
        score = converter.parse(musicxml_path)

        #key_signatures = score.recurse().getElementsByClass('KeySignature')
        key_signatures = score.analyze('key')
        harmonic_function = question_values["function"]
        keys_dict = {}
        
        if not key_signatures:
            if self.config.get('verbose', False):
                print("No key signatures found in the piece., skipping question.")
            
            return None, {}, question_values
        
        else:

            keys_dict["tonic"]  = key_signatures.name
            keys_dict["dominant"]  = key.Key(key_signatures.getDominant().name, key_signatures.mode).asKey().name
            keys_dict["relative minor/major"] = key_signatures.relative.name                       
            target_key_signature_name = self.dict_tonality_ontology[keys_dict[harmonic_function]]
            
            if not(self.random_distractors):
                distractor_pool = list(keys_dict.values())
            else:
                try:
                    distractor_pool = np.random.choice(list(self.dict_tonality_ontology.values()), self.distractor_pool_size, replace=False).tolist()
                except ValueError:
                    if self.verbose:
                        print(f"Warning: Not enough unique tonalities in the ontology. number of distractors as number of unique tonalities: {len(set(self.dict_tonality_ontology.values()))}")
                    distractor_pool = np.random.choice(list(self.dict_tonality_ontology.values()), len(set(self.dict_tonality_ontology.values())), replace=False).tolist()
            
            return target_key_signature_name, distractor_pool, question_values
        
    def get_harmonic_chord(self, path: str, question_values: dict) -> tuple[str, list[str]]:
        musicxml_path = get_musicxml_file_path(path)

        if not os.path.exists(musicxml_path):
            raise FileNotFoundError(f"Could not find file: {musicxml_path}")
        
        # Parse the MusicXML file into a music21 Stream
        score = converter.parse(musicxml_path)
        # chords = score.recurse().getElementsByClass('Chord')
        chords = score.chordify().recurse().getElementsByClass('Chord')
        chords = list(chords)

        if not chords:
            raise ValueError(f"No valid chords found.")
        if self.use_all_inds:
            note_index = int(np.random.choice(range(len(chords)-1)))
            question_values['target_index'] = self.ontology['target_index'][note_index]
        else:
            note_index = question_values.get('target_index')

        if note_index == 'end':
            note_index = -1

        # Check if the target_index is out of bounds
        if note_index >= len(chords) or int(note_index) < -len(chords):
            raise IndexError(f"Requested note target_index '{note_index}' is out of bounds. The part has {len(chords)} chords.")

        target_chord = chords[note_index].commonName
        
        if not chords:
            if self.config.get('verbose', False):
                print("No chords found in the piece., skipping question.")
            
            return None, distractor_pool, question_values
        else:

            if "with" in target_chord:  # filter out chords with added tones (e.g., "C major with added sixth")
                target_chord = target_chord.split(" with")[0]
            target_chord_name = self.dict_chord_ontology[target_chord]
            distractor_pool = list(self.dict_chord_ontology.values())

            return target_chord_name, distractor_pool, question_values
        
    def get_harmonic_cadence(self, path: str, question_values: dict) -> tuple[str, list[str]]:
        musicxml_path = get_musicxml_file_path(path)

        if not os.path.exists(musicxml_path):
            raise FileNotFoundError(f"Could not find file: {musicxml_path}")
        
        # Parse the MusicXML file into a music21 Stream
        score = converter.parse(musicxml_path)
        # chords = score.recurse().getElementsByClass('Chord')
        chords = score.chordify().recurse().getElementsByClass('Chord')
        chords = list(chords)
        signature = score.recurse().getElementsByClass('KeySignature')

        if not chords:
            raise ValueError(f"No valid chords found.")
        if self.use_all_inds:
            note_index = int(np.random.choice(range(len(chords)-1)))
            question_values['target_index'] = self.ontology['target_index'][note_index]
        else:
            note_index = question_values.get('target_index')

        if note_index == 'end':
            note_index = -1

        # Check if the target_index is out of bounds
        if note_index >= len(chords) or int(note_index) < -len(chords):
            raise IndexError(f"Requested note target_index '{note_index}' is out of bounds. The part has {len(chords)} chords.")

        target_chord = chords[note_index].commonName
        score_cadences = []
        for _ni in range(len(chords)-1):
            # dont remeber how to get the roman number progression / not sure if it is the best way
            rn1 = str(roman.romanNumeralFromChord(chords[_ni], signature[0]).figure)
            rn2 = str(roman.romanNumeralFromChord(chords[_ni+1], signature[0]).figure)
            cadence = [chords[_ni], chords[_ni+1]]
            score_cadences.append(cadence)
        if not chords:
            if self.config.get('verbose', False):
                print("No chords found in the piece., skipping question.")
            
            return None, distractor_pool, question_values
        else:
            target_cadence = score_cadences[note_index]
            target_cadence = self.dict_cadence_ontology[target_cadence]
            distractor_pool = list(self.dict_cadence_ontology.values())

            return target_cadence, distractor_pool, question_values