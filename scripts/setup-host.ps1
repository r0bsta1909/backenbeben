param(
    [string]$PythonPath = '',
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot

function Test-HostPython([string]$Executable, [string[]]$PrefixArgs = @()) {
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { return $false }
    try {
        $version = & $Executable @PrefixArgs -c "import sys; print('%s.%s' % sys.version_info[:2])" 2>$null
        return ($LASTEXITCODE -eq 0 -and ($version -join '').Trim() -eq '3.12')
    } catch { return $false }
}

$venvPython = Join-Path $projectRoot '.venv/Scripts/python.exe'
$selectedPython = $null
$selectedArgs = @()
if (Test-Path -LiteralPath $venvPython) {
    if (-not (Test-HostPython $venvPython)) {
        throw 'Die vorhandene .venv verwendet nicht Python 3.12. Ordner .venv umbenennen und SETUP_HOST.bat erneut starten. Es wurde nichts geloescht.'
    }
    $selectedPython = $venvPython
} elseif ($PythonPath) {
    if (-not (Test-HostPython $PythonPath)) { throw 'Der angegebene PythonPath muss auf eine funktionierende Python-3.12-python.exe zeigen.' }
    $selectedPython = $PythonPath
} else {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher -and (Test-HostPython $launcher.Source @('-3.12'))) {
        $selectedPython = $launcher.Source
        $selectedArgs = @('-3.12')
    }
    if (-not $selectedPython) {
        $onPath = Get-Command python -ErrorAction SilentlyContinue
        if ($onPath -and (Test-HostPython $onPath.Source)) { $selectedPython = $onPath.Source }
    }
    if (-not $selectedPython) {
        $bundled = Join-Path $projectRoot 'tools/python/cpython-3.12-windows-x86_64-none/python.exe'
        if (Test-HostPython $bundled) { $selectedPython = $bundled }
    }
}
if (-not $selectedPython) {
    throw 'Python 3.12 wurde nicht gefunden. Python 3.12 installieren und SETUP_HOST.bat erneut starten. Alternativ: powershell -File scripts/setup-host.ps1 -PythonPath C:\Pfad\python.exe'
}
Write-Host "Python 3.12: $selectedPython"
if ($CheckOnly) { return }
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $selectedPython @selectedArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python-Umgebung konnte nicht erstellt werden.' }
}
& $venvPython -m pip install -r server/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Host-Abhaengigkeiten konnten nicht installiert werden.' }
Write-Host 'Bereit. START_HOST.bat startet das Spiel.'
