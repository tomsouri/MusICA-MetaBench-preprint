import os
import yaml

def build_frequent_cadences_ontology():
    """
    Builds a more comprehensive cadence ontology using frequent Roman numerals.
    Saves the result to selected_cadences.yaml.
    """
    ontology_path = "selected_cadences.yaml"
    
    # Common cadence sequences (Predominant -> Dominant -> Tonic)
    # Plus others in the range of 20-50 samples
    selected_list = [
        # Authentic cadences
        "V - I", "V7 - I", "v - i", "V - i", "V7 - i", 
        "vii° - I", "vii°7 - I", "vii° - i", "vii°7 - i",
        # Plagal cadences
        "IV - I", "iv - I", "IV - i", "iv - i",
        # Half cadences
        "I - V", "i - V", "IV - V", "iv - V", "ii - V", "ii° - V", 
        "vi - V", "VI - V", "ii7 - V", "ii°7 - V",
        # Deceptive cadences
        "V - vi", "V - VI", "V7 - vi", "V7 - VI",
        # Other common progressions found in cadential positions
        "vi - ii", "VI - ii°", "IV - ii", "iv - ii°", 
        "I - vi", "i - VI", "iii - vi", "III - VI",
        "ii - IV", "ii° - iv", "I - IV", "i - iv",
        "V - IV", "V - iv", "ii - V7", "ii° - V7",
        "iii - IV", "III - IV"
    ]
    
    ontology = {cad: cad for cad in selected_list}
    
    with open(ontology_path, 'w') as file:
        yaml.dump(ontology, file)
    
    print(f"Refined ontology with {len(ontology)} patterns saved to {ontology_path}")
    return ontology

if __name__ == "__main__":
    build_frequent_cadences_ontology()
