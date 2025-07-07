import requests
from bs4 import BeautifulSoup
import time
from keep_alive import keep_alive
import urllib.parse
from urllib.parse import urlparse, urlunparse

# --- YOUR TELEGRAM BOT TOKEN AND CHAT ID ---
BOT_TOKEN = "8102701244:AAEvDMpJ_OqWwtJMBRE-zjksT3r7vL3V1fw"
CHAT_ID = 5144724524

# --- YOUR SCRAPINGBEE API KEY ---
SCRAPINGBEE_API_KEY = "QY4CXL58X3ICVSJFHWUPXURWDZJN6I9Y06Y6X17YTY0HGMYOFKMJQ8REPFAXSHUPS6M7HACEHEKKTZ7F"  # 🔁 Replace this with your real key

# --- TWICKETS EVENT URLS ---
TWICKETS_URLS = [
    "https://www.twickets.live/en/event/1828748649929117696#sort=FirstListed&typeFilter=Any&qFilter=All",
    "https://www.twickets.live/en/event/1828748567179698176#sort=FirstListed&typeFilter=Any&qFilter=All",
    "https://www.twickets.live/en/event/1828444850157002752#sort=FirstListed&typeFilter=Any&qFilter=All",
]

# --- CHECK INTERVAL IN SECONDS ---
CHECK_INTERVAL = 300  # 5 minutes

# --- SEND A MESSAGE TO TELEGRAM ---
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"Failed to send message: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

# --- REMOVE FRAGMENTS FROM URL (e.g. #sort) ---
def clean_url(url):
    parsed = urlparse(url)
    cleaned = parsed._replace(fragment="", query="")  # strips # and ? queries
    return urlunparse(cleaned)

# --- CHECK ONE URL FOR TICKETS UNDER £250 ---
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
                        send_telegram_message(
                            f"🎟️ Ticket found for £{price_num}!\n{cleaned_url}"
                        )
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

# --- MAIN LOOP ---
if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ Twickets bot is now running and checking every 5 minutes!")

    while True:
        any_found = False
        for url in TWICKETS_URLS:
            if check_twickets_url(url):
                any_found = True

        if not any_found:
            print("No tickets under £250 found at any monitored URLs.")

        time.sleep(CHECK_INTERVAL)
