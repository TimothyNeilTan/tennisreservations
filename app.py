import os
import logging
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
from zoneinfo import ZoneInfo
from court_scraper import update_court_list

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key")

# Configure SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tennis_bookings.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

from models import BookingPreference, BookingAttempt, Court
from scheduler import scheduler

# Initialize scheduler
scheduler.init_app(app)
scheduler.start()

def sync_courts():
    """Synchronize courts from scraper with database"""
    try:
        courts = update_court_list()
        for court_name in courts:
            court = Court.query.filter_by(name=court_name).first()
            if not court:
                court = Court(name=court_name)
                db.session.add(court)
        db.session.commit()
    except Exception as e:
        logger.error(f"Error syncing courts: {str(e)}")

@app.route('/')
def index():
    courts = Court.query.filter_by(active=True).all()
    return render_template('index.html', courts=courts)

@app.route('/courts/refresh', methods=['POST'])
def refresh_courts():
    try:
        sync_courts()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error refreshing courts: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    if request.method == 'POST':
        try:
            pref = BookingPreference(
                court_name=request.form['court_name'],
                preferred_days=request.form.getlist('preferred_days'),
                preferred_times=request.form.getlist('preferred_times'),
                rec_account_email=request.form['rec_account_email'],
                rec_account_password=request.form['rec_account_password']
            )
            db.session.add(pref)
            db.session.commit()
            flash('Preferences saved successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Error saving preferences: {str(e)}")
            flash('Error saving preferences', 'error')

    courts = Court.query.filter_by(active=True).all()
    return render_template('preferences.html', courts=courts)

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
            booking_time=booking_time,
            status='scheduled'
        )
        db.session.add(attempt)
        db.session.commit()

        # Schedule the booking attempt
        scheduler.add_job(
            'booking_job',
            'date',
            run_date=booking_time,
            args=[attempt.id]
        )

        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error scheduling booking: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

with app.app_context():
    db.create_all()
    # Sync courts on startup
    sync_courts()