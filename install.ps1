# SkillDoctor one-line installer for Windows.
# Usage: irm https://raw.githubusercontent.com/Dongdarealest/skilldoctor/main/install.ps1 | iex
$ErrorActionPreference = "Stop"
$dest = Join-Path $HOME ".local\bin"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Dongdarealest/skilldoctor/main/skilldoctor.py" -OutFile "$dest\skilldoctor.py"
Set-Content -Path "$dest\skilldoctor.cmd" -Value "@echo off`r`npython `"%~dp0skilldoctor.py`" %*"
Write-Host "Installed the skilldoctor command in $dest"
Write-Host "If that folder is not on your PATH yet, add it, then run: skilldoctor --demo"
