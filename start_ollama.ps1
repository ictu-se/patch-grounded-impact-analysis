$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCommand) {
  $ollama = $ollamaCommand.Source
} else {
  $portable = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Ollama.Ollama.Portable_Microsoft.Winget.Source_8wekyb3d8bbwe\ollama.exe"
  if (-not (Test-Path -LiteralPath $portable)) {
    throw "Ollama executable was not found. Install Ollama or add ollama.exe to PATH."
  }
  $ollama = $portable
}
$logDir = Join-Path $PSScriptRoot "runs\logs"
New-Item -ItemType Directory -Force $logDir | Out-Null

$existing = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -eq "ollama" }
if (-not $existing) {
  Start-Process -FilePath $ollama -ArgumentList "serve" `
    -RedirectStandardOutput (Join-Path $logDir "ollama_stdout.log") `
    -RedirectStandardError (Join-Path $logDir "ollama_stderr.log") `
    -WindowStyle Hidden
  Start-Sleep -Seconds 5
}

Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing | Select-Object -ExpandProperty Content
