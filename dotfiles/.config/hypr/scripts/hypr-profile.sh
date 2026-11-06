#!/usr/bin/env bash
# Usage: hypr-profile.sh snappy|default, then reloads Hyprland
set -euo pipefail
DIR="$HOME/.config/hypr"
case "${1:-}" in
    default) rm -f "$DIR/profile.lua" ;;
    snappy)  cp "$DIR/config-snappy.lua" "$DIR/profile.lua" ;;
    *) echo "usage: ${0##*/} snappy|default" >&2; exit 1 ;;
esac
hyprctl reload
