import requests
from bs4 import BeautifulSoup
import playwright
from playwright_stealth import stealth_sync
from playwright.sync_api import sync_playwright
import json
import logging as logger
from datetime import datetime
import time
import uuid

class ReservationBot:
    def __init__(self, user_id: str, email: str, password: str):
        self.user_id = user_id
        self.email = email
        self.password = password
        self.url = "https://www.rec.us/organizations/san-francisco-rec-park"
        self.test_date = "2025-04-28"
        self.target_time_primary = "1:00"
        self.target_time_alternate = "1:30"
        
        # Parse target date
        target_date = datetime.strptime(self.test_date, "%Y-%m-%d")
        self.target_day = target_date.strftime("%d")
        self.target_month = target_date.strftime("%B")
        self.target_year = target_date.strftime("%Y")

    def run(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(java_script_enabled=True)
            page = context.new_page()

            try:
                # Initial page load
                page.goto(self.url, wait_until="networkidle")
                page.wait_for_selector("a.no-underline.hover\\:underline", state="attached", timeout=3000)

                # Click initial button
                button = page.wait_for_selector('button.rounded-2xl.border.border-gray-200.px-4.py-1.hover\\:border-black.bg-gray-200', 
                                              state="visible", timeout=3000)
                if button:
                    button.click()

                # Calendar navigation
                page.wait_for_selector('.rdp', state="visible", timeout=3000)
                
                while True:
                    current_month_element = page.locator('div[role="presentation"][id^="react-day-picker-"]')
                    current_month_text = current_month_element.text_content()
                    current_month, current_year = current_month_text.strip().split()
                    
                    if current_month == self.target_month and current_year == self.target_year:
                        break
                        
                    next_month_button = page.locator('button[name="next-month"]')
                    next_month_button.click()
                    page.wait_for_timeout(200)

                # Click target day
                day_button = page.locator(f'button[name="day"]:has-text("{self.target_day}"):not(.day-outside):not(.opacity-50)').first
                day_button.click()
                page.wait_for_timeout(1000)

                # Find and click time slot
                target_time_clicked = False
                page.wait_for_selector('div.rounded-xl.border.border-gray-200.p-3', state="visible", timeout=3000)
                
                court_containers = page.query_selector_all('div.rounded-xl.border.border-gray-200.p-3')
                
                for container in court_containers:
                    court_name_elem = container.query_selector('p.text-\\[1rem\\].font-medium.text-black.md\\:text-\\[1\\.125rem\\].mb-1')
                    sport_elem = container.query_selector('p.text-\\[0\\.875rem\\].font-medium.text-black.md\\:text-\\[1rem\\].mb-2')
                    
                    if not court_name_elem or not sport_elem:
                        continue
                    
                    court_name = court_name_elem.text_content()
                    sport_type = sport_elem.text_content()
                    
                    if "Alice Marble" in court_name and "Tennis" in sport_type:
                        time_slots = container.query_selector_all('div.swiper-slide p.text-\\[0\\.875rem\\].font-medium')
                        available_times = [slot.text_content() for slot in time_slots]
                        
                        # Try primary time
                        for i, time_text in enumerate(available_times):
                            if self.target_time_primary in time_text:
                                swiper_slides = container.query_selector_all('div.swiper-slide')
                                if i < len(swiper_slides):
                                    swiper_slides[i].click()
                                    target_time_clicked = True
                                    break
                        
                        # Try alternate time
                        if not target_time_clicked:
                            for i, time_text in enumerate(available_times):
                                if self.target_time_alternate in time_text:
                                    swiper_slides = container.query_selector_all('div.swiper-slide')
                                    if i < len(swiper_slides):
                                        swiper_slides[i].click()
                                        target_time_clicked = True
                                        break
                        
                        break

                if target_time_clicked:
                    # Book button
                    book_button = page.wait_for_selector('button.bg-\\[\\#26E164\\]:has-text("Book")', state="visible", timeout=2000)
                    if book_button:
                        book_button.click()
                        page.wait_for_timeout(1000)
                        
                        # Login process
                        login_button = page.wait_for_selector('button.font-bold.text-brand-neutral:has-text("Log In")', state="visible", timeout=2000)
                        if login_button:
                            login_button.click()
                            page.wait_for_timeout(1000)
                            
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
                                    
                                    # Select participant
                                    participant_selector = page.wait_for_selector('button[id^="headlessui-listbox-button"]', state="visible", timeout=2000)
                                    if participant_selector:
                                        participant_selector.click()
                                        page.wait_for_timeout(500)
                                        
                                        account_owner = page.wait_for_selector('div.flex.w-full.items-center:has(small:has-text("Account Owner"))', 
                                                                             state="visible", timeout=2000)
                                        if account_owner:
                                            account_owner.click()
                                            page.wait_for_timeout(500)
                                            
                                            # Click Book button again
                                            book_button = page.wait_for_selector('button.bg-\\[\\#26E164\\]:has-text("Book")', state="visible", timeout=2000)
                                            if book_button:
                                                book_button.click()
                                                page.wait_for_timeout(1000)
                                                
                                                # Click Send Code button
                                                send_code_button = page.wait_for_selector('button[type="submit"]:has-text("Send Code")', 
                                                                                       state="visible", timeout=2000)
                                                if send_code_button:
                                                    send_code_button.click()
                                                    page.wait_for_timeout(1000)
                                                    
                                                    # Wait for code input
                                                    code_input = page.wait_for_selector('input#totp[name="totp"][type="number"]', 
                                                                                     state="visible", timeout=5000)
                                                    if code_input:
                                                        # Poll for code
                                                        max_attempts = 15
                                                        verification_code = None
                                                        
                                                        for attempt in range(max_attempts):
                                                            try:
                                                                response = requests.get(f'http://localhost:8000/get_code?user_id={self.user_id}')
                                                                if response.status_code == 200:
                                                                    data = response.json()
                                                                    if data.get('status') == 'available':
                                                                        verification_code = data.get('code')
                                                                        break
                                                            except Exception as e:
                                                                print(f"Error checking for code: {str(e)}")
                                                            
                                                            time.sleep(1)
                                                        
                                                        if verification_code:
                                                            code_input.fill(verification_code)
                                                            
                                                            # Click Confirm button
                                                            confirm_button = page.wait_for_selector('button[type="button"]:has-text("Confirm")', 
                                                                                                 state="visible", timeout=2000)
                                                            if confirm_button:
                                                                confirm_button.click()
                                                                page.wait_for_timeout(2000)
                                                                return True
            except Exception as e:
                print(f"Error during reservation: {str(e)}")
                return False
            finally:
                browser.close()

def main():
    # Check for existing user session first
    response = requests.get('http://localhost:8000/list_users')
    if response.status_code == 200:
        users = response.json()['users']
        existing_user = next((user for user in users if user['email'] == 'neil81688@gmail.com'), None)
        if existing_user:
            user_id = existing_user['user_id']
            print(f"Using existing session with user_id: {user_id}")
            bot = ReservationBot(user_id, 'neil81688@gmail.com', '@Yhtomit123')
            success = bot.run()
            print(f"Reservation {'successful' if success else 'failed'}")
            return

    # If no existing session, register new user
    response = requests.post('http://localhost:8000/register', json={
        'email': 'neil81688@gmail.com',
        'password': '@Yhtomit123'
    })
    
    if response.status_code == 200:
        user_id = response.json()['user_id']
        print(f"Created new session with user_id: {user_id}")
        bot = ReservationBot(user_id, 'neil81688@gmail.com', '@Yhtomit123')
        success = bot.run()
        print(f"Reservation {'successful' if success else 'failed'}")
    else:
        print("Failed to register user")

if __name__ == "__main__":
    main()