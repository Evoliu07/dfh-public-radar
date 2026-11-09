#!/bin/zsh
set -e
cd "/Users/evo/Desktop/东方红公开学习台"

# 仅工作日 08:00–19:00 运行；Mac 睡眠/关机时不运行。
DOW=$(date +%u)
HOUR=$(date +%H)
if (( DOW > 5 || HOUR < 8 || HOUR >= 19 )); then
  exit 0
fi

LOCK="/tmp/dfh-public-radar.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  exit 0
fi
trap 'rmdir "$LOCK"' EXIT

mkdir -p logs
{
  echo "--- $(date '+%Y-%m-%d %H:%M:%S') ---"
  .venv/bin/python fetch_data.py
  .venv/bin/python publish_update.py
} >> logs/update.log 2>&1

# 限制日志体积
tail -n 2000 logs/update.log > logs/update.log.tmp && mv logs/update.log.tmp logs/update.log
