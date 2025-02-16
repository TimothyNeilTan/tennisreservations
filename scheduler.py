from flask_apscheduler import APScheduler
from automation import TennisBooker
from models import BookingAttempt, BookingPreference
from app import db
import logging

logger = logging.getLogger(__name__)

scheduler = APScheduler()

def booking_job(attempt_id):
    with scheduler.app.app_context():
        try:
            attempt = BookingAttempt.query.get(attempt_id)
            if not attempt:
                logger.error(f"Booking attempt {attempt_id} not found")
                return
                
            # Get booking preferences
            pref = BookingPreference.query.first()
            if not pref:
                raise Exception("No booking preferences found")
                
            # Initialize booker
            booker = TennisBooker(pref.rec_account_email, pref.rec_account_password)
            
            # Attempt booking
            success, error = booker.book_court(attempt.court_name, attempt.booking_time)
            
            # Update attempt status
            attempt.status = 'completed' if success else 'failed'
            if error:
                attempt.error_message = error
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error in booking job: {str(e)}")
            if attempt:
                attempt.status = 'failed'
                attempt.error_message = str(e)
                db.session.commit()
