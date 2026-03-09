import importlib.util
import os
import sys
from pathlib import Path


def get_musicxml_file_path(piece_dir: str) -> str:
    """
    Given the directory of a piece, returns the path to the MusicXML file.
    
    Args:
        piece_dir (str): The directory containing the piece's files.
        
    Returns:
        str: The path to the MusicXML file.
    """
    return os.path.join(piece_dir, "symbolic.musicxml")


def load_methods_module(file_path: str):
    """Dynamically loads a python module from a given file path."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Methods file not found: {file_path}")
    
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module