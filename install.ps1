# SkillClinic installer for Windows, pinned to a release and checksum verified.
# It downloads skillclinic.py and its published SHA-256 as assets of
# the same release and refuses to install when the two do not match.
# Usage: irm https://raw.githubusercontent.com/Dongdarealest/skillclinic/v0.4.6/install.ps1 | iex
$ErrorActionPreference = "Stop"
$version = "0.4.6"
$base = "https://github.com/Dongdarealest/skillclinic/releases/download/v$version"
$dest = Join-Path $HOME ".local\bin"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
try {
    $scriptPath = Join-Path $tmp "skillclinic.py"
    $sumPath = Join-Path $tmp "skillclinic.py.sha256"
    Invoke-WebRequest -Uri "$base/skillclinic.py" -OutFile $scriptPath
    Invoke-WebRequest -Uri "$base/skillclinic.py.sha256" -OutFile $sumPath
    $expected = ((Get-Content $sumPath -Raw) -split '\s+')[0].ToLower()
    $actual = (Get-FileHash -Algorithm SHA256 $scriptPath).Hash.ToLower()
    if ($expected -ne $actual) {
        throw "Checksum mismatch for skillclinic.py (expected $expected, got $actual). Refusing to install."
    }
    Copy-Item $scriptPath (Join-Path $dest "skillclinic.py") -Force
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
Set-Content -Path "$dest\skillclinic.cmd" -Value "@echo off`r`npython `"%~dp0skillclinic.py`" %*"
Write-Host "Installed the skillclinic command in $dest (v$version, checksum verified)"
Write-Host "If that folder is not on your PATH yet, add it, then run: skillclinic --demo"
