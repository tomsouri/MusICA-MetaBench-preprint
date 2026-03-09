import re
def regex_final_answer_extractor(response_text: str) -> str:
    """
    Dummy extraction function specified in the requirements.
    Extracts purely the single letter labeled as the final answer.
    """
    if not response_text:
        return ""
        
    # Pattern looks for "Final Answer: " optionally followed by spaces, and captures 1 alphabetical char
    match = re.search(r'Final Answer:\s*([A-Za-z])', response_text, re.IGNORECASE)
    
    if match:
        return match.group(1).upper()
        
    return "UNKNOWN"