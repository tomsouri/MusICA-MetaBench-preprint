import requests
from dataclasses import dataclass
import json
import os, sys
import base64
import argparse
import re
import datetime
import time
import logging
import csv
import random

# gspread is optional; allow the script to run without it
try:
    import gspread
except Exception:
    gspread = None

from pathlib import Path



# text how-to: https://openrouter.ai/docs/quickstart
# image how-to: https://openrouter.ai/docs/guides/overview/multimodal/images
# audio how-to: https://openrouter.ai/docs/guides/overview/multimodal/audio
# pdf how-to: https://openrouter.ai/docs/guides/overview/multimodal/pdfs

# Done: 
# x logging of everything (model, prompt, response, other details (full response JSON), price)
# x logging to table
# x log running time
# x deterministic output: set temperature, top_p, etc. and use it
# x improve logging to table: separately parameters
# x logging takes to much space (full payload with base64-encoded files)
# x full question
# x parse response to extract the actual answer
 

# TODO:
# - where to define and decide the number of distractors? (in benchmark content file?)
# - set the random guess bsln performance according to it
# - with the expensive models, I should limit the output length
# - better prompt: how to ask, how to include the file?
# - error handling
# - load prompts from files
# - load everything content from a file
# 
# TODO later:
# - multiple files: how to link them from the prompt?
# - load general setup from file: model, url, api key
# TODO nice-to-have:
# - allow for concurrent requests from model


@dataclass
class Config:
    #input_file: str  # jsonl file to send to OpenAI
    #output_file: str  # jsonl file to store the responses
    #n_threads: int = 2  # Number of threads to use for parallel processing
    #prompt_key: str = "prompt"  # Key of the prompt in the input file
    #response_key: str = "reponse"
    #answer_key: str = 'answer'

    #model: str = "google/gemini-2.0-flash-lite-001"  # cheapest model for audio-image-pdf-text
    #model: str = "google/gemini-2.5-flash" # still relatively bad
    #model: str = "google/gemini-3-flash-preview"  # mid-range model for audio-image-pdf-text
    # model = "google/gemini-3-pro-preview" # most expensive model, for audio-image-pdf-text
    # model = "openai/gpt-4.1-nano"
    # model = "allenai/molmo-2-8b:free"
    # model = "google/gemma-3-4b-it:free"
    # model = "google/gemini-2.0-flash-exp:free" # only image model, is free. It has some rate limit, which causes
    # errors sometimes. And may train on my data.
    #model = "openai/gpt-4.1-nano"
    
    url: str = "https://openrouter.ai/api/v1/chat/completions"  # OpenAI API base URL
    # temperature: float = 0.0 # for deterministic output
    # #top_k: int = 1
    # top_p: float = 0.0
    
    # https://openrouter.ai/docs/api/reference/parameters
    # find_supported_params.py can be used to find other supported parameters
    #top_p: float = 1.0
    #max_tokens: int = 100
    #n_samples: int = 1

    # questions_file: str = "expanded_output.tsv"
    questions_file: str = "expanded_output.tsv"
    
    data_base_dir: str = "data/"

    seed: int = 42
    dry_run: bool = False # if True, do not send any requests

    nota_text = "None of the above"
    #nota_text = "None of the other options is correct"



    prompt_closed = """You are a specialist in the analysis and interpretation of musical materials. You are provided with a musical work as <FORMAT>. Analyze the material carefully. Then, given a question and a set of possible answers, choose the most appropriate option.
Question:
<QUESTION>
Options:
<OPTIONS_TEXT>

<POTENTIAL_TEXTFILE_PLACEHOLDER>

After any potential reasoning, end with your final answer in this format:
Final Answer: <answer>
where <answer> is the single correct letter choice <OPTION_LABELS>. Only include the letter."""

#     system_prompt_for_png = """### Role
# You are a specialist in **music-notation reading and pitch identification** from **rendered musical scores (PNG images)**. Your job is to **visually parse the notation** (staff position, clefs, key signatures, accidentals, octave marks, ties, transpositions, etc.) and answer the question with **scientific pitch notation (SPN)** when requested.

# ### Core requirements
# 1. **Only use what is visible in the image.** Do not guess from style, common patterns, or “likely” notes.
# 2. **Be explicit about interpretation choices** (e.g., concert pitch vs written pitch for transposing instruments).
# 3. If the image resolution, cropping, or engraving ambiguity prevents a reliable answer, say so and **request a clearer crop** of the relevant region (e.g., “first measure of top staff including clef and key signature”).
# 4. When the question is ambiguous (e.g., “first note” in a multi-staff system), provide the **most reasonable interpretations** and label them clearly.

# ---

