import unittest
import os
import yaml
from music21 import key, chord, pitch, roman
import itertools

# This is a simplified version of the function for testing purposes,
# as the original is in a class.
def get_cadence_types():
    """
    Generates a dictionary of cadence types.
    If a YAML file with the ontology exists, it loads it. Otherwise, it builds the ontology and saves it.
    """
    ontology_path = "cadence_types.yaml"

    if os.path.exists(ontology_path):
        with open(ontology_path, 'r') as file:
            print(f"Loading cadence types ontology from {ontology_path}")
            return yaml.load(file, Loader=yaml.FullLoader)

    print(f"Building cadence types ontology...")
    # Generate all possible cadence types
    roman_numerals = set()
    pitch_classes = list(range(12))
    key_a = key.Key('A')

    for r in range(3, 5):  # chord size
        for pcs in itertools.combinations(pitch_classes, r):
            ch = chord.Chord([pitch.Pitch(midi=60 + pc) for pc in pcs])
            try:
                rn = roman.romanNumeralFromChord(ch, key_a)
                roman_numerals.add(str(rn.figure))
            except Exception:
                continue
    
    ontology = set()
    for rn1 in roman_numerals:
        for rn2 in roman_numerals:
            if rn1 != rn2:
                ontology.add(f"{rn1}: {rn2}")

    ontology = {cad_name: cad_name for cad_name in ontology}

    with open(ontology_path, 'w') as file:
        yaml.dump(ontology, file)
        print(f"Cadence types ontology saved to {ontology_path}")

    return ontology

class TestCadenceOntology(unittest.TestCase):

    def tearDown(self):
        if os.path.exists("cadence_types.yaml"):
            os.remove("cadence_types.yaml")

    def test_get_cadence_types(self):
        # Clean up before test
        if os.path.exists("cadence_types.yaml"):
            os.remove("cadence_types.yaml")

        # 1. Call `get_cadence_types` for the first time. It should build the ontology.
        print("First call to get_cadence_types...")
        ontology1 = get_cadence_types()
        
        # 2. Check if the .yaml file was created.
        self.assertTrue(os.path.exists("cadence_types.yaml"))
        
        # 3. Check if the returned ontology is a dictionary and not empty.
        self.assertIsInstance(ontology1, dict)
        self.assertGreater(len(ontology1), 0)

        # 4. Call `get_cadence_types` again. It should load from the file.
        print("\\nSecond call to get_cadence_types...")
        ontology2 = get_cadence_types()

        # 5. Check that the loaded ontology is the same as the first one.
        self.assertEqual(ontology1, ontology2)

        # 6. Clean up the created file.
        os.remove("cadence_types.yaml")

if __name__ == "__main__":
    unittest.main()
