"""Run the three demo requests, one per route, and print what happened."""
import asyncio
import json
import sys
import time
import warnings

from google.adk.runners import InMemoryRunner
from google.genai import types

from orchestrator.agent import in_waves, root_agent
from orchestrator.schemas import Plan

warnings.filterwarnings("ignore", category=UserWarning)  # hide ADK "experimental feature" notices

PROMPTS = [
    "What are the trading comps for Helix Robotics?",
    "Prep me for a pitch to Helix Robotics: check the restricted list, build a company one-pager, "
    "pull trading comps, and draft a 3-line intro email to the coverage MD.",
    "Write a short toast for our team's closing dinner on the Apex deal.",
]


def show_plan(plan: Plan) -> None:
    print("\n  ┌─ PLANNER " + "─" * 88)
    print(f"  │ Reasoning: {plan.reasoning}")
    for step in plan.steps:
        print(f"  │\n  │ {step.id} → {step.target_id}" + (f"   (after {', '.join(step.depends_on)})" if step.depends_on else ""))
        print(f"  │   Task: {step.task}")
        print(f"  │   Why:  {step.why}")
    waves = " → ".join("[" + ", ".join(s.id for s in wave) + "]" for wave in in_waves(plan.steps))
    print(f"  │\n  │ Engine will run: {waves}   (steps inside [ ] run in parallel)")
    print("  └" + "─" * 98 + "\n")


async def run(runner: InMemoryRunner, prompt: str) -> None:
    print("\n" + "=" * 100 + f"\nREQUEST: {prompt}\n" + "=" * 100)
    session = await runner.session_service.create_session(app_name="poc", user_id="banker")
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    start, last_author = time.monotonic(), None
    async for event in runner.run_async(user_id="banker", session_id=session.id, new_message=message):
        if event.author != last_author:  # progress line each time a different node/agent speaks
            last_author = event.author
            print(f"  [{time.monotonic() - start:5.1f}s] {event.author}")
        if event.author == "planner" and isinstance(event.output, dict):
            show_plan(Plan(**event.output))  # print the plan the moment it exists, before any step runs
        for call in event.get_function_calls() or []:
            print(f"  [{time.monotonic() - start:5.1f}s]   {event.author} calls {call.name}({json.dumps(dict(call.args or {}))})")

    state = (await runner.session_service.get_session(app_name="poc", user_id="banker", session_id=session.id)).state
    t = state["triage"]
    print(f"\nROUTE: {state['route']}  (triage said {t['route']}, target={t['target_id']}, confidence={t['confidence']})")
    print(f"WHY:   {t['reason']}")
    print(f"STATUS: {state['status']} in {time.monotonic() - start:.1f}s\n\nANSWER:\n{state['answer']}")


async def main() -> None:
    runner = InMemoryRunner(agent=root_agent, app_name="poc")
    picks = [PROMPTS[int(i) - 1] for i in sys.argv[1:]] or PROMPTS  # e.g. `python run.py 2`
    for prompt in picks:
        await run(runner, prompt)


if __name__ == "__main__":
    asyncio.run(main())
