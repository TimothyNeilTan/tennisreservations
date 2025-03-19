import json
import logging
from database import supabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_all_booking_preferences():
    """Retrieve all booking preferences from Supabase"""
    try:
        logger.info("Retrieving all booking preferences...")
        
        # Query Supabase for all booking preferences
        response = supabase.table("booking_preferences") \
            .select("*") \
            .order("created_at", desc=True) \
            .execute()
        
        if not response.data:
            logger.info("No booking preferences found.")
            return []
        
        logger.info(f"Found {len(response.data)} booking preferences.")
        return response.data
    except Exception as e:
        logger.error(f"Error retrieving booking preferences: {str(e)}")
        return []

def format_preference(pref):
    """Format a booking preference for display"""
    try:
        # Parse JSON fields
        preferred_days = json.loads(pref['preferred_days']) if pref['preferred_days'] else []
        preferred_times = json.loads(pref['preferred_times']) if pref['preferred_times'] else []
        
        # Format created_at date
        created_at = pref['created_at']
        
        return {
            "id": pref['id'],
            "court_name": pref['court_name'],
            "preferred_days": preferred_days,
            "preferred_times": preferred_times,
            "rec_account_email": pref['rec_account_email'],
            "rec_account_password": "*****" if pref['rec_account_password'] else None,
            "phone_number": pref['phone_number'],
            "playtime_duration": pref['playtime_duration'],
            "created_at": created_at
        }
    except Exception as e:
        logger.error(f"Error formatting preference: {str(e)}")
        return pref

def display_all_preferences():
    """Display all booking preferences"""
    prefs = get_all_booking_preferences()
    
    if not prefs:
        logger.info("No preferences to display.")
        return
    
    for i, pref in enumerate(prefs):
        formatted = format_preference(pref)
        logger.info(f"\n--- Booking Preference #{i+1} ---")
        for key, value in formatted.items():
            logger.info(f"{key}: {value}")

if __name__ == "__main__":
    display_all_preferences() 