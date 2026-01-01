#!/usr/bin/env bash
set -euo pipefail

DOTFILES_REPO="https://github.com/murrou-cell/hyprarch.git"


# TERMINAL_CHOICE=foot https://raw.githubusercontent.com/murrou-cell/hyprarch/main/install.sh | bash
# prompt for kitty or foot terminal
if [ -t 0 ]; then
    read -p "Which terminal do you want to install? (kitty/foot): " TERMINAL_CHOICE
else
    TERMINAL_CHOICE="${TERMINAL_CHOICE:-kitty}"
    echo "Non-interactive mode detected. Using terminal: $TERMINAL_CHOICE"
fi
if [[ "$TERMINAL_CHOICE" != "kitty" && "$TERMINAL_CHOICE" != "foot" ]]; then
    echo "Invalid choice. Please choose either 'kitty' or 'foot'."
    exit 1
fi

required_software_yay=(
    kitty
    ttf-jetbrains-mono-nerd
    stow
    hyprpaper
    swaync
    waybar
    hyprlock
    hypridle
    blueman
    pavucontrol
    wofi
    vim
    firefox
)

required_software_pacman=(
    hyprland
    git
    curl
    wget
    base-devel
    go
    foot
    flatpak
)

set_terminal_in_hyprland_conf() {
    local terminal="$1"
    local hyprland_conf="$HOME/.config/hypr/hyprland.conf"

    if grep -q '^\$terminal\s*=' "$hyprland_conf"; then
        sed -i "s|^\(\$terminal\s*=\s*\).*|\1$terminal|" "$hyprland_conf"
    else
        echo "\$terminal = $terminal" >> "$hyprland_conf"
    fi
}

install_pacman_packages() {
    echo "Installing required pacman packages..."
    for pkg in "${required_software_pacman[@]}"; do
        # check if package is already installed
        if pacman -Qq "$pkg" &>/dev/null; then
            echo "$pkg is already installed, skipping."
            continue
        fi
        sudo pacman -S --needed --noconfirm "$pkg"
    done
    echo "All required pacman packages installed."
}

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

install_yay_packages() {
    echo "Installing required yay packages..."

    for pkg in "${required_software_yay[@]}"; do
        # check if package is already installed
        if yay -Qq "$pkg" &>/dev/null; then
            echo "$pkg is already installed, skipping."
            continue
        fi
        yay -S --needed --noconfirm "$pkg"
    done
    echo "All required yay packages installed."
}

dotfiles_installation() {
    echo "Cloning dotfiles repository..."

    # if directory exists, remove it first
    if [ -d "$HOME/hyprarch" ]; then
        rm -rf "$HOME/hyprarch"
    fi
    git clone $DOTFILES_REPO ~/hyprarch

    # make all files owned by user
    chown -R "$USER":"$USER" "$HOME/hyprarch"

    # Copy all dotfiles to $HOME/.config
    echo "Copying dotfiles to $HOME/.config..."
    mkdir -p "$HOME/.config"
    cp -r ~/hyprarch/dotfiles/.config/* "$HOME/.config/"
    echo "Dotfiles copied."
}

handle_firstboot() {

echo "Creating first boot configuration script..."

touch ~/.config/hypr/.firstboot

cat > ~/.config/hypr/firstboot.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

echo "Configuring wallpapers for each monitor..."
if [[ ! -f "$HOME/.config/hypr/hyprpaper.conf" ]]; then
    echo "hyprpaper.conf not found, skipping wallpaper setup"
    exit 0
fi
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
sed -i "\|^exec-once = $HOME/.config/hypr/firstboot.sh|d" \
    "$HOME/.config/hypr/hyprland.conf"


echo "First boot configuration complete."
EOF

chmod +x ~/.config/hypr/firstboot.sh

# make firstboot exec-once in hyprland.conf
if ! grep -q "exec-once = ~/.config/hypr/firstboot.sh" ~/.config/hypr/hyprland.conf; then
    echo "Adding firstboot exec-once to hyprland.conf..."
    echo "exec-once = ~/.config/hypr/firstboot.sh > ~/.config/hypr/firstboot.log 2>&1" >> ~/.config/hypr/hyprland.conf
    echo "firstboot exec-once added."
fi

}

make_all_shell_files_executable() {
    find "$HOME/.config" -type f -name "*.sh" -exec chmod +x {} \;
}


configure_firefox_policies() {
    echo "Configuring Firefox policies..."
    FIREFOX_POLICIES_DIR="/usr/lib/firefox/distribution"
    mkdir -p "$FIREFOX_POLICIES_DIR"
    cp ~/hyprarch/firefox/policies.json "$FIREFOX_POLICIES_DIR/"
    echo "Firefox policies configured."
}

IFS=$'\n\t'

echo "Starting installation..."
# Ensure sudo exists
if ! command -v sudo &>/dev/null; then
    pacman -Sy --noconfirm sudo
fi
sudo -v
echo "Sudo verified."   
# Update system
echo "Updating system..."
sudo pacman -Syu --noconfirm

# # Multilib support
# echo "Enabling multilib repository..."
# sudo sed -i '/^\[multilib\]/,/Include/ s/^#//' /etc/pacman.conf
# sudo pacman -Syu --noconfirm
# echo "Multilib repository enabled."

install_pacman_packages
echo "Pacman packages installed."
install_yay
echo "yay installed."
install_yay_packages
echo "yay packages installed."

dotfiles_installation
echo "Dotfiles installed."
handle_firstboot
echo "First boot configuration handled."

set_terminal_in_hyprland_conf "$TERMINAL_CHOICE"
echo "Terminal set in hyprland.conf."

make_all_shell_files_executable
echo "All shell files made executable."

echo "Configuring Firefox policies..."
configure_firefox_policies
echo "Firefox policies configured."

echo "Installation complete."

start-hyprland