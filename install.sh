#!/bin/bash

required_software=(
    "git"
    "base-devel"
    "stow"
    "hyprpaper"
    "swaync"
    "waybar"
    "hyprlock"
    "hypridle"
    "blueman"
    "pavucontrol"
    "jamesdsp"
)

# install yay
echo "Installing yay..."
sudo pacman -S --noconfirm yay
echo "yay installed."

# Install required software
echo "Installing required software..."
for software in "${required_software[@]}"; do
    echo "Installing $software..."
    yay -S --noconfirm "$software"
    echo "$software installed."
done
echo "All required software installed." 

# Deescalate the sudo move to user session
sudo -k

# clone dotfiles repo if [ ! -d "$HOME/dotfiles" ]; then
echo "Cloning dotfiles repository..."
git clone https://github.com/murrou-cell/hyprarch.git

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

# Copy all dotfiles to $HOME/.config
echo "Copying dotfiles to $HOME/.config..."
mkdir -p "$HOME/.config"
cp -r ~/hyprarch/dotfiles/* "$HOME/.config/"
echo "Dotfiles copied."
