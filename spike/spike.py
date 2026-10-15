"""Phase 0 spike: prove the three risky ADK 2.0 pieces work with Claude via LiteLLM."""
import asyncio, os, pathlib
from dotenv import load_dotenv
from pydantic import BaseModel
from google.adk import Context
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset
from google.adk.workflow import Workflow, node
from google.genai import types

load_dotenv()
def pick(name):  # "anthropic/..." -> LiteLLM, plain Gemini name -> native
    return LiteLlm(model=name) if "/" in name else name

MODEL = pick(os.environ["MODEL"])


class Triage(BaseModel):
    route: str
    confidence: float


# A: Claude + output_schema inside a workflow
triage = LlmAgent(name="triage", model=MODEL, output_schema=Triage,
                  instruction="Classify the request as 'exact', 'complex' or 'fallback'. Give a confidence 0-1.")

def show(node_input: dict) -> str:
    print("  A output:", node_input, type(node_input).__name__)
    return "ok"

# B + C: dynamic node that builds agents at runtime and runs them with ctx.run_node
@node(rerun_on_resume=True)
async def dynamic(ctx: Context, node_input) -> str:
    plain = LlmAgent(name="runtime_agent", model=MODEL, instruction="Reply with one short sentence.")
    r1 = await ctx.run_node(plain, node_input="Say hello to an investment banker.")
    print("  B output:", repr(r1)[:200])
    skill = load_skill_from_dir(pathlib.Path(__file__).parent / "skills" / "haiku-recipe")
    skilled = LlmAgent(name="skill_agent", model=MODEL, tools=[SkillToolset(skills=[skill])],
                       instruction="Use your skills when relevant.")
    r2 = await ctx.run_node(skilled, node_input="Write a haiku about an IPO.")
    print("  C output:", repr(r2)[:400])
    return "done"

root = Workflow(name="spike", edges=[("START", triage), (triage, show), (show, dynamic)])


async def main():
    runner = InMemoryRunner(agent=root, app_name="spike")
    s = await runner.session_service.create_session(app_name="spike", user_id="u")
    msg = types.Content(role="user", parts=[types.Part(text="What are the trading comps for Helix Robotics?")])
    async for ev in runner.run_async(user_id="u", session_id=s.id, new_message=msg):
        for c in ev.get_function_calls() or []:
            print("  tool call:", ev.author, c.name, dict(c.args or {}))

asyncio.run(main())
