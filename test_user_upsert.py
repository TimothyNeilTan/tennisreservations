import logging
from datetime import datetime
from dotenv import load_dotenv
from models import UserInformation  # Assuming models.py is in the same directory or accessible

# Configure basic logging for the test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
# Ensure you have a .env file with SUPABASE_URL and SUPABASE_KEY
load_dotenv()

def run_upsert_test():
    """Runs insert and update tests for UserInformation.upsert_by_email."""

    test_email = "test.upsert@example.com"
    initial_password = "initial_password123"
    initial_phone = "1234567890"
    initial_duration = 60
    now = datetime.now()

    logging.info(f"--- Starting Test: Insert User {test_email} ---")
    try:
        insert_result = UserInformation.upsert_by_email(
            rec_account_email=test_email,
            rec_account_password=initial_password,
            phone_number=initial_phone,
            playtime_duration=initial_duration,
            created_at=now.isoformat() # Pass timestamp as ISO string
        )
        logging.info(f"Insert Result: {insert_result}")
        if insert_result and insert_result.get('rec_account_email') == test_email:
            logging.info(f"SUCCESS: Initial insert for {test_email} seems successful.")
        else:
            logging.warning(f"WARNING: Insert for {test_email} might not have completed as expected.")

    except Exception as e:
        logging.error(f"ERROR during initial insert for {test_email}: {e}", exc_info=True)

    # --- Test Update ---
    updated_password = "updated_password456"
    updated_phone = "0987654321"
    updated_duration = 90
    update_time = datetime.now()

    logging.info(f"--- Starting Test: Update User {test_email} ---")
    try:
        update_result = UserInformation.upsert_by_email(
            rec_account_email=test_email,
            rec_account_password=updated_password, # Updated password
            phone_number=updated_phone,       # Updated phone
            playtime_duration=updated_duration, # Updated duration
            created_at=update_time.isoformat() # Pass timestamp as ISO string
        )
        logging.info(f"Update Result: {update_result}")

        # Verification step (optional but recommended): Fetch the user again to check fields
        logging.info(f"Verifying update for {test_email} by fetching...")
        fetched_user = UserInformation.get_latest() # Assuming this gets the latest, might need adjustment if many users exist
        
        # A more robust verification would be to fetch by email if such a method exists
        # For now, we check the latest record if it matches the email
        if fetched_user and fetched_user.get('rec_account_email') == test_email:
             logging.info(f"Fetched user data after update: {fetched_user}")
             # Check specific fields
             if fetched_user.get('phone_number') == updated_phone and \
                fetched_user.get('playtime_duration') == updated_duration:
                 logging.info(f"SUCCESS: Update for {test_email} seems successful based on fetched data.")
             else:
                 logging.warning(f"WARNING: Updated fields for {test_email} do not match expected values.")
        elif update_result and update_result.get('rec_account_email') == test_email:
             logging.warning(f"Upsert operation returned success for {test_email}, but couldn't verify via get_latest.")
        else:
             logging.error(f"ERROR: Update for {test_email} might have failed or verification failed.")

    except Exception as e:
        logging.error(f"ERROR during update for {test_email}: {e}", exc_info=True)

if __name__ == "__main__":
    run_upsert_test() 