# ## Procedure (what to check, in order)
# 1. **Locate the relevant region** for the question (e.g., far left of the first system for “first note”).
# 2. Identify **clef(s)** on the relevant staff at that moment (treble, bass, alto, tenor, percussion, clef changes).
# 3. Identify **key signature** (if any) and apply it to the note spelling unless cancelled by an accidental.
# 4. Identify **time signature** only if it helps disambiguate (e.g., whether something is a grace note vs main note).
# 5. Determine the target notehead's:
#    - **Staff line/space position** (including ledger lines)
#    - **Accidental** (sharp/flat/natural/double-sharp/double-flat; cautionary accidentals count)
#    - **Octave displacement marks** (8va/8vb/15ma, ottava lines)
#    - **Ties** (tied notes are not new attacks; the “first note” may be the tied-into pitch if it's the first sounding pitch)
# 6. If the staff is for a **transposing instrument**, decide whether the question expects:
#    - **Written pitch (as notated)**, or
#    - **Concert pitch**
#    If the question does not specify, provide **both**, clearly labeled.
# 7. Convert the result to **SPN** (e.g., `C4`, `F#3`, `Bb5`). Use standard SPN where **middle C is `C4`**.
# 8. Report **confidence** and any ambiguity sources (blurred accidental, unclear clef, missing key signature, etc.).

# ---

# ## Definitions / conventions to follow
# - **Scientific pitch notation (SPN):** letter name + accidental (if any) + octave number, e.g. `G4`, `Ab3`, `A#5`.
# - **Accidental scope:** applies according to standard notation rules (typically through the measure for the same staff and octave, unless cancelled).
# - **“First note in the score”:**
#   - Default meaning: the **first sounding pitched notehead** encountered **left-to-right** in the first system.
#   - Do **not** treat clefs, key signatures, time signatures, barlines, or rests as notes.
#   - If **grace notes** occur before the first main note, treat them as **notes** and report the **earliest grace note** as the “first note” *unless the question explicitly says “first main note”*.
#   - If there is a chord as the first event, report the **lowest pitch and the full chord** (or ask which is intended), depending on the question.

# ---

# ## Response format (concise, test-friendly)
# When answering, use this structure:

# - **Answer:** `<SPN>`
# - **Context:** `clef=…; key signature=…; staff/voice=…; measure/position=…; written vs concert=… (if relevant)`
# - **Confidence:** `high / medium / low`
# - **If ambiguous:** list the plausible alternatives with short reasons.

# ---

# <details>
# <summary>Optional: What to ask for if the image is hard to read</summary>

# If you cannot confidently identify the note, request one of:
# - A **higher-resolution PNG**
# - A **tight crop** around the relevant area (e.g., “first system, left margin through beat 2, including clef and key signature”)
# - Separate crops for each staff if multi-staff

# Also say *what* is unclear (accidental shape, ledger line count, clef type, octave mark, etc.).

# </details>"""

    system_prompt_for_png = """**Role:**
You are an expert Musicologist and Optical Music Recognition (OMR) Specialist. Your task is to analyze images of musical notation with absolute precision. You must prioritize factual accuracy over creative interpretation. If a detail is blurry or not present, state that it is "not visible" rather than guessing.

**Operational Guidelines:**

1.  **Musical Metadata:** Identify the title, composer, opus number, tempo markings (e.g., $Adagio$, $\bullet = 120$), key signature (number of sharps/flats), and time signature (e.g., $3/4$, $C$).
2.  **Retrieval & Layout:** Locate specific elements by their coordinate space and logical position. Reference measures (bars) by number and systems by vertical order. Track specific symbols like фермата (fermatas), dynamics ($p$, $mf$, $sfz$), and articulation marks.
3.  **Replayability (Syntactic Accuracy):** Analyze the notes for pitch and duration. Ensure that the number of beats in a measure matches the time signature. Identify accidentals (naturals, sharps, flats) and their scope within the measure.
4.  **Reprintability (Structural Integrity):** Observe the engraving details. Note the clef types (Treble, Bass, Alto), the presence of braces/brackets for systems, barline types (double barlines, repeat signs), and the specific layout of ties vs. slurs.

**Constraint Rules:**
- **Zero Hallucination:** If a note head is ambiguous, do not assign it a pitch. Reporting "ambiguous pitch at Measure X" is better than a wrong guess.
- **Mathematical Precision:** Use LaTeX for all mathematical expressions, including time signatures like $4/4$ and frequency/rhythmic ratios.
- **Strict Reasoning:** Always perform a step-by-step "Chain of Thought" analysis of the visual evidence before arriving at a conclusion.

**Output Format:**
1.  **Analysis/Reasoning:** Provide a detailed breakdown of your visual observations.
2.  **Final Answer:** You must conclude your response with the specific answer in a concise format.

Follow this template for the conclusion:
Final Answer: <your_final_answer>
"""

    prompt_open = """**Question:**  
<QUESTION>
"""



        # prompt only for discovering whether the model even knows what it sees
