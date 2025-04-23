from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file (optional, useful for local dev)
load_dotenv()

# --- Configuration ---
# Load Supabase credentials from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
# Use SUPABASE_KEY (Service Role or other non-anon key) - Keep this secure!
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") 

# Timezone Configuration
try:
    SF_TIMEZONE = ZoneInfo("America/Los_Angeles")
except ZoneInfoNotFoundError:
    print("Error: Timezone 'America/Los_Angeles' not found. Please ensure timezone data is available.")
    exit(1) 
# --- End Configuration ---

def get_scheduled_bookings_for_a_week_from_now(supabase: Client):
    """
    Queries the Supabase database for booking attempts scheduled exactly 3 days from today.

    Args:
        supabase: An initialized Supabase client instance.

    Returns:
        list: A list of dictionaries representing the matching rows, or None if an error occurs.
    """
    try:
        # Calculate the target date (7 days from now in SF time)
        now_sf = datetime.now(SF_TIMEZONE)
        target_date_sf = now_sf.date() + timedelta(days=3)
        
        print(f"Checking for scheduled bookings on: {target_date_sf.strftime('%Y-%m-%d')}")

        # Determine the query range in UTC
        # Start of the target day in SF time
        start_of_day_sf = datetime.combine(target_date_sf, time.min, tzinfo=SF_TIMEZONE)
        # Start of the *next* day in SF time
        start_of_next_day_sf = start_of_day_sf + timedelta(days=1)
        
        # Convert boundaries to UTC ISO format strings (Supabase typically uses TIMESTAMPTZ referenced to UTC)
        start_utc_iso = start_of_day_sf.astimezone(ZoneInfo("UTC")).isoformat()
        end_utc_iso = start_of_next_day_sf.astimezone(ZoneInfo("UTC")).isoformat()

        print(f"Querying UTC range: {start_utc_iso} to {end_utc_iso}")

        # Query Supabase
        response = (
            supabase.table("booking_attempts")
            .select("*")
            .eq("status", "scheduled")
            .gte("booking_time", start_utc_iso) # booking_time >= start of target day (UTC)
            .lt("booking_time", end_utc_iso)    # booking_time < start of next day (UTC)
            .execute()
        )
        
        # Check for errors in the response
        if hasattr(response, 'error') and response.error:
             print(f"Supabase query error: {response.error}")
             return None

        # Return the data part of the response
        return response.data

    except Exception as e:
        print(f"An unexpected error occurred during Supabase query: {e}")
        return None

if __name__ == "__main__":
    print("Running scheduled booking check...")

    # Validate Supabase configuration
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set.")
        print("Please create a .env file or set them in your environment.")
    else:
        try:
            # Initialize Supabase client using SUPABASE_KEY
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            print("Supabase client initialized.")

            # Get bookings
            bookings = get_scheduled_bookings_for_a_week_from_now(supabase)
            
            if bookings is not None:
                if bookings:
                    print(f"\nFound {len(bookings)} scheduled booking attempt(s) for 3 days from now:")
                    # Supabase client returns list of dictionaries directly
                    for booking in bookings:
                        # Adjust printing based on actual column names in your Supabase table
                        print(f"- ID: {booking.get('id')}, Court: {booking.get('court_name')}, Time: {booking.get('booking_time')}, Status: {booking.get('status')}")
                else:
                    print("\nNo scheduled booking attempts found for 7 days from now.")
            else:
                print("\nFailed to retrieve scheduled bookings due to an error during the query.")
        
        except Exception as e:
            print(f"Failed to initialize Supabase client or run check: {e}") 