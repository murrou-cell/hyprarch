#!/bin/bash
set -euo pipefail
source ~/.config/waybar/weather.conf

# Windy format: windy.com/{lat}/{lon}
xdg-open "https://www.windy.com/${LATITUDE}/${LONGITUDE}"