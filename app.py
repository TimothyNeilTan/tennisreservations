import os
import logging
import json
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from court_scraper import update_court_list
from automation import TennisBooker
from models import Court, UserInformation, BookingAttempt
from database import init_db
from extensions import scheduler
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key")

# Initialize scheduler
scheduler.init_app(app)
scheduler.start()

def sync_courts():
    """Synchronize courts from scraper with database"""
    try:
        logger.info("Starting court synchronization...")
        
        # Get courts from scraper
        courts = update_court_list()
        
        # Fallback court list if scraper returns empty
        fallback_courts = [
            "Golden Gate Park Tennis Courts",
            "Alice Marble Tennis Courts",
            "JP Murphy Playground Tennis Courts",
            "Moscone Recreation Center Tennis Courts",
            "Hamilton Recreation Center Tennis Courts"
        ]
        
        if not courts:
            logger.warning("No courts returned from scraper, using fallback list")
            courts = fallback_courts
        
        logger.info(f"Retrieved {len(courts)} courts to sync: {courts}")
        
        # Track successful insertions
        success_count = 0
        
        # Sync each court
        for court_name in courts:
            try:
                logger.debug(f"Attempting to sync court: {court_name}")
                result = Court.create_or_update(court_name)
                success_count += 1
                logger.info(f"Successfully synced court: {court_name} - Result: {result}")
            except Exception as court_error:
                logger.error(f"Error syncing individual court {court_name}: {str(court_error)}")
        
        logger.info(f"Court synchronization completed. Successfully synced {success_count}/{len(courts)} courts.")
        return True
    except Exception as e:
        logger.error(f"Error in court synchronization: {str(e)}")
        return False

@app.route('/')
def index():
    # Get all active courts
    courts = Court.get_all_active()
    
    # Get tomorrow's date for display
    sf_timezone = ZoneInfo("America/Los_Angeles")
    now = datetime.now(sf_timezone)
    tomorrow = now + timedelta(days=1)
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')
    
    # Get the most recent preferences/user info
    user_info = UserInformation.get_latest()
    
    return render_template('index.html', 
                          courts=courts, 
                          tomorrow_date=tomorrow_str,
                          user_info=user_info)

@app.route('/courts/refresh', methods=['POST'])
def refresh_courts():
    try:
        sync_courts()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error refreshing courts: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/courts/debug', methods=['GET'])
