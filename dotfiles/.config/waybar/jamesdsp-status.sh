#!/bin/bash

FLATPAK_APP="me.timschneeberger.jdsp4linux"

if command -v jamesdsp >/dev/null 2>&1; then
    echo '{"text":"","tooltip":"JamesDSP (native)"}'
elif flatpak list | grep -q "$FLATPAK_APP"; then
    echo '{"text":"","tooltip":"JamesDSP (Flatpak)"}'
else
    echo '{"text":"","tooltip":"JamesDSP not installed"}'
fi
