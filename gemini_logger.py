"""
gemini_logger.py
A lightweight logging utility for Gemini API calls.

Usage:
    from gemini_logger import log_call, print_summary

    response = client.models.generate_content(...)   # your code, your way
    log_call(response, model="gemini-3.1-flash-lite-preview", call_type="text")

    response = client.models.generate_content(...)
    log_call(response, model="gemini-3.1-flash-image-preview", call_type="image", image_resolution="512")
"""

import json                                 # For reading/writing the log file
import uuid                                 # For generating unique IDs for log entries
from datetime import datetime, timezone     # For timestamping log entries
from pathlib import Path                    # For handling the log file path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

LOG_FILE = Path("gemini_api_calls.json")

PRICING = {
    "gemini-3.1-flash-lite-preview": {
        "input":  0.25  / 1_000_000,
        "output": 1.50  / 1_000_000,
    },
    "gemini-3.1-flash-image-preview": {
        "input":  0.50 / 1_000_000,
        "output": 1.50 / 1_000_000,
        "image_output": 60.0 / 1_000_000,
    },
}

IMAGE_TOKENS = {
    "512":   747,
    "1024": 1120,
    "2048": 1680,
    "4096": 2520,
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_log() -> dict:
    if LOG_FILE.exists():
        with LOG_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"calls": [], "total_cost_usd": 0.0}


def _save_log(log: dict) -> None:
    with LOG_FILE.open("w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def _compute_cost(model: str, input_tokens: int, output_tokens: int,
                  image_tokens: int = 0) -> float:
    p = PRICING[model]
    cost = input_tokens * p["input"] + output_tokens * p["output"]
    if image_tokens:
        cost += image_tokens * p["image_output"]

    return cost

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_call(response,
             model: str,
             call_type: str,
             image_resolution: str = "512",
             prompt_preview: str = "",
             explicit: bool = False) -> float:
    """
    Log a Gemini API response and return the cost in USD.

    Args:
        response:         The raw response object returned by the Gemini SDK.
        model:            Model name, e.g. "gemini-3.1-flash-lite-preview".
        call_type:        "text" or "image".
        image_resolution: Only used when call_type="image". One of: "512", "1024", "2048", "4096".
        prompt_preview:   Optional short description or prompt snippet for the log.
        explicit:         If True, print the log entry to console.

    Returns:
        cost_usd (float)
    """
    if model not in PRICING:
        raise ValueError(f"Unknown model '{model}'. Add it to PRICING in gemini_logger.py.")

    usage = response.usage_metadata
    input_tokens  = usage.prompt_token_count
    output_tokens = usage.candidates_token_count

    # Image token cost
    image_tokens = 0
    if call_type == "image":
        if image_resolution not in IMAGE_TOKENS:
            raise ValueError(f"image_resolution must be one of {list(IMAGE_TOKENS.keys())}")
        num_images = sum(
            1 for part in response.parts
            if part.inline_data and part.inline_data.mime_type.startswith("image/")
        )
        image_tokens = IMAGE_TOKENS[image_resolution] * num_images

    cost = round(_compute_cost(model, input_tokens, output_tokens, image_tokens), 5)

    entry = {
        "id":               str(uuid.uuid4()),
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "model":            model,
        "call_type":        call_type,
        "prompt_preview":   prompt_preview[:120] if prompt_preview else "",
        "input_tokens":     input_tokens,
        "output_tokens":    output_tokens,
        **({"image_resolution": image_resolution, "image_tokens": image_tokens} if call_type == "image" else {}),
        "cost_usd":         cost,
    }

    log = _load_log()
    log["calls"].append(entry)
    log["total_cost_usd"] = round(log["total_cost_usd"] + cost, 10)
    _save_log(log)

    if explicit:
        print(
            f"[LOG] {model} | {call_type} | "
            f"in={input_tokens} out={output_tokens}"
            + (f" img={image_tokens}" if image_tokens else "")
            + f" | cost=${cost:.6f} | total=${log['total_cost_usd']:.6f}"
        )

    return cost


def print_summary() -> None:
    """Print a formatted summary of all logged calls and the total cost."""
    log = _load_log()
    calls = log["calls"]

    print("\n" + "=" * 60)
    print(f"  GEMINI API SUMMARY  —  {len(calls)} call(s)")
    print("=" * 60)
    for c in calls:
        print(f"  [{c['timestamp']}]")
        print(f"    model   : {c['model']}")
        print(f"    type    : {c['call_type']}")
        if c.get("prompt_preview"):
            print(f"    prompt  : {c['prompt_preview']}")
        print(f"    tokens  : in={c['input_tokens']}  out={c['output_tokens']}", end="")
        if c.get("image_tokens"):
            print(f"  img={c['image_tokens']} ({c['image_resolution']}px)", end="")
        print(f"\n    cost    : ${c['cost_usd']:.6f}\n")

    print(f"  TOTAL: ${log['total_cost_usd']:.6f}")
    print("=" * 60 + "\n")