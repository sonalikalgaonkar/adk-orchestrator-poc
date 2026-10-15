# ADK Orchestrator POC

A deliberately tiny intent orchestrator on Google ADK 2.0 (`Workflow` API), using a mock investment-banking registry.
Every request is triaged into one of three routes:

```
START -> intake -> triage -> route --exact----> run_exact ---------------------------> reply
                                   --complex--> planner -> execute_plan -> synthesize -> reply
                                   --fallback-> run_fallback ------------------------> reply
```

## Run it

```bash
uv sync
cp .env.example .env              # then set the model and credentials
uv run python run.py              # all three demo requests
uv run python run.py 2            # just the complex one
```

Model switch (`.env`): `MODEL=gemini-3.7-flash` runs Gemini natively; `MODEL=anthropic/claude-sonnet-5-5`
runs Claude through LiteLLM (needs an `sk-ant-api03-` API key). `ROUTER_MODEL` is the small, fast triage model.

## Code walkthrough (read in this order)

| # | File | What to show |
|---|------|--------------|
| 1 | `orchestrator/registry.json` | The capability registry: agents, tools and a skill, each with a description the LLMs route on. |
| 2 | `orchestrator/tools.py` | Mock data functions. Plain Python; ADK builds the tool schema from type hints and docstrings. |
| 3 | `orchestrator/skills/company-one-pager/SKILL.md` | A skill is a recipe. It also declares the tools it unlocks (`adk_additional_tools`). |
| 4 | `orchestrator/schemas.py` | Structured outputs: `Triage`, `Plan`, `DynamicProfile`. The LLM decides; code acts on the shape. |
| 5 | `orchestrator/executors.py` | `build_executor(entry)`: one function turns any registry entry into a runnable agent. |
| 6 | `orchestrator/agent.py` | The workflow: one node per box in the architecture, and the edges at the bottom. |
| 7 | `orchestrator/models.py` | Model switch: `model()` picks Gemini or Claude from `.env`; `config()` sets Gemini's thinking level. |
| 8 | `run.py` | Runs the demo and prints route, plan, tool calls and the blackboard (session state). |

## How the architecture maps to ADK

| Architecture box | ADK 2.0 |
|---|---|
| Knowledge plane | Session state (`request`, `status`, `triage`, `route`, `plan`, `step_results`, `answer`), written via `Event(state=...)` |
| Intent triage router | `LlmAgent` with `output_schema=Triage`, then a plain function returning `Event(route=...)` |
| Domain agent / tool wrapper / skill | `LlmAgent` built at runtime by `build_executor`; skills use `SkillToolset` |
| Planner | `LlmAgent` with `output_schema=Plan` |
| Execution engine | `execute_plan`: a dynamic node; groups steps into waves, runs each wave in parallel with `asyncio.gather` over `ctx.run_node(...)` |
| Dynamic agent builder | `profile_writer` (`output_schema=DynamicProfile`) + `build_dynamic_agent` |
| Response synthesizer | `LlmAgent` run from the `synthesize` node |

## Deliberately left out

Replan on failure, per-step retries/timeouts, real retrieval (`shortlist()` returns the whole registry),
`$step.field` input references (steps get earlier outputs as plain text), multi-turn agent
stickiness, code sandbox, A2A, persistent sessions, evals.

## Performance notes

The complex request went from ~429 s to ~31 s:
- Gemini thinking set to LOW for every agent (`config()` in `models.py`); MINIMAL is rejected by gemini-3.7-flash.
- Independent plan steps run in parallel (waves in `execute_plan`).
- Planner prompt forbids "look-up only" steps, since agents and skills fetch their own data.
- Vertex `global` capacity is shared and returns intermittent 429s; retries are capped so a run fails visibly
  instead of hanging. A Google AI Studio key or a Claude key avoids that pool.
