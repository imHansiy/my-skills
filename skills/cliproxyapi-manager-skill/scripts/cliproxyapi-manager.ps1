$ErrorActionPreference = "Stop"
$ScriptPath = Join-Path $PSScriptRoot "cliproxyapi_manager.py"
$Py = Get-Command py -ErrorAction SilentlyContinue
if ($Py) {
  & py -3 $ScriptPath @args
  exit $LASTEXITCODE
}
$Python = Get-Command python -ErrorAction SilentlyContinue
if ($Python) {
  & python $ScriptPath @args
  exit $LASTEXITCODE
}
Write-Error "Python 3.8+ is required but was not found in PATH."
exit 127
