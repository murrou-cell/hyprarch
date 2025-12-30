#!/usr/bin/env bash
# connect_iwd.sh
# Usage: ./connect_iwd.sh

# --- Detect Wi-Fi device ---
DEVICE=$(iwctl device list | tail -n 3 | awk '{$1=$2; print $1}' | sed -n '2p')
if [[ -z "$DEVICE" ]]; then
    echo "No Wi-Fi device found."
    exit 1
fi

# --- Scan for networks ---
iwctl station "$DEVICE" scan
sleep 1  # give some time for scan to complete

# --- Get list of SSIDs ---
SSID=$(iwctl station "$DEVICE" get-networks | awk 'NR>5 {print $1}' | wofi -dmenu -i -p "Select Wi-Fi")
if [[ -z "$SSID" ]]; then
    echo "No SSID selected, aborting."
    exit 1
fi

# --- Check if selected SSID is in known-networks ---
known_hosts=()
while IFS= read -r line; do
  known_hosts+=("$line")
done < <(
  iwctl known-networks list |
  awk 'NR>4 && match($0, /\s+(.+?)\s{2,}(psk|--)/, m) {gsub(/[ \t]+$/, "", m[1]);print m[1]}'
)
if printf '%s\n' "${known_hosts[@]}" | grep -qx "$SSID"; then
    notify-send "Already known network: $SSID"
    notify-send "Connecting to known network: $SSID"
    iwctl station "$DEVICE" connect "$SSID"
    exit 0
fi

# --- Prompt for password ---
PASSWORD=$(wofi -dmenu -P -p "Password for $SSID")
if [[ -z "$PASSWORD" ]]; then
    echo "No password entered, aborting."
    exit 1
fi

# --- Connect using iwctl ---
notify-send "Connecting to $SSID..."
iwctl --passphrase="$PASSWORD" station "$DEVICE" connect "$SSID"

# --- Optional: confirm connection ---
sleep 2
NEW=$(iwctl station "$DEVICE" show | awk -F: '/Connected network/ {gsub("Connected network", "", $1); gsub(/^[ \t]+/, "", $1); gsub(/[ \t]+$/, "", $1); print $1}')
if [[ "$NEW" == "$SSID" ]]; then
    notify-send "Connected to $SSID"
else
    notify-send "Failed to connect to $SSID"
fi
