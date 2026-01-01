#!/bin/bash

APP_BIN="jamesdsp"
FLATPAK_APP="me.timschneeberger.jdsp4linux"

# Already installed (native)
if command -v "$APP_BIN" >/dev/null 2>&1; then
    exec "$APP_BIN"
fi

# Already installed (flatpak)
if flatpak list | grep -q "$FLATPAK_APP"; then
    exec flatpak run "$FLATPAK_APP"
fi

menu=$(printf "Install (yay)\nInstall (Flatpak)\nCancel" | \
    wofi -dmenu -i -p "JamesDSP not installed")

case "$menu" in
    "Install (yay)")
        for term in foot kitty; do
            if command -v "$term" >/dev/null 2>&1; then
                if command -v yay >/dev/null 2>&1; then
                    exec "$term" -e yay -S --noconfirm jamesdsp
                else
                    notify-send "JamesDSP" "yay is not installed"
                fi
                break
            fi
        done
        ;;
    "Install (Flatpak)")
        for term in foot kitty; do
            if command -v "$term" >/dev/null 2>&1; then
                if ! command -v flatpak >/dev/null 2>&1; then
                    notify-send "JamesDSP" "Flatpak is not installed"
                    break
                fi
                exec "$term" -e flatpak install -y flathub "$FLATPAK_APP"
                break
            fi
        done
        ;;
esac

