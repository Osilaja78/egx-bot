from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from dotenv import load_dotenv
import requests
import time
import os

app = FastAPI()
scheduler = BackgroundScheduler()

load_dotenv()

# Telegram Bot Credentials
BOT_TOKEN = "8128317803:AAFUKQid9GS95nGzHYYd0fPLB4y_sJm5GnQ"
MY_CHANNEL_ID = "-1002395208097"  # Your personal channel
CHANNEL_ID = "-1002392958037"  # The main betting channel

# Blogabet Account Details
BLOGABET_URL = "https://egxfutbol.blogabet.com/"

print("Setting up Selenium...")

# Selenium Chrome Driver Setup
options = Options()
options.add_argument("--headless")  # Run in headless mode
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
# options.binary_location = "/usr/bin/google-chrome"

print("Installing Chrome Driver Manager...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Store last posted bet time
last_bet_time = None

def get_latest_bet_time():
    """Scrape Blogabet with Selenium to get the latest bet timestamp."""
    driver.get(BLOGABET_URL)

    try:
        wait = WebDriverWait(driver, 30)

        # Wait for page readiness
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

        # Wait for feed list
        feed_list = wait.until(EC.visibility_of_element_located((By.ID, "feed-list")))
        feed_pick_title = feed_list.find_element(By.CLASS_NAME, "feed-pick-title")

        # Extract bet details
        date_element = feed_list.find_element(By.CSS_SELECTOR, "small.bet-age.text-muted").text
        match = feed_pick_title.find_element(By.TAG_NAME, "a").text
        pick = feed_pick_title.find_element(By.CSS_SELECTOR, "div.pick-line").text.split('(FT)')[0].strip()
        minute_stake = feed_pick_title.find_elements(By.TAG_NAME, "span")
        odds = minute_stake[1].text
        minute = minute_stake[3].text
        stake = minute_stake[2].text
        result = minute_stake[5].text

        return date_element, match, pick, odds, minute, stake, result

    except TimeoutException:
        print("Error: Timed out waiting for elements.")
        return None, None, None, None, None, None, None

def send_telegram_message(message, chat_id):
    """Send a message to the specified Telegram chat."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send message: {e}")

def check_and_post_bet():
    """Check for new bets and post to Telegram if new."""
    global last_bet_time

    send_telegram_message("Bot is running...", MY_CHANNEL_ID)  # Status check message

    latest_time, match, pick, odds, minute, stake, result = get_latest_bet_time()

    if latest_time and latest_time != last_bet_time:
        last_bet_time = latest_time  # Update last seen bet time

        message = f"""⚠ LIVE BET ⚠ 

⚽ Match: {match} 
🎯 Pick: {pick} 
⏳ Minute: {minute} 
💰 Odds: {odds} 
🚥 Stake: {stake} 
📊 Result: {result}"""
        print("Sending to channel...")
        send_telegram_message(message, CHANNEL_ID)

@app.on_event("startup")
def startup_event():
    """Start the scheduler when FastAPI starts."""
    if not scheduler.running:
        scheduler.start()
        scheduler.add_job(check_and_post_bet, "interval", seconds=30)
        scheduler.add_job(send_my_telegram_message, "interval", minutes=60)

@app.on_event("shutdown")
def shutdown_event():
    """Shutdown the scheduler when FastAPI stops."""
    scheduler.shutdown()
    driver.quit()  # Close Selenium driver

@app.get("/")
def home():
    return {"message": "FastAPI Bot Running with APScheduler"}
