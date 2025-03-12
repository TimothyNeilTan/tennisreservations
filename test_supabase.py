import logging
from database import supabase
from models import Court, BookingPreference
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_connection():
    """Test basic Supabase connection"""
    try:
        # Simple query to test connection
        response = supabase.table("courts").select("*").limit(1).execute()
        logger.info("✓ Successfully connected to Supabase")
        return True
    except Exception as e:
        logger.error(f"× Connection test failed: {str(e)}")
        return False

def test_court_operations():
    """Test court creation and retrieval"""
    try:
        # Create a test court
        test_court = Court("Test Court")
        result = Court.create_or_update("Test Court")
        logger.info(f"✓ Successfully created court: {result}")

        # Get all active courts
        courts = Court.get_all_active()
        logger.info(f"✓ Retrieved {len(courts)} active courts")
        for court in courts:
            logger.info(f"  - {court['name']}")
        
        return True
    except Exception as e:
        logger.error(f"× Court operations test failed: {str(e)}")
        return False

def test_booking_preference():
    """Test booking preference creation and retrieval"""
    try:
        # Create a test booking preference
        pref = BookingPreference(
            court_name="Test Court",
            preferred_days=["Monday", "Wednesday"],
            preferred_times=["09:00", "10:00"],
            rec_account_email="test@example.com",
            rec_account_password="testpass123",
            phone_number="1234567890"
        )
        result = pref.save()
        logger.info(f"✓ Successfully created booking preference")

        # Get latest preference
        latest = BookingPreference.get_latest()
        logger.info(f"✓ Retrieved latest preference for court: {latest['court_name']}")
        
        return True
    except Exception as e:
        logger.error(f"× Booking preference test failed: {str(e)}")
        return False

def run_all_tests():
    """Run all tests"""
    logger.info("Starting Supabase integration tests...")
    
    # Test connection
    if not test_connection():
        logger.error("Connection test failed, stopping further tests")
        return
    
    # Test court operations
    test_court_operations()
    
    # Test booking preferences
    test_booking_preference()
    
    logger.info("Tests completed!")

if __name__ == "__main__":
    run_all_tests() 