#!/usr/bin/env bash
# Switches the installed ~/.config/hypr/hyprland.lua from the desktop defaults to the laptop variant.
set -euo pipefail
CONF="${1:-$HOME/.config/hypr/hyprland.lua}"
[[ -f "$CONF" ]] || { echo "$CONF not found"; exit 1; }

echo "Applying laptop variant to $CONF..."
sed -i \
    -e 's|animations = { enabled = false }|animations = { enabled = true }|' \
    -e 's| & solaar"|"|' \
    -e 's|no_hardware_cursors = true|no_hardware_cursors = false|' \
    "$CONF"
echo "Laptop variant applied (animations on, no solaar, hardware cursors on). Reload with: hyprctl reload"
