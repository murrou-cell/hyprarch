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
    rofi -dmenu -p "JamesDSP not installed")

case "$menu" in
    "Install (yay)")
        if command -v yay >/dev/null 2>&1; then
            yay -S --noconfirm jamesdsp
        else
            notify-send "JamesDSP" "yay is not installed"
        fi
        ;;
    "Install (Flatpak)")
        flatpak install -y flathub "$FLATPAK_APP"
        ;;
esac

