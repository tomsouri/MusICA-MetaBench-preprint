"""
To run:
.venv/bin/python3 run_benchmark.py --config eval-config.yaml



Prompt used to generate the script, which tells precisely what the script does.

Generate the python script with functionality as described below, using the code snippets provided. When the snippets
need refactoring, do it to achieve better structure.
Also generate a sample config yaml file.

This script gets a config file and runs LLM(s) on the benchmark questions.

It should:
- load the config yaml file, specified by a cmdline arg:
    - list of models to be run
        - model = "openai/gpt-4.1-nano"
    - API endpoint to be used
        - url: str = "https://openrouter.ai/api/v1/chat/completions"
    - env var name with API KEY
    - system prompt
    - user prompt template
    - path to extraction methods file
    - name of the extraction method to be used  
    - dry_run: bool = False # if True, do not send any requests
    - user_prompt_template = "You are a specialist in the analysis and interpretation of musical materials. You are provided with a musical work as <FORMAT>. Analyze the material carefully. Then, given a question and a set of possible answers, choose the most appropriate option.
Question:
<QUESTION>
Options:
<OPTIONS_TEXT>

<POTENTIAL_TEXTFILE_PLACEHOLDER>

After any potential reasoning, end with your final answer in this format:
Final Answer: <answer>
where <answer> is the single correct letter choice <OPTION_LABELS>. Only include the letter."

    - musical_piece_format_info = {
        "audio": {"wav": "an audio recording (WAV format)"},
        "visual": {"png": "a rendered score (PNG format)",
                   "pdf": "a rendered score (PDF format)"},
        "symbolic": {"musicxml": "a musical score (MusicXML format)",
                     "midi": "a musical score (MIDI format represented as CSV)", 
                     "abc": "a musical score (ABC notation format)"
                     }
    }

    # for automatic logging to Google Sheets
    - log_to_google_sheet = True
    - sheet_id = "1cYg3U_MPDx1fzLNnWnR9Xg2epi2eaUA_4JF5Bo8Xbro"
    - sheet_name = "List 1"
    - credentials_location = "logs/protobenchmark-logging-aa9418338494.json"
- set the logdir, using the set_logdir method
- load the benchmark file (tsv), as specified in the config: config['cmdline_args']['output']
    - the relevant columns from the benchmark file are: 
        - item_id (unique)
        - question
        - labeled_final_options (e.g., ["(A) G4", "(B) F4", "(C) none of the other options is correct", "(D) B4", "(E) E4"])
        - label_of_final_correct_option: the label of the final correct option
        - path_to_question_context_file
        - submodality
        - modality
- print the stats of the file and of the other setup (number of items, questions to be asked)
- for every (model, benchmark-item) pair:
    - prepare the user prompt, using the template from config, the question and the labeled final options, prepare the
      context file (path_to_question_context_file)
    - run the request to the LLM API, using the code snippet from below (please note that the snippet needs to be
      modified, as it uses benchmarkItem and config dataclass that do not exist), and return the following:
        - price, time_taken, full_json_response, response (extracted from the json), full_prompt
    - run the extraction of the selected option from the model response, using the method specified in the config
      (provide a dummy implementation for this for now)
    - check whether the extracted answer is a correct answer
    - prepare a single-row log:
      full-original-row (whole benchmark row), plus: datetime  full_prompt parameters  model   full_json_response  extracted_response (only the
      response)  config_info label_of_answer answer  price   time_taken  correct?
    - log it to a tsv file for this run of the benchmark
    - if logging to google sheet is set up in config, log it using the append row to google sheet method
    - print a concise log to cmdline, in order for me to know what is happening
"""


import argparse
import csv
import datetime
import json
import os
import sys
import time
import uuid
from typing import Dict, Tuple

from utils import load_methods_module, append_to_google_sheet, encode_file_to_base64
from eval import evaluate_results

import requests
import yaml

# =========================================================================
# Utilities and Helper Functions
# =========================================================================

API_KEY = None

PROJECT_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "benchmark-run")

def deterministic_uuid(data):
    """Generates a deterministic UUID based on the input data dictionary."""
    normalized = json.dumps(data, sort_keys=True)
    return uuid.uuid5(PROJECT_NAMESPACE, normalized)

