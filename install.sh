#!/usr/bin/env bash
# SkillDoctor one-line installer.
# Usage: curl -fsSL https://raw.githubusercontent.com/Dongdarealest/skilldoctor/main/install.sh | bash
set -euo pipefail
DEST="${HOME}/.local/bin"
mkdir -p "$DEST"
curl -fsSL "https://raw.githubusercontent.com/Dongdarealest/skilldoctor/main/skilldoctor.py" -o "$DEST/skilldoctor"
chmod +x "$DEST/skilldoctor"
echo "Installed: $DEST/skilldoctor"
case ":$PATH:" in
  *":$DEST:"*) echo "Run it with: skilldoctor --demo" ;;
  *) echo "Add $DEST to your PATH, then run: skilldoctor --demo" ;;
esac
