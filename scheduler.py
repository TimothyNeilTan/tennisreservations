from automation import TennisBooker
from models import BookingAttempt, BookingPreference
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

            # Get booking preferences using Supabase
            pref = BookingPreference.get_latest()
            if not pref:
                raise Exception("No booking preferences found")

            # Initialize booker
            booker = TennisBooker(pref['rec_account_email'], pref['rec_account_password'])

            # Use booking time in America/Los_Angeles timezone since courts are in SF
            sf_timezone = ZoneInfo("America/Los_Angeles")
            booking_time = datetime.fromisoformat(attempt['booking_time'])
            local_booking_time = booking_time.astimezone(sf_timezone)

            # Attempt booking
            success, error = booker.book_court(attempt['court_name'], local_booking_time)

            # Update attempt status
            status = 'completed' if success else 'failed'
            error_message = error if error else None
            BookingAttempt.update_status(attempt_id, status, error_message)

        except Exception as e:
            logger.error(f"Error in booking job: {str(e)}")
            if attempt_id:
                BookingAttempt.update_status(attempt_id, 'failed', str(e))