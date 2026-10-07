$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3.12 -m venv .venv }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv .venv }
    else { throw 'Python 3.12 installieren und SETUP_HOST.bat erneut starten.' }
    if ($LASTEXITCODE -ne 0) { throw 'Python-Umgebung konnte nicht erstellt werden.' }
}
& .venv/Scripts/python.exe -m pip install -r server/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Host-Abhaengigkeiten konnten nicht installiert werden.' }
Write-Host 'Bereit. START_HOST.bat startet das Spiel.'
