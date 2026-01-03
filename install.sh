#!/usr/bin/env bash
set -euo pipefail

DOTFILES_REPO="https://github.com/murrou-cell/hyprarch.git"


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
    ttf-joypixels
    ttf-font-awesome 
    otf-font-awesome
    hyprpaper
    swaync
    waybar
    hyprlock
    hypridle
    hyprshot
    blueman
    pavucontrol
    wofi
    vim
    firefox
    dolphin
    visual-studio-code-bin
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
    fuse # for running .AppImage files
    brightnessctl
)

set_terminal_in_hyprland_conf() {
    echo "Setting terminal to $1 in hyprland.conf..."
    local terminal="$1"
    local hyprland_conf="$HOME/.config/hypr/hyprland.conf"

    if grep -q '^\$terminal\s*=' "$hyprland_conf"; then
        sed -i "s|^\(\$terminal\s*=\s*\).*|\1$terminal|" "$hyprland_conf"
    else
        echo "\$terminal = $terminal" >> "$hyprland_conf"
    fi
    echo "Terminal set in hyprland.conf."
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
    echo "Installing yay AUR helper..."
    if command -v yay &>/dev/null; then
        echo "yay already installed"
        return
    fi

    cd /tmp
    git clone https://aur.archlinux.org/yay.git
    cd yay
    makepkg -si --noconfirm
    hash -r
    echo "yay installed."
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
    echo "Adding firstboot script to hyprland.conf..."

    echo 'exec-once = ~/.config/hypr/firstboot.sh > ~/firstboot.log 2>&1' \
        >> ~/.config/hypr/hyprland.conf
    
    echo "Firstboot script added."
}

make_all_shell_files_executable() {
    echo "Making all .sh files in .config executable..."
    find "$HOME/.config" -type f -name "*.sh" -exec chmod +x {} \;
    echo "All .sh files in .config made executable."
}


configure_firefox_policies() {
    echo "Configuring Firefox policies..."
    FIREFOX_POLICIES_DIR="/usr/lib/firefox/distribution"
    sudo mkdir -p "$FIREFOX_POLICIES_DIR"
    sudo cp ~/hyprarch/firefox/policies.json "$FIREFOX_POLICIES_DIR/"
    echo "Firefox policies configured."
}

set_hyprland_autostart_prompt() {
    if ! grep -q "exec start-hyprland" "$HOME/.bash_profile"; then
        echo "Adding start-hyprland to .bash_profile..."
        cat >> "$HOME/.bash_profile" << 'EOF'

# Start Hyprland on login
if [[ $(tty) == /dev/tty1 ]]; then
    read -p "Start Hyprland? [y/N]: " start_hypr
    if [[ "$start_hypr" =~ ^[Yy]$ ]]; then
    exec start-hyprland
    fi
fi
EOF
        echo "start-hyprland added to .bash_profile."
    fi
}

add_alias_for_hyprland_recommended() {
    ALIAS_KEY="recommended-apps"
    if ! grep -q "alias $ALIAS_KEY" "$HOME/.bashrc"; then
        echo "Adding alias for installing recommended Flatpak apps to .bashrc..."
        echo "alias $ALIAS_KEY='bash ~/.config/hypr/hyprarch-recommended.sh'" >> "$HOME/.bashrc"
        echo "Alias added."
    fi
}

IFS=$'\n\t'

echo "Starting installation..."
# Ensure sudo exists and refresh credentials
if ! command -v sudo &>/dev/null; then
    pacman -Sy --noconfirm sudo
fi
# Refresh sudo timestamp to avoid mid-installation prompts
sudo -v
echo "Setup verified."

install_pacman_packages

install_yay

install_yay_packages

dotfiles_installation

handle_firstboot

set_terminal_in_hyprland_conf "$TERMINAL_CHOICE"

make_all_shell_files_executable

configure_firefox_policies

set_hyprland_autostart_prompt

add_alias_for_hyprland_recommended

echo "Installation complete."

start-hyprland