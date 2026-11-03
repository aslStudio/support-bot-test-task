"""Telegram long-polling interface for the policy-grounded demo assistant."""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from assistant import answer
from store import connect, load_policy


LOG = logging.getLogger(__name__)


class TelegramError(Exception):
    pass


def load_env_file(path: Path) -> None:
    """Read the simple KEY=VALUE format used by .env.example."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.strip() in {"TELEGRAM_BOT_TOKEN", "BOT_DB_PATH"}:
            value = value.strip().strip('"\'')
            os.environ.setdefault(key.strip(), value)


class TelegramAPI:
    def __init__(self, token: str):
        self.base_url = f"https://api.telegram.org/bot{token}/"

    def call(self, method: str, payload: dict) -> object:
        request = urllib.request.Request(
            self.base_url + method,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                data = json.load(response)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            # Do not log the request URL: Telegram includes the secret token in it.
            raise TelegramError(f"Telegram API request failed: {type(exc).__name__}") from None
        if not data.get("ok"):
            raise TelegramError(f"Telegram API {method} failed: {data.get('error_code', 'unknown error')}")
        return data["result"]


def run(token: str, db_path: str) -> None:
    api = TelegramAPI(token)
    policy = load_policy()
    connection = connect(db_path)
    bot = api.call("getMe", {})
    LOG.info("Started @%s", bot.get("username", "bot"))
    api.call(
        "setMyCommands",
        {"commands": [
            {"command": "start", "description": "Начать"},
            {"command": "help", "description": "Что умеет бот"},
            {"command": "data", "description": "Регламент и тестовая база"},
            {"command": "orders", "description": "Демо-заказы"},
            {"command": "order", "description": "Статус демо-заказа: /order 1001"},
        ]},
    )
    offset = None
    while True:
        try:
            payload = {
                "timeout": 20,
                "allowed_updates": ["message"],
            }
            if offset is not None:
                payload["offset"] = offset
            updates = api.call("getUpdates", payload)
            for update in updates:
                message = update.get("message", {})
                chat = message.get("chat", {})
                if message.get("text") and chat.get("type") == "private":
                    response = answer(message["text"], policy, connection)
                    api.call("sendMessage", {"chat_id": chat["id"], "text": response})
                offset = update["update_id"] + 1
        except TelegramError as exc:
            LOG.warning("%s; retrying in 3 seconds", exc)
            time.sleep(3)


def main() -> None:
    load_env_file(Path(__file__).resolve().parent / ".env")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token == "put_your_bot_token_here":
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env")
    db_path = os.getenv("BOT_DB_PATH", "demo.sqlite3")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        run(token, db_path)
    except KeyboardInterrupt:
        LOG.info("Stopped")


if __name__ == "__main__":
    main()
