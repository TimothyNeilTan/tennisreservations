import requests
from bs4 import BeautifulSoup
import playwright
from playwright_stealth import stealth_sync
from playwright.sync_api import sync_playwright
import json


url = "https://www.rec.us/organizations/san-francisco-rec-park"

response = requests.get(url)
html = response.content

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(java_script_enabled = True)
    # stealth_sync(context)
    page = context.new_page()

    page.goto(url, wait_until="networkidle")
    page.wait_for_selector("a.no-underline.hover\\:underline", state="attached")
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    # with open("testfile.html", "w") as file:
    #     file.write(json.dumps(soup))

    court_elements = soup.select("a.no-underline.hover\\:underline p.text-\\[1rem\\].font-medium")

    # Extract text from each <p> element
    court_names = [elem.get_text(strip=True) for elem in court_elements]

print(court_names)