import logging
from automation import TennisBooker

# Configure logging to show debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_court_scraping():
    print("Starting court scraping test...")
    booker = TennisBooker("", "")  # No credentials needed for scraping
    courts = booker.get_available_courts()
    print("\nFinal results:")
    print(f"Number of courts found: {len(courts)}")
    print("Courts:", courts)

if __name__ == "__main__":
    test_court_scraping() 