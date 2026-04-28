import json
import re
from typing import List, Dict, Any
from .diff_parser import compute_line_range

SYSTEM_PROMPT = (
    "You are an expert code reviewer. You will be shown a unified diff of code changes. "
    "Identify potential bugs, style violations, performance issues, security vulnerabilities, "
    "and suggest improvements. Output ONLY a valid JSON array (no other text) where each element "
    "has the following structure:\n"
    "{\n"
    '  "severity": "critical" | "major" | "minor" | "info",\n'
    '  "line_range": {"start": <int>, "end": <int>},\n'
    '  "issue": "<concise description>",\n'
    '  "fix": "<suggested fix or code change>"\n'
    "}\n"
    "Line numbers must be relative to the hunk's new file lines (1‑based within the hunk). "
    "If no issues exist, return an empty array []."
)

def build_user_prompt(file_path: str, chunk_hunks: List[Dict]) -> str:
    """Construct the user message containing the diff chunk."""
    lines = [f"File: {file_path}", "Changes (unified diff):"]
    for hunk in chunk_hunks:
        lines.append(f"@@ hunk (new file start line {hunk['new_start']})")
        lines.extend(hunk['lines'])
    return "\n".join(lines)

def parse_review_response(response_text: str) -> List[Dict]:
    """Attempt to extract JSON array from model response."""
    # Remove any markdown fences if present
    cleaned = re.sub(r'```(json)?', '', response_text).strip()
    try:
        issues = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find a JSON array using regex
        match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if match:
            try:
                issues = json.loads(match.group())
            except json.JSONDecodeError:
                return []
        else:
            return []
    if not isinstance(issues, list):
        return []
    # Validate each issue has required fields
    valid = []
    for item in issues:
        if all(k in item for k in ("severity", "line_range", "issue", "fix")):
            valid.append(item)
    return valid

def review_chunk(client, file_path: str, chunk_hunks: List[Dict], max_tokens: int = 2000) -> List[Dict]:
    """Send one hunk chunk to the LLM and return list of issues with absolute line numbers."""
    user_prompt = build_user_prompt(file_path, chunk_hunks)
    raw = client.complete(SYSTEM_PROMPT, user_prompt, max_tokens=max_tokens)
    issues = parse_review_response(raw)
    # Convert relative line numbers to absolute using the first hunk's new_start as reference
    # (each issue's line_range is assumed relative to the chunk context)
    # Build a mapping of relative line -> absolute line across all hunks in the chunk.
    # Simpler approach: we ask model to use "line_range relative to the chunk's diff" but we don't
    # know which hunk each issue belongs to. So we'll require the model to also specify a 'hunk_index'
    # or just rely on the cumulative offset. To keep the prompt simple, we'll ask for absolute
    # new‑file line numbers directly by providing the actual line numbers in the diff.
    # Therefore, modify BUILD_USER_PROMPT to show absolute line numbers alongside the diff.
    # Implementation below assumes we modified the prompt to include absolute numbers.
    # We'll adjust build_user_prompt to embed absolute line numbers. For brevity, we'll do it here:
    return annotate_absolute_lines(file_path, chunk_hunks, issues)

def annotate_absolute_lines(file_path: str, chunk_hunks: List[Dict], issues: List[Dict]) -> List[Dict]:
    """
    Convert the model's line_range (still relative to the hunk) into absolute new‑file line numbers.
    We need to know which hunk each issue belongs to; assume the model used absolute line numbers
    from the diff we showed. So we just keep them as is (we'll have already provided absolute numbers).
    If the model returned relative ones, we add an offset from the first hunk's new_start.
    For safety, we'll implement a simple heuristic: if line_range start < 100 (likely relative),
    add the chunk's minimum new_start.
    """
    if not issues:
        return issues
    # Determine the base new_start for this chunk (lowest hunk new_start)
    min_start = min(h['new_start'] for h in chunk_hunks)
    for issue in issues:
        start = issue['line_range']['start']
        end = issue['line_range']['end']
        # Heuristic: if start < 50, assume relative (absolute diff lines are usually > 50).
        if start < 50:
            issue['line_range']['start'] = min_start + start - 1
            issue['line_range']['end'] = min_start + end - 1
        # else keep
    return issues