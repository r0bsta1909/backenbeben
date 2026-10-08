$ErrorActionPreference = 'Stop'
$arenaRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $arenaRoot
$arenaGodot = Join-Path $arenaRoot 'tools/godot/Godot_v4.7.2-stable_win64_console.exe'
$arenaCopy = Join-Path $arenaRoot 'logs/arena-web-project'
New-Item -ItemType Directory -Force $arenaCopy, 'build/arena' | Out-Null
Get-ChildItem -LiteralPath game -Force | Where-Object { $_.Name -ne '.godot' } | Copy-Item -Destination $arenaCopy -Recurse -Force
$arenaConfig = Get-Content (Join-Path $arenaCopy 'project.godot') -Raw
$arenaConfig = $arenaConfig.Replace('res://main.tscn','res://arena_preview.tscn')
Set-Content (Join-Path $arenaCopy 'project.godot') $arenaConfig -Encoding utf8
$arenaPreset = Get-Content (Join-Path $arenaCopy 'export_presets.cfg') -Raw
$arenaPreset = $arenaPreset.Replace('html/custom_html_shell="res://web_shell.html"','html/custom_html_shell=""')
Set-Content (Join-Path $arenaCopy 'export_presets.cfg') $arenaPreset -Encoding utf8
& $arenaGodot --headless --path $arenaCopy --editor --import
if ($LASTEXITCODE -ne 0) { throw 'Arena import failed' }
& $arenaGodot --headless --path $arenaCopy --export-release Web ../../build/arena/index.html
if ($LASTEXITCODE -ne 0) { throw 'Arena export failed' }
$arenaHtml = Get-Content build/arena/index.html -Raw
$arenaHtml = $arenaHtml.Replace('<head>','<head><link rel="icon" href="index.png" type="image/png">')
Set-Content build/arena/index.html $arenaHtml -Encoding utf8
Write-Host 'Standalone arena preview ready: build/arena/index.html'
