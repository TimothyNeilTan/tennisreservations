import os
import logging
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

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

from models import BookingPreference, BookingAttempt
from scheduler import scheduler

# Initialize scheduler
scheduler.init_app(app)
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html')

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

    return render_template('preferences.html')

@app.route('/schedule-booking', methods=['POST'])
def schedule_booking():
    try:
        data = request.get_json()
        booking_time_str = data.get('booking_time')
        court_name = data.get('court_name')

        # Convert ISO string to datetime object
        booking_time = datetime.fromisoformat(booking_time_str.replace('Z', '+00:00'))

        # Get current date/time for comparison
        now = datetime.now()

        # Validate booking time is at least tomorrow
        if booking_time.date() < (now.date()):
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