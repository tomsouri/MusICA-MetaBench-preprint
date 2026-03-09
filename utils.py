import importlib.util
import os
import sys
from pathlib import Path
import base64


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


try:
    import gspread
except ImportError:
    gspread = None


def append_to_google_sheet(config: dict, row_data: list, header: list = None, force_header_print: bool = False):
    """Append a single row to a Google Sheet"""
    if gspread is None:
        print("⚠ gspread not installed; Google Sheets logging disabled.")
        return

    required = ['sheet_id', 'sheet_name', 'credentials_location']
    missing = [k for k in required if not config.get(k)]
    if missing:
        print(f"⚠ Google Sheets logging skipped: missing config fields: {', '.join(missing)}")
        return

    cred_path = config['credentials_location']
    if not os.path.exists(cred_path):
        print(f"⚠ Google Sheets logging skipped: credentials file not found at {cred_path}")
        return

    # Check and crop cells exceeding 50,000 character limit
    MAX_CELL_CHARS = 50000
    cropped_row = []
    for cell_value in row_data:
        cell_str = str(cell_value)
        if len(cell_str) > MAX_CELL_CHARS:
            cropped_row.append(cell_str[:MAX_CELL_CHARS - 4] + "...")
        else:
            cropped_row.append(cell_value)

    try:
        from google.oauth2.service_account import Credentials
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(cred_path, scopes=scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(config['sheet_id']).worksheet(config['sheet_name'])

        # Get only the first column to check if the sheet is empty (much faster than get_all_values)
        col_a_values = sheet.col_values(1)

        # If Column A is completely empty, insert the header first
        if (header and len(col_a_values) == 0) or force_header_print:
            # table_range="A:A" forces it to anchor strictly to Column A
            sheet.append_row(header, table_range="A:A", value_input_option="USER_ENTERED")
        
        # Append the new row data
        sheet.append_row(cropped_row, table_range="A:A", value_input_option="USER_ENTERED")
        
        print("✓ Logged to Google Sheet")
    except Exception as e:
        print(f"⚠ Failed to log to Google Sheet: {e}")


# TODO: if appending still fails, this bypasses the google's append_row logic:
# 
# def append_to_google_sheet(config: dict, row_data: list, header: list = None):
#     """Append a single row to a Google Sheet using explicit row calculations."""
#     if gspread is None:
#         print("⚠ gspread not installed; Google Sheets logging disabled.")
#         return

#     required = ['sheet_id', 'sheet_name', 'credentials_location']
#     missing = [k for k in required if not config.get(k)]
#     if missing:
#         print(f"⚠ Google Sheets logging skipped: missing config fields: {', '.join(missing)}")
#         return

#     cred_path = config['credentials_location']
#     if not os.path.exists(cred_path):
#         print(f"⚠ Google Sheets logging skipped: credentials file not found at {cred_path}")
#         return

#     # Check and crop cells exceeding 50,000 character limit
#     MAX_CELL_CHARS = 50000
#     cropped_row = []
#     for cell_value in row_data:
#         cell_str = str(cell_value)
#         if len(cell_str) > MAX_CELL_CHARS:
#             cropped_row.append(cell_str[:MAX_CELL_CHARS - 4] + "...")
#         else:
#             cropped_row.append(cell_value)

#     try:
#         from google.oauth2.service_account import Credentials
#         scope = ['https://www.googleapis.com/auth/spreadsheets']
#         creds = Credentials.from_service_account_file(cred_path, scopes=scope)
#         client = gspread.authorize(creds)
        
#         sheet = client.open_by_key(config['sheet_id']).worksheet(config['sheet_name'])

#         # 1. Fetch all data to definitively find the true bottom of the sheet.
#         # This works perfectly even if columns are hidden.
#         existing_data = sheet.get_all_values()
#         current_rows = len(existing_data)
        
#         rows_to_insert = []
        
#         # 2. Add header if the sheet is completely empty
#         if header and current_rows == 0:
#             rows_to_insert.append(header)
            
#         # 3. Add the actual data
#         rows_to_insert.append(cropped_row)
        
#         # 4. Calculate exactly which row number we should start writing on
#         next_row_index = current_rows + 1
        
#         # 5. Insert rows targeting the exact cell coordinates (e.g., "A5", "A6")
#         # By targeting a specific cell, we completely bypass the API's broken table-guessing.
#         for row in rows_to_insert:
#             target_cell = f"A{next_row_index}"
#             sheet.append_row(row, table_range=target_cell, value_input_option="USER_ENTERED")
#             next_row_index += 1
            
#         print("✓ Logged to Google Sheet")
#     except Exception as e:
#         print(f"⚠ Failed to log to Google Sheet: {e}")

def encode_file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as file:
        return base64.b64encode(file.read()).decode('utf-8')