# https://wiki.hypr.land/Configuring/Monitors/
# for every monitor detected by hyprctl add config like this one after prompt:
# monitor=DP-1, preferred, auto-left, 1
# monitor=eDP-1, preferred, auto, 1, transform, 0
# workspace = 1, monitor:DP-1
# workspace = 2, monitor:eDP-1

#!/usr/bin/env bash
set -euo pipefail
echo "Configuring monitor layout in hyprland.conf..."
CONF="$HOME/.config/hypr/hyprland.conf"
[[ -f "$CONF" ]] || exit 0
MONITORS=($(hyprctl monitors all | awk '/^Monitor / {gsub(/^Monitor |:$/,""); print $1}'))
echo "Found ${#MONITORS[@]} monitors."

# Remove existing monitor and workspace lines
sed -i '/^monitor=/d' "$CONF"
sed -i '/^workspace = /d' "$CONF"

# for every monitor prompt the user for position transformation and workspace number
INDEX=1
for m in "${MONITORS[@]}"; do
    echo "Configuring monitor: $m"
    read -rp "Enter position for monitor $m (options: auto, auto-left, auto-right, auto-up, auto-down) [default: auto]: " POS
    POS=${POS:-auto}
    read -rp "Enter transform for monitor $m (options: 0, 1, 2, 3) [default: 0]: " TRANSFORM
    TRANSFORM=${TRANSFORM:-0}
    read -rp "Enter workspace number to assign to monitor $m [default: $INDEX]: " WS
    WS=${WS:-$INDEX}
    INDEX=$((INDEX + 1))
    echo "Adding monitor configuration: monitor=$m, preferred, $POS, 1, transform, $TRANSFORM"
    echo "monitor=$m, highres, $POS, 1, transform, $TRANSFORM" >> "$CONF"
    echo "Adding workspace configuration: workspace = $WS, monitor:$m"
    echo "workspace = $WS, monitor:$m" >> "$CONF"

done

echo "Monitor configuration updated in $CONF."
