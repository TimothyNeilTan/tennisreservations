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
            logger.debug(f"Starting court scraping from {url}")

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(java_script_enabled = True)
                page = context.new_page()

                logger.debug("Navigating to page...")
                page.goto(url)
                
                logger.debug("Waiting for court elements to load...")
                page.wait_for_selector("a.no-underline.hover\\:underline", state="attached")
                
                logger.debug("Getting page content...")
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                logger.debug("Searching for court elements...")
                court_elements = soup.select("a.no-underline.hover\\:underline p.text-\\[1rem\\].font-medium")
                
                # Log the raw elements found
                logger.debug(f"Found {len(court_elements)} court elements")
                for elem in court_elements:
                    logger.debug(f"Found court element: {elem.get_text(strip=True)}")

                # Extract text from each <p> element
                court_names = [elem.get_text(strip=True) for elem in court_elements]
                
                logger.debug(f"Final court list: {court_names}")
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
    
    def get_available_times(self, court_name: str, date_str: str) -> List[str]:
        """
        Get available time slots for a specific court and date.
        
        Args:
            court_name: Name of the court
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            List of available time slots in HH:MM format (24-hour)
        """
        try:
            with sync_playwright() as playwright:
                # Launch browser
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()

                # Go to SF Rec & Park page (no login needed to view available times)
                page.goto("https://www.rec.us/organizations/san-francisco-rec-park")
                
                # Find and click on the specific court
                court_selector = f'//p[contains(text(), "{court_name}")]'
                page.wait_for_selector(court_selector, state="visible")
                page.click(court_selector)

                # Wait for calendar to load
                page.wait_for_selector('.calendar-day', state="visible")

                # Click on the date
                date_selector = f'[data-date="{date_str}"]'
                page.wait_for_selector(date_selector)
                page.click(date_selector)

                # Wait for time slots to load
                page.wait_for_selector('.time-slot', state="visible", timeout=5000)
                
                # Get all available time slots
                time_slots_html = page.content()
                soup = BeautifulSoup(time_slots_html, "html.parser")
                
                # Find all time slot buttons that are not disabled
                time_slots = soup.select('button.time-slot:not([disabled])')
                
                # Extract the time text and convert to 24-hour format
                available_times = []
                for slot in time_slots:
                    time_text = slot.get_text(strip=True)
                    # Convert from "9:00 AM" format to "09:00" format
                    if "AM" in time_text:
                        hour = time_text.split(':')[0]
                        minute = time_text.split(':')[1].split(' ')[0]
                        if len(hour) == 1:
                            hour = f"0{hour}"
                        available_times.append(f"{hour}:{minute}")
                    elif "PM" in time_text:
                        hour = int(time_text.split(':')[0])
                        if hour < 12:
                            hour += 12
                        minute = time_text.split(':')[1].split(' ')[0]
                        available_times.append(f"{hour}:{minute}")
                
                return available_times

        except Exception as e:
            error_msg = f"Error getting available times: {str(e)}"
            logger.error(error_msg)
            return []

if __name__ == "__main__":
    email = "neil81688@gmail.com"
    password = "123455"
    tennis_booker = TennisBooker(email, password)
    print(tennis_booker.get_available_courts())