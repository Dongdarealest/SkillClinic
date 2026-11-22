# SkillDoctor one-line installer for Windows.
# Usage: irm https://raw.githubusercontent.com/Dongdarealest/skilldoctor/main/install.ps1 | iex
$ErrorActionPreference = "Stop"
$dest = Join-Path $HOME ".local\bin"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Dongdarealest/skilldoctor/main/skilldoctor.py" -OutFile "$dest\skilldoctor.py"
Write-Host "Installed: $dest\skilldoctor.py"
Write-Host "Run it with: python $dest\skilldoctor.py --demo"
