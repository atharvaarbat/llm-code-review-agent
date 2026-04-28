import tiktoken
from typing import List, Dict

# Use cl100k_base as a generic tokenizer (works for GPT‑4/Claude roughly)
ENCODING = tiktoken.get_encoding("cl100k_base")

def estimate_token_count(text: str) -> int:
    return len(ENCODING.encode(text))

def chunk_hunks_per_file(
    file_diff: Dict,
    max_tokens: int = 3500,
    overhead_per_chunk: int = 200,      # reserved for system/user prompt prefix
    min_hunk_tokens: int = 100,
) -> List[List[Dict]]:
    """
    Given one file’s diff (dict with 'path' and 'hunks'),
    return a list of chunks, where each chunk is a list of hunks
    that fit within max_tokens after accounting for overhead.
    """
    hunks = file_diff['hunks']
    chunks = []
    current_chunk = []
    current_tokens = overhead_per_chunk  # start with prompt overhead

    for hunk in hunks:
        hunk_text = "\n".join(hunk['lines'])
        hunk_tokens = estimate_token_count(hunk_text)
        # If a single hunk exceeds max_tokens alone, split it line‑wise (simple fallback)
        if hunk_tokens > max_tokens - overhead_per_chunk:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = overhead_per_chunk
            # Slice hunk into sub‑chunks (each line added individually)
            sub_chunk = []
            sub_tokens = overhead_per_chunk
            for line in hunk['lines']:
                line_tokens = estimate_token_count(line)
                if sub_tokens + line_tokens > max_tokens - 50:
                    chunks.append(sub_chunk)
                    sub_chunk = []
                    sub_tokens = overhead_per_chunk
                sub_chunk.append({
                    'header': hunk['header'],
                    'lines': [line],
                    'new_start': hunk['new_start'],
                    'target_length': 1,  # not strictly accurate, but line‑wise
                })
                sub_tokens += line_tokens
            if sub_chunk:
                chunks.append(sub_chunk)
            continue

        if current_tokens + hunk_tokens <= max_tokens:
            current_chunk.append(hunk)
            current_tokens += hunk_tokens
        else:
            # Start a new chunk
            chunks.append(current_chunk)
            current_chunk = [hunk]
            current_tokens = overhead_per_chunk + hunk_tokens

    if current_chunk:
        chunks.append(current_chunk)
    return chunks
