#!/bin/bash

# Fix GRUB not detecting Windows 10
# This script installs os-prober, enables it, and regenerates GRUB config

echo "=== GRUB Windows 10 Detection Fix ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Step 1: Install os-prober
echo "[1/3] Installing os-prober..."
pacman -S --needed --noconfirm os-prober

# Step 2: Enable os-prober in GRUB config
echo "[2/3] Enabling os-prober in GRUB configuration..."
if grep -q "^GRUB_DISABLE_OS_PROBER=true" /etc/default/grub; then
    sed -i 's/^GRUB_DISABLE_OS_PROBER=true/GRUB_DISABLE_OS_PROBER=false/' /etc/default/grub
    echo "  - Changed GRUB_DISABLE_OS_PROBER to false"
elif grep -q "^#GRUB_DISABLE_OS_PROBER=false" /etc/default/grub; then
    sed -i 's/^#GRUB_DISABLE_OS_PROBER=false/GRUB_DISABLE_OS_PROBER=false/' /etc/default/grub
    echo "  - Uncommented GRUB_DISABLE_OS_PROBER=false"
elif ! grep -q "GRUB_DISABLE_OS_PROBER" /etc/default/grub; then
    echo "GRUB_DISABLE_OS_PROBER=false" >> /etc/default/grub
    echo "  - Added GRUB_DISABLE_OS_PROBER=false"
else
    echo "  - GRUB_DISABLE_OS_PROBER already set to false"
fi

# Step 3: Regenerate GRUB configuration
echo "[3/3] Regenerating GRUB configuration..."
grub-mkconfig -o /boot/grub/grub.cfg

echo ""
echo "=== Done! ==="
echo "Please reboot to see Windows 10 in the GRUB menu."
echo "Run: reboot"