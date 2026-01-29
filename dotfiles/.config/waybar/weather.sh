#!/bin/bash
source ~/.config/waybar/weather.conf
set -euo pipefail

# =======================
# HELPERS
# =======================
round() {
  awk '{printf "%.0f", $1}'
}

code_to_icon() {
  case "$1" in
    0) echo "☀️" ;;
    1|2|3) echo "🌤️" ;;
    45|48) echo "🌫️" ;;
    51|53|55) echo "🌦️" ;;
    61|63|65) echo "🌧️" ;;
    71|73|75) echo "❄️" ;;
    95) echo "⛈️" ;;
    *) echo "❔" ;;
  esac
}

code_to_text() {
  case "$1" in
    0) echo "Ясно" ;;
    1|2|3) echo "Частично облачно" ;;
    45|48) echo "Мъгла" ;;
    51|53|55) echo "Ръмеж" ;;
    61|63|65) echo "Дъжд" ;;
    71|73|75) echo "Сняг" ;;
    95) echo "Гръмотевична буря" ;;
    *) echo "Неизвестно" ;;
  esac
}

# =======================
# WEATHER FETCH
# =======================
WEATHER_JSON=$(curl -s \
  "https://api.open-meteo.com/v1/forecast\
?latitude=$LATITUDE\
&longitude=$LONGITUDE\
&current_weather=true\
&hourly=temperature_2m,apparent_temperature,precipitation_probability,weathercode,windspeed_10m\
&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode\
&timezone=auto"
)

# =======================
# CURRENT WEATHER
# =======================
TEMP=$(jq -r '.current_weather.temperature' <<<"$WEATHER_JSON" | round)
CODE=$(jq -r '.current_weather.weathercode' <<<"$WEATHER_JSON")
WIND=$(jq -r '.current_weather.windspeed' <<<"$WEATHER_JSON" | round)

ICON=$(code_to_icon "$CODE")

# =======================
# DAILY FORECAST
# =======================
TODAY_MIN=$(jq -r '.daily.temperature_2m_min[0]' <<<"$WEATHER_JSON" | round)
TODAY_MAX=$(jq -r '.daily.temperature_2m_max[0]' <<<"$WEATHER_JSON" | round)
TODAY_CODE=$(jq -r '.daily.weathercode[0]' <<<"$WEATHER_JSON")
TODAY_RAIN=$(jq -r '.daily.precipitation_probability_max[0]' <<<"$WEATHER_JSON")

TOM_MIN=$(jq -r '.daily.temperature_2m_min[1]' <<<"$WEATHER_JSON" | round)
TOM_MAX=$(jq -r '.daily.temperature_2m_max[1]' <<<"$WEATHER_JSON" | round)
TOM_CODE=$(jq -r '.daily.weathercode[1]' <<<"$WEATHER_JSON")
TOM_RAIN=$(jq -r '.daily.precipitation_probability_max[1]' <<<"$WEATHER_JSON")

# =======================
# HOURLY FORECAST (aligned to NOW)
# =======================
NOW=$(date +"%Y-%m-%dT%H:00")

START_INDEX=$(jq -r --arg now "$NOW" '
  .hourly.time | index($now) // 0
' <<<"$WEATHER_JSON")

FEELS_LIKE=$(jq -r ".hourly.apparent_temperature[$START_INDEX]" <<<"$WEATHER_JSON" | round)

HOURLY_FMT=""
for ((i=START_INDEX; i<START_INDEX+HOURS_AHEAD; i++)); do
  TIME=$(jq -r ".hourly.time[$i]" <<<"$WEATHER_JSON" | cut -dT -f2)
  TEMP_H=$(jq -r ".hourly.temperature_2m[$i]" <<<"$WEATHER_JSON" | round)
  FEELS_H=$(jq -r ".hourly.apparent_temperature[$i]" <<<"$WEATHER_JSON" | round)
  WIND_H=$(jq -r ".hourly.windspeed_10m[$i]" <<<"$WEATHER_JSON" | round)
  RAIN_H=$(jq -r ".hourly.precipitation_probability[$i]" <<<"$WEATHER_JSON")
  CODE_H=$(jq -r ".hourly.weathercode[$i]" <<<"$WEATHER_JSON")

  HOURLY_FMT+="$TIME  ${TEMP_H}°C (≈${FEELS_H}°)  🌧 ${RAIN_H}%  🌬 ${WIND_H} km/h  $(code_to_text "$CODE_H")"$'\n'
done

# =======================
# METEOALARM
# =======================
ALERT_TITLE=$(curl -s \
  "https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-$COUNTRY" \
  | xmllint --xpath \
    "string(//*[local-name()='entry']//*[local-name()='areaDesc' and text()='$TOWN']/../*[local-name()='title'])" \
    - 2>/dev/null \
  | tr '\n' ' '
)

LEVEL=$(grep -oE 'Green|Yellow|Orange|Red' <<<"$ALERT_TITLE" || true)

if [[ -n "$LEVEL" ]]; then
  ALERT_ICON="⚠️"
  CLASS="alert-${LEVEL,,}"
else
  ALERT_ICON=""
  CLASS="ok"
fi

# =======================
# TOOLTIP
# =======================
TOOLTIP=$(cat <<EOF
$TOWN

Сега: $TEMP°C (усеща се $FEELS_LIKE°C), $(code_to_text "$CODE")
Вятър: $WIND km/h 🌬

Днес: $TODAY_MIN°C – $TODAY_MAX°C, $(code_to_text "$TODAY_CODE"), 🌧 ${TODAY_RAIN}%
Утре: $TOM_MIN°C – $TOM_MAX°C, $(code_to_text "$TOM_CODE"), 🌧 ${TOM_RAIN}%

Следващи часове:
$HOURLY_FMT
$([[ -n "$LEVEL" ]] && echo "⚠️ $ALERT_TITLE" || echo "Няма предупреждения")
EOF
)

TOOLTIP_JSON=$(jq -Rs . <<<"$TOOLTIP")

# =======================
# WAYBAR OUTPUT
# =======================
printf '{"text":"%s %s°C %s","tooltip":%s,"class":"%s"}\n' \
  "$ICON" "$TEMP" "$ALERT_ICON" "$TOOLTIP_JSON" "$CLASS"