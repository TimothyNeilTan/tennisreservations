from app import db
import json

class Court(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)
    last_updated = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

class BookingPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    court_name = db.Column(db.String(100), nullable=False)
    preferred_days = db.Column(db.String(200), nullable=False)  # Stored as JSON
    preferred_times = db.Column(db.String(200), nullable=False)  # Stored as JSON
    rec_account_email = db.Column(db.String(120), nullable=False)
    rec_account_password = db.Column(db.String(120), nullable=False)

    def set_preferred_days(self, days):
        self.preferred_days = json.dumps(days)

    def get_preferred_days(self):
        return json.loads(self.preferred_days)

    def set_preferred_times(self, times):
        self.preferred_times = json.dumps(times)

    def get_preferred_times(self):
        return json.loads(self.preferred_times)

class BookingAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    court_name = db.Column(db.String(100), nullable=False)
    booking_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # scheduled, completed, failed
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())