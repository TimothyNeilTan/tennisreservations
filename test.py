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



    # container = soup.find('div', class_="rounded-xl border border-gray-200 p-3", 
    #                   string=lambda text: text and "Alice Marble" in text)

    # if container:
    #     logger.debug("Found container, checking for Tennis sport tag")
    #     try:
    #         # Check that the container also has "Tennis" in the sport tag
    #         sport_tag = container.find('p', class_="text-[0.875rem] font-medium text-black md:text-[1rem] mb-2")
    #         if sport_tag and "Tennis" in sport_tag.get_text(strip=True):
    #             logger.debug("Found Tennis sport tag, looking for swiper wrapper")
    #             try:
    #                 swiper_wrapper = container.find('div', class_="swiper-wrapper")
    #                 if swiper_wrapper:
    #                     logger.debug("Found swiper wrapper, extracting time tags")
    #                     try:
    #                         time_tags = swiper_wrapper.find_all('p', class_="text-[0.875rem] font-medium")
    #                         times = [tag.get_text(strip=True) for tag in time_tags]
    #                         logger.info(f"Successfully extracted times: {times}")
    #                         print(times)
    #                     except Exception as e:
    #                         logger.error(f"Error extracting time tags: {str(e)}")
    #                 else:
    #                     logger.warning("No swiper wrapper found")
    #             except Exception as e:
    #                 logger.error(f"Error finding swiper wrapper: {str(e)}")
    #         else:
    #             logger.warning("Container does not contain Tennis sport tag")
    #     except Exception as e:
    #         logger.error(f"Error checking sport tag: {str(e)}")
    # else:
    #     logger.warning("No container found")

    # with open("testfile.html", "w") as file:
    #     file.write(json.dumps(soup))

    # court_elements = soup.select("a.no-underline.hover\\:underline p.text-\\[1rem\\].font-medium")

    # Extract text from each <p> element
    # court_names = [elem.get_text(strip=True) for elem in court_elements]

# print(court_names)