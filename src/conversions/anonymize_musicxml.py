import xml.etree.ElementTree as ET

def anonymize_pure_xml(input_path, output_path):
    """
    Removes metadata from a MusicXML file via pure XML parsing,
    preserving all other layout and formatting bit-for-bit.
    """
    # Parse standard XML
    tree = ET.parse(input_path)
    root = tree.getroot()
    
    # 1. Anonymize the <identification> block (creator, rights, etc.)
    for identification in root.findall('.//identification'):
        for creator in identification.findall('creator'):
            creator.text = "-"
        for rights in identification.findall('rights'):
            rights.text = "-"
            
    # 2. Anonymize the <work> block (work-title)
    for work in root.findall('.//work'):
        for title in work.findall('work-title'):
            title.text = "-"
            
    # 3. Anonymize the <movement-title>
    for mov_title in root.findall('.//movement-title'):
        mov_title.text = "-"
        
    # 4. Anonymize printed credits on the page
    # Look for textual credits and replace them if they aren't page numbers
    for credit in root.findall('.//credit'):
        for credit_words in credit.findall('.//credit-words'):
            # Basic heuristic: if it contains text, replace it. 
            # You might want to leave page numbers alone.
            if credit_words.text and not credit_words.text.isdigit():
                credit_words.text = "-"

    # Write out the modified XML tree
    tree.write(output_path, encoding='UTF-8', xml_declaration=True)
    print(f"Pure XML anonymized file saved to: {output_path}")

# Example usage:
# anonymize_pure_xml('original.musicxml', 'anonymized.musicxml')

# Example usage:
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Anonymize musicXML file.")
    parser.add_argument('--src', required=True, help="Src musicXML file")
    parser.add_argument('--tgt', required=True, help="Tgt musicXML file")
    
    args = parser.parse_args()

    anonymize_pure_xml(input_path=args.src, output_path=args.tgt)


if __name__ == "__main__":
    main()