#     prompt_open = """You are a specialist in the analysis of documents. You are provided with a document in PDF format. Analyze the material carefully. Then, answer the given question.

# Question:
# <QUESTION>
# """


    musical_piece_format_info = {
        "audio": {"wav": "an audio recording (WAV format)"},
        "visual": {"png": "a rendered score (PNG format)",
                   "pdf": "a rendered score (PDF format)"},
        "symbolic": {"musicxml": "a musical score (MusicXML format)",
                     "midi": "a musical score (MIDI format represented as CSV)", 
                     "abc": "a musical score (ABC notation format)"
                     }
    }


    is_closed_ended = False # Multiple-choice, options are given

    normal_options_count = 4  # excluding NOTA
    
    potential_option_labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
    label_option_divider = ")"

    # for automatic logging to Google Sheets
    sheet_id = "12Oaw4k-ElD4OvdHxWbP9KFV6CgQH4M5aRz-GuHTG10w"
    sheet_name = "List 1"
    credentials_location = "logs/protobenchmark-logging-aa9418338494.json"

    
    def __post_init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key is None:
            raise RuntimeError("OPENROUTER_API_KEY environment variable is not set")
        self.api_key = api_key



@dataclass
class BenchmarkItem:
    """Holds all data for a single benchmark question from the TSV file."""
    item_id: str
    category: str
    sub_category: str
    difficulty: str
    question_short: str
    question_natural: str
    question_rewritten: str
    source_dataset: str
    piece_id: str
    ground_truth: str
    distractors: list
    modality: str
    submodality: str
    note: str
    filetype: str
    notation_type: str
    notation_complexity: str
    content_file: str
    add_nota: bool
    is_nota_correct: bool
    random_guess_performance: str
    correct_answer: str
    correct_answer_label: str
    correct_answer_text: str
    options: list[str]
    options_random_order: list[str]
    option_labels: list[str]
    labels2options: dict[str, str]



    @classmethod
    def from_dict(cls, row: dict, config: Config):
        """Create a BenchmarkItem from a TSV row dictionary."""

        item_id=row.get("question ID", "unknown")
        category=row.get("category", "")
        sub_category=row.get("sub-category", "")
        difficulty=row.get("difficulty", "")
        question_short=row.get("question: short", "")
        question_natural=row.get("question: natural", "")
        question_rewritten=row.get("question: rewritten for LLM", "")
        source_dataset=row.get("source dataset", "")
        piece_id=row.get("piece ID", "")
        ground_truth=row.get("ground truth", "")
        distractors_text=row.get("distractors", "[]")
        modality=row.get("modality", "")
        submodality=row.get("submodality", "")
        filetype=row.get("filetype", "")
        notation_type = row.get("notation type", "")
        notation_complexity = row.get("notation complexity", "")
        note=row.get("note", "")
        add_nota = row.get("add NOTA", "no") in ["yes", "true", "1"]
        is_nota_correct = row.get("is NOTA correct", "no") in ["yes", "true", "1"]
        random_guess_performance=row.get("random guess performance accuracy", "")

        # Parse distractors
        try:
            distractors = json.loads(distractors_text)
        except json.JSONDecodeError:
            distractors = []
                
        # validate the consistency of the flags
        if is_nota_correct and not add_nota:
            raise ValueError("If NOTA is supposed to be the correct answer, add_nota must be True.")
        
        content_file_path = Path(config.data_base_dir) / row.get("content file", "")
        
        # Validate that content file exists
        if not content_file_path.is_file():
            logging.error(f"Content file not found: {content_file_path}")
            raise FileNotFoundError(f"Content file not found: {content_file_path}")

        # if ground truth is included in the options (is_nota_correct is False), correct answer is ground truth,
        # otherwise it is the text for NOTA        
        if is_nota_correct:
            # exclude ground truth from options
            options = distractors[:config.normal_options_count]
            correct_answer = config.nota_text
        else:    
            options = distractors[:config.normal_options_count-1] + [ground_truth]
            correct_answer = ground_truth
        
            

        # sort options randomly
        options_random_order = sort_randomly(options)

        if add_nota:
            options_random_order.append(config.nota_text)

        option_labels = config.potential_option_labels[:len(options_random_order)]

        correct_answer_label = option_labels[options_random_order.index(correct_answer)]
        correct_answer_text = f"{correct_answer_label}) {correct_answer}."
        labels2options = {label: option for label, option in zip(option_labels, options_random_order)}

        if not config.is_closed_ended:
            # if it is open-ended, those fields are not applicable
            distractors = []
            correct_answer = ""
            correct_answer_label = ""
            correct_answer_text = ""
            options = []
            options_random_order = []
            option_labels = []
            labels2options = {}
            add_nota = "-"
            is_nota_correct = "-"
            random_guess_performance = "-"

        instance = cls(
            item_id=item_id,
            category=category,
            sub_category=sub_category,
            difficulty=difficulty,
            question_short=question_short,
            question_natural=question_natural,
            question_rewritten=question_rewritten,
            source_dataset=source_dataset,
            piece_id=piece_id,
            ground_truth=ground_truth,
            distractors=distractors,
            modality=modality,
            submodality=submodality,
            note=note,
            filetype=filetype,
            notation_type=notation_type,
            notation_complexity=notation_complexity,
            content_file=content_file_path,
            add_nota=add_nota,
            is_nota_correct=is_nota_correct,
            random_guess_performance=random_guess_performance,
            correct_answer=correct_answer,
            options=options,
            options_random_order=options_random_order,
            option_labels=option_labels,
            correct_answer_label=correct_answer_label,
            correct_answer_text=correct_answer_text,
            labels2options=labels2options
        )

        return instance
    
    @staticmethod
    def get_logs_header() -> list[str]:
        """Return the header for logging all benchmark item fields."""
        return [
            "item_id",
            "category",
            "sub_category",
            # "difficulty",
            # "question_short",
            # "question_natural",
            "question_rewritten",
            "source_dataset",
            "piece_id",
            # "distractors",
            "modality",
            "submodality",
            "filetype",
            "notation_type",
            "notation_complexity",
            "note",
            "content_file",
            # "add_nota",
            # "is_nota_correct",
            # "random_guess_performance",
            # "correct_answer",
            # "correct_answer_label",
            # "correct_answer_text",
            # "options",
            # "options_random_order",
            # "option_labels",
            # "labels2options",
            "ground_truth",
        ]
    
    def convert_to_logs(self) -> list[str]:
        """Convert the benchmark item to a list of strings for logging."""
        return [
            self.item_id,
            self.category,
            self.sub_category,
            # self.difficulty,
            # self.question_short,
            # self.question_natural,
            self.question_rewritten,
            self.source_dataset,
            self.piece_id,
            # json.dumps(self.distractors),
            self.modality,
            self.submodality,
            self.filetype,
            self.note,
            self.notation_complexity,
            self.notation_type,
            str(self.content_file),
            # str(self.add_nota),
            # str(self.is_nota_correct),
            # self.random_guess_performance,
            # self.correct_answer,
            # self.correct_answer_label,
            # self.correct_answer_text,
            # json.dumps(self.options),
            # json.dumps(self.options_random_order),
            # json.dumps(self.option_labels),
            # json.dumps(self.labels2options),
            self.ground_truth
        ]



