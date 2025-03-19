from automation import TennisBooker
import logging
from typing import List

logger = logging.getLogger(__name__)

def get_sf_tennis_courts() -> List[str]:
    """
    Scrapes the SF Rec & Park website to get a list of tennis court locations.
    Returns a list of court names.
    """
    try:
        # Initialize TennisBooker without credentials (only needed for booking)
        booker = TennisBooker("", "")
        courts = booker.get_available_courts()

        if not courts:
            # Fallback to default list if scraping fails
            logger.warning("Failed to scrape courts, using default list")
            courts = [
                "Alice Marble",
                "Dolores",
                "Hamilton",
                "Moscone",
                "Upper Noe",
                "J.P. Murphy",
                "Parkside Square",
                "St. Mary's",
                "Mountain Lake",
                "Balboa",
                "Buena Vista"
            ]

        return courts
    except Exception as e:
        logger.error(f"Error scraping tennis courts: {str(e)}")
        return []

def update_court_list() -> List[str]:
    """
    Gets the current list of tennis courts, with fallback to default list.
    """
    courts = get_sf_tennis_courts()
    if not courts:
        # Fallback to minimum default list if scraping fails
        courts = [
            "Alice Marble",
            "Dolores",
            "Hamilton"
        ]
    return courts