## Complete Usage Guide

### Quick Start Installation

This repository provides an automated setup for Hyprland on Arch Linux with pre-configured dotfiles, including waybar, wofi, hyprlock, hypridle, and more.

#### Prerequisites
- Fresh or existing Arch Linux installation
- Internet connection
- Sudo access

#### Installation Methods

**Method 1: Interactive Installation (Recommended)**
```bash
curl -fsSL https://raw.githubusercontent.com/murrou-cell/hyprarch/refs/heads/main/install.sh | sudo bash
```
You'll be prompted to choose between `kitty` or `foot` as your terminal emulator.

**Method 2: Non-Interactive Installation**
```bash
# For kitty (default):
curl -fsSL https://raw.githubusercontent.com/murrou-cell/hyprarch/refs/heads/main/install.sh | sudo TERMINAL_CHOICE=kitty bash

# For foot:
curl -fsSL https://raw.githubusercontent.com/murrou-cell/hyprarch/refs/heads/main/install.sh | sudo TERMINAL_CHOICE=foot bash
```

**Method 3: Local Installation (Safer)**
```bash
# Clone and review the script before running:
git clone https://github.com/murrou-cell/hyprarch.git
cd hyprarch
cat install.sh  # Review the script
sudo bash install.sh
```

### What Gets Installed

**Core Components:**
- **Window Manager**: Hyprland
- **Terminal**: Kitty or Foot (your choice)
- **App Launcher**: Wofi
- **Status Bar**: Waybar
- **Notifications**: SwayNC
- **Lock Screen**: Hyprlock
- **Idle Manager**: Hypridle
- **Screenshot Tool**: Hyprshot
- **Wallpaper**: Hyprpaper
- **File Manager**: Dolphin
- **Browser**: Firefox (with uBlock Origin & Bitwarden pre-installed)
- **Code Editor**: VS Code
- **System Utilities**: Blueman, PulseAudio, vim, and more

### Post-Installation Configuration

#### 1. **First Boot Setup**
On first Hyprland launch, the system will automatically:
- Configure wallpapers for each detected monitor
- Set up monitor layouts
- Remove the first-boot script from autostart

#### 2. **Monitor Configuration**
If you need to reconfigure monitors after installation:
```bash
bash ~/hyprarch/MONITOR_CONFIG.sh
```
This will guide you through:
- Monitor positioning (auto, auto-left, auto-right, auto-up, auto-down)
- Screen rotation/transformation (0°, 90°, 180°, 270°)
- Workspace assignments

#### 3. **Dual-Boot with Windows**
If GRUB doesn't detect Windows 10/11:
```bash
sudo bash ~/hyprarch/FIX_BOOTLOADER.sh
```
This will install os-prober, enable it, and regenerate GRUB configuration.

#### 4. **Installing Recommended Apps**
After installation, you can install recommended Flatpak applications:
```bash
recommended-apps
```
This opens a wofi menu to select and install apps from [recommendations/flatpak.txt](recommendations/flatpak.txt):

### Configuration Files

All configuration files are located in `~/.config/`:

| Component | Config Location |
|-----------|----------------|
| Hyprland | `~/.config/hypr/hyprland.conf` |
| Waybar | `~/.config/waybar/config` |
| Wofi | `~/.config/wofi/` |
| Hyprlock | `~/.config/hypr/hyprlock.conf` |
| Hypridle | `~/.config/hypr/hypridle.conf` |
| Kitty | `~/.config/kitty/kitty.conf` |
| Foot | `~/.config/foot/foot.ini` |

### Key Bindings

**Custom Keybindings:**

| Key Combination | Action |
|----------------|--------|
| `SUPER + Q` | Open terminal |
| `SUPER + C` | Close active window |
| `SUPER + M` | Exit Hyprland |
| `SUPER + E` | Open file manager (Dolphin) |
| `SUPER + SPACE` | Open Wofi (app launcher) |
| `SUPER + SHIFT + L` | Lock screen (Hyprlock) |
| `SUPER + V` | Toggle floating mode |
| `SUPER + P` | Toggle pseudo-tiling (dwindle) |
| `SUPER + J` | Toggle split (dwindle) |
| `SUPER + S` | Toggle special workspace (scratchpad) |
| `SUPER + SHIFT + S` | Move window to special workspace |
| `SUPER + [0-9]` | Switch to workspace 0-9 |
| `SUPER + SHIFT + [0-9]` | Move window to workspace 0-9 |
| `SUPER + Arrow Keys` | Move focus between windows |
| `SUPER + SHIFT + R` | Reload Waybar |
| `SUPER + Mouse Scroll` | Scroll through workspaces |
| `SUPER + Mouse Left` | Move window |
| `SUPER + Mouse Right` | Resize window |
| `PRINT` | Screenshot (region select) |
| `SHIFT + PRINT` | Screenshot (full screen) |
| `ALT + SHIFT` | Switch keyboard layout (US/BG) |

**Media Keys:**
- `XF86AudioRaiseVolume` - Increase volume by 5%
- `XF86AudioLowerVolume` - Decrease volume by 5%
- `XF86AudioMute` - Mute/unmute audio
- `XF86AudioMicMute` - Mute/unmute microphone
- `XF86MonBrightnessUp` - Increase brightness by 5%
- `XF86MonBrightnessDown` - Decrease brightness by 5%
- `XF86AudioNext` - Next track (requires playerctl)
- `XF86AudioPrev` - Previous track (requires playerctl)
- `XF86AudioPlay/Pause` - Play/pause media (requires playerctl)

To view all keybindings:
```bash
grep "^bind" ~/.config/hypr/hyprland.conf
```

### Updating Your Setup

To update dotfiles:
```bash
cd ~/hyprarch
git pull
cp -r dotfiles/.config/* ~/.config/
```
or use stow if tou prefer

### Troubleshooting

**Problem: Hyprland won't start**
- Check logs: `cat ~/firstboot.log`
- Ensure your GPU supports Wayland
- Try starting manually: `Hyprland` (or `start-hyprland` if available)

**Problem: Terminal not working**
- Verify installation: `which kitty` or `which foot`
- Check hyprland.conf: `grep '\$terminal' ~/.config/hypr/hyprland.conf`

**Problem: Wallpaper not showing**
- Verify hyprpaper is running: `ps aux | grep hyprpaper`
- Check config: `cat ~/.config/hypr/hyprpaper.conf`
- Ensure wallpaper exists: `ls ~/.config/hypr/wallpaper.jpg`

**Problem: No sound/Bluetooth**
- PulseAudio: `pavucontrol`
- Bluetooth: `blueman-manager`

### Security Notes

- The installation script requires sudo privileges
- Firefox policies auto-install browser extensions
- Review scripts before running if concerned about security
- All scripts use `set -euo pipefail` for safer execution

### Customization

**Change Terminal:**
Edit `~/.config/hypr/hyprland.conf`:
```bash
$terminal = foot  # or kitty
```

**Modify Waybar:**
Edit `~/.config/waybar/config` and `~/.config/waybar/style.css`

**Change Wallpaper:**
Replace `~/.config/hypr/wallpaper.jpg` with your image

### License

This is a personal dotfiles repository. Use at your own risk and discretion.