# Agent backend integration

The current harness uses `mock_agent.py` so the pipeline can be tested end-to-end without a real coding agent.

There is also an `ollama_agent.py` backend that calls a local Ollama server over HTTP.

Quick local use:

- set `AGENT_BACKEND=ollama`
- optionally set `OLLAMA_MODEL=qwen2.5-coder:7b`
- run `python run_pilot.py`

To integrate a real backend:

1. Create a new module beside `mock_agent.py`.
2. Implement a function with the same shape:
   - input: `JobSpec`, `workspace: Path`
   - output: `AgentRunResult`
3. Replace the import in `harness/run_task.py`.

Minimum fields your backend should populate:

- `status`
- `summary`
- `commands`
- `files_touched`
- `patch_text`
- `trajectory`
- `metadata`
