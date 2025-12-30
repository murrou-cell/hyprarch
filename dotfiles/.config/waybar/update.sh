#!/usr/bin/env bash

# Get terminal configured in hyprland
TERMINAL=$(grep -oP '^\$terminal\s*=\s*\K.*' ~/.config/hypr/hyprland.conf 2>/dev/null || echo "kitty")

if [[ ! -x /usr/bin/checkupdates ]]; then
    # Install pacman-contrib if missing
    "$TERMINAL" --detach -e sh -c '
        echo "pacman-contrib not found. Installing..."
        sudo pacman -S --noconfirm pacman-contrib
        echo "Done. Press Enter to exit."
        read
    '
else
    # Run full system upgrade
    "$TERMINAL" --detach -e sh -c '
        echo "Starting full system upgrade..."
        sudo pacman -Syu
        echo "Done. Press Enter to exit."
        read
    '
fi
