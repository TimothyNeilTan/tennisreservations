import os
import logging
import json
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from court_scraper import update_court_list
from automation import TennisBooker
from models import Court, BookingPreference, BookingAttempt
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
    
    # Get the most recent preferences
    preferences = BookingPreference.get_latest()
    
    return render_template('index.html', 
                          courts=courts, 
                          tomorrow_date=tomorrow_str,
                          preferences=preferences)

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

@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    if request.method == 'POST':
        try:
            # Get preferred times from the hidden input (comma-separated string)
            preferred_times_str = request.form.get('preferred_times', '')
            preferred_times = preferred_times_str.split(',') if preferred_times_str else []
            
            # Filter out any empty strings
            preferred_times = [time for time in preferred_times if time.strip()]
            
            # Ensure all times are in the correct format (HH:MM)
            for i, time in enumerate(preferred_times):
                if not time.strip():
                    continue
                    
                # If time doesn't match HH:MM format, log an error
                if not re.match(r'^\d{2}:\d{2}$', time):
                    logger.warning(f"Invalid time format: {time}, skipping")
                    preferred_times[i] = None
            
            # Remove any None values
            preferred_times = [time for time in preferred_times if time is not None]
            
            # Get playtime duration (default to 60 minutes)
            playtime_duration = request.form.get('playtime_duration', '60')
            try:
                playtime_duration = int(playtime_duration)
                # Validate that playtime duration is one of the allowed values
                if playtime_duration not in [60, 90]:
                    logger.warning(f"Invalid playtime duration: {playtime_duration}, defaulting to 60")
                    playtime_duration = 60
            except (ValueError, TypeError):
                logger.warning(f"Invalid playtime duration format: {playtime_duration}, defaulting to 60")
                playtime_duration = 60
            
            pref = BookingPreference(
                court_name=request.form['court_name'],
                preferred_days=request.form.getlist('preferred_days'),
                preferred_times=preferred_times,
                playtime_duration=playtime_duration,
                rec_account_email=request.form['rec_account_email'],
                rec_account_password=request.form['rec_account_password'],
                phone_number=request.form['phone_number']
            )
            pref.save()
            flash('Preferences saved successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Error saving preferences: {str(e)}")
            flash('Error saving preferences', 'error')

    # Get the most recent preferences and courts
    current_preferences = BookingPreference.get_latest()
    courts = Court.get_all_active()
    
    return render_template('preferences.html', 
                         courts=courts, 
                         preferences=current_preferences)

@app.route('/schedule-booking', methods=['POST'])
def schedule_booking():
    try:
        data = request.get_json()
        booking_time_str = data.get('booking_time')
        court_name = data.get('court_name')

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
            booking_time=booking_time
        )
        attempt_data = attempt.save()

        if not attempt_data:
            return jsonify({
                'status': 'error',
                'message': 'Failed to create booking attempt'
            }), 500

        # Schedule the booking attempt with a unique job ID
        job_id = f'booking_{attempt_data["id"]}_{booking_time.strftime("%Y%m%d_%H%M")}'

        try:
            scheduler.add_job(
                func='scheduler:booking_job',  # Use string reference to function
                trigger='date',
                run_date=booking_time,
                args=[attempt_data["id"]],
                id=job_id
            )
        except Exception as scheduler_error:
            logger.error(f"Scheduler error: {str(scheduler_error)}")
            attempt.update_status('failed', f"Failed to schedule: {str(scheduler_error)}")
            return jsonify({
                'status': 'error',
                'message': 'Failed to schedule booking'
            }), 500

        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error scheduling booking: {str(e)}")
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
        
        if not court_name or not date_str:
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
        
        # Calculate the difference in days
        days_difference = (selected_date - today).days
        
        # If within a week, scrape available times
        if days_difference <= 7:
            # Get the most recent preferences to use credentials
            pref = BookingPreference.get_latest()
            
            if not pref:
                return jsonify({
                    'status': 'error',
                    'message': 'No booking preferences found. Please set your preferences first.'
                }), 400
                
            # Initialize TennisBooker with credentials
            booker = TennisBooker(pref['rec_account_email'], pref['rec_account_password'])
            
            # Get available times
            available_times = booker.get_available_times(court_name, date_str)
            
            return jsonify({
                'status': 'success',
                'times': available_times,
                'is_scraped': True
            })
        else:
            # For dates beyond a week, return standard 30-minute intervals
            standard_times = []
            current_time = datetime(2023, 1, 1, 9, 0)  # Start at 9:00 AM
            end_time = datetime(2023, 1, 1, 18, 0)     # End at 6:00 PM
            
            while current_time <= end_time:
                standard_times.append(current_time.strftime('%H:%M'))
                current_time += timedelta(minutes=30)
                
            return jsonify({
                'status': 'success',
                'times': standard_times,
                'is_scraped': False
            })
            
    except Exception as e:
        logger.error(f"Error getting available times: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
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
        
        # Get the most recent preferences to use credentials
        pref = BookingPreference.get_latest()
        
        if not pref:
            return jsonify({
                'status': 'error',
                'message': 'No booking preferences found. Please set your preferences first.'
            }), 400
            
        # Initialize TennisBooker with credentials
        booker = TennisBooker(pref['rec_account_email'], pref['rec_account_password'])
        
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
    """Save the user's booking information to the preferences table"""
    try:
        data = request.get_json()
        court_name = data.get('court_name')
        rec_account_email = data.get('rec_account_email')
        rec_account_password = data.get('rec_account_password')
        phone_number = data.get('phone_number')
        playtime_duration = data.get('playtime_duration', 60)
        
        # Validate required fields
        if not all([court_name, rec_account_email, rec_account_password, phone_number]):
            return jsonify({
                'status': 'error',
                'message': 'All fields are required'
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
        
        # Get the latest preferences to maintain the preferred days and times
        current_preferences = BookingPreference.get_latest()
        
        # Use existing values or empty lists if no preferences exist
        preferred_days = current_preferences.get('preferred_days', []) if current_preferences else []
        preferred_times = current_preferences.get('preferred_times', []) if current_preferences else []
        
        # Create a new booking preference
        pref = BookingPreference(
            court_name=court_name,
            preferred_days=preferred_days,
            preferred_times=preferred_times,
            playtime_duration=playtime_duration,
            rec_account_email=rec_account_email,
            rec_account_password=rec_account_password,
            phone_number=phone_number
        )
        
        # Save to database
        result = pref.save()
        
        if not result:
            return jsonify({
                'status': 'error',
                'message': 'Failed to save booking information'
            }), 500
        
        logger.info(f"Successfully saved booking information for {rec_account_email}")
        return jsonify({
            'status': 'success',
            'message': 'Booking information saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error saving booking information: {str(e)}")
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