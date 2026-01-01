#!/usr/bin/env bash
set -euo pipefail

RECOMMENDED_URL="https://raw.githubusercontent.com/murrou-cell/hyprarch/main/recommendations/flatpak.txt"
CACHE_DIR="$HOME/.cache/hyprarch"
CACHE_FILE="$CACHE_DIR/flatpak.txt"

mkdir -p "$CACHE_DIR"

echo "🌐 Fetching recommended Flatpak apps..."

if ! command -v curl &>/dev/null; then
    echo "❌ curl is required but not installed."
    exit 1
fi

if ! command -v flatpak &>/dev/null; then
    echo "❌ Flatpak is not installed."
    exit 1
fi

# Fetch list (with fallback to cache)
if ! curl -fsSL "$RECOMMENDED_URL" -o "$CACHE_FILE.tmp"; then
    echo "⚠️ Failed to fetch list from GitHub."
    if [[ -f "$CACHE_FILE" ]]; then
        echo "Using cached recommendations."
    else
        echo "No cached list available."
        exit 1
    fi
else
    mv "$CACHE_FILE.tmp" "$CACHE_FILE"
fi

# Ensure Flathub exists
if ! flatpak remote-list | grep -q flathub; then
    echo "➕ Adding Flathub remote..."
    flatpak remote-add --if-not-exists flathub \
        https://flathub.org/repo/flathub.flatpakrepo
fi

mapfile -t APPS < <(
    grep -Ev '^\s*#|^\s*$' "$CACHE_FILE"
)

missing=()

for app in "${APPS[@]}"; do
    if ! flatpak info "$app" &>/dev/null; then
        missing+=("$app")
    fi
done

if [[ ${#missing[@]} -eq 0 ]]; then
    echo "✅ All recommended Flatpak apps are already installed."
    exit 0
fi

echo
echo "📦 Recommended Flatpak apps not installed:"
printf "  • %s\n" "${missing[@]}"
echo

if [[ ${#missing[@]} -eq 0 ]]; then
    echo "✅ All recommended Flatpak apps are already installed."
    exit 0
fi

echo "📦 Select Flatpak apps to install (TAB to select, ENTER to confirm):"

if ! command -v fzf &>/dev/null; then
    echo "❌ fzf is not installed."
    echo "Install it with: sudo pacman -S fzf"
    exit 1
fi

selected=$(printf "%s\n" "${missing[@]}" | wofi --dmenu --multi-select)

[[ -z "$selected" ]] && exit 0

flatpak install -y flathub $selected
echo "🎉 Selected apps installed!"