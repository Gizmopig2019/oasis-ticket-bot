import os
import sys
import requests
from bs4 import BeautifulSoup
import time
import urllib.parse
from urllib.parse import urlparse, urlunparse
from datetime import datetime, timezone

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

CHECK_INTERVAL = 300  # 5 minutes in seconds

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        response = requests.post(url, data=data)
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

    try:
        response = requests.get(api_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        prices = soup.find_all("span", class_="TicketCard__price___3Oxo2")

        # Count tickets under £250
        tickets_under_250 = []
        for price_tag in prices:
            price_text = price_tag.get_text(strip=True)
            if price_text.startswith("£"):
                price_num = int(price_text.replace("£", "").replace(",", ""))
                if price_num <= 250:
                    tickets_under_250.append(price_text)

        if tickets_under_250:
            count = len(tickets_under_250)
            first_price = tickets_under_250[0]
            message = f"{count}x ticket{'s' if count > 1 else ''} found at {first_price} on {cleaned_url}"
            send_telegram_message(message)
            print(f"Sent alert: {message}")
            return True

        print("No tickets under £250 found at this URL.")
        return False

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error: {http_err}")
        return False
    except Exception as e:
        print(f"General error checking Twickets: {e}")
        return False

if __name__ == "__main__":
    send_telegram_message("✅ Twickets bot is now running and checking every 5 minutes!")

    last_hour = -1
    ticket_found_this_hour = False

    while True:
        now = datetime.now(timezone.utc)
        current_hour = now.hour
        current_minute = now.minute

        if current_hour != last_hour:
            # Hour changed - reset flags and send no tickets found message if none found last hour
            if not ticket_found_this_hour and last_hour != -1:
                send_telegram_message("No tickets found in the last hour, I'll keep searching...")
                print("Hourly no tickets message sent.")
            ticket_found_this_hour = False
            last_hour = current_hour

        any_found = False
        for url in TWICKETS_URLS:
            if check_twickets_url(url):
                any_found = True

        if any_found:
            ticket_found_this_hour = True
        else:
            print("No tickets under £250 found at any monitored URLs.")

        time.sleep(CHECK_INTERVAL)
