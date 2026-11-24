#!/usr/bin/env bash
# SkillClinic installer, pinned to a release and checksum verified.
# It downloads skillclinic.py and its published SHA-256 as assets of
# the same release and refuses to install when the two do not match.
# Usage: curl -fsSL https://raw.githubusercontent.com/Dongdarealest/skillclinic/v0.4.6/install.sh | bash
set -euo pipefail
VERSION="0.4.6"
BASE="https://github.com/Dongdarealest/skillclinic/releases/download/v${VERSION}"
DEST="${HOME}/.local/bin"
mkdir -p "$DEST"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL "${BASE}/skillclinic.py" -o "$TMP/skillclinic.py"
curl -fsSL "${BASE}/skillclinic.py.sha256" -o "$TMP/skillclinic.py.sha256"
EXPECTED="$(awk '{print $1}' "$TMP/skillclinic.py.sha256")"
if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL="$(sha256sum "$TMP/skillclinic.py" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  ACTUAL="$(shasum -a 256 "$TMP/skillclinic.py" | awk '{print $1}')"
else
  echo "error: no SHA-256 tool found (need sha256sum or shasum); refusing to install unverified" >&2
  exit 1
fi
if [ "$EXPECTED" != "$ACTUAL" ]; then
  echo "error: checksum mismatch for skillclinic.py" >&2
  echo "  expected: $EXPECTED" >&2
  echo "  actual:   $ACTUAL" >&2
  echo "Refusing to install." >&2
  exit 1
fi
install -m 0755 "$TMP/skillclinic.py" "$DEST/skillclinic"
echo "Installed: $DEST/skillclinic (v${VERSION}, checksum verified)"
case ":$PATH:" in
  *":$DEST:"*) echo "Run it with: skillclinic --demo" ;;
  *) echo "Add $DEST to your PATH, then run: skillclinic --demo" ;;
esac
