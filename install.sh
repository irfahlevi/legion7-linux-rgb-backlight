#!/usr/bin/env bash
# Installs the udev rule, app-menu launcher and (optionally) login restore.
# Usage: ./install.sh [--autostart]   |   ./install.sh --uninstall
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULE=/etc/udev/rules.d/99-legion-rgb.rules
APPS="$HOME/.local/share/applications"
AUTOSTART="$HOME/.config/autostart"
SYSTEMD_USER="$HOME/.config/systemd/user"
ICONS="$HOME/.local/share/icons/hicolor"
SIZES="48 64 128 256"

if [[ "${1:-}" == "--uninstall" ]]; then
    sudo rm -f "$RULE"
    sudo udevadm control --reload-rules || true
    rm -f "$APPS/legion-rgb.desktop" "$AUTOSTART/legion-rgb-restore.desktop"
    rm -f "$SYSTEMD_USER/legion-rgb.service"
    systemctl --user daemon-reload 2>/dev/null || true
    for n in $SIZES; do rm -f "$ICONS/${n}x${n}/apps/legion-rgb.png"; done
    echo "Uninstalled. Settings remain in ~/.config/legion-rgb/."
    exit 0
fi

chmod +x "$DIR/legion-rgb-cli" "$DIR/legion-rgb-gui" "$DIR/legion-rgb-restore" "$DIR/legion-rgb-daemon"

echo "Installing udev rule (needs sudo)..."
sudo cp "$DIR/99-legion-rgb.rules" "$RULE"
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=hidraw || true

for n in $SIZES; do
    install -Dm644 "$DIR/assets/icon-$n.png" "$ICONS/${n}x${n}/apps/legion-rgb.png"
done
gtk-update-icon-cache -q -t "$ICONS" 2>/dev/null || true

mkdir -p "$APPS"
cat > "$APPS/legion-rgb.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Legion Backlit RGB
Comment=Control Legion 7 (c968/c967) keyboard, logo, vent and strip lighting
Exec="$DIR/legion-rgb-gui"
Path=$DIR
Icon=legion-rgb
StartupWMClass=Legion-rgb
Terminal=false
Categories=Settings;HardwareSettings;
EOF
echo "Launcher installed: search 'Legion Backlit RGB' in the app menu."

if [[ "${1:-}" == "--autostart" ]]; then
    mkdir -p "$AUTOSTART" "$SYSTEMD_USER"
    # Static restore (backward compatible, exits fast for animated).
    cat > "$AUTOSTART/legion-rgb-restore.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Legion RGB restore
Exec="$DIR/legion-rgb-restore"
X-GNOME-Autostart-enabled=true
NoDisplay=true
EOF
    # Persistent daemon for animated effects (static = apply-and-exit).
    cat > "$SYSTEMD_USER/legion-rgb.service" <<EOF
[Unit]
Description=Legion RGB persistent effect
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=$DIR/legion-rgb-daemon --foreground
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload 2>/dev/null || true
    systemctl --user enable --now legion-rgb.service 2>/dev/null || \
        echo "(systemd user unit written; run: systemctl --user enable --now legion-rgb.service)"
    echo "Login restore enabled (restore desktop + legion-rgb.service daemon)."
fi
