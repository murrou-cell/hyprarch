#!/bin/bash

$DOTFILES_REPO = "https://github.com/murrou-cell/hyprarch.git"

required_software=(
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

# install git and base-devel if not installed
echo "Installing git and base-devel..."
sudo pacman -S --noconfirm git base-devel
echo "git and base-devel installed."

# install yay
echo "Installing yay..."
# # currently go version in arch repos is 1.23, need 1.24+
# sudo pacman -S "go>=1.24" --noconfirm
# #################################
cd /tmp
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si
## get the output of last command
if [[ $? -ne 0 ]]; then
    echo "Error installing yay. Exiting."
    exit 1
fi
cd ..
rm -rf yay
echo "yay installed."

# Install required software
echo "Installing required software..."
for software in "${required_software[@]}"; do
    echo "Installing $software..."
    yay -S --noconfirm "$software"
    # check the output of last command
    if [[ $? -ne 0 ]]; then
        echo "Error installing $software. Exiting."
        exit 1
    fi
    echo "$software installed."
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
