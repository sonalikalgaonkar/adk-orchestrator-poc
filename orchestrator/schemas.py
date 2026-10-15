"""Structured outputs. The LLM must answer in these shapes, so code can act on them."""
from typing import Literal

from pydantic import BaseModel


class Triage(BaseModel):
    route: Literal["exact", "complex", "fallback"]
    target_id: str | None = None  # registry id, only for route == "exact"
    confidence: float  # 0..1
    reason: str


class Step(BaseModel):
    id: str  # e.g. "s1"
    target_id: str  # registry id, or "dynamic" when nothing in the registry fits
    task: str  # what this step must produce
    depends_on: list[str] = []
    why: str  # why this target, and why these dependencies


class Plan(BaseModel):
    reasoning: str  # how the request was broken down; written before the steps, so the model thinks first
    steps: list[Step]


class DynamicProfile(BaseModel):
    instruction: str  # just-in-time system prompt for a temporary agent
    tool_ids: list[str] = []  # registry tools it may use
