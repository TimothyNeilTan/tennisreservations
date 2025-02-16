from playwright.sync_api import sync_playwright
import logging

logger = logging.getLogger(__name__)

class TennisBooker:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        
    def book_court(self, court_name, booking_time):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                
                # Navigate to booking site
                page.goto('https://www.rec.us/organizations/san-francisco-rec-park')
                
                # Login
                page.click('text=Sign In')
                page.fill('input[type="email"]', self.email)
                page.fill('input[type="password"]', self.password)
                page.click('button[type="submit"]')
                
                # Navigate to tennis courts
                page.click('text=Activities')
                page.click('text=Tennis')
                
                # Select court and time
                page.click(f'text={court_name}')
                page.click(f'text={booking_time.strftime("%I:%M %p")}')
                
                # Complete booking
                page.click('text=Book Now')
                page.click('text=Confirm Booking')
                
                # Verify booking success
                success = page.query_selector('text=Booking Confirmed') is not None
                
                browser.close()
                return success, None
                
        except Exception as e:
            logger.error(f"Booking error: {str(e)}")
            return False, str(e)
