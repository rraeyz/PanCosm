#!/bin/sh
# Installs PanCosm on Linux for the current user: the newest AppImage from GitHub Releases, a command in
# ~/.local/bin and an entry in the application menu. No root, no FUSE needed.
#
#   install / update:  curl -fsSL https://raw.githubusercontent.com/rraeyz/PanCosm/main/packaging/install.sh | sh
#   remove:            curl -fsSL https://raw.githubusercontent.com/rraeyz/PanCosm/main/packaging/install.sh | sh -s -- --uninstall
set -eu

REPO="rraeyz/PanCosm"
NAME="PanCosm"
ID="pancosm"
BIN="${XDG_BIN_HOME:-$HOME/.local/bin}"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
HOME_DIR="$DATA/$ID"                       # the extracted application
MENU="$DATA/applications/$ID.desktop"
ICON="$DATA/icons/hicolor/512x512/apps/$ID.png"

refresh_menu() {
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q "$DATA/applications" || true
    command -v kbuildsycoca6 >/dev/null 2>&1 && kbuildsycoca6 >/dev/null 2>&1 || true
}

if [ "${1:-}" = "--uninstall" ]; then
    rm -rf "$HOME_DIR" "$MENU" "$ICON" "$BIN/$ID"
    refresh_menu
    echo "$NAME removed. Your settings are kept in ~/.config/$ID (delete that folder to remove them too)."
    exit 0
fi

case "$(uname -m)" in
    x86_64 | amd64) ARCH=x86_64 ;;
    aarch64 | arm64) ARCH=aarch64 ;;
    *) echo "Sorry, $NAME has no Linux build for $(uname -m)." >&2; exit 1 ;;
esac

echo "Looking for the newest $NAME release..."
URL=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
    | grep -o "https://[^\"]*-linux-$ARCH\.AppImage" | head -n 1)
[ -n "$URL" ] || { echo "No Linux $ARCH download found on the Releases page." >&2; exit 1; }
VERSION=$(echo "$URL" | sed -n "s/.*$NAME-\(.*\)-linux-$ARCH\.AppImage/\1/p")

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
echo "Downloading $NAME $VERSION..."
curl -fL --progress-bar "$URL" -o "$TMP/app.AppImage"
chmod +x "$TMP/app.AppImage"

echo "Installing..."
# extracted once: starts faster than the AppImage and needs no FUSE
(cd "$TMP" && APPIMAGE_EXTRACT_AND_RUN=1 ./app.AppImage --appimage-extract >/dev/null)
rm -rf "$HOME_DIR"
mkdir -p "$DATA" "$BIN" "$(dirname "$MENU")" "$(dirname "$ICON")"
mv "$TMP/squashfs-root" "$HOME_DIR"
cp "$HOME_DIR/$ID.png" "$ICON"
ln -sf "$HOME_DIR/AppRun" "$BIN/$ID"

cat > "$MENU" <<EOF
[Desktop Entry]
Type=Application
Name=$NAME
Comment=Astronomy workbench
Exec="$HOME_DIR/AppRun" %F
Icon=$HOME_DIR/$ID.png
Categories=Science;Astronomy;Education;
Terminal=false
EOF
refresh_menu

echo "$NAME $VERSION is installed. Start it from the application menu, or type: $ID"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "(To use the '$ID' command, add $BIN to your PATH.)" ;; esac
echo "To update later, run the same command again."
