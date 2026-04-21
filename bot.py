import os
import time
import threading
import requests
from playwright.sync_api import sync_playwright

BOT_TOKEN = os.environ["TG_BOT_TOKEN"]
CHAT_ID = os.environ["TG_CHAT_ID"]
CHECK_INTERVAL = 900  # 15 minutes

GLOVO_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
GLOVO_CLOSED = "\u0422\u0438\u043c\u0447\u0430\u0441\u043e\u0432\u043e \u043d\u0435 \u043f\u0440\u0430\u0446\u044e\u0454"
BOLT_OPEN = "\u0417\u0430\u0440\u0430\u0437 \u0432\u0456\u0434\u0447\u0438\u043d\u0435\u043d\u043e"

STORES = [
    {
        "id": "glovo_dnipro",
        "name": "\u0414\u043d\u0456\u043f\u0440\u043e",
        "platform": "Glovo",
        "url": "https://glovoapp.com/uk/ua/dnipro/stores/sushi-island-dnp",
    },
    {
        "id": "glovo_zpr",
        "name": "\u0417\u0430\u043f\u043e\u0440\u0456\u0436\u0436\u044f",
        "platform": "Glovo",
        "url": "https://glovoapp.com/uk/ua/zaporizhzhia/stores/sushi-island-zpr-1hh7e",
    },
    {
        "id": "bolt_dnipro",
        "name": "\u0414\u043d\u0456\u043f\u0440\u043e",
        "platform": "Bolt Food",
        "url": "https://food.bolt.eu/uk-ua/499-dnipro/p/159274-sushi-island/info/",
    },
    {
        "id": "bolt_zpr_sobornyi",
        "name": "\u0417\u0430\u043f\u043e\u0440\u0456\u0436\u0436\u044f (\u0421\u043e\u0431\u043e\u0440\u043d\u0438\u0439 91)",
        "platform": "Bolt Food",
        "url": "https://food.bolt.eu/uk-ua/500-zaporizhia/p/159274-sushi-island/info/",
    },
    {
        "id": "bolt_zpr_yevropeyska",
        "name": "\u0417\u0430\u043f\u043e\u0440\u0456\u0436\u0436\u044f (\u0404\u0432\u0440\u043e\u043f\u0435\u0439\u0441\u044c\u043a\u0430 4)",
        "platform": "Bolt Food",
        "url": "https://food.bolt.eu/uk-ua/500-zaporizhia/p/143786/info/",
    },
]


def send_telegram(chat_id: str, text: str):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )


def check_glovo(url: str) -> bool:
    resp = requests.get(url, headers=GLOVO_HEADERS, timeout=15)
    return GLOVO_CLOSED not in resp.text


def check_bolt(url: str, browser) -> bool:
    ctx = browser.new_context(
        locale="uk-UA",
        extra_http_headers={"Accept-Language": "uk-UA,uk;q=0.9"},
    )
    page = ctx.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        try:
            page.wait_for_function(
                "(document.body.innerText.includes('\u0432\u0456\u0434\u0447\u0438\u043d\u0435\u043d\u043e') || "
                "document.body.innerText.includes('\u0437\u0430\u0447\u0438\u043d\u0435\u043d\u043e'))",
                timeout=8000,
            )
        except Exception:
            pass
        text = page.inner_text("body")
        snippet = text[:300].replace("\n", " ")
        print(f"[BOLT DEBUG] {url[-30:]} | {snippet}", flush=True)
        return "\u0432\u0456\u0434\u0447\u0438\u043d\u0435\u043d\u043e" in text.lower()
    finally:
        page.close()
        ctx.close()


def check_store(store: dict, browser) -> bool:
    if store["platform"] == "Glovo":
        return check_glovo(store["url"])
    else:
        return check_bolt(store["url"], browser)


def build_status_message(statuses: dict) -> str:
    emoji = {True: "\U0001F7E2", False: "\U0001F534", None: "\u26AA"}
    label = {True: "\u0432\u0456\u0434\u043a\u0440\u0438\u0442\u043e", False: "\u0437\u0430\u043a\u0440\u0438\u0442\u043e", None: "?"}

    lines = ["\U0001F4CA \u0421\u0442\u0430\u0442\u0443\u0441 \u0432\u0441\u0456\u0445 \u0442\u043e\u0447\u043e\u043a:\n"]
    current_platform = None
    for store in STORES:
        if store["platform"] != current_platform:
            current_platform = store["platform"]
            lines.append(f"\n{store['platform']}:")
        st = statuses.get(store["id"])
        lines.append(f"  {emoji[st]} {store['name']} \u2014 {label[st]}")

    return "\n".join(lines)


def monitor_loop(was_open: dict):
    print("Monitor started.")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
            while True:
                for store in STORES:
                    try:
                        open_now = check_store(store, browser)
                        status = "OPEN" if open_now else "CLOSED"
                        print(f"[{time.strftime('%H:%M:%S')}] {store['platform']} {store['name']}: {status}")
                        if open_now and was_open[store["id"]] is False:
                            send_telegram(
                                CHAT_ID,
                                f"\U0001F7E2 Sushi Island \u0432\u0456\u0434\u043a\u0440\u0438\u043b\u043e\u0441\u044f!\n\n"
                                f"\U0001F4F1 {store['platform']}\n"
                                f"\U0001F4CD {store['name']}\n"
                                f"\U0001F517 {store['url']}"
                            )
                        was_open[store["id"]] = open_now
                    except Exception as e:
                        print(f"[ERROR] {store['id']}: {e}")
                time.sleep(CHECK_INTERVAL)
        finally:
            browser.close()


def command_loop(was_open: dict):
    print("Command handler started.")
    offset = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        try:
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
                            statuses = {}
                            for store in STORES:
                                try:
                                    statuses[store["id"]] = check_store(store, browser)
                                except Exception:
                                    statuses[store["id"]] = None
                            send_telegram(chat_id, build_status_message(statuses))
                        elif text == "/screenshot" and chat_id:
                            bolt_url = STORES[2]["url"]
                            ctx = browser.new_context(locale="uk-UA")
                            pg = ctx.new_page()
                            try:
                                pg.goto(bolt_url, wait_until="networkidle", timeout=30000)
                                pg.wait_for_timeout(3000)
                                shot = pg.screenshot(full_page=False)
                                requests.post(
                                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                                    data={"chat_id": chat_id},
                                    files={"photo": ("screen.png", shot, "image/png")},
                                    timeout=15,
                                )
                            finally:
                                pg.close()
                                ctx.close()
                except Exception as e:
                    print(f"[CMD ERROR] {e}")
                    time.sleep(5)
        finally:
            browser.close()


def main():
    print("Bot started. Monitoring Sushi Island (all locations)...")
    was_open = {store["id"]: None for store in STORES}

    t = threading.Thread(target=command_loop, args=(was_open,), daemon=True)
    t.start()

    monitor_loop(was_open)


if __name__ == "__main__":
    main()