def debug_courts():
    try:
        # Get all courts from database
        courts = Court.get_all_active()
        
        # Get freshly scraped courts
        fresh_courts = update_court_list()
        
        return jsonify({
            "database_courts": courts,
            "freshly_scraped_courts": fresh_courts
        })
    except Exception as e:
        logger.error(f"Error in debug courts: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        try:
            email = request.form.get('rec_account_email')
            password = request.form.get('rec_account_password')
            phone = request.form.get('phone_number')
            playtime_duration_str = request.form.get('playtime_duration', '60')

            if not all([email, password, phone]):
                flash('Email, Password, and Phone Number are required.', 'error')
                current_user_info = UserInformation.get_latest()
                return render_template('settings.html', 
                                     courts=None, 
                                     user_info=current_user_info) 

            try:
                playtime_duration = int(playtime_duration_str)
                if playtime_duration not in [60, 90]:
                    logger.warning(f"Invalid playtime duration: {playtime_duration}, defaulting to 60")
                    playtime_duration = 60
            except (ValueError, TypeError):
                logger.warning(f"Invalid playtime duration format: {playtime_duration_str}, defaulting to 60")
                playtime_duration = 60
            
            timestamp_to_upsert = datetime.now().isoformat()
            logging.info(f"APP_UPSERT (Settings): Attempting to upsert user with email: {email}")
            logging.info(f"APP_UPSERT (Settings): Password: {'*' * len(password) if password else 'None'}")
            logging.info(f"APP_UPSERT (Settings): Phone: {phone}")
            logging.info(f"APP_UPSERT (Settings): Duration: {playtime_duration}")
            logging.info(f"APP_UPSERT (Settings): Timestamp: {timestamp_to_upsert}")

            upsert_result = UserInformation.upsert_by_email(
                rec_account_email=email,
                rec_account_password=password, 
                phone_number=phone,
                playtime_duration=playtime_duration,
                created_at=timestamp_to_upsert
            )
            logging.info(f"APP_UPSERT (Settings): Result from upsert_by_email: {upsert_result}")

            if upsert_result:
                flash('Settings saved successfully!', 'success')
                return redirect(url_for('index')) 
            else:
                 flash('Error saving settings. Please try again.', 'error')
                 # Fall through handled below

        except Exception as e:
            logger.error(f"Error processing settings form: {str(e)}", exc_info=True)
            flash('An unexpected error occurred while saving settings.', 'error')
            # Fall through handled below

    # GET request or POST request failed/fell through
    current_user_info = UserInformation.get_latest()
    return render_template('settings.html', 
                         courts=None, 
                         user_info=current_user_info)

@app.route('/schedule-booking', methods=['POST'])
def schedule_booking():
    try:
        data = request.get_json()
        booking_time_str = data.get('booking_time')
        court_name = data.get('court_name')

        # Get email for the attempt
        latest_user_for_email = UserInformation.get_latest()
        if not latest_user_for_email or not latest_user_for_email.get('rec_account_email'):
            logger.error("SCHEDULE_BOOKING: Cannot proceed without a user email. No recent user info found or email missing.")
            return jsonify({
                'status': 'error',
                'message': 'User information not found or incomplete. Please ensure settings are saved.'
            }), 400
        user_email_for_attempt = latest_user_for_email['rec_account_email']
        logger.info(f"SCHEDULE_BOOKING: Associating attempt with email: {user_email_for_attempt}")

        # Parse the ISO string as SF local time
        sf_timezone = ZoneInfo("America/Los_Angeles")
        booking_time = datetime.fromisoformat(booking_time_str.replace('Z', '+00:00')).astimezone(sf_timezone)

        # Get current time in SF
        now = datetime.now(sf_timezone)

        # For comparison, set both times to start of day
        booking_date = datetime(
            booking_time.year, booking_time.month, booking_time.day,
            tzinfo=sf_timezone
        )
        today = datetime(
            now.year, now.month, now.day,
            tzinfo=sf_timezone
        )

        # Validate booking time is at least tomorrow
        if booking_date <= today:
            return jsonify({
                'status': 'error',
                'message': 'Booking must be for a future date'
            }), 400

        # Create booking attempt record
        attempt = BookingAttempt(
            court_name=court_name,
            booking_time=booking_time,
            user_email=user_email_for_attempt
        )
        attempt_data = attempt.save()

        if not attempt_data:
            logger.error(f"SCHEDULE_BOOKING: Failed to save booking attempt for {user_email_for_attempt}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to create booking attempt record'
            }), 500

        # Calculate days difference between booking date and today
        days_difference = (booking_date - today).days

        # If booking is within a week, attempt to book immediately
        if days_difference <= 7:
            logger.info(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - Date within 7 days. Attempting immediate booking.")

            # Get the full attempt record first (includes user_email)
            attempt_record = BookingAttempt.get_by_id(attempt_data["id"])
            if not attempt_record:
                 logger.error(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - Failed to retrieve attempt record after saving.")
                 # Update status? Unlikely to happen, but safer.
                 BookingAttempt.update_status(attempt_data["id"], 'failed', "Internal error: Could not retrieve attempt record")
                 return jsonify({
                    'status': 'error',
                    'message': 'Internal error retrieving booking details.'
                 }), 500

            email = attempt_record.get('user_email')
            if not email:
                logger.error(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - Booking attempt record is missing user_email.")
                BookingAttempt.update_status(attempt_data["id"], 'failed', "Internal error: Attempt record missing email")
                return jsonify({
                   'status': 'error',
                   'message': 'Internal error: Booking attempt missing user email.'
                }), 500

            logger.info(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - Fetching credentials for user: {email}")
            user_info = UserInformation.get_by_email(email)

            if not user_info:
                logger.error(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - No user information found for email {email}. Cannot book.")
                BookingAttempt.update_status(attempt_data["id"], 'failed', f"User info not found for email {email}")
                return jsonify({
                    'status': 'error',
                    'message': f'No user information found for {email}. Please set your settings first.'
                }), 400

            # Get the password from user info
            password = user_info.get('rec_account_password')
            if not password:
                 logger.error(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - User {email} record found, but password is missing.")
                 BookingAttempt.update_status(attempt_data["id"], 'failed', f"Password missing for user {email}")
                 return jsonify({
                     'status': 'error',
                     'message': f'Password not found for user {email}. Please update settings.'
                 }), 400

            # Initialize TennisBooker with specific user's credentials
            logger.debug(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - Initializing TennisBooker for {email}.")
            booker = TennisBooker(email, password, user_id=email)

            # Get playtime duration (default to 60 minutes if not set or invalid in user_info)
            playtime_duration = user_info.get('playtime_duration', 60)
            if playtime_duration not in [60, 90]:
                logger.warning(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - Invalid playtime duration {playtime_duration} for user {email}, defaulting to 60")
                playtime_duration = 60

            # Attempt booking
            logger.info(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - Calling booker.book_court...")
            success, error = booker.book_court(
                court_name,
                booking_time,
                playtime_duration=playtime_duration
            )
            
            # Update attempt status based on immediate attempt
            status = 'completed' if success else 'failed'
            error_message = error if error else None
            # Log the immediate result before potentially scheduling
            logger.debug(f"Updating booking attempt {attempt_data['id']} status to '{status}' after immediate attempt.")
            BookingAttempt.update_status(attempt_data["id"], status, error_message)
            
            if success:
                logger.info(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - Immediate booking successful for {email}")
                return jsonify({
                    'status': 'success',
                    'message': 'Court booked successfully'
                })
            else:
                # Immediate booking failed, schedule it for the future as a backup
                logger.warning(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - Immediate booking failed for {email}: {error}. Scheduling for the future.")
                # Schedule the booking attempt with a unique job ID
                job_id = f'booking_{attempt_data["id"]}_{booking_time.strftime("%Y%m%d_%H%M")}'
                try:
                    scheduler.add_job(
                        func='scheduler:booking_job',  # Use string reference to function
                        trigger='date',
                        run_date=booking_time,
                        args=[attempt_data["id"]],
                        id=job_id,
                        replace_existing=True # Avoid duplicate jobs if somehow triggered again
                    )
                    # Update status to 'scheduled' since immediate failed but scheduling worked
                    # Keep the original error message about the immediate failure
                    logger.info(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - Successfully scheduled future booking job {job_id} despite immediate failure.")
                    BookingAttempt.update_status(attempt_data["id"], 'scheduled', error_message) 
                    # Return success status but with a specific message
                    return jsonify({
                        'status': 'success', # Keep status success for frontend simplicity
                        'message': f'Immediate booking failed ({error_message or "reason unknown"}).' # Simplified message
                    })
                except Exception as scheduler_error:
                    # Immediate booking failed AND scheduling failed
                    full_error = f"Immediate fail: {error_message}. Scheduler fail: {str(scheduler_error)}"
                    logger.error(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - Immediate booking failed AND scheduler error for attempt {attempt_data['id']}: {str(scheduler_error)}", exc_info=True)
                    BookingAttempt.update_status(attempt_data["id"], 'failed', full_error)
                    return jsonify({
                        'status': 'error',
                        'message': f'Immediate booking failed and failed to schedule future attempt: {str(scheduler_error)}'
                    }), 500
        
        # This part is now only reached if days_difference > 7
        logger.info(f"Booking date is > 7 days away ({days_difference} days). Scheduling job.")
        job_id = f'booking_{attempt_data["id"]}_{booking_time.strftime("%Y%m%d_%H%M")}'
        try:
            scheduler.add_job(
                func='scheduler:booking_job',  # Use string reference to function
                trigger='date',
                run_date=booking_time,
                args=[attempt_data["id"]],
                id=job_id,
                replace_existing=True
            )
            logger.info(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - Successfully scheduled future booking job {job_id}.")
            # Ensure attempt status is 'scheduled'
            BookingAttempt.update_status(attempt_data["id"], 'scheduled') 
            return jsonify({
                'status': 'success',
                'message': 'Booking successfully scheduled for the future.' # Provide specific message
                })
        except Exception as scheduler_error:
            logger.error(f"SCHEDULE_BOOKING: Attempt {attempt_data['id']} - Scheduler error for future booking attempt {attempt_data['id']}: {str(scheduler_error)}", exc_info=True)
            BookingAttempt.update_status(attempt_data["id"], 'failed', f"Failed to schedule: {str(scheduler_error)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to schedule booking'
            }), 500

    except Exception as e:
        logger.error(f"Error in schedule_booking endpoint: {str(e)}", exc_info=True)
        # Attempt to find the attempt_id if it exists to mark as failed
        attempt_id = locals().get('attempt_data', {}).get('id')
        if attempt_id:
             try:
                 BookingAttempt.update_status(attempt_id, 'failed', f"Error in submission: {str(e)}")
             except Exception as update_err:
                 logger.error(f"Failed to update attempt status on error: {update_err}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/get-available-times', methods=['POST'])
def get_available_times():
    try:
        data = request.get_json()
        court_name = data.get('court_name')
        date_str = data.get('date')
        logger.debug(f"[get_available_times] Received request for court: '{court_name}', date: '{date_str}'")

        if not court_name or not date_str:
            logger.warning("[get_available_times] Missing court_name or date_str")
            return jsonify({
                'status': 'error',
                'message': 'Court name and date are required'
            }), 400

        # Get current date in SF timezone
        sf_timezone = ZoneInfo("America/Los_Angeles")
        now = datetime.now(sf_timezone)
        today = datetime(now.year, now.month, now.day, tzinfo=sf_timezone)

        # Parse the selected date
        selected_date = datetime.strptime(date_str, '%Y-%m-%d')
        selected_date = selected_date.replace(tzinfo=sf_timezone)
        logger.debug(f"[get_available_times] Parsed selected_date: {selected_date}")

        # Calculate the difference in days
        days_difference = (selected_date - today).days
        logger.debug(f"[get_available_times] Calculated days_difference: {days_difference}")

        # If within a week, scrape available times
        if days_difference <= 7:
            logger.info("[get_available_times] Date is within 7 days. Attempting to scrape publicly.")
            # Initialize TennisBooker with placeholder credentials for public scraping
            # Actual credentials from preferences are only needed for booking, not viewing times.
            logger.debug("[get_available_times] Initializing TennisBooker with dummy credentials for scraping...")
            # Use dummy values, as get_available_times likely doesn't need login
            booker = TennisBooker(email="dummy@example.com", password="dummypass") 

            # Get available times
            logger.debug(f"[get_available_times] Calling booker.get_available_times for {court_name}, {date_str}...")
            try:
                available_times = booker.get_available_times(court_name, date_str)
                logger.info(f"[get_available_times] Scraper returned {len(available_times)} times: {available_times}")

                response_data = {
                    'status': 'success',
                    'times': available_times,
                    'is_scraped': True
                }
                logger.debug(f"[get_available_times] Sending response: {response_data}")
                return jsonify(response_data)
            except Exception as scraper_error:
                 logger.error(f"[get_available_times] Error during scraping: {str(scraper_error)}", exc_info=True)
                 # Return error but indicate it was a scraping issue
                 return jsonify({
                    'status': 'error',
                    'message': 'Could not retrieve real-time availability. The booking site may be down or changed.'
                 }), 500
        else:
            # For dates beyond a week, return standard 30-minute intervals
            logger.info("[get_available_times] Date is > 7 days away. Returning standard intervals.")
            standard_times = []
            current_time = datetime(2023, 1, 1, 9, 0)  # Start at 9:00 AM
            end_time = datetime(2023, 1, 1, 18, 0)     # End at 6:00 PM

            while current_time <= end_time:
                standard_times.append(current_time.strftime('%H:%M'))
                current_time += timedelta(minutes=30)
            logger.debug(f"[get_available_times] Generated standard_times: {standard_times}")
            
            response_data = {
                'status': 'success',
                'times': standard_times,
                'is_scraped': False
            }
            logger.debug(f"[get_available_times] Sending response: {response_data}")
            return jsonify(response_data)

    except Exception as e:
        logger.error(f"[get_available_times] Error getting available times: {str(e)}", exc_info=True) # Log traceback
        return jsonify({
            'status': 'error',
            'message': f"An error occurred: {str(e)}" # Provide error details
        }), 500

@app.route('/get-available-times-for-preferences', methods=['POST'])
def get_available_times_for_preferences():
    try:
        data = request.get_json()
        court_name = data.get('court_name')
        
        if not court_name:
            return jsonify({
                'status': 'error',
                'message': 'Court name is required'
            }), 400
            
        # Get tomorrow's date
        sf_timezone = ZoneInfo("America/Los_Angeles")
        now = datetime.now(sf_timezone)
        tomorrow = now + timedelta(days=1)
        tomorrow_str = tomorrow.strftime('%Y-%m-%d')
        
        # Get the most recent user info to use credentials
        user_info = UserInformation.get_latest()
        
        if not user_info:
            return jsonify({
                'status': 'error',
                'message': 'No user information found. Please set your settings first.'
            }), 400
            
        # Initialize TennisBooker with credentials
        booker = TennisBooker(user_info['rec_account_email'], user_info['rec_account_password'])
        
        # Get available times
        logger.info(f"Getting available times for preferences: {court_name} on {tomorrow_str}")
        available_times = booker.get_available_times(court_name, tomorrow_str)
        
        if not available_times:
            logger.warning(f"No available times found for {court_name} on {tomorrow_str}")
            
        logger.info(f"Found {len(available_times)} available times")
        return jsonify({
            'status': 'success',
            'times': available_times,
            'date': tomorrow_str
        })
            
    except Exception as e:
        logger.error(f"Error getting available times for preferences: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/save-booking-info', methods=['POST'])
def save_booking_info():
    """Save the user's booking information to the user info table"""
    try:
        data = request.get_json()
        court_name = data.get('court_name')
        rec_account_email = data.get('rec_account_email')
        rec_account_password = data.get('rec_account_password')
        phone_number = data.get('phone_number')
        playtime_duration = data.get('playtime_duration', 60)
        
        # Validate required fields (excluding court_name for this specific upsert)
        if not all([rec_account_email, rec_account_password, phone_number]):
            return jsonify({
                'status': 'error',
                'message': 'Email, Password, and Phone Number are required'
            }), 400
        
        # Validate playtime duration
        try:
            playtime_duration = int(playtime_duration)
            if playtime_duration not in [60, 90]:
                logger.warning(f"Invalid playtime duration {playtime_duration}. Defaulting to 60 minutes.")
                playtime_duration = 60
        except (ValueError, TypeError):
            logger.warning(f"Invalid playtime duration format. Defaulting to 60 minutes.")
            playtime_duration = 60
        
        timestamp_to_upsert = datetime.now().isoformat()
        logging.info(f"APP_UPSERT (SaveInfo): Attempting to upsert user with email: {rec_account_email}")
        logging.info(f"APP_UPSERT (SaveInfo): Password: {'*' * len(rec_account_password) if rec_account_password else 'None'}")
        logging.info(f"APP_UPSERT (SaveInfo): Phone: {phone_number}")
        logging.info(f"APP_UPSERT (SaveInfo): Duration: {playtime_duration}")
        logging.info(f"APP_UPSERT (SaveInfo): Timestamp: {timestamp_to_upsert}")

        upsert_result = UserInformation.upsert_by_email(
            rec_account_email=rec_account_email,
            rec_account_password=rec_account_password, 
            phone_number=phone_number,
            playtime_duration=playtime_duration,
            created_at=timestamp_to_upsert
        )
        logging.info(f"APP_UPSERT (SaveInfo): Result from upsert_by_email: {upsert_result}")
        
        if not upsert_result:
            logger.error(f"APP_UPSERT (SaveInfo): upsert_by_email failed for {rec_account_email}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to save user information'
            }), 500
        
        logger.info(f"Successfully saved user information for {rec_account_email} via save-booking-info")
        return jsonify({
            'status': 'success',
            'message': 'User information saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error saving user information via save-booking-info: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == "__main__":
    # Initialize database
    init_db()
    # Sync courts on startup
    sync_courts()
    app.run(host="0.0.0.0", port=8000, debug=True)