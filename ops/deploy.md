# Шпаргалка деплоя

## Контекст

- Домен: `rtbkonkurs.ru` → `82.22.3.8`
- SSH-ключ: `~/.ssh/contest_ed25519` (локально на машине разработчика)
- Папка проекта на сервере: `/opt/contest`
- Email для Let's Encrypt: `rostabakrostabak@gmail.com`

## Первый деплой (one-time)

### 1. Положить публичный ключ на сервер

С локальной машины (Windows PowerShell):
```powershell
# Установка ключа через ssh-copy-id (Windows 10+ имеет OpenSSH client).
# Введи пароль root один раз, дальше ходим по ключу.
type C:\Users\ASUS\.ssh\contest_ed25519.pub | ssh root@82.22.3.8 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Проверка:
```powershell
ssh -i C:\Users\ASUS\.ssh\contest_ed25519 root@82.22.3.8 "echo ok"
```

### 2. Аудит сервера

```powershell
ssh -i C:\Users\ASUS\.ssh\contest_ed25519 root@82.22.3.8 "bash -s" < ops\audit.sh
```

Прочитать вывод, согласовать что чистить / что оставлять.

### 3. Базовая настройка системы

```bash
# на сервере
timedatectl set-timezone Europe/Moscow
apt update
apt install -y ca-certificates curl gnupg ufw nginx certbot python3-certbot-nginx jq
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

### 4. Установка Docker

```bash
# на сервере (если ещё нет)
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker run --rm hello-world
```

### 5. Перенос проекта

С локальной машины (Windows). Выбери один вариант.

**Вариант A — rsync (если установлен через Git for Windows / WSL):**
```bash
rsync -av --delete \
  --exclude='.venv' --exclude='__pycache__' --exclude='.env' \
  --exclude='node_modules' --exclude='dist' --exclude='.git' \
  -e "ssh -i /c/Users/ASUS/.ssh/contest_ed25519" \
  /c/Users/ASUS/contest-new/ root@82.22.3.8:/opt/contest/
```

**Вариант B — scp (всегда работает):**
```powershell
ssh -i C:\Users\ASUS\.ssh\contest_ed25519 root@82.22.3.8 "mkdir -p /opt/contest"
scp -i C:\Users\ASUS\.ssh\contest_ed25519 -r C:\Users\ASUS\contest-new\* root@82.22.3.8:/opt/contest/
```

### 6. .env на сервере

```bash
# на сервере
cd /opt/contest
cp .env.example .env
# Сгенерировать пароль БД
sed -i "s|POSTGRES_PASSWORD=changeme_please|POSTGRES_PASSWORD=$(openssl rand -hex 24)|" .env
# Поправить MINIAPP_URL
sed -i "s|MINIAPP_URL=https://example.com/miniapp|MINIAPP_URL=https://rtbkonkurs.ru/miniapp|" .env
# Вписать BOT_TOKEN вручную (НЕ в чат!)
nano .env
chmod 600 .env
```

### 7. Поднять Postgres + Redis и накатить миграции

```bash
cd /opt/contest
docker compose up -d postgres redis
sleep 5
docker compose ps                  # проверить healthy
docker compose build bot           # собрать образ backend
docker compose run --rm bot alembic upgrade head
docker compose exec postgres psql -U contest -c "\dt"
```

### 8. Smoke-тест Telegram токена

```bash
cd /opt/contest
set -a && . ./.env && set +a
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe" | jq
```

Должно вернуть `"ok": true` и имя бота.

### 9. nginx + Let's Encrypt

```bash
# на сервере
cp /opt/contest/ops/nginx.conf.example /etc/nginx/sites-available/contest
ln -sf /etc/nginx/sites-available/contest /etc/nginx/sites-enabled/contest
nginx -t && systemctl reload nginx
certbot --nginx -d rtbkonkurs.ru \
    --non-interactive --agree-tos -m rostabakrostabak@gmail.com --redirect
curl -I https://rtbkonkurs.ru/miniapp/      # 404 без cert error — OK
```

### 10. Закрыть SSH парольный вход

**Только после того как новый ключ работает!**
```bash
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl reload sshd
```

## Регулярный деплой (после правок кода)

С локальной машины:
```bash
rsync -av --delete --exclude='.venv' --exclude='__pycache__' --exclude='.env' \
  --exclude='node_modules' --exclude='dist' --exclude='.git' \
  -e "ssh -i /c/Users/ASUS/.ssh/contest_ed25519" \
  /c/Users/ASUS/contest-new/ root@82.22.3.8:/opt/contest/
```

На сервере:
```bash
cd /opt/contest
docker compose build bot api scheduler
docker compose up -d
docker compose run --rm bot alembic upgrade head   # если есть новые миграции
docker compose logs -f --tail=100 bot
```

## Полезные команды отладки

```bash
docker compose logs -f bot                    # логи бота
docker compose logs -f api                    # логи API
docker compose exec postgres psql -U contest  # консоль БД
docker compose exec redis redis-cli           # консоль Redis
journalctl -u nginx -n 50                     # логи nginx
certbot renew --dry-run                       # проверка авто-обновления сертификата
```
