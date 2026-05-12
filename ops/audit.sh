#!/usr/bin/env bash
# Аудит сервера перед деплоем contest-бота.
# Запускается через SSH одной командой, ничего не меняет.
#
#   ssh -i ~/.ssh/contest_ed25519 root@82.22.3.8 'bash -s' < ops/audit.sh
#
set -uo pipefail

hr() { printf '\n=== %s ===\n' "$1"; }

hr "uname / lsb_release"
uname -a
( . /etc/os-release && echo "OS: $PRETTY_NAME" ) 2>/dev/null

hr "uptime / load"
uptime

hr "disk"
df -hT -x tmpfs -x devtmpfs

hr "memory"
free -h

hr "timedatectl"
timedatectl 2>/dev/null || date

hr "что установлено"
for cmd in docker "docker compose" nginx certbot psql redis-cli git curl jq ufw fail2ban-client; do
  if [ "$cmd" = "docker compose" ]; then
    if docker compose version >/dev/null 2>&1; then
      printf '  %-22s %s\n' "$cmd" "$(docker compose version | head -1)"
    else
      printf '  %-22s NOT INSTALLED\n' "$cmd"
    fi
  else
    if command -v "$cmd" >/dev/null 2>&1; then
      printf '  %-22s %s\n' "$cmd" "$(command -v "$cmd")"
    else
      printf '  %-22s NOT INSTALLED\n' "$cmd"
    fi
  fi
done

hr "docker daemon"
if command -v docker >/dev/null 2>&1; then
  systemctl is-active docker 2>/dev/null || echo "docker service status unknown"
  echo "--- containers (all) ---"
  docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>&1 | head -50
  echo "--- images ---"
  docker images --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}' 2>&1 | head -30
  echo "--- volumes ---"
  docker volume ls 2>&1 | head -30
  echo "--- networks ---"
  docker network ls 2>&1 | head -20
else
  echo "docker not installed"
fi

hr "слушают порты (22/80/443/5432/6379/8000)"
ss -tlnp 2>/dev/null | awk 'NR==1 || /:(22|80|443|5432|6379|8000) /'

hr "запущенные сервисы (важные)"
systemctl list-units --type=service --state=running --no-legend --no-pager 2>/dev/null | \
  awk '{print $1}' | grep -E '^(nginx|postgresql|redis|docker|ssh|fail2ban|ufw|certbot)' || true

hr "ufw status"
ufw status 2>/dev/null || echo "ufw not installed"

hr "/opt и /home — что лежит"
ls -la /opt 2>/dev/null
echo "--"
ls -la /home 2>/dev/null
echo "--"
ls -la /root 2>/dev/null | head -20

hr "поиск возможных артефактов от прошлых попыток"
echo "--- *.env в /opt /home /root ---"
find /opt /home /root -maxdepth 4 -name "*.env" -type f 2>/dev/null
echo "--- docker-compose файлы ---"
find /opt /home /root -maxdepth 4 -name "docker-compose*" -type f 2>/dev/null
echo "--- проекты с package.json или pyproject.toml ---"
find /opt /home /root -maxdepth 4 \( -name "package.json" -o -name "pyproject.toml" -o -name "requirements.txt" \) -type f 2>/dev/null

hr "nginx конфиги (если есть)"
ls -la /etc/nginx/sites-enabled/ 2>/dev/null
ls -la /etc/nginx/conf.d/ 2>/dev/null

hr "letsencrypt"
ls -la /etc/letsencrypt/live/ 2>/dev/null || echo "no certs yet"

hr "DNS-проверка домена изнутри сервера"
( command -v dig >/dev/null && dig +short rtbkonkurs.ru A ) || \
( command -v host >/dev/null && host rtbkonkurs.ru ) || \
( getent hosts rtbkonkurs.ru )

hr "GOTOVO"
echo "Аудит закончен."