def download_google_sheet_as_tsv(sheet_url: str, output_file: str) -> str:
    """
    Download a Google Sheet as TSV format.
    
    Args:
        sheet_url: URL of the Google Sheet (e.g., https://docs.google.com/spreadsheets/d/SHEET_ID/edit)
        output_file: Path to save the TSV file
    
    Returns:
        Path to the downloaded TSV file
    """
    import re
    
    # Extract sheet ID from URL
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheet_url)
    if not match:
        raise ValueError(f"Invalid Google Sheets URL: {sheet_url}")
    
    sheet_id = match.group(1)
    
    # Construct export URL for TSV format (gid=0 for first sheet)
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=tsv&gid=0"
    
    logging.info(f"Downloading Google Sheet from: {export_url}")
    
    response = requests.get(export_url)
    response.raise_for_status()
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Save TSV file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    logging.info(f"Google Sheet downloaded and saved to: {output_file}")
    return output_file

def is_list_empty_deep(lst):
    """Recursively check if a list (or nested lists) is empty."""
    if not isinstance(lst, list):
        return False  # Not a list, so it's not empty
    if len(lst) == 0:
        return True  # Empty list
    return all(is_list_empty_deep(item) for item in lst)


def append_to_google_sheet(config, row_data, header=None):
    """Append a single row to a Google Sheet"""
    # Quick checks: ensure gspread is available and required config fields exist
    if gspread is None:
        print("⚠ gspread not installed; Google Sheets logging disabled.")
        return

    required = ['sheet_id', 'sheet_name', 'credentials_location']
    missing = [k for k in required if not getattr(config, k, None)]
    if missing:
        print(f"⚠ Google Sheets logging skipped: missing config fields: {', '.join(missing)}")
        return

    # Check credentials file exists
    cred_path = config.credentials_location
    if not os.path.exists(cred_path):
        print(f"⚠ Google Sheets logging skipped: credentials file not found at {cred_path}")
        return

    # Check and crop cells exceeding 50,000 character limit
    MAX_CELL_CHARS = 50000
    cropped_row = []
    for cell_value in row_data:
        cell_str = str(cell_value)
        if len(cell_str) > MAX_CELL_CHARS:
            cropped_value = cell_str[:MAX_CELL_CHARS - 4] + "..."
            cropped_row.append(cropped_value)
        else:
            cropped_row.append(cell_value)

    try:
        from google.oauth2.service_account import Credentials

        # Authenticate
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(cred_path, scopes=scope)
        client = gspread.authorize(creds)

        # Open sheet and append row
        sheet = client.open_by_key(config.sheet_id).worksheet(config.sheet_name)

        # if the sheet is empty, add the header first
        if header:
            existing_values = sheet.get_all_values()
            if len(existing_values) == 0 or (len(existing_values) == 1 and len(existing_values[0]) == 0):
                sheet.append_row(header, table_range="A1")
        
        sheet.append_row(cropped_row, table_range="A1")
        print("✓ Logged to Google Sheet")
    except Exception as e:
        # Don't raise — just report and continue
        print(f"⚠ Failed to log to Google Sheet: {e}")

