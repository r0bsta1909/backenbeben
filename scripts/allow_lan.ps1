# One-time rules: game runtime + local subnet; Public profile is explicit opt-in.
param([int]$Port=8765,[int]$DiscoveryPort=8766,[switch]$NoPause,[switch]$IncludePublic)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$pythonPath=Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { $pythonPath=Join-Path $projectRoot 'tools/blender-mcp/venv/Scripts/python.exe' }
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Game Python runtime missing' }
# Windows venv launches the base interpreter, which owns the listening sockets.
$basePython=(& $pythonPath -c "import sys; print(sys._base_executable)").Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $basePython)) { throw 'Python runtime check failed' }
$profiles=@('Private')
if ($IncludePublic) { $profiles+= 'Public' }
foreach ($profile in $profiles) {
foreach ($protocol in @('TCP','UDP')) {
    $localPort=if ($protocol -eq 'TCP') { $Port } else { $DiscoveryPort }
    $ruleName="Backenbeben-$profile-LAN-$protocol-$localPort-Runtime"
    if (-not (Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -Name $ruleName -DisplayName "Backenbeben - $profile LAN $protocol $localPort" -Direction Inbound -Action Allow -Profile $profile -Protocol $protocol -LocalPort $localPort -RemoteAddress LocalSubnet -Program $basePython | Out-Null
    } else {
        Get-NetFirewallRule -Name $ruleName | Get-NetFirewallApplicationFilter | Set-NetFirewallApplicationFilter -Program $basePython | Out-Null
    }
}
}
Write-Host "LAN enabled for $profiles / local subnet: TCP $Port (game), UDP $DiscoveryPort (automatic host search)."
if (-not $NoPause) { Read-Host 'Enter to close' }
