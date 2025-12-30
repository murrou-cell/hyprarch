#!/usr/bin/env bash
set -euo pipefail

DOTFILES_REPO="https://github.com/murrou-cell/hyprarch.git"

required_software=(
    stow
    hyprpaper
    swaync
    waybar
    hyprlock
    hypridle
    blueman
    pavucontrol
    jamesdsp
)

echo "Installing base dependencies..."
sudo pacman -S --needed --noconfirm git base-devel go

install_yay() {
    if command -v yay &>/dev/null; then
        echo "yay already installed"
        return
    fi

    cd /tmp
    git clone https://aur.archlinux.org/yay.git
    cd yay
    makepkg -si --noconfirm
    hash -r
}

install_yay

echo "Installing required software..."
for pkg in "${required_software[@]}"; do
    yay -S --needed --noconfirm "$pkg"
done

echo "All required software installed." 

# clone dotfiles repo if [ ! -d "$HOME/dotfiles" ]; then
echo "Cloning dotfiles repository..."
git clone $DOTFILES_REPO

echo "Configuring wallpapers for each monitor..."

# MONITORS=$(hyprctl -j get_monitors | jq length)
MONITORS=($(hyprctl monitors all | awk '/^Monitor / {gsub(/^Monitor |:$/,""); print $1}'))
# modify dotfiles/hypr/hyprpaper.conf to set wallpapers for each monitor
for i in "${!MONITORS[@]}"; do
    MONITOR_NAME=${MONITORS[$i]}
    WALLPAPER_PATH="$HOME/.config/hypr/wallpaper.jpg"
    # wallpaper {
    #     monitor = eDP-1
    #     path = ~/.config/hypr/wallpaper.jpg
    #     fit_mode = cover
    # }
    # rm file if exists
    rm -f ~/hyprarch/dotfiles/hypr/hyprpaper.conf
    sed -i "/^wallpaper {/,/^}/ s/^\(\s*monitor = \).*/\1$MONITOR_NAME/" ~/hyprarch/dotfiles/hypr/hyprpaper.conf
    sed -i "/^wallpaper {/,/^}/ s#^\(\s*path = \).*#\1 $WALLPAPER_PATH#" ~/hyprarch/dotfiles/hypr/hyprpaper.conf
    sed -i "/^wallpaper {/,/^}/ s/^\(\s*fit_mode = \).*/\1cover/" ~/hyprarch/dotfiles/hypr/hyprpaper.conf

    echo "Configured wallpaper for monitor $MONITOR_NAME"
done

# change the $terminal variable in hyprland.conf to currently configured one
CURRENT_TERMINAL=$(grep -oP '^\$terminal\s*=\s*\K.*' ~/.config/hypr/hyprland.conf 2>/dev/null || echo "kitty")
sed -i "s/^\(\$terminal\s*=\s*\).*/\1$CURRENT_TERMINAL/" ~/hyprarch/dotfiles/hypr/hyprland.conf
echo "Set terminal in hyprland.conf to $CURRENT_TERMINAL"

# Copy all dotfiles to $HOME/.config
echo "Copying dotfiles to $HOME/.config..."
mkdir -p "$HOME/.config"
cp -r ~/hyprarch/dotfiles/* "$HOME/.config/"
echo "Dotfiles copied."
