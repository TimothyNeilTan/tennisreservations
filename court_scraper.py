import trafilatura
import logging
from typing import List

logger = logging.getLogger(__name__)

def get_sf_tennis_courts() -> List[str]:
    """
    Scrapes the SF Rec & Park website to get a list of tennis court locations.
    Returns a list of court names.
    """
    try:
        # URL for SF Rec & Park tennis facilities
        url = 'https://www.rec.us/organizations/san-francisco-rec-park'
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text_content = trafilatura.extract(downloaded)
            
            # Hardcoded initial list as fallback
            default_courts = [
                "Golden Gate Park Tennis Courts",
                "Mission Dolores Tennis Courts",
                "Hamilton Recreation Center",
                "Alice Marble Tennis Courts",
                "Moscone Recreation Center",
                "Julius Kahn Playground",
                "Upper Noe Recreation Center"
            ]
            
            # TODO: Parse the actual court names from text_content
            # For now, return the default list
            return default_courts
    except Exception as e:
        logger.error(f"Error scraping tennis courts: {str(e)}")
        return []

def update_court_list() -> List[str]:
    """
    Gets the current list of tennis courts, with fallback to default list.
    """
    courts = get_sf_tennis_courts()
    if not courts:
        # Fallback to default list if scraping fails
        courts = [
            "Golden Gate Park Tennis Courts",
            "Mission Dolores Tennis Courts",
            "Hamilton Recreation Center"
        ]
    return courts
