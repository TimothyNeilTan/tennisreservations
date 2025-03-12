import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def init_db():
    """Initialize database tables if they don't exist"""
    # Create courts table
    supabase.table("courts").execute()
    
    # Create booking_preferences table
    supabase.table("booking_preferences").execute()
    
    # Create booking_attempts table
    supabase.table("booking_attempts").execute() 