#!/usr/bin/env bash
set -euo pipefail

DOTFILES_REPO="https://github.com/murrou-cell/hyprarch.git"

required_software=(
    # hyprland-git-bin
    ttf-dejavu
    ttf-font-awesome 
    stow
    hyprpaper
    swaync
    waybar
    hyprlock
    hypridle
    blueman
    pavucontrol
    # jamesdsp
)

IFS=$'\n\t'

# Ensure sudo exists
if ! command -v sudo &>/dev/null; then
    pacman -Sy --noconfirm sudo
fi
sudo -v

# Update system
sudo pacman -Syu --noconfirm

# Essentials
sudo pacman -S --needed --noconfirm base-devel git curl wget go

# Multilib support
sudo sed -i '/^\[multilib\]/,/Include/ s/^#//' /etc/pacman.conf
sudo pacman -Syu --noconfirm

# Wayland essentials + terminal
sudo pacman -S --needed --noconfirm xorg-xwayland mesa libinput \
    wayland-protocols wl-clipboard foot alacritty
sudo pacman -S hyprland --needed --noconfirm
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
### Install Qt6 (required by jamesdsp)
# sudo pacman -S --needed qt6-base qt6-tools qt6-declarative


echo "Installing required software..."
oldIFS=$IFS
IFS=$'\n'
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
