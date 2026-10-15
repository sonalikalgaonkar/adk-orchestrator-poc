"""The capability registry: every agent, tool and skill the orchestrator can use."""
import json
from pathlib import Path

REGISTRY: dict[str, dict] = {e["id"]: e for e in json.loads((Path(__file__).parent / "registry.json").read_text())}


def shortlist(request: str) -> list[dict]:
    """Candidates for a request. POC: the whole registry. At scale: embedding search, top-k."""
    return list(REGISTRY.values())


def describe(entries: list[dict]) -> str:
    """One line per entry, for prompts."""
    return "\n".join(f"- {e['id']} ({e['type']}): {e['description']}" for e in entries)
