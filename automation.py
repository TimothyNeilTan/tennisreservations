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
            logger.info(f"Getting available times for {court_name} on {date_str}")
            
            with sync_playwright() as playwright:
                # Launch browser with stealth mode to avoid detection
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
                page = context.new_page()
                
                # Apply stealth mode
                stealth_sync(page)
                
                # Go to SF Rec & Park page
                logger.debug("Navigating to SF Rec & Park page")
                page.goto("https://www.rec.us/organizations/san-francisco-rec-park")
                
                # Wait for page to load completely
                page.wait_for_load_state("networkidle")
                
                # Find and click on the specific court
                logger.debug(f"Looking for court: {court_name}")
                
                # Try different selectors to find the court
                court_found = False
                
                # First try exact match
                try:
                    exact_selector = f'//p[text()="{court_name}"]'
                    if page.is_visible(exact_selector, timeout=2000):
                        logger.debug(f"Found court with exact match: {court_name}")
                        page.click(exact_selector)
                        court_found = True
                except:
                    logger.debug(f"Court not found with exact match, trying contains")
                
                # Then try contains
                if not court_found:
                    try:
                        contains_selector = f'//p[contains(text(), "{court_name}")]'
                        if page.is_visible(contains_selector, timeout=2000):
                            logger.debug(f"Found court with contains: {court_name}")
                            page.click(contains_selector)
                            court_found = True
                    except:
                        logger.debug(f"Court not found with contains, trying parent element")
                
                # Try clicking on parent element
                if not court_found:
                    try:
                        parent_selector = f'//a[.//p[contains(text(), "{court_name}")]]'
                        if page.is_visible(parent_selector, timeout=2000):
                            logger.debug(f"Found court with parent selector: {court_name}")
                            page.click(parent_selector)
                            court_found = True
                    except:
                        logger.error(f"Could not find court: {court_name}")
                        return []
                
                # Wait for calendar to load
                logger.debug("Waiting for calendar to load")
                page.wait_for_selector('div[role="grid"]', state="visible", timeout=10000)
                
                # Click on the date
                logger.debug(f"Selecting date: {date_str}")
                
                # Try different date selector formats
                date_selectors = [
                    f'[data-date="{date_str}"]',
                    f'//div[@role="gridcell" and @data-date="{date_str}"]',
                    f'//div[@role="gridcell" and contains(@aria-label, "{date_str}")]',
                    f'//button[contains(@aria-label, "{date_str}")]'
                ]
                
                date_clicked = False
                for selector in date_selectors:
                    try:
                        if page.is_visible(selector, timeout=2000):
                            page.click(selector)
                            date_clicked = True
                            logger.debug(f"Successfully clicked date with selector: {selector}")
                            break
                    except:
                        continue
                
                if not date_clicked:
                    logger.error(f"Could not find date selector for: {date_str}")
                    
                    # Take a screenshot for debugging
                    page.screenshot(path="calendar_debug.png")
                    logger.debug("Saved calendar screenshot for debugging")
                    
                    # Try to navigate by clicking on the correct date in the calendar
                    try:
                        # Parse the date components
                        year, month, day = date_str.split('-')
                        day_int = int(day)
                        
                        # Try clicking on the day number directly
                        day_selector = f'//div[@role="gridcell"]//span[text()="{day_int}"]'
                        if page.is_visible(day_selector, timeout=2000):
                            page.click(day_selector)
                            date_clicked = True
                            logger.debug(f"Clicked on day number: {day_int}")
                    except:
                        logger.error("Failed to click on day number")
                
                # Wait for time slots to load
                logger.debug("Waiting for time slots to load")
                
                # Try different selectors for time slots
                time_slot_selectors = [
                    'button.time-slot',
                    'button[data-testid="time-slot"]',
                    'div.time-slot button',
                    'button[aria-label*="time slot"]',
                    'button:has-text("AM")',
                    'button:has-text("PM")'
                ]
                
                time_slots_visible = False
                for selector in time_slot_selectors:
                    try:
                        if page.is_visible(selector, timeout=2000):
                            time_slots_visible = True
                            logger.debug(f"Time slots visible with selector: {selector}")
                            break
                    except:
                        continue
                
                if not time_slots_visible:
                    logger.error("Time slots not visible")
                    page.screenshot(path="timeslots_debug.png")
                    logger.debug("Saved time slots screenshot for debugging")
                    return []
                
                # Get all available time slots
                logger.debug("Getting time slots content")
                time_slots_html = page.content()
                soup = BeautifulSoup(time_slots_html, "html.parser")
                
                # Try different selectors to find available time slots
                available_times = []
                
                # First try the standard selector
                time_slots = soup.select('button.time-slot:not([disabled])')
                if not time_slots:
                    # Try alternative selectors
                    time_slots = soup.select('button[data-testid="time-slot"]:not([disabled])')
                
                if not time_slots:
                    # Try to find any button with time text
                    time_slots = soup.select('button:not([disabled])')
                    # Filter to only include buttons that have time text (e.g., "9:00 AM")
                    time_slots = [slot for slot in time_slots if any(x in slot.get_text() for x in ["AM", "PM"])]
                
                logger.debug(f"Found {len(time_slots)} available time slots")
                
                # Extract the time text and convert to 24-hour format
                for slot in time_slots:
                    time_text = slot.get_text(strip=True)
                    logger.debug(f"Processing time slot: {time_text}")
                    
                    # Try to extract time in format like "9:00 AM"
                    if ":" in time_text and ("AM" in time_text or "PM" in time_text):
                        try:
                            # Split by space to handle formats like "9:00 AM - 10:00 AM"
                            # Just take the start time
                            time_parts = time_text.split(" - ")[0].strip()
                            
                            if "AM" in time_parts:
                                hour = time_parts.split(':')[0]
                                minute = time_parts.split(':')[1].split(' ')[0]
                                if len(hour) == 1:
                                    hour = f"0{hour}"
                                available_times.append(f"{hour}:{minute}")
                            elif "PM" in time_parts:
                                hour = int(time_parts.split(':')[0])
                                if hour < 12:
                                    hour += 12
                                minute = time_parts.split(':')[1].split(' ')[0]
                                available_times.append(f"{hour}:{minute}")
                        except Exception as e:
                            logger.error(f"Error parsing time text '{time_text}': {str(e)}")
                
                logger.info(f"Found {len(available_times)} available times: {available_times}")
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