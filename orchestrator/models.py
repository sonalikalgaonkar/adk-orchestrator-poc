"""Model switch. Change MODEL / ROUTER_MODEL in .env; no code changes needed."""
import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.models import Gemini
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

load_dotenv(Path(__file__).parents[1] / ".env")

RETRY = types.HttpRetryOptions(attempts=4, initial_delay=2, max_delay=15)  # ride out short 429s, then fail visibly


def _name(kind: str) -> str:
    return os.environ["ROUTER_MODEL" if kind == "router" else "MODEL"]


def model(kind: str = "main"):
    """kind "main" = MODEL, "router" = ROUTER_MODEL (small and fast).
    'anthropic/claude-...' goes through LiteLLM; a plain Gemini name goes direct."""
    name = _name(kind)
    return LiteLlm(model=name, num_retries=3) if "/" in name else Gemini(model=name, retry_options=RETRY)


def config(kind: str = "main") -> types.GenerateContentConfig | None:
    """Gemini thinks before every reply; LOW keeps it fast (MINIMAL is rejected by gemini-3.7-flash).
    Not a Gemini model -> None (use the provider's defaults)."""
    if "/" in _name(kind):
        return None
    return types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="LOW"))
