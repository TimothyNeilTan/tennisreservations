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
    def __init__(self, email: str, password: str, user_id: str = None):
        self.email = email
        self.password = password
        self.user_id = user_id

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
        
        logger.info(f"Starting booking process for court: {court_name}, time: {booking_time}, duration: {playtime_duration}")
        
        # Format target date
        target_date = booking_time
        # Use str(day) to avoid leading zero (e.g., '8' instead of '08') for matching button text
        target_day = str(target_date.day)
        target_month = target_date.strftime("%B")
        target_year = target_date.strftime("%Y")
        
        # Extract time for direct matching - exactly like test.py does
        target_time_primary = target_date.strftime("%-I:%M")  # Format like "7:30" without leading zero
        target_time_alternate = None  # Could add an alternate time option if needed
        
        logger.info(f"Target date: {target_month} {target_day}, {target_year}, time: {target_time_primary}")
        
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(java_script_enabled=True)
            page = context.new_page()

            try:
                # Initial page load
                logger.debug("Loading initial page")
                page.goto("https://www.rec.us/organizations/san-francisco-rec-park", wait_until="networkidle")
                page.wait_for_selector("a.no-underline.hover\\:underline", state="attached", timeout=3000)
                
                # Click initial button
                logger.debug("Looking for initial booking button")
                button = page.wait_for_selector('button.rounded-2xl.border.border-gray-200.px-4.py-1.hover\\:border-black.bg-gray-200', 
                                             state="visible", timeout=3000)
                if button:
                    button.click()

                # Calendar navigation
                page.wait_for_selector('.rdp', state="visible", timeout=3000)
                
                logger.debug(f"Navigating to month: {target_month} {target_year}")
                while True:
                    current_month_element = page.locator('div[role="presentation"][id^="react-day-picker-"]')
                    current_month_text = current_month_element.text_content()
                    current_month, current_year = current_month_text.strip().split()
                    
                    if current_month == target_month and current_year == target_year:
                        break
                        
                    logger.debug("Clicking next month button")
                    next_month_button = page.locator('button[name="next-month"]')
                    next_month_button.click()
                    page.wait_for_timeout(200)

                # Click target day
                day_button = page.locator(f'button[name="day"]:has-text("{target_day}"):not(.day-outside):not(.opacity-50)').first
                day_button.click()
                page.wait_for_timeout(1000)

                # Find and click time slot
                target_time_clicked = False
                page.wait_for_selector('div.rounded-xl.border.border-gray-200.p-3', state="visible", timeout=3000)
                
                court_containers = page.query_selector_all('div.rounded-xl.border.border-gray-200.p-3')
                
                # Save HTML for debugging
                # page.screenshot(path="debug_court_listing.png")
                
                for container in court_containers:
                    court_name_elem = container.query_selector('p.text-\\[1rem\\].font-medium.text-black.md\\:text-\\[1\\.125rem\\].mb-1')
                    sport_elem = container.query_selector('p.text-\\[0\\.875rem\\].font-medium.text-black.md\\:text-\\[1rem\\].mb-2')
                    
                    if not court_name_elem or not sport_elem:
                        continue
                    
                    current_court = court_name_elem.text_content()
                    sport_type = sport_elem.text_content()
                    
                    # Check if this is our target court
                    if court_name in current_court and "Tennis" in sport_type:
                        
                        time_slots = container.query_selector_all('div.swiper-slide p.text-\\[0\\.875rem\\].font-medium')
                        available_times = [slot.text_content() for slot in time_slots]
                        
                        # Try to find and click our target time
                        for i, time_text in enumerate(available_times):
                            if target_time_primary in time_text:
                                swiper_slides = container.query_selector_all('div.swiper-slide')
                                if i < len(swiper_slides):
                                    logger.debug(f"Clicking time slot {i}")
                                    swiper_slides[i].click()
                                    target_time_clicked = True
                                    break
                        
                        # If we have an alternate time and primary wasn't found
                        if not target_time_clicked and target_time_alternate:
                            for i, time_text in enumerate(available_times):
                                if target_time_alternate in time_text:
                                    logger.debug(f"Found alternate time: {time_text}")
                                    swiper_slides = container.query_selector_all('div.swiper-slide')
                                    if i < len(swiper_slides):
                                        logger.debug(f"Clicking alternate time slot {i}")
                                        swiper_slides[i].click()
                                        target_time_clicked = True
                                        break
                        
                        break

                if not target_time_clicked:
                    return False, f"No matching time slot found for {target_time_primary}"

                # Book button
                book_button = page.wait_for_selector('button.bg-\\[\\#26E164\\]:has-text("Book")', state="visible", timeout=2000)
                if book_button:
                    book_button.click()
                    page.wait_for_timeout(1000)
                else:
                    return False, "Book button not found"
                
                # Login process
                login_button = page.wait_for_selector('button.font-bold.text-brand-neutral:has-text("Log In")', state="visible", timeout=2000)
                if login_button:
                    login_button.click()
                    page.wait_for_timeout(1000)
                else:
                    # page.screenshot(path="debug_no_login_button.png")
                    return False, "Login button not found"
                
                # Fill login form
                email_input = page.wait_for_selector('input#email', state="visible", timeout=2000)
                password_input = page.wait_for_selector('input#password', state="visible", timeout=2000)
                
                if email_input and password_input:
                    email_input.fill(self.email)
                    password_input.fill(self.password)
                    
                    # Submit login
                    submit_button = page.wait_for_selector('button[type="submit"]', state="visible", timeout=2000)
                    if submit_button:
                        submit_button.click()
                        page.wait_for_timeout(2000)
                    else:
                        logger.error("Submit button not found")
                        return False, "Submit button not found"
                else:
                    logger.error("Email or password input not found")
                    return False, "Email or password input not found"
                
                # Select participant
                try:
                    participant_selector = page.wait_for_selector('button[id^="headlessui-listbox-button"]', 
                                                              state="visible", 
                                                              timeout=5000)
                    
                    if participant_selector:
                        participant_selector.click()
                        page.wait_for_timeout(1000)  # Increased wait time after click
                        account_owner = page.wait_for_selector('div.flex.w-full.items-center:has(small:has-text("Account Owner"))', 
                                                            state="visible", 
                                                            timeout=3000)
                        if account_owner:
                            account_owner.click()
                            page.wait_for_timeout(1000)  # Increased wait time
                        else:
                            logger.error("Account Owner option not found")
                            try:
                                alt_account_owner = page.wait_for_selector('div.flex.items-center:has-text("Account Owner")', 
                                                                       state="visible", 
                                                                       timeout=2000)
                                if alt_account_owner:
                                    alt_account_owner.click()
                                    page.wait_for_timeout(1000)
                                else:
                                    return False, "Account Owner option not found (both selectors)"
                            except Exception as e:
                                logger.error(f"Alternative account owner selector failed: {str(e)}")
                                return False, "Account Owner option not found"
                    else:
                        logger.error("Participant selector not found even with increased timeout")
                        return False, "Participant selector not found"
                        
                except Exception as e:
                    logger.error(f"Error during participant selection: {str(e)}")
                
                # Click Book button again
                book_button = page.wait_for_selector('button.bg-\\[\\#26E164\\]:has-text("Book")', state="visible", timeout=2000)
                if book_button:
                    book_button.click()
                    page.wait_for_timeout(1000)
                else:
                    # page.screenshot(path="debug_no_second_book_button.png")
                    return False, "Second Book button not found"
                
                send_code_button = page.wait_for_selector('button[type="submit"]:has-text("Send Code")', 
                                                     state="visible", timeout=2000)
                if send_code_button:
                    send_code_button.click()
                    page.wait_for_timeout(1000)
                else:
                    logger.error("Send Code button not found")
                    return False, "Send Code button not found"
                
                # Wait for code input
                code_input = page.wait_for_selector('input#totp[name="totp"][type="number"]', 
                                               state="visible", timeout=5000)
                if code_input:
                    # Poll for code
                    max_attempts = 10
                    verification_code = None
                    
                    logger.debug(f"Polling for verification code, user_id: {self.user_id}")
                    for attempt in range(max_attempts):
                        try:
                            logger.debug(f"Code polling attempt {attempt+1}/{max_attempts}")
                            response = requests.get(f'http://localhost:8000/get_code?user_id={self.user_id}')
                            if response.status_code == 200:
                                data = response.json()
                                logger.debug(f"Code poll response: {data}")
                                if data.get('status') == 'available':
                                    verification_code = data.get('code')
                                    logger.debug(f"Verification code received: {verification_code}")
                                    break
                        except Exception as e:
                            logger.error(f"Error checking for code: {str(e)}")
                        
                        time.sleep(1)
                    
                    if verification_code:
                        logger.debug(f"Filling code input with: {verification_code}")
                        code_input.fill(verification_code)
                        
                        # Click Confirm button
                        logger.debug("Looking for Confirm button")
                        confirm_button = page.wait_for_selector('button[type="button"]:has-text("Confirm")', 
                                                           state="visible", timeout=2000)
                        if confirm_button:
                            logger.debug("Clicking Confirm button")
                            confirm_button.click()
                            page.wait_for_timeout(2000)
                            logger.info("Court booked successfully")
                            return True, "Court booked successfully"
                        else:
                            logger.error("Confirm button not found")
                            # page.screenshot(path="debug_no_confirm_button.png")
                            return False, "Confirm button not found"
                    else:
                        logger.error(f"No verification code received after {max_attempts} attempts")
                        return False, f"No verification code received after {max_attempts} attempts"
                else:
                    logger.error("Code input field not found")
                    return False, "Code input field not found"
                
            except Exception as e:
                error_msg = f"Booking failed with exception: {str(e)}"
                logger.error(error_msg)
                return False, error_msg
            finally:
                browser.close()

    def get_available_times(self, court_name: str, date_str: str) -> List[str]:
        """
        Get available time slots for a specific court and date.
        
        Args:
            court_name: Name of the court
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            List of available time slots in HH:MM format (24-hour)
        """

        logger.info(f"[TennisBooker.get_available_times] START for '{court_name}' on {date_str}")
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        # Use str(day) to avoid leading zero (e.g., '8' instead of '08')
        target_day = str(target_date.day) 
        target_month = target_date.strftime("%B")  # Full month name
        target_year = target_date.strftime("%Y")
        logger.debug(f"[TennisBooker.get_available_times] Target date parsed: Day={target_day}, Month={target_month}, Year={target_year}")

        with sync_playwright() as playwright:
            browser = None # Initialize browser variable
            try:
                logger.debug("[TennisBooker.get_available_times] Launching Playwright browser...")
                browser = playwright.chromium.launch()
                context = browser.new_context(java_script_enabled = True)
                page = context.new_page()
                logger.debug("[TennisBooker.get_available_times] Browser launched. Navigating to page...")

                page.goto("https://www.rec.us/organizations/san-francisco-rec-park", wait_until="networkidle")
                page.wait_for_selector("a.no-underline.hover\\:underline", state="attached")
                logger.debug("[TennisBooker.get_available_times] Initial page loaded.")

                # Find and click the button with the specified classes
                button_selector = 'button.rounded-2xl.border.border-gray-200.px-4.py-1.hover\\:border-black.bg-gray-200'
                try:
                    logger.debug("[TennisBooker.get_available_times] Waiting for initial button...")
                    button = page.wait_for_selector(button_selector, state="visible", timeout=5000)
                    if button:
                        logger.debug("[TennisBooker.get_available_times] Clicking initial button...")
                        button.click()
                        logger.info("[TennisBooker.get_available_times] Successfully clicked the initial button")
                    else:
                        logger.warning("[TennisBooker.get_available_times] Initial button selector found no element.")
                except Exception as e:
                    logger.error(f"[TennisBooker.get_available_times] Error clicking initial button: {str(e)}", exc_info=True)
                    # page.screenshot(path="button_error.png")
                    # Decide if we should re-raise or return empty list
                    return [] # Return empty on error here
                
                logger.debug("[TennisBooker.get_available_times] Waiting for calendar...")
                page.wait_for_selector('.rdp', state="visible")
                logger.debug("[TennisBooker.get_available_times] Calendar visible. Navigating month...")
        
                # Navigate to the correct month
                navigation_attempts = 0
                while navigation_attempts < 12: # Limit attempts to prevent infinite loops
                    # Get current month and year from the calendar
                    current_month_element = page.locator('div[role="presentation"][id^="react-day-picker-"]')
                    current_month_text = current_month_element.text_content()
                    current_month, current_year = current_month_text.strip().split()
                    logger.debug(f"[TennisBooker.get_available_times] Current calendar month: {current_month} {current_year}")
                    
                    # If we're at the correct month and year, break
                    if current_month == target_month and current_year == target_year:
                        logger.info(f"[TennisBooker.get_available_times] Target month found: {target_month} {target_year}")
                        break
                        
                    # Click next month button
                    logger.debug("[TennisBooker.get_available_times] Clicking next month...")
                    next_month_button = page.locator('button[name="next-month"]')
                    next_month_button.click()
                    # Wait for calendar to update
                    page.wait_for_timeout(500)
                    navigation_attempts += 1
                else:
                    logger.error("[TennisBooker.get_available_times] Failed to navigate to target month after 12 attempts.")
                    return []
                
                # Find and click on the target day
                try:
                    # First try: Use the most specific selector for the active day in current month
                    specific_selector = f'button[name="day"]:has-text("{target_day}"):not(.day-outside):not(.opacity-50)'
                    logger.debug(f"[TennisBooker.get_available_times] Attempting to click day with selector: {specific_selector}")
                    page.locator(specific_selector).first.click()
                    logger.info(f"[TennisBooker.get_available_times] Clicked day {target_day} using primary selector.")
                except Exception as e:
                    logger.warning(f"[TennisBooker.get_available_times] Primary day selector failed: {str(e)}. Trying alternatives...")
                    try:
                        # Second try: Get all day buttons with the target day text and filter out the one from previous/next month
                        all_day_buttons = page.locator(f'button[name="day"]:has-text("{target_day}")').all()
                        logger.debug(f"[TennisBooker.get_available_times] Found {len(all_day_buttons)} buttons matching day {target_day}")
                        
                        current_month_button = None
                        for button in all_day_buttons:
                            class_attr = button.get_attribute("class")
                            if class_attr and "day-outside" not in class_attr and "opacity-50" not in class_attr:
                                current_month_button = button
                                logger.debug("[TennisBooker.get_available_times] Found valid button for current month.")
                                break
                        
                        if current_month_button:
                            current_month_button.click()
                            logger.info(f"[TennisBooker.get_available_times] Clicked day {target_day} using secondary selector.")
                        else:
                            # Last resort: just click the nth button (careful, this is brittle)
                            logger.warning("[TennisBooker.get_available_times] Secondary day selector failed. Trying nth(1) fallback.")
                            page.locator(f'button[name="day"]:has-text("{target_day}")').nth(1).click()
                            logger.info(f"[TennisBooker.get_available_times] Clicked day {target_day} using nth(1) selector.")
                    except Exception as e2:
                        logger.error(f"[TennisBooker.get_available_times] All attempts to click day {target_day} failed: {str(e2)}", exc_info=True)
                        # page.screenshot(path="day_selection_error.png")
                        return []
                
                # Wait after clicking the day for content to load
                logger.debug("[TennisBooker.get_available_times] Waiting for court times to load after day click...")
                page.wait_for_timeout(5000) # Consider adjusting or using explicit waits if possible

                logger.debug("[TennisBooker.get_available_times] Parsing page content for courts and times...")
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                times_list = []
                found_court = False
                
                for container in soup.find_all('div', class_="rounded-xl border border-gray-200 p-3"):
                    court_name_tag = container.find('p', class_="text-[1rem] font-medium text-black md:text-[1.125rem] mb-1")
                    sport_tag = container.find('p', class_="text-[0.875rem] font-medium text-black md:text-[1rem] mb-2")
                    
                    if court_name_tag and sport_tag:
                        current_court_name = court_name_tag.get_text(strip=True)
                        current_sport = sport_tag.get_text(strip=True)
                        logger.debug(f"[TennisBooker.get_available_times] Checking container: Court='{current_court_name}', Sport='{current_sport}'")
                        
                        if current_court_name == court_name and current_sport == "Tennis":
                            logger.info(f"[TennisBooker.get_available_times] Found target court container: '{court_name}'")
                            found_court = True
                            swiper_wrapper = None
                            for rel_div in container.select("div.relative"):
                                potential_swiper = rel_div.find("div", class_="swiper-wrapper")
                                if potential_swiper:
                                    swiper_wrapper = potential_swiper
                                    logger.debug("[TennisBooker.get_available_times] Found swiper-wrapper.")
                                    break
                                    
                            if swiper_wrapper:
                                # Iterate over each swiper slide that has "swiper-slide" in its class
                                for slide in swiper_wrapper.find_all('div', class_=lambda c: c and 'swiper-slide' in c):
                                    time_tag = slide.find('p', class_="text-[0.875rem] font-medium")
                                    if time_tag:
                                        time_text = time_tag.get_text(strip=True)
                                        logger.debug(f"[TennisBooker.get_available_times] Found raw time text: '{time_text}'")
                                        # Convert from "7:30 AM" format to "07:30" format (24-hour)
                                        if ":" in time_text:
                                            try:
                                                parsed_time = datetime.strptime(time_text, "%I:%M %p") # e.g., 7:30 AM
                                                formatted_time = parsed_time.strftime("%H:%M") # e.g., 07:30
                                                times_list.append(formatted_time)
                                                logger.debug(f"[TennisBooker.get_available_times] Parsed time: {formatted_time}")
                                            except ValueError:
                                                # Handle cases like '12:00 PM' which might need special handling or just use raw
                                                try:
                                                     parsed_time = datetime.strptime(time_text, "%I:%M") # Handle case without AM/PM maybe?
                                                     formatted_time = parsed_time.strftime("%H:%M")
                                                     times_list.append(formatted_time)
                                                     logger.warning(f"[TennisBooker.get_available_times] Parsed time '{time_text}' without AM/PM to {formatted_time}")
                                                except ValueError:
                                                     logger.error(f"[TennisBooker.get_available_times] Error parsing time '{time_text}'. Appending raw.", exc_info=False)
                                                     times_list.append(time_text) # Add raw time as fallback
                                        else:
                                             logger.warning(f"[TennisBooker.get_available_times] Time text '{time_text}' does not contain ':'. Skipping parsing.")
                                             # Decide if you want to add non-standard times or ignore them
                                             # times_list.append(time_text)
                                else:
                                     logger.debug("[TennisBooker.get_available_times] Slide found without time tag.")
                            else:
                                logger.warning("[TennisBooker.get_available_times] Swiper wrapper not found in the target court container.")
                            # Found the target court, no need to check other containers
                            break 
                
                if not found_court:
                    logger.warning(f"[TennisBooker.get_available_times] Container for court '{court_name}' was not found on the page.")

                logger.info(f"[TennisBooker.get_available_times] FINISHED. Extracted times: {times_list}")
                return times_list

            except Exception as e:
                logger.error(f"[TennisBooker.get_available_times] An unexpected error occurred during scraping: {str(e)}", exc_info=True)
                # page.screenshot(path="scraping_error.png") # Capture state on error
                return [] # Return empty list on error
            finally:
                 if browser:
                      logger.debug("[TennisBooker.get_available_times] Closing Playwright browser.")
                      browser.close()

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