def set_logdir(args):
    logargs = dict(vars(args).items())
    
    irrelevant_args = ["logdir"]
    for key in irrelevant_args:
        del logargs[key]

    args.datetime_string = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    args.args_string = ",".join(("{}={}".format(re.sub("(.)[^_]*_?", r"\1", key),
                                            re.sub("^.*/", "", value) if type(value) == str else value)
                                for key, value in sorted(logargs.items())))
    logname = "{}-{}-{}".format(
        args.datetime_string,
        args.expid,
        args.args_string
    )

    args.parent_logdir = args.logdir
    args.logdir = "{}/{}".format(args.logdir, logname)
    os.makedirs(args.logdir, exist_ok=True)
    return

def setup_logging(log_dir: str):
    """Set up logging to save stdout and stderr to separate files."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Create timestamp for log files
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Set up stdout logging
    stdout_handler = logging.FileHandler(log_path / f"stdout_{timestamp}.log")
    stdout_handler.setLevel(logging.INFO)
    stdout_formatter = logging.Formatter('%(message)s')
    stdout_handler.setFormatter(stdout_formatter)
    
    # Set up stderr logging
    stderr_handler = logging.FileHandler(log_path / f"stderr_{timestamp}.log")
    stderr_handler.setLevel(logging.ERROR)
    stderr_formatter = logging.Formatter('%(message)s')
    stderr_handler.setFormatter(stderr_formatter)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)
    
    return stdout_handler, stderr_handler

def encode_file_to_base64(file_path):
    with open(file_path, "rb") as file:
        return base64.b64encode(file.read()).decode('utf-8')

def ask_model(args, config, user_prompt, benchmark_item: BenchmarkItem):
    print(f"\n{'='*100}")
    start_time = datetime.datetime.now()

    model = config.model
    api_key = config.api_key
    url = config.url

    logging.info("=============================\n")
    logging.info(f"Model: {model}\n")

    original_user_prompt = user_prompt
    
    modality = benchmark_item.modality
    submodality = benchmark_item.submodality
    content_file = benchmark_item.content_file

    is_closed_ended = config.is_closed_ended
    
    plugins = None
    if modality == "visual" and submodality in ["png"]:
        base64_image = encode_file_to_base64(content_file)
        data_url = f"data:image/jpeg;base64,{base64_image}"

        # TODO: rewrite to include a specific system prompt for music notation reading
        messages = [
            {
                "role": "system",
                "content": config.system_prompt_for_png
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_url
                        }
                    }
                ]
            }
        ]
    elif modality == "visual" and submodality in ["pdf"]: 
        base64_pdf = encode_file_to_base64(content_file)
        data_url = f"data:application/pdf;base64,{base64_pdf}"
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt
                    },
                    {
                        "type": "file",
                        "file": {
                            "filename": "document.pdf", # TODO
                            "file_data": data_url
                        }
                    },
                ]
            }
        ]
        plugins = [
            {
                "id": "file-parser",
                "pdf": {
                    "engine": "native"  # defaults to "mistral-ocr". See https://openrouter.ai/docs/guides/overview/multimodal/pdfs
                    #"engine": "mistral-ocr"
                    #"engine": "pdf-text"
                }
            }
        ]
    elif modality == "audio":
        base64_audio = encode_file_to_base64(content_file)
        messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": user_prompt
                },
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": base64_audio,
                        "format": "wav" # TODO hard-coded format
                    }
                }
            ]
        }
        ]
    elif modality == "symbolic":
        file_content = content_file.read_text(encoding="utf-8", errors="replace") # TODO error handling

        user_prompt = user_prompt.replace("<FILE-PLACEHOLDER>", file_content) # TODO hardcoded placeholder
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt
                    }
                ]
            }
        ]
    else:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt
                    }
                ]
            }
        ] 

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": messages,

        # For now, we do not enforce deterministic output, as:
        # (1) for some models, even setting all those parameters does not guarantee deterministic output
        # (2) models are in reality used with some randomness, so better to see how they perform in that setting
        #"temperature": config.temperature,
        #"top_k": config.top_k,
        #"top_p": config.top_p,
        #"seed": config.seed,
        "provider": { 
            "require_parameters": True,
             "zdr": True, # Zero Data Retention: a provider will not store your data for any period of time.
             "data_collection": "deny", # Control whether to use providers that may store data.
            }
    }

    if plugins is not None:
        payload["plugins"] = plugins

    ######################## Logging ##############################################################
    # Sanitize payload to replace base64 media with file paths
    sanitized_payload = json.loads(json.dumps(payload))
    if modality == "visual" and submodality in ["png"]:
        # sanitized_payload['messages'][0]['content'][1]['image_url']['url'] = f"file://{content_file}"
        sanitized_payload['messages'][1]['content'][1]['image_url']['url'] = f"file://{content_file}"
   
    elif modality == "audio":
        sanitized_payload['messages'][0]['content'][1]['input_audio']['data'] = f"file://{content_file}"
    elif modality == "visual" and submodality in ["pdf"]:
        sanitized_payload['messages'][0]['content'][1]['file']['file_data'] = f"file://{content_file}"
    elif modality == "symbolic":
        original_user_prompt = original_user_prompt.replace("<FILE-PLACEHOLDER>", f"file://{content_file}")
        sanitized_payload['messages'][0]['content'][0]['text'] = original_user_prompt

    logging.info(f"User prompt: {original_user_prompt}\n")
    print(f"User prompt: {original_user_prompt}")
    logging.info(f"Model: {model}\n")
    print(f"Model: {model}")
    logging.info(f"Ground truth: {benchmark_item.ground_truth}\n")
    print(f"Ground truth: {benchmark_item.ground_truth}\n")
    if is_closed_ended:
        logging.info(f"Correct answer: {benchmark_item.correct_answer_text}\n")
        print(f"Correct answer: {benchmark_item.correct_answer_text}")
    logging.info(f"Modality: {modality}\n")
    print(f"Modality: {modality}")
    logging.info(f"File: {content_file}\n")
    print(f"File: {content_file}")
    logging.info(f"Sending request to {url}\n")
    ############################################################################################

    # TO avoid "$MODEL is temporarily rate-limited upstream. Please retry shortly, or add your own key to accumulate
    # your rate limits: https://openrouter.ai/settings/integrations" error.

    response_json = {}
    retries = 0
    max_retries = 5

    while 'choices' not in response_json:

        # Send the POST request to OpenRouter API
        response = requests.post(url, headers=headers, json=payload)
        response_json = response.json()
        logging.info(f"Full response JSON: {json.dumps(response_json, indent=2)}\n\n")

        if 'choices' in response_json:
            break
        else:
            logging.error(f"Error in response: {json.dumps(response_json, indent=2)}\n")
            print(f"Error in response: {json.dumps(response_json, indent=2)}\n")
            retries += 1
            if retries >= max_retries:
                logging.error("ERROR Max retries reached. Exiting.\n")
                print("ERROR Max retries reached. Exiting.\n")
                break
                # return "ERROR: Max retries reached"
            
            logging.info("Waiting for 60 seconds before retrying...\n")
            print("Waiting for 60 seconds before retrying...\n")
            time.sleep(60)  # wait before retrying
            logging.info("Retrying...\n")
            print("Retrying...\n")
    
    # check if the response does not contain choices, and if not, print the full response
    # if 'choices' not in response_json:
    #     logging.error(f"Error in response: {json.dumps(response_json, indent=2)}\n")
    #     print(f"Error in response: {json.dumps(response_json, indent=2)}\n")

    
    response_text = response_json['choices'][0]['message']['content']

    if is_closed_ended:
        answer_label = extract_final_answer(response_text)
        answer = benchmark_item.labels2options.get(answer_label, "INVALID LABEL")
    else:
        answer_label = ''
        if args.extract_final_answer_open_ended:
            answer = extract_final_answer_open_ended(response_text)
        else:
            answer = ''


    ########################### Logging ##############################################################
    logging.info(f"=============================\n")
    print(f"=============================\n")
    logging.info(f"Response text: {response_text}\n")
    print(f"Response text: {response_text}")
    if is_closed_ended:
        logging.info(f"Extracted final answer: {answer_label}) {answer}\n")
        print(f"Extracted final answer: {answer_label}) {answer}")
    cost = response_json.get('usage', {}).get('cost', '') if 'usage' in response_json else ''
    logging.info(f"Cost: {cost}\n")
    print(f"Cost: {cost}")
    print()
    logging.info("")
    ############################################################################################

    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    tsv_file = os.path.join(args.parent_logdir, "requests.tsv")
    file_exists = os.path.isfile(tsv_file)
    
    # Prepare benchmark item logs
    benchmark_item_logs = benchmark_item.convert_to_logs()
    
    # Prepare config info
    config_info = {
        "url": config.url,
        "seed": config.seed,
        "dry_run": config.dry_run
    }
    
    row_data = benchmark_item_logs + [
        start_time.isoformat(),
        original_user_prompt,
        json.dumps(sanitized_payload),
        model,
        json.dumps(response_json),
        response_text,
        json.dumps(config_info),
        answer_label,
        answer,
        cost,
        duration,
        str(is_closed_ended)
    ]
    
    # Prepare headers combining benchmark item headers with additional headers
    header_row = BenchmarkItem.get_logs_header() + [
        'datetime',
        'full_prompt',
        'parameters',
        'model_used',
        'full_json_response',
        'extracted_response',
        'config_info',
        'extracted_answer_label',
        'extracted_answer',
        'cost',
        'duration_seconds',
        "closed_ended",
        "correct?",
        "manually extracted answer",
        "pozn",
        "validity"
    ]
    
    with open(tsv_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='\t')
        if not file_exists:
            writer.writerow(header_row)
        writer.writerow(row_data)
    
    # Append to Google Sheet
    append_to_google_sheet(config, row_data, header=header_row)

    print()
    return response_text

def sort_randomly(options: list[str]) -> list[str]:
    options_random_order = options.copy() # to not sort in place
    options_random_order.sort()  # to have deterministic order before shuffling
    random.shuffle(options_random_order)
    return options_random_order

def extract_final_answer(response_text):
    """Closed-ended toy matching, TODO: replace with https://github.com/MMMU-Benchmark/MMMU/blob/main/mmmu/utils/eval_utils.py"""
    match = re.search(r'nswer:\s*([A-J])', response_text)
    if match:
        return match.group(1)
    else:
        return "NOT FOUND"


