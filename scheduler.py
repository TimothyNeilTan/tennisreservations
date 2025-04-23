from automation import TennisBooker
from models import BookingAttempt, UserInformation
from extensions import scheduler
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

def booking_job(attempt_id):
    with scheduler.app.app_context():
        try:
            # Get the booking attempt using Supabase
            attempt = BookingAttempt.get_by_id(attempt_id)
            if not attempt:
                logger.error(f"Booking attempt {attempt_id} not found")
                return

            # Use UserInformation instead of BookingPreference
            user_info = UserInformation.get_by_email(attempt['user_email'])
            if not user_info:
                logger.error(f"Could not find UserInformation for email {attempt.get('user_email')} associated with attempt {attempt_id}")
                raise Exception(f"No user information found for email {attempt.get('user_email')}")

            # Initialize booker using fetched user info
            if not user_info.get('rec_account_password'):
                logger.error(f"Password missing for user {user_info.get('rec_account_email')} needed for attempt {attempt_id}")
                raise Exception("User information is missing password")
                
            booker = TennisBooker(user_info['rec_account_email'], user_info['rec_account_password'])

            # Use booking time in America/Los_Angeles timezone since courts are in SF
            sf_timezone = ZoneInfo("America/Los_Angeles")
            booking_time = datetime.fromisoformat(attempt['booking_time'])
            local_booking_time = booking_time.astimezone(sf_timezone)
            
            # Get playtime duration from user_info (default to 60 minutes if not set or invalid)
            playtime_duration = user_info.get('playtime_duration', 60)
            if playtime_duration not in [60, 90]:
                logger.warning(f"Invalid playtime duration: {playtime_duration}, defaulting to 60")
                playtime_duration = 60
            logger.info(f"Using playtime duration: {playtime_duration} minutes")

            # Attempt booking
            success, error = booker.book_court(
                attempt['court_name'], 
                local_booking_time, 
                playtime_duration=playtime_duration
            )

            # Update attempt status
            status = 'completed' if success else 'failed'
            error_message = error if error else None
            BookingAttempt.update_status(attempt_id, status, error_message)

        except Exception as e:
            logger.error(f"Error in booking job for attempt {attempt_id}: {str(e)}", exc_info=True)
            # Ensure attempt_id is valid before trying to update status
            if attempt_id:
                try:
                    # Update status even if fetching attempt initially failed
                    BookingAttempt.update_status(attempt_id, 'failed', str(e))
                except Exception as update_err:
                    logger.error(f"Failed to update status to failed for attempt {attempt_id} after error: {update_err}")