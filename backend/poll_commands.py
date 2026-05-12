#!/usr/bin/env python3
"""Проверяет новые сообщения от админа и сохраняет в файл."""
import os
import json
import urllib.request
import time

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_TG_ID", "0"))
STATE_FILE = "/opt/contest/commands/last_update.txt"
QUEUE_FILE = "/opt/contest/commands/queue.txt"

def get_updates():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
            return data.get("result", [])
    except Exception as e:
        print(f"Error: {e}")
        return []

def main():
    # Читаем последний обработанный update_id
    last_id = 0
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            last_id = int(f.read().strip())

    updates = get_updates()
    new_messages = []

    for update in updates:
        update_id = update.get("update_id", 0)
        if update_id <= last_id:
            continue

        msg = update.get("message", {})
        chat = msg.get("chat", {})
        text = msg.get("text", "")
        from_user = msg.get("from", {})

        # Только сообщения от админа
        if from_user.get("id") == ADMIN_ID and text:
            new_messages.append({
                "id": update_id,
                "text": text,
                "date": msg.get("date"),
            })
            # Сохраняем самый большой update_id
            with open(STATE_FILE, "w") as f:
                f.write(str(update_id))

    # Добавляем новые сообщения в очередь
    if new_messages:
        with open(QUEUE_FILE, "a") as f:
            for m in new_messages:
                f.write(json.dumps(m) + "\n")
        print(f"New messages: {len(new_messages)}")

if __name__ == "__main__":
    main()
