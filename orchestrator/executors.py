"""build_executor: turn any registry entry into a runnable LlmAgent."""
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset

from .models import config, model
from .tools import TOOLS

SKILLS_DIR = Path(__file__).parent / "skills"


def build_executor(entry: dict) -> LlmAgent:
    name = entry["id"].replace("-", "_")  # agent names must be identifiers
    tools = [TOOLS[t] for t in entry.get("tools", [])]

    if entry["type"] == "agent":  # domain agent: its own prompt + tools
        return LlmAgent(name=name, model=model(), generate_content_config=config(),
                        instruction=entry["instruction"], tools=tools)

    if entry["type"] == "tool":  # naked tool: a thin agent extracts strict args and calls it once
        return LlmAgent(
            name=f"{name}_wrapper", model=model("router"), generate_content_config=config("router"),
            instruction=f"Extract the arguments from the request, call `{entry['id']}` once, and report the result plainly.",
            tools=[TOOLS[entry["id"]]],
        )

    if entry["type"] == "skill":  # skill: a recipe the agent loads and follows
        skill = load_skill_from_dir(SKILLS_DIR / entry["id"])
        return LlmAgent(
            name=name, model=model(), generate_content_config=config(),
            instruction=f"Load the skill '{entry['id']}' first, then follow every step of it, including its tool calls.",
            tools=[SkillToolset(skills=[skill], additional_tools=tools)],
        )

    raise ValueError(f"Unknown registry type: {entry['type']}")


def build_dynamic_agent(profile: dict) -> LlmAgent:
    """Fallback: a temporary agent from an LLM-written profile, limited to existing tools."""
    tools = [TOOLS[t] for t in profile.get("tool_ids", []) if t in TOOLS]
    return LlmAgent(name="dynamic_agent", model=model(), generate_content_config=config(),
                    instruction=profile["instruction"], tools=tools)
