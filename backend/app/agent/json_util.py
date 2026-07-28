"""Shared JSON extraction helpers for LLM outputs (Ollama-friendly)."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any] | None:
    """
    Pull the first JSON object from model text.
    Handles markdown fences and trailing prose better than greedy regex.
    """
    if not text or not str(text).strip():
        return None
    text = str(text).strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```.*$", "", text, flags=re.DOTALL)
        text = text.strip()

    # Direct parse
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and data and isinstance(data[0], dict):
            # Some models return a bare questions array
            return {"questions": data}
    except json.JSONDecodeError:
        pass

    # Decode from first '{'
    start = text.find("{")
    if start >= 0:
        decoder = json.JSONDecoder()
        try:
            data, _ = decoder.raw_decode(text[start:])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # Bare array of questions
    start_arr = text.find("[")
    if start_arr >= 0:
        decoder = json.JSONDecoder()
        try:
            data, _ = decoder.raw_decode(text[start_arr:])
            if isinstance(data, list):
                return {"questions": data}
        except json.JSONDecodeError:
            pass

    return None
