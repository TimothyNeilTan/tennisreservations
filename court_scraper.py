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
                "Golden Gate Park Tennis Courts",
                "Mission Dolores Tennis Courts",
                "Hamilton Recreation Center",
                "Alice Marble Tennis Courts",
                "Moscone Recreation Center",
                "Julius Kahn Playground",
                "Upper Noe Recreation Center",
                "JP Murphy Playground",
                "Parkside Square",
                "St. Mary's Recreation Center",
                "Mountain Lake Park"
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
            "Golden Gate Park Tennis Courts",
            "Mission Dolores Tennis Courts",
            "Hamilton Recreation Center"
        ]
    return courts