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
import pytz
from datetime import datetime, timedelta

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
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(java_script_enabled = True)
            # stealth_sync(context)
            page = context.new_page()

            page.goto("https://www.rec.us/organizations/san-francisco-rec-park", wait_until="networkidle")
            page.wait_for_selector("a.no-underline.hover\\:underline", state="attached")
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            # with open("testfile.html", "w") as file:
            #     file.write(json.dumps(soup))

            court_elements = soup.select("a.no-underline.hover\\:underline p.text-\\[1rem\\].font-medium")

            # Extract text from each <p> element
            court_names = [elem.get_text(strip=True) for elem in court_elements]
            return court_names

    def book_court(self, court_name: str, booking_time, playtime_duration: int = 60) -> tuple[bool, str]:
        # Validate playtime duration
        if playtime_duration not in [60, 90]:
            logger.warning(f"Invalid playtime duration: {playtime_duration}, defaulting to 60")
            playtime_duration = 60
            
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
                
                # Select the duration if available
                try:
                    # Look for duration options
                    duration_selector = f'//button[contains(text(), "{playtime_duration} min")]'
                    duration_element = page.wait_for_selector(duration_selector, timeout=5000)
                    if duration_element:
                        duration_element.click()
                        logger.info(f"Selected {playtime_duration} minutes duration")
                    else:
                        logger.warning(f"Duration option for {playtime_duration} minutes not found, using default")
                except Exception as duration_error:
                    logger.warning(f"Could not select duration: {str(duration_error)}")

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

        logger.info(f"Getting available times for {court_name} on {date_str}")
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        target_day = target_date.strftime("%d")
        target_month = target_date.strftime("%B")  # Full month name
        target_year = target_date.strftime("%Y")
        
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(java_script_enabled = True)
            # stealth_sync(context)
            page = context.new_page()

            page.goto("https://www.rec.us/organizations/san-francisco-rec-park", wait_until="networkidle")
            page.wait_for_selector("a.no-underline.hover\\:underline", state="attached")

            # Find and click the button with the specified classes
            button_selector = 'button.rounded-2xl.border.border-gray-200.px-4.py-1.hover\\:border-black.bg-gray-200'
            try:
                button = page.wait_for_selector(button_selector, state="visible", timeout=5000)
                if button:
                    button.click()
                    print("Successfully clicked the button")
                else:
                    print("Button not found")
            except Exception as e:
                print(f"Error clicking button: {str(e)}")
                page.screenshot(path="button_error.png")
            
            # Find and click on day 15 in the calendar
            page.wait_for_selector('.rdp', state="visible")
    
    # Navigate to the correct month
            while True:
                # Get current month and year from the calendar
                current_month_element = page.locator('div[role="presentation"][id^="react-day-picker-"]')
                current_month_text = current_month_element.text_content()
                current_month, current_year = current_month_text.strip().split()
                
                print(f"Current month: {current_month} {current_year}")
                print(f"Target month: {target_month} {target_year}")
                
                # If we're at the correct month and year, break
                if current_month == target_month and current_year == target_year:
                    break
                    
                # Click next month button
                next_month_button = page.locator('button[name="next-month"]')
                next_month_button.click()
                # Wait for calendar to update
                page.wait_for_timeout(500)
            
            # Find and click on the target day
            try:
        # First try: Use the most specific selector for the active day in current month
                specific_selector = f'button[name="day"]:has-text("{target_day}"):not(.day-outside):not(.opacity-50)'
                page.locator(specific_selector).first.click()
            except Exception as e:
                print(f"Error with specific selector: {str(e)}")
                try:
                    # Second try: Get all day buttons with the target day text and filter out the one from previous/next month
                    all_day_buttons = page.locator(f'button[name="day"]:has-text("{target_day}")').all()
                    
                    # Debug info
                    print(f"Found {len(all_day_buttons)} buttons for day {target_day}")
                    
                    # Find the first button that doesn't have the day-outside class
                    current_month_button = None
                    for button in all_day_buttons:
                        # Check if this is NOT a day from outside the current month
                        class_attr = button.get_attribute("class")
                        if class_attr and "day-outside" not in class_attr and "opacity-50" not in class_attr:
                            current_month_button = button
                            break
                    
                    if current_month_button:
                        current_month_button.click()
                        print(f"Successfully clicked on day {target_day} from current month")
                    else:
                        # Last resort: just click the nth button
                        page.locator(f'button[name="day"]:has-text("{target_day}")').nth(1).click()
                        print(f"Clicked on day {target_day} using nth selector")
                except Exception as e2:
                    print(f"All attempts to click day {target_day} failed: {str(e2)}")
                    page.screenshot(path="day_selection_error.png")
            
            # Wait after clicking the day
            page.wait_for_timeout(5000)


            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            for container in soup.find_all('div', class_="rounded-xl border border-gray-200 p-3"):
                court_name_tag = container.find('p', class_="text-[1rem] font-medium text-black md:text-[1.125rem] mb-1")
                sport_tag = container.find('p', class_="text-[0.875rem] font-medium text-black md:text-[1rem] mb-2")
                
                if court_name_tag and sport_tag:
                    if court_name_tag.get_text(strip=True) == court_name and sport_tag.get_text(strip=True) == "Tennis":
                        print(f"Found container for {court_name} playing Tennis")
                        swiper_wrapper = None
                        for rel_div in container.select("div.relative"):
                            potential_swiper = rel_div.find("div", class_="swiper-wrapper")
                            if potential_swiper:
                                swiper_wrapper = potential_swiper
                                break
                                
                        if swiper_wrapper:
                            times_list = []
                            # Iterate over each swiper slide that has "swiper-slide" in its class
                            for slide in swiper_wrapper.find_all('div', class_=lambda c: c and 'swiper-slide' in c):
                                time_tag = slide.find('p', class_="text-[0.875rem] font-medium")
                                if time_tag:
                                    time_text = time_tag.get_text(strip=True)
                                    # Convert from "7:30 AM" format to "07:30" format (24-hour)
                                    if ":" in time_text:
                                        try:
                                            if "AM" in time_text:
                                                hour = time_text.split(':')[0]
                                                minute = time_text.split(':')[1].split(' ')[0]
                                                if len(hour) == 1:
                                                    hour = f"0{hour}"
                                                times_list.append(f"{hour}:{minute}")
                                            elif "PM" in time_text:
                                                hour = int(time_text.split(':')[0])
                                                if hour < 12:
                                                    hour += 12
                                                minute = time_text.split(':')[1].split(' ')[0]
                                                times_list.append(f"{hour}:{minute}")
                                            else:
                                                # If no AM/PM indicator, just add the raw time
                                                times_list.append(time_text)
                                        except Exception as e:
                                            print(f"Error parsing time '{time_text}': {str(e)}")
                                            # Add the raw time as fallback
                                            times_list.append(time_text)
                            print("Extracted times:", times_list)
                            return times_list
                        else:
                            print("Swiper wrapper not found in this container.")

