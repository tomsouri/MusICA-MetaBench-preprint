# Copyright (C) 2026  Tomáš Sourada, Katia Vendrame, Jan Hajič, jr.
#
# This file is part of the MusICA MetaBench source code, licensed under
# the GNU General Public License v3.0 or later (SPDX: GPL-3.0-or-later).
# See the LICENSE-SOURCE-CODE file in the repository root for the full
# license text, or <https://www.gnu.org/licenses/>.

import re
"""
Every answer extraction method should accept the same input and output format:
Input:
- response_text: the raw text response from the model (string)
- all_choices: a list of all the answer choices (e.g., ["A", "
B", "C", "D"])
- index2ans: a dictionary mapping from choice index to the actual answer content (e.g., {"A": "Paris", "B": "London",
"C": "Berlin", "D": "Rome"})
Output:
- The extracted answer choice (e.g., "A", "B", "C", or "D"). 
If the answer cannot be parsed, return "UNPARSABLE".
"""

def regex_final_answer_extractor(response_text: str, all_choices: list, index2ans: dict) -> str:
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
        
    return "UNPARSABLE"