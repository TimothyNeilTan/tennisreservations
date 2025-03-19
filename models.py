import logging
from datetime import datetime
import json
from typing import Dict, Any, List, Optional
from database import supabase

logger = logging.getLogger(__name__)

class Court:
    def __init__(self, name: str, active: bool = True):
        self.name = name
        self.active = active
        self.last_updated = datetime.now().isoformat()

    @staticmethod
    def get_all_active() -> List[Dict[str, Any]]:
        """Get all active courts"""
        try:
            response = supabase.table("courts").select("*").eq("active", True).order("name").execute()
            logger.debug(f"Retrieved {len(response.data)} active courts")
            return response.data
        except Exception as e:
            logger.error(f"Error retrieving active courts: {str(e)}")
            return []

    @staticmethod
    def create_or_update(name: str, active: bool = True) -> Dict[str, Any]:
        """Create or update a court"""
        try:
            logger.debug(f"Creating/updating court: {name}")
            data = {
                "name": name,
                "active": active,
                "last_updated": datetime.now().isoformat()
            }
            
            # Check if court exists
            logger.debug(f"Checking if court exists: {name}")
            existing = supabase.table("courts").select("*").eq("name", name).execute()
            
            if existing.data:
                logger.debug(f"Updating existing court: {name}")
                response = supabase.table("courts").update(data).eq("name", name).execute()
            else:
                logger.debug(f"Inserting new court: {name}")
                response = supabase.table("courts").insert(data).execute()
            
            if not response.data:
                raise Exception("No data returned from database operation")
            
            logger.info(f"Successfully created/updated court {name}")
            return response.data[0]
        except Exception as e:
            error_msg = f"Error creating/updating court {name}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

class BookingPreference:
    def __init__(self, court_name: str, preferred_days: List[str], 
                 preferred_times: List[str], rec_account_email: str, 
                 rec_account_password: str, phone_number: str, playtime_duration: int = 60):
        self.court_name = court_name
        self.preferred_days = json.dumps(preferred_days)
        self.preferred_times = json.dumps(preferred_times)
        self.rec_account_email = rec_account_email
        self.rec_account_password = rec_account_password
        self.phone_number = phone_number
        self.playtime_duration = playtime_duration

    @staticmethod
    def get_latest() -> Optional[Dict[str, Any]]:
        """Get the most recent booking preference"""
        response = supabase.table("booking_preferences").select("*").order("created_at", desc=True).limit(1).execute()
        if not response.data:
            return None
            
        pref = response.data[0]
        # Parse JSON fields
        try:
            pref['preferred_days'] = json.loads(pref['preferred_days'])
            pref['preferred_times'] = json.loads(pref['preferred_times'])
        except (json.JSONDecodeError, KeyError):
            # If JSON parsing fails, return empty lists
            pref['preferred_days'] = []
            pref['preferred_times'] = []
        
        # Set default playtime duration if not present or invalid
        if 'playtime_duration' not in pref or pref['playtime_duration'] is None or pref['playtime_duration'] not in [60, 90]:
            pref['playtime_duration'] = 60
            
        return pref

    def save(self) -> Dict[str, Any]:
        """Save booking preference"""
        data = {
            "court_name": self.court_name,
            "preferred_days": self.preferred_days,
            "preferred_times": self.preferred_times,
            "rec_account_email": self.rec_account_email,
            "rec_account_password": self.rec_account_password,
            "phone_number": self.phone_number,
            "playtime_duration": self.playtime_duration,
            "created_at": datetime.now().isoformat()
        }
        response = supabase.table("booking_preferences").insert(data).execute()
        return response.data[0] if response.data else None

class BookingAttempt:
    def __init__(self, court_name: str, booking_time: datetime, status: str = "scheduled"):
        self.court_name = court_name
        self.booking_time = booking_time
        self.status = status
        self.error_message = None

    def save(self) -> Dict[str, Any]:
        """Save booking attempt"""
        data = {
            "court_name": self.court_name,
            "booking_time": self.booking_time.isoformat(),
            "status": self.status,
            "error_message": self.error_message,
            "created_at": datetime.now().isoformat()
        }
        response = supabase.table("booking_attempts").insert(data).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def get_by_id(id: int) -> Optional[Dict[str, Any]]:
        """Get booking attempt by ID"""
        response = supabase.table("booking_attempts").select("*").eq("id", id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def update_status(id: int, status: str, error_message: str = None) -> Dict[str, Any]:
        """Update booking attempt status"""
        data = {
            "status": status,
            "error_message": error_message
        }
        response = supabase.table("booking_attempts").update(data).eq("id", id).execute()
        return response.data[0] if response.data else None