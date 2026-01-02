#!/usr/bin/env bash
set -euo pipefail

RECOMMENDED_URL="https://raw.githubusercontent.com/murrou-cell/hyprarch/main/recommendations/flatpak.txt"

if ! command -v curl &>/dev/null; then
    echo "curl is required but not installed."
    exit 1
fi

if ! command -v flatpak &>/dev/null; then
    echo "Flatpak is not installed."
    exit 1
fi

echo "Fetching recommended Flatpak apps..."
mapfile -t APPS < <(curl -sSL "$RECOMMENDED_URL")

missing=()

# Get list of installed Flatpak app IDs, trimming whitespace and special characters
mapfile -t INSTALLED < <(flatpak list --app --columns=application)

# Trim whitespace and remove carriage returns from app IDs and check installation
for app in "${APPS[@]}"; do
    clean_app="$(echo "$app" | xargs)"  # Trim extra spaces
    if [[ -z "$clean_app" ]]; then
        continue
    fi

    # Remove any carriage returns or extra newlines
    clean_app=$(echo "$clean_app" | tr -d '\r')

    # Clean the INSTALLED apps for comparison, removing any carriage returns and newlines
    clean_installed=($(printf "%s\n" "${INSTALLED[@]}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | tr -d '\r'))

    if printf '%s\n' "${clean_installed[@]}" | grep -Fxq "$clean_app"; then
        echo "Checking for $clean_app... installed."
    else
        echo "Checking for $clean_app... not installed."
        missing+=("$clean_app")
    fi
done

if [[ ${#missing[@]} -eq 0 ]]; then
    echo "All recommended Flatpak apps are already installed."
    exit 0
fi

echo
echo "📦 Recommended Flatpak apps not installed:"
printf "  • %s\n" "${missing[@]}"
echo

# Prompt user to select which apps to install
selected=$(printf "%s\n" "${missing[@]}" | wofi --dmenu -i -p "Select apps to install")

# Remove hidden control characters
selected=$(printf '%s' "$selected" | tr -d '\r\0')

[[ -z "$selected" ]] && exit 0

flatpak install -y flathub "$selected"
