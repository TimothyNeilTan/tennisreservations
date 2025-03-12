from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from playwright_stealth import stealth_sync
from playwright.sync_api import sync_playwright
import requests
import logging
from typing import List
import time

logger = logging.getLogger(__name__)

class TennisBooker:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password

    def setup_driver(self):
        """Initialize and configure Chrome WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headfull")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_window_size(1280, 720)
        return driver

    def get_available_courts(self) -> List[str]:
        """Scrapes and returns a list of all available tennis courts."""
        try:
            url = "https://www.rec.us/organizations/san-francisco-rec-park"
            # response = requests.get(url)
            # html = response.content

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(java_script_enabled = True)
                # stealth_sync(context)
                page = context.new_page()

                page.goto(url)
                page.wait_for_selector("a.no-underline.hover\\:underline", state="attached")
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # with open("testfile.html", "w") as file:
                #     file.write(json.dumps(soup))

                court_elements = soup.select("a.no-underline.hover\\:underline p.text-\\[1rem\\].font-medium")

                # Extract text from each <p> element
                court_names = [elem.get_text(strip=True) for elem in court_elements]
                return court_names

        except Exception as e:
            logger.error(f"Error getting courts: {str(e)}")
            return []

    def book_court(self, court_name: str, booking_time) -> tuple[bool, str]:
        try:
            with sync_playwright() as playwright:
                # Launch browser
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()

                # Go to login page
                page.goto("https://www.rec.us/login")
                
                # Login
                page.fill('input[type="email"]', self.email)
                page.fill('input[type="password"]', self.password)
                page.click('button[type="submit"]')

                # Wait for login to complete
                page.wait_for_navigation()

                # Go to SF Rec & Park page
                page.goto("https://www.rec.us/organizations/san-francisco-rec-park")
                
                # Find and click on the specific court
                court_selector = f'//p[contains(text(), "{court_name}")]'
                page.wait_for_selector(court_selector, state="visible")
                page.click(court_selector)

                # Wait for calendar to load
                page.wait_for_selector('.calendar-day', state="visible")

                # Format the booking time for selection
                booking_date = booking_time.strftime("%Y-%m-%d")
                booking_hour = booking_time.strftime("%I:%M %p")

                # Click on the date
                date_selector = f'[data-date="{booking_date}"]'
                page.wait_for_selector(date_selector)
                page.click(date_selector)

                # Click on the time slot
                time_selector = f'//button[contains(text(), "{booking_hour}")]'
                page.wait_for_selector(time_selector)
                page.click(time_selector)

                # Click reserve button
                page.click('button:has-text("Reserve")')

                # Wait for confirmation and get success message
                success_message = page.wait_for_selector('.success-message', timeout=10000)
                
                if success_message:
                    return True, "Court booked successfully"
                else:
                    return False, "Booking confirmation not received"

        except Exception as e:
            error_msg = f"Booking failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
if __name__ == "__main__":
    email = "neil81688@gmail.com"
    password = "123455"
    tennis_booker = TennisBooker(email, password)
    print(tennis_booker.get_available_courts())