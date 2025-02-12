import requests
from bs4 import BeautifulSoup
import time
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import os

app = FastAPI()
scheduler = BackgroundScheduler()

load_dotenv()
# Telegram Bot Credentials
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# Step 1: Define Headers
headers = {
    "authority": "egxfutbol.blogabet.com",
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "dnt": "1",
    "referer": "https://egxfutbol.blogabet.com/",
    "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36",
    "x-requested-with": "XMLHttpRequest"
}

# Step 2: Define Cookies (Modify these if needed)
cookies = {
    "_ga": "GA1.1.2044397025.1738259425",
    "cookiesDirective": "1",
    "_ga_Z05SGDYTHK": "GS1.1.1738880045.9.1.1738882904.56.0.1275113323"
}

# Step 3: Start a Session
session = requests.Session()
session.headers.update(headers)
session.cookies.update(cookies)

# Store last posted bet time
print("Before setting latest bet time...")
last_bet_time = "Wed, Feb 12th, 2025, 16:34"

def login():
    """Logs into the website and maintains a session"""
    loginurl = "https://egxfutbol.blogabet.com/cp/processLogin"

    payload = {
        "email": EMAIL,
        "password": PASSWORD,
        "remember-me": 1
    }

    print("🔑 Logging in to Blogabet...")

    # Perform login
    login_response = session.post(loginurl, data=payload)

    if login_response.status_code == 200 and "errorMessages" not in login_response.json():
        print("✅ Login successful!")
        return True
    else:
        print("❌ Login failed. Check credentials or website structure.")
        time.sleep(20)
        login()
        return False

def get_latest_bet_time():
    print("Getting latest bet time...")
    # Visit Homepage to Establish Session

    # Ensure we're logged in
    session_cookie = session.cookies.get("login_string")
    if not session_cookie:
        login()
        return None, None, None, None, None, None, None

    homepage_url = "https://egxfutbol.blogabet.com/"
    session.get(homepage_url)

    # Fetch Bet Data
    bet_data_url = "https://egxfutbol.blogabet.com/blog/dashboard"
    response = session.get(bet_data_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, features="html.parser")
        feed_title = soup.find("h2", class_="pick-feed-title").text

        if "Pending Picks" in feed_title:
            try:
                feed_pick = soup.find("ul", class_="pick-list")

                feed_pick_title = feed_pick.find("div", class_="feed-pick-title")

                date_element = soup.find("small", class_="bet-age").text
                match = feed_pick_title.find("a").text
                pick = feed_pick_title.find("div", class_="pick-line").text.split('@')[0].strip()
                odd = feed_pick_title.find("div", class_="pick-line").text.split('@')[1].strip()
                minute_stake = feed_pick_title.find_all("span", class_="label")
                minute = minute_stake[2].text
                stake = minute_stake[1].text
                results = feed_pick_title.find("div", class_="labels")

                for result in results:
                    try:
                        neww = result.find('i', class_='enable-tooltip')
                        score = result.text.strip()
                    except:
                        continue
                return date_element, match, pick, odd, minute, stake, ""
            except Exception as e:
                print(e)
                login()
                return None, None, None, None, None, None, None
        else:
            return None, None, None, None, None, None, None
    else:
        print(f"❌ Failed to fetch bets. Status code: {response.status_code}")
        login()
        return None, None, None, None, None, None, None


def send_telegram_message(message):
    """Send the extracted bet details to the Telegram channel."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHANNEL_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("Message sent successfully!")
    except Exception as e:
        print(f"Failed to send message: {str(e)}")


def check_and_post_bet():
    """Check for new bets and post to Telegram if new."""
    global last_bet_time

    latest_time, match, pick, odds, minute, stake, result = get_latest_bet_time()
    print(f"Last time ==> {last_bet_time}, Latest time: {latest_time}")

    if latest_time and latest_time != last_bet_time:
        last_bet_time = latest_time  # Update last seen bet time
        message = f"""⚠ LIVE BET ⚠ 

⚽ Match: {match} 
🎯 Pick: {pick} 
⏳ Minute: {minute} 
💰 Odds: {odds} 
🚥 Stake: {stake} 
📊 Result: {result}"""
        if os.getpid() == 16:
            send_telegram_message(message)
    # else:
        # if os.getpid() == 16:
            # send_telegram_message(f"No new post, checking,\nLatest time: {latest_time},\nLast time: {last_bet_time}")

@app.on_event("startup")
def startup_event():
    """Start the scheduler when FastAPI starts."""
    if not scheduler.running:
        scheduler.add_job(check_and_post_bet, "interval", seconds=30, id="bet_checker", replace_existing=True)
        scheduler.start()


@app.on_event("shutdown")
def shutdown_event():
    """Shutdown the scheduler when FastAPI stops."""
    scheduler.shutdown()

@app.get("/")
def home():
    return {"message": "FastAPI Bot Running with APScheduler"}

