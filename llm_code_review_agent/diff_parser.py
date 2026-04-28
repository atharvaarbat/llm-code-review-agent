# import re
from typing import List, Dict, Tuple, Optional
from unidiff import PatchSet

# We'll use unidiff for robust parsing, but you can replace with a custom parser.
# unidiff gives us hunks directly.

def parse_diff(diff_text: str) -> List[Dict]:
    """
    Parse a unified diff string and return a list of file‑level diff objects.
    Each object: {
        'path': str,
        'hunks': list of hunk dicts with 'header', 'lines', 'new_start'
    }
    """
    patch = PatchSet.from_string(diff_text)
    files = []
    for patched_file in patch:
        hunks = []
        for hunk in patched_file:
            # Extract lines as list of strings (including the +/- prefix)
            lines = [str(line) for line in hunk]
            hunks.append({
                'header': hunk.section_header or '',
                'lines': lines,
                # new_start is the starting line number in the new file (1‑based)
                'new_start': hunk.target_start if hunk.target_start else 1,
                # target_length is the number of lines in the new file hunk
                'target_length': hunk.target_length,
            })
        files.append({
            'path': patched_file.path,
            'hunks': hunks,
        })
    return files

def compute_line_range(hunk: Dict, issue_start_line_relative: int, issue_end_line_relative: int) -> Tuple[int, int]:
    """
    Convert hunk‑relative line numbers to absolute new‑file line numbers.
    `issue_start_line_relative` is 1‑based within the hunk’s new lines.
    """
    abs_start = hunk['new_start'] + issue_start_line_relative - 1
    abs_end = hunk['new_start'] + issue_end_line_relative - 1
    return abs_start, abs_end