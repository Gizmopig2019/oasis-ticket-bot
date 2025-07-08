import requests
import os
import time
import urllib.parse
from datetime import datetime, timezone
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY")

bot = Bot(token=BOT_TOKEN)

# List of Twickets URLs to monitor
urls = [
    "https://www.twickets.live/en/event/1828748649929117696#sort=FirstListed&typeFilter=Any&qFilter=All",
    "https://www.twickets.live/en/event/1828748567179698176#sort=FirstListed&typeFilter=Any&qFilter=All",
    "https://www.twickets.live/en/event/1828444850157002752#sort=FirstListed&typeFilter=Any&qFilter=All"
]

last_alert_time = {}
last_no_ticket_time = datetime.now(timezone.utc)

def check_tickets(url):
    encoded_url = urllib.parse.quote(url, safe='')
    api_url = f"https://app.scrapingbee.com/api/v1/?api_key={SCRAPINGBEE_API_KEY}&url={encoded_url}"
    
    try:
        response = requests.get(api_url)
        if response.status_code == 401:
            print(f"[{datetime.now()}] ERROR: Unauthorized. Check your API key.")
            return False
        elif response.status_code >= 500:
            print(f"[{datetime.now()}] ERROR: Server error from ScrapingBee.")
            return False

        html = response.text.lower()
        if "£" in html and "sold" not in html:
            return True
    except Exception as e:
        print(f"[{datetime.now()}] ERROR: {e}")
    return False

def send_alert(message):
    bot.send_message(chat_id=CHAT_ID, text=message)

def monitor():
    global last_no_ticket_time

    while True:
        found = False
        for url in urls:
            if check_tickets(url):
                now = datetime.now(timezone.utc)
                if url not in last_alert_time or (now - last_alert_time[url]).seconds > 300:
                    send_alert(f"🎫 Tickets found! {url}")
                    last_alert_time[url] = now
                    found = True
            time.sleep(1)

        # Send hourly update if no tickets found
        now = datetime.now(timezone.utc)
        if not found and (now - last_no_ticket_time).seconds >= 3600:
            send_alert("🚫 No tickets under £250 found on any monitored URLs.")
            last_no_ticket_time = now

        time.sleep(300)  # wait 5 minutes

if __name__ == "__main__":
    print("🟢 Bot is running...")
    monitor()
