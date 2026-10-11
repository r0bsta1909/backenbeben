$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$godot = Join-Path $projectRoot 'tools/godot/Godot_v4.7.2-stable_win64_console.exe'
New-Item -ItemType Directory -Force build/web | Out-Null
New-Item -ItemType Directory -Force logs | Out-Null
function Invoke-CheckedGodot([string]$Step, [string[]]$GodotArguments) {
    $stepLog = Join-Path $projectRoot "logs/godot-$Step-build.log"
    & $godot @GodotArguments *> $stepLog
    $stepExitCode = $LASTEXITCODE
    Get-Content -LiteralPath $stepLog | Write-Output
    if ($stepExitCode -ne 0 -or (Select-String -LiteralPath $stepLog -Pattern '^(SCRIPT ERROR:|ERROR:)' -Quiet)) {
        throw "Godot $Step failed; see $stepLog"
    }
}
Invoke-CheckedGodot 'import' @('--headless','--path','game','--editor','--import')
Invoke-CheckedGodot 'export' @('--headless','--path','game','--export-release','Web','../build/web/index.html')
Copy-Item game/assets/slap.wav,game/assets/bell.wav build/web/ -Force
Copy-Item game/browser_support.js,game/combat.js build/web/ -Force
Write-Host 'Web build ready: build/web/index.html'
