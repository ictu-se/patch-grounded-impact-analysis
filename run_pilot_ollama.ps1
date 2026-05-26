$env:AGENT_BACKEND = "ollama"
if (-not $env:OLLAMA_MODEL) {
  $env:OLLAMA_MODEL = "qwen2.5-coder:7b"
}

& (Join-Path $PSScriptRoot "start_ollama.ps1")
python (Join-Path $PSScriptRoot "run_pilot.py") @args
