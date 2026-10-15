"""The orchestrator workflow.

START -> intake -> triage -> route --exact----> run_exact ---------------------------> reply
                                   --complex--> planner -> execute_plan -> synthesize -> reply
                                   --fallback-> run_fallback ------------------------> reply

Knowledge plane = session state: request, status, triage, plan, step_results, answer.
"""
import asyncio

from google.adk import Context
from google.adk.agents import LlmAgent
from google.adk.events.event import Event
from google.adk.workflow import Workflow, node
from google.genai import types

from .executors import build_dynamic_agent, build_executor
from .models import config, model
from .registry import REGISTRY, describe, shortlist
from .schemas import DynamicProfile, Plan, Triage
from .tools import TOOLS

CONFIDENCE_THRESHOLD = 0.7


def finish(answer: str) -> Event:
    """Every path ends here: write the answer to state and show it to the caller."""
    return Event(output=answer, message=answer, state={"answer": answer, "status": "COMPLETED"})


# 1. Intake: put the request on the blackboard.
def intake(node_input: types.Content) -> Event:
    request = node_input.parts[0].text
    return Event(output=request, state={"request": request, "status": "EXECUTING"})


# 2. Triage: a small, fast model classifies. It never executes anything.
triage = LlmAgent(
    name="triage",
    model=model("router"),
    generate_content_config=config("router"),
    output_schema=Triage,
    instruction=lambda ctx: f"""Classify an investment-banking request against this registry:
{describe(shortlist(ctx.state["request"]))}

- exact: ONE registry entry can fully handle it. Set target_id to that entry's id.
- complex: it needs several entries, or several steps.
- fallback: nothing in the registry is relevant.
Give a confidence from 0 to 1.""",
)


# 3. Route: plain code decides the path. Low-confidence "exact" goes to the planner.
def route(node_input: Triage) -> Event:
    path = node_input.route
    if path == "exact" and (node_input.confidence < CONFIDENCE_THRESHOLD or node_input.target_id not in REGISTRY):
        path = "complex"
    return Event(output=node_input.model_dump(), route=path, state={"triage": node_input.model_dump(), "route": path})


# 4a. Exact match: build the one executor from the registry and run it.
@node(rerun_on_resume=True)
async def run_exact(ctx: Context, request: str, triage: dict) -> Event:
    executor = build_executor(REGISTRY[triage["target_id"]])
    return finish(await ctx.run_node(executor, node_input=request))


# 4b. Complex: plan -> execute -> synthesize.
planner = LlmAgent(
    name="planner",
    model=model(),
    generate_content_config=config(),
    output_schema=Plan,
    instruction=lambda ctx: f"""Break this investment-banking request into steps.
Request: {ctx.state["request"]}

Registry:
{describe(shortlist(ctx.state["request"]))}

Rules: each step uses one registry id as target_id. If no entry fits a step, use target_id "dynamic".
Use depends_on only when a step truly needs an earlier step's output; independent steps run in parallel.
Agents and skills fetch their own data, so never add a step just to look something up for another step.
Keep it to the fewest steps.
First write `reasoning`: the parts of the request, and which registry entry covers each (or why none does).
For each step, give `why`: why that target, and why it depends on what it depends on.""",
)


def in_waves(steps: list) -> list[list]:
    """Group steps into waves: every step in a wave only depends on earlier waves.
    Also rejects cycles and unknown dependencies."""
    done, waves = set(), []
    while len(done) < len(steps):
        ready = [s for s in steps if s.id not in done and set(s.depends_on) <= done]
        if not ready:
            raise ValueError("Plan has a cycle or an unknown dependency")
        waves.append(ready)
        done |= {s.id for s in ready}
    return waves


async def run_step(ctx: Context, step, results: dict) -> str:
    context = "\n".join(f"[{d}] {results[d]}" for d in step.depends_on)
    task = f"{step.task}\n\nOutputs of earlier steps:\n{context}" if context else step.task
    if step.target_id in REGISTRY:
        return await ctx.run_node(build_executor(REGISTRY[step.target_id]), node_input=task)
    return await run_dynamic(ctx, task)


@node(rerun_on_resume=True)
async def execute_plan(ctx: Context, node_input: Plan) -> Event:
    """Deterministic engine: no LLM decides what runs next. Steps in the same wave run in parallel."""
    results = {}
    for wave in in_waves(node_input.steps):
        outputs = await asyncio.gather(*(run_step(ctx, step, results) for step in wave))
        results.update({step.id: out for step, out in zip(wave, outputs)})
    return Event(output=results, state={"plan": node_input.model_dump(), "step_results": results})


synthesizer = LlmAgent(
    name="synthesizer",
    model=model(),
    generate_content_config=config(),
    instruction="Merge the step outputs into one clear reply for an investment banker. Keep all numbers and the compliance result.",
)


@node(rerun_on_resume=True)
async def synthesize(ctx: Context, node_input: dict, request: str) -> Event:
    steps = "\n\n".join(f"[{k}]\n{v}" for k, v in node_input.items())
    return finish(await ctx.run_node(synthesizer, node_input=f"Request: {request}\n\nStep outputs:\n{steps}"))


# 4c. Fallback: nothing matched, so write a profile for a temporary agent and run it.
profile_writer = LlmAgent(
    name="profile_writer",
    model=model(),
    generate_content_config=config(),
    output_schema=DynamicProfile,
    instruction=f"""Write a short system prompt for a temporary agent that will do the task you are given.
Only pick tool_ids from this list if they are clearly useful: {", ".join(TOOLS)}""",
)


async def run_dynamic(ctx: Context, task: str) -> str:
    profile = await ctx.run_node(profile_writer, node_input=task)
    return await ctx.run_node(build_dynamic_agent(profile), node_input=task)


@node(rerun_on_resume=True)
async def run_fallback(ctx: Context, request: str) -> Event:
    return finish(await run_dynamic(ctx, request))


root_agent = Workflow(
    name="orchestrator",
    edges=[  # each tuple is a chain; a dict is a set of routes
        ("START", intake, triage, route, {"exact": run_exact, "complex": planner, "fallback": run_fallback}),
        (planner, execute_plan, synthesize),
    ],
)
