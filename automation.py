from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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
        chrome_options.add_argument("--headless")
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
            driver = self.setup_driver()
            logger.info("Chrome WebDriver initialized successfully")

            # Navigate to booking site
            logger.info("Navigating to booking site")
            driver.get('https://www.rec.us/organizations/san-francisco-rec-park')

            # Click Activities and Tennis with explicit waits
            wait = WebDriverWait(driver, 20)

            try:
                activities_btn = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//*[text()='Activities']"))
                )
                activities_btn.click()
                time.sleep(1)  # Short wait for animation

                tennis_btn = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//*[text()='Tennis']"))
                )
                tennis_btn.click()
                logger.info("Successfully navigated to tennis courts page")
            except TimeoutException as e:
                logger.error(f"Timeout waiting for navigation elements: {str(e)}")
                driver.quit()
                return []

            # Wait for court listings and scroll
            courts = set()
            scroll_attempts = 0
            max_scroll_attempts = 10
            last_height = driver.execute_script("return document.body.scrollHeight")

            while scroll_attempts < max_scroll_attempts:
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for content to load

                # Extract court names
                try:
                    elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'facility-name')]")
                    for elem in elements:
                        text = elem.text.strip()
                        if 'Tennis' in text:
                            courts.add(text)
                    logger.info(f"Found {len(courts)} courts after scroll {scroll_attempts + 1}")
                except Exception as e:
                    logger.warning(f"Error extracting courts on scroll {scroll_attempts}: {str(e)}")

                # Check if we've reached the bottom
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    logger.info("Reached bottom of page")
                    break

                last_height = new_height
                scroll_attempts += 1

            driver.quit()
            logger.info(f"Final court list: {courts}")
            return list(courts)

        except Exception as e:
            logger.error(f"Error getting courts: {str(e)}")
            if 'driver' in locals():
                driver.quit()
            return []

    def book_court(self, court_name: str, booking_time) -> tuple[bool, str]:
        """This will be implemented next after confirming scraping works"""
        return False, "Booking functionality not yet implemented"