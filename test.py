import requests
from bs4 import BeautifulSoup
import playwright
from playwright_stealth import stealth_sync
from playwright.sync_api import sync_playwright
import json
import logging as logger
from datetime import datetime

url = "https://www.rec.us/organizations/san-francisco-rec-park"

# Test date - replace with your desired date
test_date = "2025-03-25"  # Format: YYYY-MM-DD
target_date = datetime.strptime(test_date, "%Y-%m-%d")
target_day = target_date.strftime("%d")
target_month = target_date.strftime("%B")  # Full month name
target_year = target_date.strftime("%Y")

# Target time to select - primary and alternate options
target_time_primary = "1:00"  # Just check for "1:00" in the time string
target_time_alternate = "1:30"  # Alternate time if primary isn't available

response = requests.get(url)
html = response.content

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(java_script_enabled = True)
    # stealth_sync(context)
    page = context.new_page()

    page.goto(url, wait_until="networkidle")
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
    
    # Wait for calendar to load
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
    
    # Try different strategies to click on the target day
    try:
        # First try: Use the most specific selector for the active day in current month
        specific_selector = f'button[name="day"]:has-text("{target_day}"):not(.day-outside):not(.opacity-50)'
        page.locator(specific_selector).first.click()
        print(f"Successfully clicked on day {target_day} with specific selector")
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

    # Check for Alice Marble Tennis court and available times
    target_time_clicked = False
    
    # Wait for the court containers to appear
    page.wait_for_selector('div.rounded-xl.border.border-gray-200.p-3', state="visible")
    
    # Get all court containers
    court_containers = page.query_selector_all('div.rounded-xl.border.border-gray-200.p-3')
    print(f"Found {len(court_containers)} court containers")
    
    for container in court_containers:
        # Get court name
        court_name_elem = container.query_selector('p.text-\\[1rem\\].font-medium.text-black.md\\:text-\\[1\\.125rem\\].mb-1')
        if not court_name_elem:
            continue
        
        court_name = court_name_elem.text_content()
        
        # Get sport type
        sport_elem = container.query_selector('p.text-\\[0\\.875rem\\].font-medium.text-black.md\\:text-\\[1rem\\].mb-2')
        if not sport_elem:
            continue
        
        sport_type = sport_elem.text_content()
        
        print(f"Found court: {court_name} - Sport: {sport_type}")
        
        # Check if this is Alice Marble Tennis court
        if "Alice Marble" in court_name and "Tennis" in sport_type:
            print("Found Alice Marble Tennis court!")
            
            # Get time slots
            time_slots = container.query_selector_all('div.swiper-slide p.text-\\[0\\.875rem\\].font-medium')
            available_times = [slot.text_content() for slot in time_slots]
            print(f"Available times: {available_times}")
            
            # First try to find primary target time
            primary_time_found = False
            for i, time_text in enumerate(available_times):
                if target_time_primary in time_text:
                    print(f"Found primary target time {target_time_primary}!")
                    # Get the parent swiper-slide element and click it
                    try:
                        # Get index of this time slot
                        swiper_slides = container.query_selector_all('div.swiper-slide')
                        if i < len(swiper_slides):
                            print(f"Clicking on time slot {time_text}")
                            swiper_slides[i].click()
                            target_time_clicked = True
                            primary_time_found = True
                            print(f"Successfully clicked on time slot {time_text}")
                            # Wait after selecting the time
                            page.wait_for_timeout(2000)
                            break
                    except Exception as e:
                        print(f"Error clicking on time slot: {str(e)}")
            
            # If primary time not found, try alternate time
            if not primary_time_found:
                print(f"Primary time {target_time_primary} not found. Looking for alternate time {target_time_alternate}")
                for i, time_text in enumerate(available_times):
                    if target_time_alternate in time_text:
                        print(f"Found alternate target time {target_time_alternate}!")
                        # Get the parent swiper-slide element and click it
                        try:
                            # Get index of this time slot
                            swiper_slides = container.query_selector_all('div.swiper-slide')
                            if i < len(swiper_slides):
                                print(f"Clicking on time slot {time_text}")
                                swiper_slides[i].click()
                                target_time_clicked = True
                                print(f"Successfully clicked on time slot {time_text}")
                                # Wait after selecting the time
                                page.wait_for_timeout(2000)
                                break
                        except Exception as e:
                            print(f"Error clicking on time slot: {str(e)}")
            
            # Break out of the loop once we've found and processed Alice Marble
            break
    
    if target_time_clicked:
        # Wait for submit button and click it
        print("Time selected, now looking for reservation/confirmation button...")
        try:
            # Use a dummy loop to allow breaking out once a button is found
            for _ in range(1):
                # Try the specific Book button with the exact class
                try:
                    book_button = page.wait_for_selector('button.uppercase.text-sm.font-bold.border-2.disabled\\:opacity-30.disabled\\:pointer-events-none.transition-colors.outline-none.py-4.px-14.bg-\\[\\#26E164\\].rounded-none.border-\\[\\#26E164\\].hover\\:bg-\\[\\#1DB14E\\].hover\\:border-\\[\\#1DB14E\\].active\\:bg-\\[\\#029D38\\].active\\:border-\\[\\#029D38\\].focus\\:bg-\\[\\#029D38\\].focus\\:border-\\[\\#029D38\\].flex-shrink-0.max-w-max', state="visible", timeout=3000)
                    
                    if book_button:
                        book_button.click()
                        print("Clicked the specific 'Book' button")
                        page.wait_for_timeout(3000)
                        page.screenshot(path="after_book_button.png")
                        break
                except Exception as e:
                    print(f"Could not find the specific Book button: {str(e)}")
                
                # Try a simpler selector for the Book button based on color and text
                try:
                    green_book_button = page.wait_for_selector('button.bg-\\[\\#26E164\\]:has-text("Book")', state="visible", timeout=2000)
                    if green_book_button:
                        green_book_button.click()
                        print("Clicked the green 'Book' button")
                        page.wait_for_timeout(3000)
                        page.screenshot(path="after_book_button.png")
                        break
                except Exception as e:
                    print(f"Could not find green Book button: {str(e)}")
                
                # Try button with text "Book" as a fallback
                try:
                    book_text_button = page.wait_for_selector('button:has-text("Book")', state="visible", timeout=2000)
                    if book_text_button:
                        book_text_button.click()
                        print("Clicked button with text 'Book'")
                        page.wait_for_timeout(3000)
                        page.screenshot(path="after_book_button.png")
                        break
                except Exception as e:
                    print(f"Could not find button with text 'Book': {str(e)}")
                
                # Take a screenshot if no button could be found
                print("Failed to find the Book button")
                page.screenshot(path="no_book_button.png")
                
        except Exception as e:
            print(f"Error handling book button: {str(e)}")
            page.screenshot(path="book_button_error.png")
            
        # Login process after clicking Book button
        try:
            # Wait for the Log In button to appear
            print("Looking for Log In button...")
            login_button = page.wait_for_selector('button.font-bold.text-brand-neutral:has-text("Log In")', state="visible", timeout=5000)
            
            if login_button:
                # Take screenshot before clicking login
                page.screenshot(path="before_login_click.png")
                
                # Click the Log In button
                login_button.click()
                print("Clicked the Log In button")
                
                # Wait for login form to appear
                page.wait_for_timeout(2000)
                
                # Input email
                email_input = page.wait_for_selector('input#email.flex.h-10.w-full.border-2', state="visible", timeout=5000)
                if email_input:
                    email_input.fill("neil81688@gmail.com")
                    print("Entered email")
                else:
                    print("Email input field not found")
                    page.screenshot(path="email_input_not_found.png")
                
                # Input password
                password_input = page.wait_for_selector('input#password.flex.h-10.w-full.border-2', state="visible", timeout=5000)
                if password_input:
                    password_input.fill("")
                    print("Entered password")
                else:
                    print("Password input field not found")
                    page.screenshot(path="password_input_not_found.png")
                
                # Look for submit/login button
                submit_button = page.wait_for_selector('button[type="submit"]', state="visible", timeout=5000)
                if submit_button:
                    # Take screenshot before final submission
                    page.screenshot(path="before_login_submit.png")
                    
                    # Click submit button
                    submit_button.click()
                    print("Clicked login submit button")
                    
                    # Wait for login to process
                    page.wait_for_timeout(5000)
                    
                    # Take screenshot after login
                    page.screenshot(path="after_login.png")
                    
                    # After login, first select the participant
                    print("Logged in successfully. Looking for participant selector...")
                    
                    # Try to find and click the participant selector
                    try:
                        participant_found = False
                        
                        # Method 1: Using ID attribute that starts with headlessui-listbox-button
                        try:
                            participant_selector = page.wait_for_selector('button[id^="headlessui-listbox-button"][aria-haspopup="listbox"]', state="visible", timeout=3000)
                            
                            if participant_selector:
                                participant_selector.click()
                                print("Clicked the participant selector dropdown (Method 1)")
                                participant_found = True
                                # Wait for dropdown to appear
                                page.wait_for_timeout(1000)
                                page.screenshot(path="participant_dropdown_method1.png")
                        except Exception as e:
                            print(f"Participant selector Method 1 failed: {str(e)}")
                        
                        # Method 2: Try using the text content
                        if not participant_found:
                            try:
                                select_participant_button = page.wait_for_selector('button:has-text("Select participant")', state="visible", timeout=3000)
                                if select_participant_button:
                                    select_participant_button.click()
                                    print("Clicked the participant selector dropdown (Method 2)")
                                    participant_found = True
                                    page.wait_for_timeout(1000)
                                    page.screenshot(path="participant_dropdown_method2.png")
                            except Exception as e:
                                print(f"Participant selector Method 2 failed: {str(e)}")
                        
                        # Method 3: Try using the class attributes described
                        if not participant_found:
                            try:
                                class_selector_button = page.wait_for_selector('button.w-full', state="visible", timeout=3000)
                                if class_selector_button:
                                    class_selector_button.click()
                                    print("Clicked the participant selector dropdown (Method 3)")
                                    participant_found = True
                                    page.wait_for_timeout(1000)
                                    page.screenshot(path="participant_dropdown_method3.png")
                            except Exception as e:
                                print(f"Participant selector Method 3 failed: {str(e)}")
                        
                        # Method 4: Try looking for any button with a dropdown icon
                        if not participant_found:
                            try:
                                down_caret_button = page.wait_for_selector('button:has(img[src*="caret-down"])', state="visible", timeout=3000)
                                if down_caret_button:
                                    down_caret_button.click()
                                    print("Clicked button with dropdown icon (Method 4)")
                                    participant_found = True
                                    page.wait_for_timeout(1000)
                                    page.screenshot(path="participant_dropdown_method4.png")
                            except Exception as e:
                                print(f"Participant selector Method 4 failed: {str(e)}")
                        
                        if participant_found:
                            # Now try to find the account owner option
                            account_owner_found = False
                            
                            # Method 1: Look for div with "Account Owner" text
                            try:
                                account_owner = page.wait_for_selector('div.flex.w-full.items-center:has(small:has-text("Account Owner"))', state="visible", timeout=3000)
                                
                                if account_owner:
                                    account_owner.click()
                                    print("Selected Account Owner (Method 1)")
                                    account_owner_found = True
                                    page.wait_for_timeout(1000)
                                    page.screenshot(path="after_participant_selection_method1.png")
                            except Exception as e:
                                print(f"Account owner selection Method 1 failed: {str(e)}")
                            
                            # Method 2: Try a simpler selector for Account Owner
                            if not account_owner_found:
                                try:
                                    alt_account_owner = page.wait_for_selector('div:has-text("Account Owner")', state="visible", timeout=3000)
                                    if alt_account_owner:
                                        alt_account_owner.click()
                                        print("Selected Account Owner (Method 2)")
                                        account_owner_found = True
                                        page.wait_for_timeout(1000)
                                        page.screenshot(path="after_participant_selection_method2.png")
                                except Exception as e:
                                    print(f"Account owner selection Method 2 failed: {str(e)}")
                            
                            # Method 3: Look for the name Timothy Tan
                            if not account_owner_found:
                                try:
                                    name_div = page.wait_for_selector('div.flex.flex-col:has-text("Timothy Tan")', state="visible", timeout=3000)
                                    if name_div:
                                        # Get the parent div that's clickable
                                        parent_div = page.evaluate('element => element.closest(".flex.w-full.items-center")', name_div)
                                        if parent_div:
                                            page.click(f'div.flex.w-full.items-center:has-text("Timothy Tan")')
                                            print("Selected Timothy Tan (Method 3)")
                                            account_owner_found = True
                                            page.wait_for_timeout(1000)
                                            page.screenshot(path="after_participant_selection_method3.png")
                                except Exception as e:
                                    print(f"Account owner selection Method 3 failed: {str(e)}")
                            
                            # Method 4: If can't find account owner specifically, try clicking the first participant option
                            if not account_owner_found:
                                try:
                                    first_participant = page.wait_for_selector('div.hover\\:bg-gray-100', state="visible", timeout=3000)
                                    if first_participant:
                                        first_participant.click()
                                        print("Selected first available participant (fallback)")
                                        page.wait_for_timeout(1000)
                                        page.screenshot(path="after_first_participant_selection.png")
                                        account_owner_found = True
                                except Exception as e:
                                    print(f"Account owner selection Method 4 failed: {str(e)}")
                            
                            if not account_owner_found:
                                print("Could not find any participant to select")
                                page.screenshot(path="no_participant_found.png")
                        else:
                            print("Participant selector dropdown not found using any method")
                            page.screenshot(path="participant_selector_not_found.png")
                    
                    except Exception as e:
                        print(f"Error selecting participant: {str(e)}")
                        page.screenshot(path="participant_selection_error.png")
                    
                    # Now continue with looking for the Book button again
                    print("Looking for Book button after participant selection...")
                    
                    # Try to find and click the Book button again
                    try:
                        book_after_login_found = False
                        
                        # Try method 1: Using the full class selector
                        try:
                            book_button_after_login = page.wait_for_selector('button.uppercase.text-sm.font-bold.border-2.disabled\\:opacity-30.disabled\\:pointer-events-none.transition-colors.outline-none.py-4.px-14.bg-\\[\\#26E164\\].rounded-none.border-\\[\\#26E164\\].hover\\:bg-\\[\\#1DB14E\\].hover\\:border-\\[\\#1DB14E\\].active\\:bg-\\[\\#029D38\\].active\\:border-\\[\\#029D38\\].focus\\:bg-\\[\\#029D38\\].focus\\:border-\\[\\#029D38\\].flex-shrink-0.max-w-max', state="visible", timeout=3000)
                            
                            if book_button_after_login:
                                book_button_after_login.click()
                                print("Clicked the Book button again after login (using full class)")
                                book_after_login_found = True
                                page.wait_for_timeout(3000)
                                page.screenshot(path="after_second_book_click.png")
                        except Exception as e:
                            print(f"Method 1 failed: {str(e)}")
                        
                        # Method 2: Try looking for any green button with "Book" text
                        if not book_after_login_found:
                            try:
                                green_book_button = page.wait_for_selector('button.bg-\\[\\#26E164\\]:has-text("Book")', state="visible", timeout=3000)
                                if green_book_button:
                                    green_book_button.click()
                                    print("Clicked the Book button again after login (using green button selector)")
                                    book_after_login_found = True
                                    page.wait_for_timeout(3000)
                                    page.screenshot(path="after_second_book_click_green.png")
                            except Exception as e:
                                print(f"Method 2 failed: {str(e)}")
                        
                        # Method 3: Try using just the text "Book"
                        if not book_after_login_found:
                            try:
                                text_book_button = page.wait_for_selector('button:has-text("Book")', state="visible", timeout=3000)
                                if text_book_button:
                                    text_book_button.click()
                                    print("Clicked the Book button again after login (using text selector)")
                                    book_after_login_found = True
                                    page.wait_for_timeout(3000)
                                    page.screenshot(path="after_second_book_click_text.png")
                            except Exception as e:
                                print(f"Method 3 failed: {str(e)}")
                        
                        # Method 4: Try finding any green button as a last resort
                        if not book_after_login_found:
                            try:
                                any_green_button = page.wait_for_selector('button.bg-\\[\\#26E164\\]', state="visible", timeout=3000)
                                if any_green_button:
                                    button_text = any_green_button.text_content().strip()
                                    any_green_button.click()
                                    print(f"Clicked a green button with text: '{button_text}'")
                                    book_after_login_found = True
                                    page.wait_for_timeout(3000)
                                    page.screenshot(path="after_second_book_click_any_green.png")
                            except Exception as e:
                                print(f"Method 4 failed: {str(e)}")
                        
                        if not book_after_login_found:
                            print("Could not find Book button after login using any method")
                            page.screenshot(path="book_after_login_not_found.png")
                            # We'll still try to continue to the Send Code button
                        
                        # Now look for the Send Code button
                        print("Looking for Send Code button...")
                        send_code_found = False
                        
                        # Method 1: Try using the full class selector
                        try:
                            send_code_button = page.wait_for_selector('button.uppercase.text-sm.font-bold.border-2.disabled\\:opacity-30.disabled\\:pointer-events-none.transition-colors.outline-none.py-4.px-14.bg-\\[\\#26E164\\].rounded-none.border-\\[\\#26E164\\].hover\\:bg-\\[\\#1DB14E\\].hover\\:border-\\[\\#1DB14E\\].active\\:bg-\\[\\#029D38\\].active\\:border-\\[\\#029D38\\].focus\\:bg-\\[\\#029D38\\].focus\\:border-\\[\\#029D38\\].w-full[type="submit"]:has-text("Send Code")', state="visible", timeout=3000)
                            
                            if send_code_button:
                                # Take screenshot before clicking Send Code
                                page.screenshot(path="before_send_code.png")
                                
                                # Click the Send Code button
                                send_code_button.click()
                                print("Clicked the Send Code button (using full class)")
                                send_code_found = True
                                
                                # Wait for confirmation page
                                page.wait_for_timeout(5000)
                                page.screenshot(path="after_send_code.png")
                        except Exception as e:
                            print(f"Send Code Method 1 failed: {str(e)}")
                        
                        # Method 2: Try using type="submit" and text
                        if not send_code_found:
                            try:
                                submit_send_code = page.wait_for_selector('button[type="submit"]:has-text("Send Code")', state="visible", timeout=3000)
                                if submit_send_code:
                                    page.screenshot(path="before_send_code_method2.png")
                                    submit_send_code.click()
                                    print("Clicked the Send Code button (using type and text)")
                                    send_code_found = True
                                    page.wait_for_timeout(5000)
                                    page.screenshot(path="after_send_code_method2.png")
                            except Exception as e:
                                print(f"Send Code Method 2 failed: {str(e)}")
                        
                        # Method 3: Try just using the text "Send Code"
                        if not send_code_found:
                            try:
                                text_send_code = page.wait_for_selector('button:has-text("Send Code")', state="visible", timeout=3000)
                                if text_send_code:
                                    page.screenshot(path="before_send_code_method3.png")
                                    text_send_code.click()
                                    print("Clicked the Send Code button (using just text)")
                                    send_code_found = True
                                    page.wait_for_timeout(5000)
                                    page.screenshot(path="after_send_code_method3.png")
                            except Exception as e:
                                print(f"Send Code Method 3 failed: {str(e)}")
                        
                        # Method 4: Try finding any green submit button
                        if not send_code_found:
                            try:
                                green_submit = page.wait_for_selector('button.bg-\\[\\#26E164\\][type="submit"]', state="visible", timeout=3000)
                                if green_submit:
                                    button_text = green_submit.text_content().strip()
                                    page.screenshot(path="before_send_code_method4.png")
                                    green_submit.click()
                                    print(f"Clicked a green submit button with text: '{button_text}'")
                                    send_code_found = True
                                    page.wait_for_timeout(5000)
                                    page.screenshot(path="after_send_code_method4.png")
                            except Exception as e:
                                print(f"Send Code Method 4 failed: {str(e)}")
                        
                        if not send_code_found:
                            print("Send Code button not found using any method")
                            page.screenshot(path="send_code_not_found.png")
                    
                    except Exception as e:
                        print(f"Error in post-login process: {str(e)}")
                        page.screenshot(path="post_login_error.png")
                else:
                    print("Login submit button not found")
                    page.screenshot(path="login_submit_not_found.png")
            else:
                print("Log In button not found")
                page.screenshot(path="login_button_not_found.png")
                
        except Exception as e:
            print(f"Error during login process: {str(e)}")
            page.screenshot(path="login_error.png")
            
    else:
        print(f"Could not find target time {target_time_primary} or {target_time_alternate} for Alice Marble Tennis court")
    
    # Wait a few seconds to see the final result
    page.wait_for_timeout(5000)
    
    # Optional: Save a screenshot of the final state
    page.screenshot(path="booking_result.png")
    
    print("Test completed.")

    # Original BeautifulSoup code for extracting court info (for reference)
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")
    for container in soup.find_all('div', class_="rounded-xl border border-gray-200 p-3"):
        court_name_tag = container.find('p', class_="text-[1rem] font-medium text-black md:text-[1.125rem] mb-1")
        sport_tag = container.find('p', class_="text-[0.875rem] font-medium text-black md:text-[1rem] mb-2")
        
        if court_name_tag and sport_tag:
            if court_name_tag.get_text(strip=True) == "Alice Marble" and sport_tag.get_text(strip=True) == "Tennis":
                print("Found container for Alice Marble playing Tennis")
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
                            times_list.append(time_tag.get_text(strip=True))
                    print("Extracted times:", times_list)
                else:
                    print("Swiper wrapper not found in this container.")