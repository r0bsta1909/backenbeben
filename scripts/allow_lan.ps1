# Optional one-time Windows firewall setup, scoped to this game, private LAN only.
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$pythonPath=Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { $pythonPath=Join-Path $projectRoot 'tools/blender-mcp/venv/Scripts/python.exe' }
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Game Python runtime missing' }
$ruleName='Backenbeben-Private-LAN-8765'
if (-not (Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name $ruleName -DisplayName 'Backenbeben - Private LAN' -Direction Inbound -Action Allow -Profile Private -Protocol TCP -LocalPort 8765 -RemoteAddress LocalSubnet -Program $pythonPath | Out-Null
}
Write-Host 'Private LAN access enabled for Backenbeben on TCP 8765.'
Read-Host 'Enter to close'
