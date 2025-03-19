import requests
import json
import logging
from datetime import datetime
from database import supabase
from models import BookingPreference

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test data
test_data = {
    "court_name": "Alice Marble Tennis Courts",
    "rec_account_email": "test@example.com",
    "rec_account_password": "testpassword123",
    "phone_number": "4155551234",
    "playtime_duration": 90  # Test with 90 minutes
}

def test_save_booking_info_api():
    """Test the /save-booking-info API endpoint"""
    try:
        # Make the API request
        logger.info("Testing /save-booking-info API endpoint...")
        response = requests.post(
            "http://localhost:5000/save-booking-info",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Check response
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                logger.info("✓ API test successful: %s", data.get('message'))
                return True
            else:
                logger.error("✗ API test failed: %s", data.get('message'))
        else:
            logger.error("✗ API test failed with status code %d: %s", response.status_code, response.text)
        
        return False
    except Exception as e:
        logger.error("✗ Error testing API: %s", str(e))
        return False

def test_save_booking_info_direct():
    """Test saving booking info directly using the model"""
    try:
        logger.info("Testing direct model save...")
        
        # Create a test booking preference
        pref = BookingPreference(
            court_name=test_data["court_name"],
            preferred_days=["Monday", "Wednesday"],  # Example days
            preferred_times=["09:00", "10:00"],      # Example times
            playtime_duration=60,
            rec_account_email=test_data["rec_account_email"],
            rec_account_password=test_data["rec_account_password"],
            phone_number=test_data["phone_number"]
        )
        
        # Save to database
        result = pref.save()
        
        if result:
            logger.info("✓ Direct save successful: %s", result)
            return True
        else:
            logger.error("✗ Direct save failed, no result returned")
            return False
    except Exception as e:
        logger.error("✗ Error in direct save: %s", str(e))
        return False

def verify_saved_data():
    """Verify that the test data was saved to Supabase"""
    try:
        logger.info("Verifying saved data in Supabase...")
        
        # Query Supabase for the most recent booking preference
        response = supabase.table("booking_preferences") \
            .select("*") \
            .eq("rec_account_email", test_data["rec_account_email"]) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        
        if response.data:
            record = response.data[0]
            logger.info("Found record: %s", record)
            
            # Verify key fields match
            if record["court_name"] == test_data["court_name"] and \
               record["rec_account_email"] == test_data["rec_account_email"] and \
               record["phone_number"] == test_data["phone_number"]:
                logger.info("✓ Data verification successful")
                
                # Log all fields for inspection
                for key, value in record.items():
                    if key == "rec_account_password":
                        # Don't log the full password
                        logger.info("Field %s: ********", key)
                    else:
                        logger.info("Field %s: %s", key, value)
                
                return True
            else:
                logger.error("✗ Data verification failed: field values don't match")
                return False
        else:
            logger.error("✗ Data verification failed: no records found")
            return False
    except Exception as e:
        logger.error("✗ Error verifying data: %s", str(e))
        return False

def run_tests():
    """Run all tests"""
    logger.info("Starting booking info tests...")
    
    # Run direct save test first
    if test_save_booking_info_direct():
        logger.info("Direct save test passed")
        
        # Verify the data was saved
        if verify_saved_data():
            logger.info("Data verification test passed")
        else:
            logger.error("Data verification test failed")
    else:
        logger.error("Direct save test failed")
    
    # Run API test (requires app to be running)
    logger.info("\nTesting API endpoint (requires app to be running)")
    api_input = input("Do you want to test the API endpoint? (server must be running) [y/N]: ")
    if api_input.lower() == 'y':
        if test_save_booking_info_api():
            logger.info("API test passed")
            
            # Verify the data was saved
            if verify_saved_data():
                logger.info("API data verification test passed")
            else:
                logger.error("API data verification test failed")
        else:
            logger.error("API test failed")
    
    logger.info("Tests completed!")

if __name__ == "__main__":
    run_tests() 