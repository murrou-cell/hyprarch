#!/usr/bin/env bash
set -euo pipefail

DOTFILES_REPO="https://github.com/murrou-cell/hyprarch.git"

required_software=(
    kitty
    ttf-font-awesome 
    stow
    hyprpaper
    swaync
    waybar
    hyprlock
    hypridle
    blueman
    pavucontrol
    wofi
    # jamesdsp
)

IFS=$'\n\t'
echo "Starting installation of HyprArch dotfiles..."
# Ensure sudo exists
if ! command -v sudo &>/dev/null; then
    pacman -Sy --noconfirm sudo
fi
sudo -v
echo "Sudo verified."   
# Update system
echo "Updating system..."
sudo pacman -Syu --noconfirm

# Essentials
echo "Installing base development packages..."  
sudo pacman -S --needed --noconfirm base-devel git curl wget go
echo "Base development packages installed."

# Multilib support
echo "Enabling multilib repository..."
sudo sed -i '/^\[multilib\]/,/Include/ s/^#//' /etc/pacman.conf
sudo pacman -Syu --noconfirm
echo "Multilib repository enabled."

# DEBUG
sudo pacman -S --needed --noconfirm foot
#
# Install Hyprland from official repos
echo "Installing Hyprland..."
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
echo "yay installed."

### Install Qt6 (required by jamesdsp)
# sudo pacman -S --needed qt6-base qt6-tools qt6-declarative


echo "Installing required software..."
# oldIFS=$IFS
# IFS=$'\n'
for pkg in "${required_software[@]}"; do
    yay -S --needed --noconfirm "$pkg"
done
echo "All required software installed." 

echo "Cloning dotfiles repository..."
# if directory exists, remove it first
if [ -d "$HOME/hyprarch" ]; then
    rm -rf "$HOME/hyprarch"
fi
git clone $DOTFILES_REPO


# Copy all dotfiles to $HOME/.config
echo "Copying dotfiles to $HOME/.config..."
mkdir -p "$HOME/.config"
cp -r ~/hyprarch/dotfiles/.config/* "$HOME/.config/"
echo "Dotfiles copied."


# TODO: MAKE THIS EXECUTABLE SCRIPT AND PUT IT in exec-once in hyprland.conf also remove it from there when it is finished
touch ~/.config/hypr/.firstboot

cat > ~/.config/hypr/firstboot.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

echo "Configuring wallpapers for each monitor..."

MONITORS=($(hyprctl monitors all | awk '/^Monitor / {gsub(/^Monitor |:$/,""); print $1}'))
echo "Found ${#MONITORS[@]} monitors."

for i in "${!MONITORS[@]}"; do
    MONITOR_NAME=${MONITORS[$i]}
    WALLPAPER_PATH="$HOME/.config/hypr/wallpaper.jpg"
    
    sed -i "/^wallpaper {/,/^}/ s/^\(\s*monitor = \).*/\1$MONITOR_NAME/" ~/.config/hypr/hyprpaper.conf
    sed -i "/^wallpaper {/,/^}/ s#^\(\s*path = \).*#\1$WALLPAPER_PATH#" ~/.config/hypr/hyprpaper.conf
    sed -i "/^wallpaper {/,/^}/ s/^\(\s*fit_mode = \).*/\1cover/" ~/.config/hypr/hyprpaper.conf
    
    echo "Configured wallpaper for monitor $MONITOR_NAME"
done

# Remove firstboot marker and this script
rm -f ~/.config/hypr/.firstboot
rm -f ~/.config/hypr/firstboot.sh

# Remove exec-once line from hyprland.conf
sed -i '/^exec-once = ~/.config\/hypr\/firstboot.sh/d' ~/.config/hypr/hyprland.conf

echo "First boot configuration complete."
EOF

chmod +x ~/.config/hypr/firstboot.sh

# make firstboot exec-once in hyprland.conf
if ! grep -q "exec-once = ~/.config/hypr/firstboot.sh" ~/.config/hypr/hyprland.conf; then
    echo "Adding firstboot exec-once to hyprland.conf..."
    echo "exec-once = ~/.config/hypr/firstboot.sh" >> ~/.config/hypr/hyprland.conf
    echo "firstboot exec-once added."
fi

# change the $terminal variable in hyprland.conf to currently configured one
# CURRENT_TERMINAL=$(grep -oP '^\$terminal\s*=\s*\K.*' ~/.config/hypr/hyprland.conf 2>/dev/null || echo "kitty")
# sed -i "s/^\(\$terminal\s*=\s*\).*/\1$CURRENT_TERMINAL/" ~/hyprarch/dotfiles/.config/hypr/hyprland.conf
# echo "Set terminal in hyprland.conf to $CURRENT_TERMINAL"


start-hyprland