import logging
from datetime import datetime, timedelta
import json
from typing import Dict, Any, List, Optional
import os # Added for environment variable access
from cryptography.fernet import Fernet # Added for encryption
from database import supabase

logger = logging.getLogger(__name__)

# --- Encryption Setup ---
# Load the secret key from environment variable
# Ensure ENCRYPTION_KEY is set in your environment!
encryption_key = os.getenv('ENCRYPTION_KEY')
if not encryption_key:
    logger.critical("CRITICAL: ENCRYPTION_KEY environment variable not set. Password encryption/decryption will fail.")
    # Optionally raise an error here to prevent the app from starting without a key
    # raise ValueError("ENCRYPTION_KEY environment variable not set.")
    fernet = None # Set fernet to None to indicate unavailability
else:
    try:
        fernet = Fernet(encryption_key.encode()) # Create Fernet instance
        logger.info("Encryption key loaded successfully.")
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to initialize Fernet with provided key. Error: {e}")
        fernet = None
        # raise # Re-raise exception to halt execution if key is invalid

def encrypt_data(data: str) -> Optional[str]:
    """Encrypts a string using the loaded Fernet key."""
    if not fernet or not data:
        # Log warning if encryption isn't possible or data is empty
        if not fernet: logger.error("Encryption attempted but Fernet key is not available/valid.")
        return data # Return original data if encryption cannot occur or data is empty
    try:
        return fernet.encrypt(data.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return None # Indicate encryption failure

def decrypt_data(encrypted_data: str) -> Optional[str]:
    """Decrypts a string using the loaded Fernet key."""
    if not fernet or not encrypted_data:
        # Log warning if decryption isn't possible or data is empty
        if not fernet: logger.error("Decryption attempted but Fernet key is not available/valid.")
        return encrypted_data # Return original data if decryption cannot occur or data is empty
    try:
        # Ensure the data is bytes
        return fernet.decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        # Common error: InvalidToken if key mismatch or data corrupted
        logger.error(f"Decryption failed: {e}. Returning None.") 
        return None # Indicate decryption failure
# --- End Encryption Setup ---

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
        """Get the most recent user record, decrypting password and phone number."""
        response = supabase.table("users").select("*").order("created_at", desc=True).limit(1).execute()
        if not response.data:
            logger.warning("No user records found.")
            return None

        user_record = response.data[0]
        
        # --- Decrypt Password ---
        encrypted_password = user_record.get('rec_account_password')
        if encrypted_password:
            decrypted_password = decrypt_data(encrypted_password)
            if decrypted_password is None:
                 logger.error(f"Failed to decrypt password for user {user_record.get('rec_account_email')}. Automation may fail.")
                 user_record['rec_account_password'] = None # Set to None if decryption fails
            else:
                 user_record['rec_account_password'] = decrypted_password
        else:
            user_record['rec_account_password'] = None # Ensure it's None if not present
        # --- End Decrypt ---
        
        # --- Decrypt Phone Number ---
        encrypted_phone = user_record.get('phone_number')
        if encrypted_phone:
            decrypted_phone = decrypt_data(encrypted_phone)
            if decrypted_phone is None:
                 logger.error(f"Failed to decrypt phone number for user {user_record.get('rec_account_email')}. Returning None for phone.")
                 user_record['phone_number'] = None
            else:
                 user_record['phone_number'] = decrypted_phone
        else:
            user_record['phone_number'] = None
        # --- End Decrypt Phone ---
        
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
        """Get a user record by email, decrypting password and phone number."""
        if not email:
            logger.warning("get_by_email called without an email.")
            return None
        try:
            response = supabase.table("users").select("*").eq("rec_account_email", email).limit(1).execute()
            if response.data:
                logger.debug(f"Found user record for email: {email}")
                user_record = response.data[0]
                
                # --- Decrypt Password ---
                encrypted_password = user_record.get('rec_account_password')
                if encrypted_password:
                    decrypted_password = decrypt_data(encrypted_password)
                    if decrypted_password is None:
                        logger.error(f"Failed to decrypt password for user {email}. Automation may fail.")
                        user_record['rec_account_password'] = None
                    else:
                        user_record['rec_account_password'] = decrypted_password
                else:
                     user_record['rec_account_password'] = None
                # --- End Decrypt ---
                
                # --- Decrypt Phone Number ---
                encrypted_phone = user_record.get('phone_number')
                if encrypted_phone:
                    decrypted_phone = decrypt_data(encrypted_phone)
                    if decrypted_phone is None:
                        logger.error(f"Failed to decrypt phone number for user {email}. Returning None for phone.")
                        user_record['phone_number'] = None
                    else:
                        user_record['phone_number'] = decrypted_phone
                else:
                     user_record['phone_number'] = None
                # --- End Decrypt Phone ---
                
                if user_record.get('playtime_duration') not in [60, 90]:
                    user_record['playtime_duration'] = 60
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
        Inserts or updates user record, encrypting password and phone number if provided.
        """
        if not rec_account_email:
            logger.error("Cannot upsert user without an email address.")
            return None

        try:
            data_to_upsert = {
                "rec_account_email": rec_account_email,
                "playtime_duration": playtime_duration,
                "created_at": created_at
            }
            
            # --- Encrypt Password if provided ---
            if rec_account_password is not None:
                encrypted_password = encrypt_data(rec_account_password)
                if encrypted_password is None:
                    logger.error(f"Failed to encrypt password for user {rec_account_email}. Aborting upsert for password.")
                    # Decide if you want to proceed without password or abort entirely
                    # Let's proceed without password for now, but log critical error
                    pass # Don't add password to upsert data
                else:
                     data_to_upsert["rec_account_password"] = encrypted_password
                     logger.info(f"Upserting user {rec_account_email} with encrypted password.")
            # --- End Encrypt ---

            # --- Encrypt Phone Number if provided ---
            if phone_number is not None:
                encrypted_phone = encrypt_data(phone_number)
                if encrypted_phone is None:
                    logger.error(f"Failed to encrypt phone number for user {rec_account_email}. Aborting upsert for phone number.")
                    # Decide if you want to proceed without phone or abort entirely
                    pass # Don't add phone to upsert data
                else:
                     data_to_upsert["phone_number"] = encrypted_phone
                     logger.info(f"Upserting user {rec_account_email} with encrypted phone number.")
            # --- End Encrypt Phone ---

            logger.info(f"Upserting user record for email: {rec_account_email}")
            response = supabase.table("users").upsert(
                data_to_upsert,
                on_conflict="rec_account_email" 
            ).execute()

            if response.data:
                logger.info(f"Successfully upserted user {rec_account_email}")
                # Decrypt password for immediate return if needed, or rely on subsequent gets
                # For simplicity, let's return the potentially encrypted data as is from upsert
                # Caller should use get_by_email if decrypted data is immediately required
                return response.data[0]
            else:
                logger.warning(f"Upsert for user {rec_account_email} executed, but no data returned. Assuming success.")
                existing_user = UserInformation.get_by_email(rec_account_email)
                return existing_user if existing_user else {"status": "success", "email": rec_account_email}

        except Exception as e:
            logger.error(f"Error upserting user {rec_account_email}: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def get_by_phone_number(phone_number: str) -> Optional[Dict[str, Any]]:
        """Get a user record by phone number. NOTE: Requires searching encrypted data if phone is encrypted.
           This current implementation will likely FAIL if phone numbers are encrypted, 
           as Supabase cannot directly match the encrypted value unless specifically configured.
           Consider fetching by email or ID instead if phone is encrypted.
        """
        # !! WARNING: THIS METHOD WILL LIKELY BREAK IF PHONE NUMBERS ARE ENCRYPTED !!
        # Searching for an exact match on an encrypted value requires the database to 
        # perform the exact same encryption or requires a different search strategy.
        # For now, we will add decryption, assuming a match *could* be found somehow,
        # but this method needs rethinking if used with encrypted phones.
        logger.warning("get_by_phone_number may not work correctly with encrypted phone numbers.")

        if not phone_number:
            logger.warning("get_by_phone_number called without a phone number.")
            return None
        try:
            # This .eq() query will probably not find encrypted matches directly.
            # You would need to fetch potential candidates some other way and decrypt,
            # or use database-level encryption features if available/appropriate.
            response = supabase.table("users").select("*").eq("phone_number", encrypt_data(phone_number)).limit(1).execute() # Attempt to search by encrypted value
            
            if response.data:
                logger.debug(f"Found potential user record matching encrypted phone number: {phone_number}")
                user_record = response.data[0]
                
                # --- Decrypt Password ---
                encrypted_password = user_record.get('rec_account_password')
                if encrypted_password:
                    decrypted_password = decrypt_data(encrypted_password)
                    user_record['rec_account_password'] = decrypted_password # Assign None if decrypt fails
                else:
                     user_record['rec_account_password'] = None
                # --- End Decrypt Password ---

                # --- Decrypt Phone Number ---
                encrypted_phone_retrieved = user_record.get('phone_number') # Get the actual stored value
                if encrypted_phone_retrieved:
                    decrypted_phone = decrypt_data(encrypted_phone_retrieved)
                    if decrypted_phone is None:
                         logger.error(f"Failed to decrypt phone number for user {user_record.get('rec_account_email')}. Returning None for phone.")
                         user_record['phone_number'] = None
                    else:
                         # Store the decrypted phone number back in the record being returned
                         user_record['phone_number'] = decrypted_phone 
                else:
                     user_record['phone_number'] = None
                # --- End Decrypt Phone ---
                
                return user_record
            else:
                logger.warning(f"No user record found matching encrypted phone number: {phone_number}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving user by encrypted phone number {phone_number}: {str(e)}")
            return None

    @staticmethod
    def update_verification_code(email: str, code: str) -> bool:
        """Updates the verification code and timestamp for a user."""
        if not email or not code:
            logger.error("update_verification_code requires email and code.")
            return False
        try:
            update_data = {
                "verification_code": code,
                "verification_code_timestamp": datetime.now().isoformat()
            }
            response = supabase.table("users").update(update_data).eq("rec_account_email", email).execute()
            
            # Check if the update affected any row
            if response.data: # Supabase update returns the updated rows
                 logger.info(f"Successfully updated verification code for user {email}")
                 return True
            else:
                 # This might happen if the email doesn't exist, or if the data is the same.
                 # Check if user exists to differentiate
                 user_exists_res = supabase.table("users").select("rec_account_email").eq("rec_account_email", email).limit(1).execute()
                 if not user_exists_res.data:
                     logger.warning(f"Attempted to update verification code for non-existent user: {email}")
                 else:
                      logger.warning(f"Verification code update for {email} did not return data (maybe code unchanged or issue?). Response: {response}")
                 return False # Indicate potential issue or no actual update
        except Exception as e:
            logger.error(f"Error updating verification code for user {email}: {str(e)}")
            return False

    @staticmethod
    def get_and_clear_verification_code(email: str, max_age_minutes: int = 5) -> Optional[str]:
        """Gets the latest verification code if it's recent enough, then clears it."""
        if not email:
            logger.error("get_and_clear_verification_code requires an email.")
            return None
        
        try:
            # 1. Get user and current code/timestamp
            response = supabase.table("users").select("verification_code, verification_code_timestamp").eq("rec_account_email", email).limit(1).execute()
            
            if not response.data:
                logger.warning(f"User not found for verification code retrieval: {email}")
                return None

            user_data = response.data[0]
            code = user_data.get("verification_code")
            timestamp_str = user_data.get("verification_code_timestamp")

            if not code or not timestamp_str:
                logger.info(f"No verification code found for user: {email}")
                return None

            # 2. Check timestamp validity
            try:
                # Supabase TIMESTAMPTZ often includes timezone info like +00:00
                # datetime.fromisoformat handles this directly in Python 3.7+
                timestamp = datetime.fromisoformat(timestamp_str)
                # Make timestamp timezone-aware (UTC) if it's naive, assuming Supabase stores in UTC
                if timestamp.tzinfo is None:
                     # This might be risky if server timezone != UTC. Best if Supabase returns TZ info.
                     # Let's assume fromisoformat handles the +00:00 correctly.
                     pass 
                
                now_utc = datetime.now(timestamp.tzinfo) # Use the same timezone for comparison
                age = now_utc - timestamp

                if age > timedelta(minutes=max_age_minutes):
                    logger.warning(f"Verification code for {email} has expired (received at {timestamp_str}).")
                    # Optionally clear the expired code here as well
                    # supabase.table("users").update({"verification_code": None, "verification_code_timestamp": None}).eq("rec_account_email", email).execute()
                    return None
            except ValueError as e:
                logger.error(f"Error parsing verification code timestamp '{timestamp_str}' for user {email}: {e}")
                return None

            # 3. Clear the code in the database
            clear_data = {
                "verification_code": None,
                "verification_code_timestamp": None
            }
            clear_response = supabase.table("users").update(clear_data).eq("rec_account_email", email).execute()

            if not clear_response.data:
                 logger.warning(f"Could not clear verification code for user {email} after retrieval. It might be retrieved again.")
                 # Decide if we should still return the code or not. Let's return it for now.

            logger.info(f"Retrieved and cleared verification code for user: {email}")
            return code # Return the valid, now-cleared code

        except Exception as e:
            logger.error(f"Error getting/clearing verification code for user {email}: {str(e)}")
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