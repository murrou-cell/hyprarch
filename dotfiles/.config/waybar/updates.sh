#!/usr/bin/env bash

CHECKUPDATES=/usr/bin/checkupdates

if [[ ! -x "$CHECKUPDATES" ]]; then
    echo '{"text":"\uf071 checkupdates not found","tooltip":"Install pacman-contrib","class":"updates-error"}'
    exit 0
fi

UPDATES=$($CHECKUPDATES 2>/dev/null | wc -l)

if [[ "$UPDATES" -gt 0 ]]; then
    echo "{\"text\": \"\uf0ed $UPDATES updates\", \"tooltip\": \"$UPDATES package(s) pending update\", \"class\": \"updates\"}"
else
    echo '{"text":"\uf00c","tooltip":"No updates","class":"updates"}'
fi
