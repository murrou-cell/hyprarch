#!/usr/bin/env bash

# --- CPU usage (since last check, using cached snapshot) ---
CACHE=~/.cache/waybar-sysmon
mkdir -p ~/.cache
if [[ -f "$CACHE" ]]; then
	read -r OLD_IDLE_OLD TOTAL_OLD < "$CACHE"
fi
read -r CPU_ID CPU_NICE CPU_SYS CPU_IDLE _REST < <(cat /proc/stat | head -1)
TOTAL=$((CPU_ID + CPU_NICE + CPU_SYS + CPU_IDLE))

if [[ -n "$TOTAL_OLD" ]] && (( TOTAL > TOTAL_OLD )); then
	DEL_IDLE=$((CPU_IDLE - OLD_IDLE_OLD))
	DEL_TOTAL=$((TOTAL - TOTAL_OLD))
	CPU_PCT=$(( (DEL_TOTAL - DEL_IDLE) * 100 / DEL_TOTAL ))
else
	CPU_PCT=0
fi
echo "$CPU_IDLE $TOTAL" > "$CACHE"

# --- Memory usage ---
MEM_TOTAL=$(awk '/^MemTotal:/{print $2}' /proc/meminfo)
MEM_AVAIL=$(awk '/^MemAvailable:/{print $2}' /proc/meminfo)
MEM_PCT=$(( (MEM_TOTAL - MEM_AVAIL) * 100 / MEM_TOTAL ))

# --- GPU VRAM usage (AMD via /sys, fallback rocm-smi) ---
GPU_MEM_TOTAL=0
GPU_MEM_USED=0
if ls /sys/class/drm/card*/device/mem_info_vram_total &>/dev/null; then
	GPU_MEM_TOTAL=$(cat /sys/class/drm/card*/device/mem_info_vram_total 2>/dev/null | head -1)
	GPU_MEM_USED=$(cat /sys/class/drm/card*/device/mem_info_vram_used 2>/dev/null | head -1)
fi
if [[ "$GPU_MEM_TOTAL" -gt 0 ]] 2>/dev/null; then
	GPU_PCT=$(( GPU_MEM_USED * 100 / GPU_MEM_TOTAL ))
else
	GPU_PCT=$(rocm-smi --showmeminfo vram 2>/dev/null | awk '/VRAM Total/{total=$NF} /VRAM Total Used/{used=$NF} END{if(total>0) printf "%d", used*100/total; else print 0}')
fi

# --- Build formatted output ---
CPU_ICON=$'\uf200'
MEM_ICON=$'\uf538'
GPU_ICON=$'\ue715'

echo "{\"text\":\"${CPU_ICON}  ${CPU_PCT}%  ${MEM_ICON}  ${MEM_PCT}%  ${GPU_ICON}  ${GPU_PCT}%   \",\"tooltip\":\"CPU: ${CPU_PCT}% / MEM: ${MEM_PCT}% / GPU VRAM: ${GPU_PCT}%\",\"class\":\"sysmon\"}"
