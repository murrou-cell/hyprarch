#!/usr/bin/env bash
set -euo pipefail

echo "Configuring wallpapers for each monitor..."

CONF="$HOME/.config/hypr/hyprpaper.conf"
WALLPAPER="$HOME/.config/hypr/wallpaper.jpg"

[[ -f "$CONF" ]] || exit 0

MONITORS=($(hyprctl monitors all | awk '/^Monitor / {gsub(/^Monitor |:$/,""); print $1}'))
echo "Found ${#MONITORS[@]} monitors."

# Remove existing wallpaper blocks
sed -i '/^wallpaper {/,/^}/d' "$CONF"

for m in "${MONITORS[@]}"; do
cat >> "$CONF" << 'WALLPAPER_BLOCK'
wallpaper {
    monitor = MONITOR_NAME
    path = WALLPAPER_PATH
    fit_mode = cover
}
WALLPAPER_BLOCK

sed -i \
    -e "s/MONITOR_NAME/$m/" \
    -e "s#WALLPAPER_PATH#$WALLPAPER#" \
    "$CONF"
done

rm -f ~/.config/hypr/.firstboot
sed -i "\|firstboot.sh|d" ~/.config/hypr/hyprland.conf