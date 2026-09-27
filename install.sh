#!/usr/bin/env bash
# Installs the udev rule, app-menu launcher and (optionally) login restore.
# Usage: ./install.sh [--autostart]   |   ./install.sh --uninstall
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULE=/etc/udev/rules.d/99-legion-rgb.rules
APPS="$HOME/.local/share/applications"
AUTOSTART="$HOME/.config/autostart"

if [[ "${1:-}" == "--uninstall" ]]; then
    sudo rm -f "$RULE"
    sudo udevadm control --reload-rules
    rm -f "$APPS/legion-rgb.desktop" "$AUTOSTART/legion-rgb-restore.desktop"
    echo "Uninstalled. Settings remain in ~/.config/legion-rgb/."
    exit 0
fi

chmod +x "$DIR/legion-rgb-cli" "$DIR/legion-rgb-gui" "$DIR/legion-rgb-restore"

echo "Installing udev rule (needs sudo)..."
sudo cp "$DIR/99-legion-rgb.rules" "$RULE"
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=hidraw

mkdir -p "$APPS"
cat > "$APPS/legion-rgb.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Legion Backlit RGB
Comment=Control Legion 7 16ACHg6 keyboard, logo, vent and strip lighting
Exec="$DIR/legion-rgb-gui"
Path=$DIR
Icon=preferences-desktop-color
Terminal=false
Categories=Settings;HardwareSettings;
EOF
echo "Launcher installed: search 'Legion Backlit RGB' in the app menu."

if [[ "${1:-}" == "--autostart" ]]; then
    mkdir -p "$AUTOSTART"
    cat > "$AUTOSTART/legion-rgb-restore.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Legion RGB restore
Exec="$DIR/legion-rgb-restore"
X-GNOME-Autostart-enabled=true
NoDisplay=true
EOF
    echo "Login restore enabled."
fi
