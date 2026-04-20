import os
import time
import requests

BOT_TOKEN = os.environ["TG_BOT_TOKEN"]
CHAT_ID = os.environ["TG_CHAT_ID"]
GLOVO_URL = "https://glovoapp.com/uk/ua/dnipro/stores/sushi-island-dnp"
CHECK_INTERVAL = 900  # 15 хвилин

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def is_store_open() -> bool:
    resp = requests.get(GLOVO_URL, headers=HEADERS, timeout=15)
    return "Тимчасово не працює" not in resp.text


def send_telegram(text: str):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text},
        timeout=10,
    )


def main():
    print("Bot started. Monitoring Sushi Island...")
    was_open = None
    while True:
        try:
            open_now = is_store_open()
            status = "OPEN" if open_now else "CLOSED"
            print(f"[{time.strftime('%H:%M:%S')}] Store is {status}")
            if open_now and was_open is False:
                send_telegram(
                    "🍣 Sushi Island відкрито! Можна замовляти:\n"
                    "https://glovoapp.com/uk/ua/dnipro/stores/sushi-island-dnp"
                )
            was_open = open_now
        except Exception as e:
            print(f"[ERROR] {e}")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
