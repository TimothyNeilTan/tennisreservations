from typing import Dict, Optional
import uuid
from datetime import datetime
import json
import os

class UserSession:
    def __init__(self, user_id: str, email: str, password: str):
        self.user_id = user_id
        self.email = email
        self.password = password
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        self.verification_code = None
        self.code_received = False
        self.reservation_status = "idle"  # idle, waiting_for_code, booking, completed, failed
        self.reservation_details = None

class UserManager:
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        self.reservation_queue = []
        self.load_users()

    def load_users(self):
        """Load user credentials from a JSON file"""
        if os.path.exists('users.json'):
            with open('users.json', 'r') as f:
                users_data = json.load(f)
                for user_data in users_data:
                    session = UserSession(
                        user_id=user_data['user_id'],
                        email=user_data['email'],
                        password=user_data['password']
                    )
                    self.sessions[user_data['user_id']] = session

    def save_users(self):
        """Save user credentials to a JSON file"""
        users_data = []
        for session in self.sessions.values():
            users_data.append({
                'user_id': session.user_id,
                'email': session.email,
                'password': session.password
            })
        with open('users.json', 'w') as f:
            json.dump(users_data, f, indent=2)

    def create_session(self, email: str, password: str) -> str:
        """Create a new user session"""
        user_id = str(uuid.uuid4())
        session = UserSession(user_id, email, password)
        self.sessions[user_id] = session
        self.save_users()
        return user_id

    def get_session(self, user_id: str) -> Optional[UserSession]:
        """Get a user session by ID"""
        return self.sessions.get(user_id)

    def update_verification_code(self, user_id: str, code: str):
        """Update the verification code for a user"""
        session = self.get_session(user_id)
        if session:
            session.verification_code = code
            session.code_received = True
            session.last_active = datetime.now()

    def get_verification_code(self, user_id: str) -> Optional[str]:
        """Get the verification code for a user"""
        session = self.get_session(user_id)
        if session and session.code_received:
            return session.verification_code
        return None

    def add_to_queue(self, user_id: str, reservation_details: dict):
        """Add a user to the reservation queue"""
        session = self.get_session(user_id)
        if session:
            session.reservation_status = "waiting_for_code"
            session.reservation_details = reservation_details
            self.reservation_queue.append(user_id)

    def get_next_in_queue(self) -> Optional[str]:
        """Get the next user in the reservation queue"""
        if self.reservation_queue:
            return self.reservation_queue.pop(0)
        return None

    def update_reservation_status(self, user_id: str, status: str):
        """Update the reservation status for a user"""
        session = self.get_session(user_id)
        if session:
            session.reservation_status = status
            session.last_active = datetime.now()

    def cleanup_inactive_sessions(self, max_age_minutes: int = 30):
        """Remove inactive sessions"""
        current_time = datetime.now()
        inactive_sessions = []
        
        for user_id, session in self.sessions.items():
            age = (current_time - session.last_active).total_seconds() / 60
            if age > max_age_minutes:
                inactive_sessions.append(user_id)
        
        for user_id in inactive_sessions:
            del self.sessions[user_id]
        
        self.save_users() 