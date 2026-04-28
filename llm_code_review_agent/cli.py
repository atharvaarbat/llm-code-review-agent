import argparse
import sys
import json
# import os
from typing import List, Dict
from .diff_parser import parse_diff
from .chunker import chunk_hunks_per_file
from .llm_client import get_client
from .review import review_chunk
from .utils import Timer

MAX_TOKENS_PER_CHUNK = 3500

def main():
    parser = argparse.ArgumentParser(
        description="LLM Code Review Agent – pipe git diff, get structured review JSON"
    )
    parser.add_argument(
        "diff_file", nargs="?", type=argparse.FileType("r", encoding="utf-8"),
        default=sys.stdin,
        help="Path to a unified diff file (default: stdin)"
    )
    parser.add_argument(
        "-p", "--provider", choices=["openrouter"], default="openrouter",
        help="LLM provider (default: openrouter)"
    )
    parser.add_argument(
        "-m", "--model", default=None,
        help="Model name (provider‑specific). Anthropic default: OpenRouter default: openai/gpt-oss-120b:free"
    )
    parser.add_argument(
        "-o", "--output", type=argparse.FileType("w", encoding="utf-8"),
        default=sys.stdout,
        help="Output JSON file (default: stdout)"
    )
    parser.add_argument(
        "--max-chunk-tokens", type=int, default=MAX_TOKENS_PER_CHUNK,
        help=f"Max tokens per diff chunk sent to LLM (default: {MAX_TOKENS_PER_CHUNK})"
    )
    args = parser.parse_args()

    diff_text = args.diff_file.read()
    if not diff_text.strip():
        print("Empty diff input.", file=sys.stderr)
        sys.exit(0)

    # Parse diff
    file_diffs = parse_diff(diff_text)
    if not file_diffs:
        print("No file changes detected.", file=sys.stderr)
        sys.exit(0)

    # Set up LLM client
    client = get_client(args.provider, args.model)

    all_issues = []
    total_chunks = 0
    with Timer("End‑to‑end review"):
        for file_diff in file_diffs:
            chunks = chunk_hunks_per_file(file_diff, max_tokens=args.max_chunk_tokens)
            total_chunks += len(chunks)
            for chunk_hunks in chunks:
                issues = review_chunk(client, file_diff['path'], chunk_hunks)
                all_issues.extend(issues)

    # Output JSON
    result = {
        "review": all_issues,
        "metadata": {
            "provider": args.provider,
            "model": client.model if hasattr(client, "model") else "unknown",
            "total_chunks": total_chunks,
            "total_issues": len(all_issues),
        }
    }
    json.dump(result, args.output, indent=2)
    args.output.write("\n")

    # Stats to stderr
    print(f"Reviewed {len(file_diffs)} file(s), {total_chunks} chunk(s), {len(all_issues)} issue(s) found.",
          file=sys.stderr)

if __name__ == "__main__":
    main()