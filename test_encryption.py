import os
import logging
from cryptography.fernet import Fernet
from typing import Optional
# Use python-dotenv to load .env file if present (optional but recommended for local dev)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded environment variables from .env file (if found).")
except ImportError:
    print("python-dotenv not installed, skipping .env file loading.")
    pass 

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Replicated Encryption Setup from models.py ---
# Load the secret key from environment variable
encryption_key = os.getenv('ENCRYPTION_KEY')
fernet = None # Initialize fernet as None

if not encryption_key:
    logger.critical("CRITICAL: ENCRYPTION_KEY environment variable not set. Testing will fail.")
else:
    try:
        fernet = Fernet(encryption_key.encode()) # Create Fernet instance
        logger.info("Encryption key loaded successfully for testing.")
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to initialize Fernet with provided key. Error: {e}")
        fernet = None

def encrypt_data(data: str) -> Optional[str]:
    """Encrypts a string using the loaded Fernet key."""
    if not fernet or not data:
        if not fernet: logger.error("Encryption attempted but Fernet key is not available/valid.")
        return data 
    try:
        return fernet.encrypt(data.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return None

def decrypt_data(encrypted_data: str) -> Optional[str]:
    """Decrypts a string using the loaded Fernet key."""
    if not fernet or not encrypted_data:
        if not fernet: logger.error("Decryption attempted but Fernet key is not available/valid.")
        return encrypted_data
    try:
        return fernet.decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}. Returning None.") 
        return None
# --- End Replicated Encryption Setup ---

if __name__ == "__main__":
    print("\n--- Encryption Test Script ---")
    
    if not fernet:
        print("ERROR: Encryption key not loaded. Please set the ENCRYPTION_KEY environment variable.")
    else:
        while True:
            print("\nEnter the text you want to encrypt and decrypt (or type 'quit' to exit):")
            original_text = input("> ")
            
            if original_text.lower() == 'quit':
                break
            
            if not original_text:
                print("Input cannot be empty.")
                continue

            print(f"\nOriginal: '{original_text}'")
            
            # Encrypt
            encrypted_text = encrypt_data(original_text)
            if encrypted_text is None:
                print("Encryption failed.")
            elif encrypted_text == original_text:
                 print("Encryption did not occur (key missing or input empty?).")
            else:
                print(f"Encrypted: '{encrypted_text}'")
            
                # Decrypt
                decrypted_text = decrypt_data(original_text)
                if decrypted_text is None:
                    print("Decryption failed.")
                elif decrypted_text == encrypted_text:
                     print("Decryption did not occur (key missing or input empty?).")
                else:
                    print(f"Decrypted: '{decrypted_text}'")
                    
                    # Verify
                    if decrypted_text == original_text:
                        print("Verification: SUCCESS - Decrypted text matches original.")
                    else:
                        print("Verification: FAILED - Decrypted text does NOT match original!")

            print("-" * 30)

    print("Exiting test script.") 