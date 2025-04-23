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

class UserInformation:
    @staticmethod
    def get_latest() -> Optional[Dict[str, Any]]:
        """Get the most recent user record from the 'users' table."""
        response = supabase.table("users").select("*").order("created_at", desc=True).limit(1).execute()
        if not response.data:
            logger.warning("No user records found.")
            return None

        user_record = response.data[0]
        # Try to load fields that might have been stored as JSON (if applicable)
        try:
            user_record['preferred_days'] = json.loads(user_record.get('preferred_days', '[]'))
        except (json.JSONDecodeError, TypeError):
            user_record['preferred_days'] = [] 
        try:
            user_record['preferred_times'] = json.loads(user_record.get('preferred_times', '[]'))
        except (json.JSONDecodeError, TypeError):
            user_record['preferred_times'] = [] 

        # Ensure playtime_duration is valid
        if user_record.get('playtime_duration') not in [60, 90]:
            user_record['playtime_duration'] = 60

        # Set defaults for potentially missing essential fields
        user_record.setdefault('rec_account_email', None)
        user_record.setdefault('rec_account_password', None)
        user_record.setdefault('phone_number', None)
        # Remove fields no longer expected to be primary
        user_record.pop('court_name', None) 

        return user_record

    @staticmethod
    def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Get a user record by email address."""
        if not email:
            logger.warning("get_by_email called without an email.")
            return None
        try:
            response = supabase.table("users").select("*").eq("rec_account_email", email).limit(1).execute()
            if response.data:
                logger.debug(f"Found user record for email: {email}")
                # Perform similar cleanup/defaulting as get_latest if necessary
                user_record = response.data[0]
                if user_record.get('playtime_duration') not in [60, 90]:
                    user_record['playtime_duration'] = 60
                user_record.setdefault('rec_account_password', None)
                user_record.setdefault('phone_number', None)
                return user_record
            else:
                logger.warning(f"No user record found for email: {email}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving user by email {email}: {str(e)}")
            return None

    @staticmethod
    def upsert_by_email(rec_account_email: str, 
                      playtime_duration: int, 
                      created_at: datetime, 
                      rec_account_password: Optional[str] = None, 
                      phone_number: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Inserts or updates a user record in the 'users' table based on email.
        Only updates password and phone if they are provided (not None).
        """
        if not rec_account_email:
            logger.error("Cannot upsert user without an email address.")
            return None

        try:
            # Start with fields that are always updated or required for matching
            data_to_upsert = {
                "rec_account_email": rec_account_email,
                "playtime_duration": playtime_duration,
                "created_at": created_at
            }
            
            # Only include password and phone if they are provided
            if rec_account_password is not None:
                data_to_upsert["rec_account_password"] = rec_account_password
                logger.info(f"Upserting user {rec_account_email} with updated password.")
            if phone_number is not None:
                data_to_upsert["phone_number"] = phone_number
                logger.info(f"Upserting user {rec_account_email} with updated phone number.")

            logger.info(f"Upserting user record for email: {rec_account_email}")

            # Use upsert with on_conflict to handle insert vs update
            response = supabase.table("users").upsert(
                data_to_upsert,
                on_conflict="rec_account_email" 
            ).execute()

            if response.data:
                logger.info(f"Successfully upserted user {rec_account_email}")
                return response.data[0]
            else:
                # Upsert might not return data if the record already existed and wasn't changed 
                # based on Supabase settings, but the operation likely succeeded.
                logger.warning(f"Upsert for user {rec_account_email} executed, but no data returned in response. Assuming success.")
                # Return a success indicator or the known email
                existing_user = UserInformation.get_by_email(rec_account_email)
                return existing_user if existing_user else {"status": "success", "email": rec_account_email} 

        except Exception as e:
            logger.error(f"Error upserting user {rec_account_email}: {str(e)}", exc_info=True)
            return None

class BookingAttempt:
    def __init__(self, court_name: str, booking_time: datetime, user_email: str, status: str = "scheduled"):
        self.court_name = court_name
        self.booking_time = booking_time
        self.status = status
        self.error_message = None
        self.user_email = user_email

    def save(self) -> Optional[Dict[str, Any]]: 
        """Save booking attempt using the email provided during initialization."""
        if not self.user_email:
             logger.error(f"Cannot save booking attempt: Instance is missing the 'user_email'.")
             raise ValueError(f"BookingAttempt instance is missing the 'user_email' field.")

        logger.info(f"Saving booking attempt for user email: {self.user_email}")
        data = {
            "court_name": self.court_name,
            "booking_time": self.booking_time.isoformat(),
            "status": self.status,
            "error_message": self.error_message,
            "created_at": datetime.now().isoformat(),
            "user_email": self.user_email 
        }
        try:
            response = supabase.table("booking_attempts").insert(data).execute()
            
            if not response.data:
                logger.error(f"Failed to insert booking attempt for user {self.user_email}. Response: {response}")
                return None 
                
            logger.info(f"Successfully inserted booking attempt ID: {response.data[0].get('id')}")
            return response.data[0]
        except Exception as e:
             logger.error(f"Exception inserting booking attempt for user {self.user_email}: {str(e)}", exc_info=True)
             return None 

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