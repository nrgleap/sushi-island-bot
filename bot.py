import os
import time
import threading
import requests

BOT_TOKEN = os.environ["TG_BOT_TOKEN"]
CHAT_ID = os.environ["TG_CHAT_ID"]
GLOVO_URL = "https://glovoapp.com/uk/ua/dnipro/stores/sushi-island-dnp"
CHECK_INTERVAL = 900  # 15 minutes

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

CLOSED_TEXT = "\u0422\u0438\u043c\u0447\u0430\u0441\u043e\u0432\u043e \u043d\u0435 \u043f\u0440\u0430\u0446\u044e\u0454"
OPEN_MSG = (
    "\U0001F363 Sushi Island \u0432\u0456\u0434\u043a\u0440\u0438\u0442\u043e! "
    "\u041c\u043e\u0436\u043d\u0430 \u0437\u0430\u043c\u043e\u0432\u043b\u044f\u0442\u0438:\n"
    "https://glovoapp.com/uk/ua/dnipro/stores/sushi-island-dnp"
)


def is_store_open() -> bool:
    resp = requests.get(GLOVO_URL, headers=HEADERS, timeout=15)
    return CLOSED_TEXT not in resp.text


def send_telegram(chat_id: str, text: str):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )


def monitor_loop():
    print("Monitor started.")
    was_open = None
    while True:
        try:
            open_now = is_store_open()
            status = "OPEN" if open_now else "CLOSED"
            print(f"[{time.strftime('%H:%M:%S')}] Store is {status}")
            if open_now and was_open is False:
                send_telegram(CHAT_ID, OPEN_MSG)
            was_open = open_now
        except Exception as e:
            print(f"[MONITOR ERROR] {e}")
        time.sleep(CHECK_INTERVAL)


def command_loop():
    print("Command handler started.")
    offset = 0
    while True:
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=35,
            )
            for update in resp.json().get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "").strip()
                chat_id = str(msg.get("chat", {}).get("id", ""))
                if text == "/check" and chat_id:
                    try:
                        open_now = is_store_open()
                        if open_now:
                            reply = (
                                "\u2705 Sushi Island \u0437\u0430\u0440\u0430\u0437 "
                                "\u0412\u0406\u0414\u041a\u0420\u0418\u0422\u041e! "
                                "\u041c\u043e\u0436\u043d\u0430 \u0437\u0430\u043c\u043e\u0432\u043b\u044f\u0442\u0438:\n"
                                "https://glovoapp.com/uk/ua/dnipro/stores/sushi-island-dnp"
                            )
                        else:
                            reply = (
                                "\u274c Sushi Island \u0437\u0430\u0440\u0430\u0437 "
                                "\u0417\u0410\u041a\u0420\u0418\u0422\u041e "
                                "(\u0422\u0438\u043c\u0447\u0430\u0441\u043e\u0432\u043e "
                                "\u043d\u0435 \u043f\u0440\u0430\u0446\u044e\u0454)"
                            )
                        send_telegram(chat_id, reply)
                    except Exception as e:
                        send_telegram(chat_id, f"Error: {e}")
        except Exception as e:
            print(f"[CMD ERROR] {e}")
            time.sleep(5)


def main():
    print("Bot started. Monitoring Sushi Island...")
    t = threading.Thread(target=command_loop, daemon=True)
    t.start()
    monitor_loop()


if __name__ == "__main__":
    main()