def random_uuid():
    """Generates a random UUID."""
    return uuid.uuid4()


def set_logdir(config: dict) -> str:
    """Sets up a unique logging directory based on the run."""
    dt_string = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base_log_dir = config.get("logdir", "logs")
    
    unique_logdir = os.path.join(base_log_dir, f"run_{dt_string}_{config.get('benchmark_run_uuid', '')}")
    os.makedirs(unique_logdir, exist_ok=True)
    return unique_logdir



# =========================================================================
# Core LLM Call & Payload Builder
# =========================================================================

def prepare_llm_payload(model: str, user_prompt: str, system_prompt: str, content_file: str, modality: str, submodality: str, no_content_file: bool = False) -> Tuple[Dict, str]:
    """
    Generates the messages payload based on the modality and files.

    If no_content_file is True, it will prepare a payload but will exclude the content (musical) file. To be used as
    "text-onlyLLM" baseline.    
    """
    messages = []
    plugins = None
    
    # We remove the placeholder from the textual prompt since we'll append data separately
    user_prompt_clean = user_prompt.replace("<POTENTIAL_TEXTFILE_PLACEHOLDER>", "").strip()

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    
    if no_content_file:
        # Ignore the content file and just send the user prompt (question and options) as text.
        # To be used as "text-only LLM" baseline, to see how well the model can do without seeing the actual musical
        # material. (How well it can guess the correct answer from distractor set.)
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": user_prompt_clean}]
        })
    else:
        if modality == "visual" and submodality in ["visual.png"]:
            base64_image = encode_file_to_base64(content_file)
            data_url = f"data:image/jpeg;base64,{base64_image}"
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt_clean},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            })
            
        elif modality == "visual" and submodality in ["visual.pdf"]: 
            base64_pdf = encode_file_to_base64(content_file)
            data_url = f"data:application/pdf;base64,{base64_pdf}"
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt_clean},
                    {"type": "file", "file": {"filename": "document.pdf", "file_data": data_url}},
                ]
            })
            plugins = [{"id": "file-parser", "pdf": {"engine": "native"}}]
            
        elif modality == "audio":
            base64_audio = encode_file_to_base64(content_file)
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt_clean},
                    {"type": "input_audio", "input_audio": {"data": base64_audio, "format": "wav"}}
                ]
            })
            
        elif modality == "symbolic":
            try:
                with open(content_file, 'r', encoding="utf-8", errors="replace") as f:
                    file_content = f.read()
            except FileNotFoundError:
                file_content = "[FILE NOT FOUND]"
                
            # Add the explicit data block separately from the instruction text block
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt_clean},
                    {"type": "text", "text": f"--- Attached Symbolic Data ---\n{file_content}"}
                ]
            })
            
        else:
            messages.append({
                "role": "user",
                "content": [{"type": "text", "text": user_prompt_clean}]
            }) 

    payload = {
        "model": model,
        "messages": messages,
        "provider": { 
             "require_parameters": True,
             "zdr": True,
             "data_collection": "deny",
        }
    }
    if plugins:
        payload["plugins"] = plugins
        
    return payload, user_prompt_clean

def ask_model(config: dict, payload: dict, original_user_prompt: str, dry_run: bool = False) -> Tuple[float, float, dict, str]:
    """Runs the API request and returns (price, time_taken, full_json_response, response_text)."""
    start_time = datetime.datetime.now()
    url = config['url']
    headers = {
        "Authorization": f"Bearer {os.environ.get(config['env_api_key_name'], '')}",
        "Content-Type": "application/json"
    }

    if dry_run:
        time_taken = (datetime.datetime.now() - start_time).total_seconds()
        dummy_json = {"choices": [{"message": {"content": "Dry run response. Final Answer: A"}}], "usage": {"cost": 0.0}}
        return 0.0, time_taken, dummy_json, dummy_json['choices'][0]['message']['content']

    retries = 0
    max_retries = 5
    response_json = {}
    
    while 'choices' not in response_json:
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            response_json = response.json()
        except Exception as e:
            print(f"Error calling API: {e}")
            
        if 'choices' in response_json:
            break
            
        retries += 1
        if retries >= max_retries:
            print("ERROR Max retries reached. Returning empty.")
            response_json = {"error": "Max retries reached."}
            break
            
        print("Waiting for 60 seconds before retrying...")
        time.sleep(60)
        
    end_time = datetime.datetime.now()
    time_taken = (end_time - start_time).total_seconds()
    
    response_text = response_json.get('choices', [{}])[0].get('message', {}).get('content', '')
    cost = float(response_json.get('usage', {}).get('cost', 0.0))
    
    return cost, time_taken, response_json, response_text