def extract_final_answer_open_ended(model_output: str) -> str:
    """
    Extracts the final answer from model output, supporting:
    - Variations: "Final Answer:", "Answer:", "final answer:"
    - Markdown: "**Final Answer:**" 
    - Layout: Newline(s) between the label and the actual answer.
    """
    if not model_output or not isinstance(model_output, str):
        return "PARSING FAILED"

    # 1. Regex Explanation:
    # (?i)             -> Case-insensitive
    # (?:\*\*|__)      -> Optional markdown bold start
    # (?:final\s+)?    -> Optional "final "
    # answer\s*        -> "answer" followed by optional space
    # (?:\*\*|__)      -> Optional markdown bold end
    # \s*:\s*          -> The colon, surrounded by any amount of whitespace (including newlines)
    # (.*)             -> The final answer we want to capture
    pattern = r"(?i)(?:\*\*|__)?(?:final\s+)?answer(?:\*\*|__)?\s*:\s*(.*)"
    
    # Use re.DOTALL so that (.*) can capture across newlines if necessary, 
    # though usually we want the remainder of the text.
    match = re.search(pattern, model_output, re.DOTALL)
    
    if match:
        answer = match.group(1).strip()
        # If the answer contains further text/distractions, we take the first paragraph
        # or first significant line captured.
        if answer:
            # Cleanup: Remove trailing bold tags if the model closed them after the answer
            answer = re.sub(r"(\*\*|__)$", "", answer).strip()
            return answer

    # 2. Fallback: Take the last non-empty line if "Answer:" text wasn't found
    lines = [line.strip() for line in model_output.strip().split('\n') if line.strip()]
    if lines:
        last_line = lines[-1]
        # Remove bolding markers from the fallback line
        clean_line = re.sub(r"\*\*|__", "", last_line).strip()
        return clean_line

    return "PARSING FAILED"

