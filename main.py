import os
import sys
import requests
from bs4 import BeautifulSoup
import time
import urllib.parse
from urllib.parse import urlparse, urlunparse
from datetime import datetime

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

CHECK_INTERVAL = 300  # 5 minutes

def send_telegram_message(text):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
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

            valid_prices = []
            for price_tag in prices:
                price_text = price_tag.get_text(strip=True)
                if price_text.startswith("£"):
                    price_num = int(price_text.replace("£", "").replace(",", ""))
                    if price_num <= 250:
                        valid_prices.append(price_text)

            if valid_prices:
                count = len(valid_prices)
                price_summary = ", ".join(valid_prices[:3])
                more_text = "..." if count > 3 else ""
                plural = "tickets" if count > 1 else "ticket"
                message = f"{count}x {plural} found on Twickets at prices: {price_summary}{more_text}\n{cleaned_url}"
                print(f"Found tickets: {message}")
                return message  # Return message instead of sending here, so caller controls sending

            print("No tickets under £250 found at this URL.")
            return None

        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 500 and attempt < retries - 1:
                print(f"500 error, retrying ({attempt + 1}/{retries})...")
                time.sleep(10)
            else:
                print(f"HTTP error: {http_err}")
                return None
        except Exception as e:
            print(f"General error checking Twickets: {e}")
            return None

if __name__ == "__main__":
    send_telegram_message("✅ Twickets bot is now running and checking every 5 minutes!")

    tickets_found_messages = []
    last_reported_hour = None

    while True:
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute

        # Check all URLs and gather messages if tickets found
        for url in TWICKETS_URLS:
            msg = check_twickets_url(url)
            if msg:
                tickets_found_messages.append(msg)

        # Send immediate alert for any new tickets found this round
        for message in tickets_found_messages:
            send_telegram_message(message)
        tickets_found_messages.clear()

        # At exactly minute 0 of any hour, send summary message
        if current_minute == 0 and last_reported_hour != current_hour:
            last_reported_hour = current_hour

            # If tickets were found in the previous hour, report them
            # Since we cleared after sending immediate alerts, here we just say no tickets
            send_telegram_message("No tickets found, I'll keep searching.")

        time.sleep(CHECK_INTERVAL)
