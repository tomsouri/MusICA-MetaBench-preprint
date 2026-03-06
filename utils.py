import os

def get_musicxml_file_path(piece_dir: str) -> str:
    """
    Given the directory of a piece, returns the path to the MusicXML file.
    
    Args:
        piece_dir (str): The directory containing the piece's files.
        
    Returns:
        str: The path to the MusicXML file.
    """
    return os.path.join(piece_dir, "symbolic.musicxml")