def main(args):
    stdout_handler, stderr_handler = setup_logging(args.logdir)
    config = Config()

    if args.dry_run:
        config.dry_run = True

    if args.model:
        config.model = args.model
    
    if args.log_sheet_id:
        config.sheet_id = args.log_sheet_id

    if args.log_sheet_list_name:
        config.sheet_name = args.log_sheet_list_name
    
    if args.benchmark_file_tsv:
        config.questions_file = args.benchmark_file_tsv

    random.seed(config.seed)

    # Load questions from TSV file
    questions_file = config.questions_file
    if not os.path.isabs(questions_file):
        questions_file = os.path.join(os.path.dirname(__file__), questions_file)


    # Download Google Sheet if provided and save to Config.questions_file
    if args.benchmark_file_google_sheet:
        output_file = os.path.join(os.path.dirname(__file__), "tmp.tsv")
        download_google_sheet_as_tsv(args.benchmark_file_google_sheet, output_file)
        os.replace(output_file, questions_file)
        print(f"✓ Benchmark downloaded from Google Sheets to TSV and is ready at: {questions_file}")
    
    with open(questions_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        questions_data = list(reader)

    processed_items = 0
    
    # Iterate over each question
    for question_row in questions_data:
        # Create BenchmarkItem from the row
        benchmark_item = BenchmarkItem.from_dict(question_row, config)

        prompt = config.prompt_closed if config.is_closed_ended else config.prompt_open

        
        prompt = prompt.replace( # TODO
                "<FORMAT>", config.musical_piece_format_info[benchmark_item.modality][benchmark_item.submodality]
            ).replace(
                "<QUESTION>", benchmark_item.question_rewritten
            ).replace(
                "<OPTIONS_TEXT>", "\n".join(
                    [f"{label}{config.label_option_divider} {option}" 
                        for label, option in 
                        zip(benchmark_item.option_labels, benchmark_item.options_random_order)
                     ]) 
            ).replace(
                "<OPTION_LABELS>", ', '.join(benchmark_item.option_labels)
            ).replace(
                # files in symbolic modality are text files, thus placed into the prompt directly
                "<POTENTIAL_TEXTFILE_PLACEHOLDER>", ("The piece: <FILE-PLACEHOLDER>" if benchmark_item.modality == "symbolic" else "")  
            )
        
        logging.info(f"Processing item ID: {benchmark_item.item_id}")

        if not config.dry_run:
            ask_model(args, config, prompt, benchmark_item)
            
            # sleep for 15 seconds between requests to avoid rate limiting
            # print("Sleeping for 60 seconds to avoid rate limiting...")
            # time.sleep(60)

        else:
            print("===================================================")
            print(f"Prompt:\n{prompt}\n")


        processed_items += 1
        if 0 < args.max_items <= processed_items:
            print(f"Reached maximum number of items to process: {args.max_items}. Stopping.")
            break


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--logdir", default="logs", type=str, help="Logdir name.")
        parser.add_argument("--expid", default="x", type=str,
                            help="Experiment ID to be included in the results file.")
        parser.add_argument("--benchmark_file_google_sheet", default=None, type=str,
                            help="Google Sheets URL to download benchmark questions from. If provided, the sheet will be downloaded as TSV before running.")
        # parser.add_argument("--benchmark_file_google_sheet", default="https://docs.google.com/spreadsheets/d/1q-f-gb2pw2-U2DDsmohoszLFaLzVGXJ5PR2w_zdu2eU/edit?usp=sharing", type=str,
                            # help="Google Sheets URL to download benchmark questions from. If provided, the sheet will be downloaded as TSV before running.")
        parser.add_argument("--max_items", default=-1, type=int, help="Maximum number of benchmark items to process. -1 for all.")
        parser.add_argument("--dry_run", action="store_true", help="If set, do not send requests to the model API.")
        parser.add_argument("--model", default="google/gemini-3-flash-preview", type=str, help="Model name to use for the benchmark.")
        parser.add_argument("--log_sheet_id", default=None, type=str, help="Google Sheet ID to log results to. Requires Config.credentials_location to be set.")
        parser.add_argument("--log_sheet_list_name", default=None, type=str, help="Google Sheet list name to log results to. Requires Config.credentials_location to be set.")
        parser.add_argument("--benchmark_file_tsv", default=None, type=str,
                            help="TSV file with benchmark questions.")
        
        parser.add_argument("--extract_final_answer_open_ended", action="store_true", help="Whether to extract the final answer from the model response using regex.")
        
        # for gemini:
        # google/gemini-3-pro-preview
        # "12Oaw4k-ElD4OvdHxWbP9KFV6CgQH4M5aRz-GuHTG10w" 
        #
        # for gpt:
        # openai/gpt-4o
        # OR
        # openai/gpt-4o-mini
        # "1aqK3VESRN30ujcEV82pacj4nAY86Cn-gGBuKlJGAOgg"
        #
        # for claude:
        # anthropic/claude-sonnet-4.5
        # 11ro5n2DW9AsktLfQf2gz1gN2VvWw2uOYcZytgaTzQ44

        args = parser.parse_args([] if "__file__" not in globals() else None)

        
        set_logdir(args)
        main(args)

    except Exception as e:
        print(f"❌ Fatal error: {e}", file=sys.stderr)
        raise e
        #sys.exit(1)
