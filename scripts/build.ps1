$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$godot = Join-Path $projectRoot 'tools/godot/Godot_v4.7.2-stable_win64_console.exe'
New-Item -ItemType Directory -Force build/web | Out-Null
& $godot --headless --path game --editor --import
if ($LASTEXITCODE -ne 0) { throw 'Godot import failed' }
& $godot --headless --path game --export-release Web ../build/web/index.html
if ($LASTEXITCODE -ne 0) { throw 'Godot export failed' }
Copy-Item game/assets/slap.wav,game/assets/bell.wav build/web/ -Force
Copy-Item game/browser_support.js,game/combat.js build/web/ -Force
Write-Host 'Web build ready: build/web/index.html'
