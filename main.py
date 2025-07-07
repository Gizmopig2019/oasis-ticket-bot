import os
import sys
import requests
from bs4 import BeautifulSoup
import time
import urllib.parse
from urllib.parse import urlparse, urlunparse

# --- LOAD TOKENS FROM ENVIRONMENT VARIABLES ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID_ENV = os.getenv("CHAT_ID")
SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY")

print(f"BOT_TOKEN: {'SET' if BOT_TOKEN else 'NOT SET'}")
print(f"CHAT_ID: {CHAT_ID_ENV if CHAT_ID_ENV else 'NOT SET'}")
print(f"SCRAPINGBEE_API_KEY: {'SET' if SCRAPINGBEE_API_KEY else 'NOT SET'}")

if not BOT_TOKEN or not CHAT_ID_ENV or not SCRAPINGBEE_API_KEY:
    print("ERROR: Missing environment variables. Exiting.")
    sys.exit(1)

try:
    CHAT_ID = int(CHAT_ID_ENV)
except ValueError:
    print("ERROR: CHAT_ID must be an integer. Exiting.")
    sys.exit(1)

TWICKETS_URLS = [
    "https://www.twickets.live/en/event/1828748649929117696#sort=FirstListed&typeFilter=Any&qFilter=All",
    "https://www.twickets.live/en/event/1828748567179698176#sort=FirstListed&typeFilter=Any&qFilter=All",
    "https://www.twickets.live/en/event/1828444850157002752#sort=FirstListed&typeFilter=Any&qFilter=All",
]

CHECK_INTERVAL = 300  # seconds

def send_telegram_message(price_text, url=None):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    if url:
        # Escape special chars for MarkdownV2
        def escape_md(text):
            escape_chars = r"\_*[]()~`>#+-=|{}.!"
            for ch in escape_chars:
                text = text.replace(ch, "\\" + ch)
            return text

        safe_price = escape_md(price_text)
        safe_url = escape_md(url)
        message = f"🎟️ *Ticket found for:* {safe_price}\n[Click here to view tickets]({safe_url})"
        data = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "MarkdownV2"
        }
    else:
        data = {"chat_id": CHAT_ID, "text": price_text}

    try:
        response = requests.post(api_url, data=data)
        if response.status_code != 200:
            print(f"Failed to send message: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def clean_url(url):
    parsed = urlparse(url)
    cleaned = parsed._replace(fragment="", query="")
    return urlunparse(cleaned)

def check_twickets_url(url, retries=3):
    print(f"Checking tickets at: {url}")
    cleaned_url = clean_url(url)
    encoded_url = urllib.parse.quote_plus(cleaned_url)

    api_url = (
        f"https://app.scrapingbee.com/api/v1/"
        f"?api_key={SCRAPINGBEE_API_KEY}"
        f"&url={encoded_url}"
        f"&render_js=true"
    )

    for attempt in range(retries):
        try:
            response = requests.get(api_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            prices = soup.find_all("span", class_="TicketCard__price___3Oxo2")

            for price_tag in prices:
                price_text = price_tag.get_text(strip=True)
                if price_text.startswith("£"):
                    price_num = int(price_text.replace("£", "").replace(",", ""))
                    if price_num <= 250:
                        send_telegram_message(price_text, url=cleaned_url)
                        print(f"Sent alert: Ticket for {price_text} at {cleaned_url}")
                        return True

            print("No tickets under £250 found at this URL.")
            return False

        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 500 and attempt < retries - 1:
                print(f"500 error, retrying ({attempt + 1}/{retries})...")
                time.sleep(10)
            else:
                print(f"HTTP error: {http_err}")
                return False
        except Exception as e:
            print(f"General error checking Twickets: {e}")
            return False

if __name__ == "__main__":
    send_telegram_message("✅ Twickets bot is now running and checking every 5 minutes!")

    while True:
        any_found = False
        for url in TWICKETS_URLS:
            if check_twickets_url(url):
                any_found = True

        if not any_found:
            print("No tickets under £250 found at any monitored URLs.")

        time.sleep(CHECK_INTERVAL)
