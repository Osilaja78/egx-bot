from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests
import time

# Telegram Bot Credentials
BOT_TOKEN = "8128317803:AAFUKQid9GS95nGzHYYd0fPLB4y_sJm5GnQ"
CHANNEL_ID = "1209251779"  # Use @username if public

# Blogabet Account Details
BLOGABET_URL = "https://egxfutbol.blogabet.com/"  # Change to actual profile URL

print("Running setup.....")
# Selenium setup
options = Options()
options.add_argument("--headless")  # Run in headless mode
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
print("Installing chrome driver manager...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Store last posted bet time
print("Before setting latest bet time...")
last_bet_time = None


def get_latest_bet_time():
    """Scrape Blogabet with Selenium to get the latest bet timestamp."""
    print("Scraping.....................................")
    driver.get(BLOGABET_URL)

    try:
        wait = WebDriverWait(driver, 30)
        
        # First wait for page readiness
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        
        # Then wait for feed list
        feed_list = wait.until(
            EC.visibility_of_element_located((By.ID, "feed-list"))
        )

        feed_pick_title = feed_list.find_element(By.CLASS_NAME, "feed-pick-title")
        
        # Get required information
        date_element = feed_list.find_element(By.CSS_SELECTOR, "small.bet-age.text-muted").text
        match = feed_pick_title.find_element(By.TAG_NAME, "a").text # Al Ain SCC - Al Rayyan SC
        pick = feed_pick_title.find_element(By.CSS_SELECTOR, "div.pick-line").text # Over 2.5 O/U (FT) (0:0) @ 2.085
        clean_pick = pick.split('(FT)')[0].strip()
        minute_stake = feed_pick_title.find_elements(By.TAG_NAME, "span")
        odds = minute_stake[0].text # 2.085
        minute = minute_stake[2].text # LIVE
        stake = minute_stake[1].text # 1
        result = minute_stake[4].text # 1-2

        return date_element, match, clean_pick, odds, minute, stake, result
        
    except TimeoutException as e:
        print("Debugging Info:")
        print(f"Current URL: {driver.current_url}")
        print(f"Page title: {driver.title}")
        print(f"Page source snippet: {driver.page_source[:1000]}...")
        driver.save_screenshot("debug_screenshot.png")
        raise



def send_to_telegram(message):
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

# Continuous loop to check for new bets
while True:
    latest_time, match, pick, odds, minute, stake, result = get_latest_bet_time()

    if latest_time and latest_time != last_bet_time:
        last_bet_time = latest_time  # Update last seen bet time
        message = f"""⚠ LIVE BET ⚠ \n⚽ Match: {match} \n🎯 Pick: {pick} \n⏳ Minute: {minute} \n💰 Odds: {odds} \n🚥 Stake: {stake} \n📊 Result: {result}"""
        send_to_telegram(message)

    time.sleep(30)  # Check every 30 seconds
