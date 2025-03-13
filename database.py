import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def init_db():
    """Test database connection and ensure tables exist"""
    try:
        logger.info("Testing database connection...")
        
        # Test connection by trying to select from courts table
        response = supabase.table("courts").select("*").limit(1).execute()
        logger.info("Successfully connected to database")
        
        return True
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

# Test database connection on module import
try:
    init_db()
except Exception as e:
    logger.error("Failed to initialize database connection")
    raise 