def sanitize_payload_for_logging(payload: dict) -> dict:
    """Removes base64 data streams from logs."""
    sanitized = json.loads(json.dumps(payload))
    for msg in sanitized.get('messages', []):
        for part in msg.get('content', []):
            if msg.get("role") == "user":
                if part.get('type') == 'image_url':
                    part['image_url']['url'] = '[BASE64_IMAGE_STRIPPED]'
                elif part.get('type') == 'input_audio':
                    part['input_audio']['data'] = '[BASE64_AUDIO_STRIPPED]'
                elif part.get('type') == 'file':
                    part['file']['file_data'] = '[BASE64_FILE_STRIPPED]'
                elif part.get('type') == 'text' and part.get('text').startswith("--- Attached Symbolic Data ---"):
                    part['text'] = '[SYMBOLIC_FILE_STRIPPED]'
    return sanitized

# =========================================================================
# Main Benchmark Loop
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description="Run LLM benchmark.")
    parser.add_argument("--config", required=True, help="Path to config yaml file")
    cmdline_args = parser.parse_args()

    # Load Config
    with open(cmdline_args.config, 'r') as f:
        config = yaml.safe_load(f)

    benchmark_run_uuid = str(random_uuid())

    config["benchmark_run_uuid"] = benchmark_run_uuid

    # Allow cmdline override of output parameter
    target_benchmark_file = config.get('benchmark_file')
    if not target_benchmark_file:
         raise ValueError("Benchmark file must be specified in config.")
         
    # Load extraction method
    methods_module = load_methods_module(config['path_to_extraction_file'])
    extraction_func = getattr(methods_module, config['extraction_method'])

    # Prepare logdir
    logdir = set_logdir(config)
    log_tsv_path = os.path.join(logdir, "benchmark_logs.tsv")
    results_tsv_path = os.path.join(logdir, "results.tsv")
    
    # Check API key presence 
    api_key_name = config.get("env_api_key_name", "OPENROUTER_API_KEY")
    if not os.environ.get(api_key_name) and not config.get('dry_run'):
        print(f"Warning: Environment variable {api_key_name} is missing!")

    # Read Benchmark TSV
    items = []
    with open(target_benchmark_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        headers = reader.fieldnames
        for row in reader:
            items.append(row)


    # =====================================================================
    # Filter the benchmark items
    # =====================================================================
    print(f"\n--- Data Loading & Filtering ---")
    print(f"Loaded initial benchmark with {len(items)} items.")

    filters = config.get("filters", {})
    if filters:
        for column, allowed_values in filters.items():
            if allowed_values:  # If list is empty, ignore this filter
                temp_items = [i for i in items if i.get(column) in allowed_values]
                print(f"Filter applied: Column '{column}' {allowed_values} -> Kept {len(temp_items)}")
                items = temp_items

    if len(items) == 0:
        print("No items match the required filters. Exiting.")
        sys.exit(0)


    print(f"Models to evaluate: {len(config['models'])}")
    total_runs = len(items) * len(config['models'])
    print(f"Total question/model loops to perform: {total_runs}\n")



    # Prepare the log TSV headers
    log_headers = headers + [
        "benchmark_run_uuid", "datetime", "full_prompt", "parameters" , "model", "full_json_response",
        "extracted_response", "config_info", "label_of_answer", 
        "price", "time_taken", "is_correct"
    ]

    with open(log_tsv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=log_headers, delimiter='\t')
        writer.writeheader()

    # Track all log rows to pass to the evaluator later
    all_executed_logs = []

    run_count = 0
    for model in config['models']:
        for item in items:
            run_count += 1
            print(f"\n[{run_count}/{total_runs}] Running Model: {model} | Item ID: {item.get('item_id')}")

            # Prepare User Prompt

            options = json.loads(item['labeled_final_options'])
            labels = json.loads(item['all_choices'])
            options_text = "\n".join(options)

            fmt_info = config['musical_piece_format_info']
            modality = item.get('modality')
            submodality = item.get('submodality')
            format_desc = fmt_info.get(modality, {}).get(submodality, "a musical excerpt")

            # print(f"Modality: {modality:>10} | Submodality: {submodality:>19} | Question: {item['shortened (opt)']}")
            print(f"Modality: {modality:>10} | Submodality: {submodality:>19} | Question: {item['question']}")
            print(f"Options:" + ", ".join(options))

            prompt = config['user_prompt_template']
            prompt = prompt.replace("<FORMAT>", format_desc)
            prompt = prompt.replace("<QUESTION>", item['question'])
            prompt = prompt.replace("<OPTIONS_TEXT>", options_text)
            prompt = prompt.replace("<OPTION_LABELS>", ', '.join(labels))

            # Build Payload
            content_file = item['path_to_question_context_file']
            # TODO: if empty/noise file should be used, replace with the corresponding path from item

            text_only_baseline = config.get('text_only_baseline', False)

            payload, final_prompt = prepare_llm_payload(
                model=model, 
                user_prompt=prompt, 
                system_prompt=config['system_prompt'], 
                content_file=content_file, 
                modality=modality, 
                submodality=submodality,
                no_content_file=text_only_baseline
            )

            # Execute Request
            cost, time_taken, full_json, resp_text = ask_model(config, payload, final_prompt, config['dry_run'])

            # Extract Response and Check Correctness
            # extracted_answer = extraction_func(resp_text)
            extracted_answer = extraction_func(response=resp_text, all_choices=json.loads(item['all_choices']), index2ans=json.loads(item['index2ans']))
            correct_label = item.get('label_of_final_correct_option', '').strip()
            is_correct = (extracted_answer == correct_label) if extracted_answer else "EXTRACTION FAILED"

            # Logging Logic
            log_row = item.copy()
            model_str = "text-only-" + model if text_only_baseline else model
            log_row.update({
                "benchmark_run_uuid": benchmark_run_uuid,
                "datetime": datetime.datetime.now().isoformat(),
                "full_prompt": final_prompt,
                "parameters": json.dumps(sanitize_payload_for_logging(payload=payload)),
                "model": model_str,
                "full_json_response": json.dumps(full_json),
                "extracted_response": resp_text,
                "config_info": json.dumps({"text-only-baseline": text_only_baseline, "dry_run": config['dry_run'], "url": config['url'], "seed": config['seed']}),                
                "label_of_answer": extracted_answer,
                "price": cost,
                "time_taken": time_taken,
                "is_correct": is_correct
            })

            # Save line into memory
            all_executed_logs.append(log_row)


            # 1. Log to local TSV
            with open(log_tsv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=log_headers, delimiter='\t')
                writer.writerow(log_row)

            # 2. Log to Google Sheets
            if config.get('log_to_google_sheet'):
                row_list = [log_row.get(h, "") for h in log_headers]
                append_to_google_sheet(config, row_list, header=log_headers, force_header_print=config.get("force_header_print", False))
                # Enforce the header print only for the first item
                config["force_header_print"] = False

            # 3. Print concise log
            print(f"  -> Extracted: {extracted_answer} | Expected: {correct_label} | Correct: {is_correct} | Time: {time_taken:.2f}s | Cost: ${cost:.6f}")
    
    # =====================================================================
    # Trigger final evaluation logic
    # =====================================================================
    evaluation_criteria = config.get("evaluation_criteria", [])
    output_tsvs = [results_tsv_path]
    results_path = config.get("evaluation_output_file", None)
    if results_path:
        output_tsvs += [results_path]

    evaluate_results(all_executed_logs, evaluation_criteria, output_tsvs=output_tsvs)


if __name__ == "__main__":
    main()