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

# --- TWICKETS EVENT URLS ---
TWICKETS_URLS = [
    "https://www.twickets.live/en/event/1828748649929117696#sort=FirstListed&typeFilter=Any&qFilter=All",
    "https://www.twickets.live/en/event/1828748567179698176#sort=FirstListed&typeFilter=Any&qFilter=All",
    "https://www.twickets.live/en/event/1828444850157002752#sort=FirstListed&typeFilter=Any&qFilter=All",
]

# --- CHECK INTERVAL IN SECONDS ---
CHECK_INTERVAL = 300  # 5 minutes

def send_telegram_message(text, markdown=False):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
    }
    if markdown:
        data["parse_mode"] = "MarkdownV2"
    try:
        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"Failed to send message: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def escape_md(text):
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    for ch in escape_chars:
        text = text.replace(ch, "\\" + ch)
    return text

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

            count = 0
            for price_tag in prices:
                price_text = price_tag.get_text(strip=True)
                if price_text.startswith("£"):
                    price_num = int(price_text.replace("£", "").replace(",", ""))
                    if price_num <= 250:
                        count += 1

            if count > 0:
                plural = "tickets" if count > 1 else "ticket"
                price_sample = prices[0].get_text(strip=True)
                message = (
                    f"🎟️ *{count}x {plural} found for {escape_md(price_sample)}!*\n"
                    f"[Click here to view tickets]({escape_md(cleaned_url)})"
                )
                send_telegram_message(message, markdown=True)
                print(f"Alert sent for {count}x ticket(s) at {cleaned_url}")
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

    last_hour = -1
    ticket_found_this_hour = False

    while True:
        now = datetime.utcnow()
        current_hour = now.hour
        current_minute = now.minute

        if current_hour != last_hour:
            ticket_found_this_hour = False
            last_hour = current_hour

        any_found = False
        for url in TWICKETS_URLS:
            if check_twickets_url(url):
                any_found = True
                ticket_found_this_hour = True

        if not any_found:
            print("No tickets under £250 found at any monitored URLs.")

        # Send message at the top of the hour if no tickets found
        if current_minute == 0 and not ticket_found_this_hour:
            send_telegram_message("❌ No tickets found, I'll keep searching.")
            print("Sent hourly status: No tickets found.")

        time.sleep(CHECK_INTERVAL)