if __name__ == "__main__":
    # Configure logging to show debug messages
    logging.basicConfig(level=logging.DEBUG, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Test credentials - replace with your actual credentials
    email = "neil81688@gmail.com"
    password = "123455"
    
    # Initialize TennisBooker
    print("Initializing TennisBooker...")
    tennis_booker = TennisBooker(email, password)

    # Get available courts
    print("\nGetting available courts...")
    courts = tennis_booker.get_available_courts()
    print(f"Found {len(courts)} courts: {courts}")
    
    # Test court and date
    test_court = "Alice Marble Tennis Courts"
    
    # Get tomorrow's date
    sf_timezone = pytz.timezone("America/Los_Angeles")
    now = datetime.now(sf_timezone)
    tomorrow = now + timedelta(days=1)
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')
    
    print(f"\nTesting get_available_times() for {test_court} on {tomorrow_str}...")
    
    try:
        # Get available times
        times = tennis_booker.get_available_times(test_court, tomorrow_str)
        
        if times:
            print(f"SUCCESS! Found {len(times)} available times:")
            for time in times:
                print(f"  - {time}")
        else:
            print("No available times found. This could be because:")
            print("  - The court is fully booked for tomorrow")
            print("  - There was an issue with the scraping process")
            print("  - The website structure may have changed")
    except Exception as e:
        print(f"ERROR: Failed to get available times: {str(e)}")
        import traceback
        traceback.print_exc()