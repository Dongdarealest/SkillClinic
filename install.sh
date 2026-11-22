#!/usr/bin/env bash
# SkillDoctor installer, pinned to a release and checksum verified.
# It downloads skilldoctor.py and its published SHA-256 as assets of
# the same release and refuses to install when the two do not match.
# Usage: curl -fsSL https://raw.githubusercontent.com/Dongdarealest/skilldoctor/v0.3.9/install.sh | bash
set -euo pipefail
VERSION="0.3.9"
BASE="https://github.com/Dongdarealest/skilldoctor/releases/download/v${VERSION}"
DEST="${HOME}/.local/bin"
mkdir -p "$DEST"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL "${BASE}/skilldoctor.py" -o "$TMP/skilldoctor.py"
curl -fsSL "${BASE}/skilldoctor.py.sha256" -o "$TMP/skilldoctor.py.sha256"
EXPECTED="$(awk '{print $1}' "$TMP/skilldoctor.py.sha256")"
if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL="$(sha256sum "$TMP/skilldoctor.py" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  ACTUAL="$(shasum -a 256 "$TMP/skilldoctor.py" | awk '{print $1}')"
else
  echo "error: no SHA-256 tool found (need sha256sum or shasum); refusing to install unverified" >&2
  exit 1
fi
if [ "$EXPECTED" != "$ACTUAL" ]; then
  echo "error: checksum mismatch for skilldoctor.py" >&2
  echo "  expected: $EXPECTED" >&2
  echo "  actual:   $ACTUAL" >&2
  echo "Refusing to install." >&2
  exit 1
fi
install -m 0755 "$TMP/skilldoctor.py" "$DEST/skilldoctor"
echo "Installed: $DEST/skilldoctor (v${VERSION}, checksum verified)"
case ":$PATH:" in
  *":$DEST:"*) echo "Run it with: skilldoctor --demo" ;;
  *) echo "Add $DEST to your PATH, then run: skilldoctor --demo" ;;
esac
