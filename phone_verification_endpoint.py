import re
import logging
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

# Assuming database.py and models.py are in the same directory or accessible
# If they are in a parent directory, you might need path adjustments
from database import supabase # Import the initialized Supabase client
from models import UserInformation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Consider adding security to this endpoint, e.g., checking a secret 
# header or verifying webhook signatures from your SMS provider.
@app.route('/sms', methods=['POST'])
def sms_webhook():
    """Webhook to receive SMS messages (presumably containing verification codes)."""
    data = request.json
    # These field names are assumptions - ADJUST BASED ON YOUR SMS PROVIDER'S WEBHOOK
    phone_number = data.get('phone_number') # The recipient phone number
    code_text = data.get('code_text')     # The body of the SMS
    
    if not phone_number or not code_text:
        logger.warning("SMS webhook received incomplete data: phone_number or code_text missing.")
        return jsonify({"error": "phone_number and code_text are required"}), 400
    
    # 1. Find user by phone number
    user = UserInformation.get_by_phone_number(phone_number)
    if not user:
        logger.warning(f"Received SMS for unknown phone number: {phone_number}")
        # Still return 200 OK so the provider doesn't keep retrying, 
        # but don't process further.
        return jsonify({"status": "received, user not found"}), 200 

    user_email = user.get('rec_account_email')
    if not user_email:
         logger.error(f"Found user for phone {phone_number} but they are missing 'rec_account_email'. Cannot process SMS.")
         return jsonify({"status": "received, user data incomplete"}), 200

    # 2. Extract the code (assuming it's the last sequence of digits)
    numbers = re.findall(r'\d+', code_text)
    if not numbers:
        logger.warning(f"No numerical code found in SMS text for {phone_number}: '{code_text}'")
        return jsonify({"status": "received, no code found"}), 200
        
    verification_code = numbers[-1]
    logger.info(f"Extracted verification code '{verification_code}' for user {user_email} (from phone {phone_number})")

    # 3. Store the code using the UserInformation model method
    success = UserInformation.update_verification_code(user_email, verification_code)
    
    if success:
        logger.info(f"Successfully stored verification code for {user_email}.")
        return jsonify({"status": "received and processed"}), 200
    else:
        logger.error(f"Failed to store verification code for {user_email}.")
        # Again, return 200 to prevent retries, but log the error.
        return jsonify({"status": "received, failed to store code"}), 200

@app.route('/get_code', methods=['GET'])
def get_verification_code():
    """Endpoint for the main application to retrieve the latest verification code for a user."""
    user_email = request.args.get('email')
    if not user_email:
        logger.warning("/get_code called without email parameter.")
        return jsonify({'status': 'error', 'message': 'email query parameter is required'}), 400
    
    logger.info(f"Attempting to retrieve verification code for user: {user_email}")

    # Retrieve and clear the code using the UserInformation model method
    # It handles checking the timestamp and clearing the code.
    code = UserInformation.get_and_clear_verification_code(user_email, max_age_minutes=5)
    
    if code:
        logger.info(f"Returning verification code '{code}' for user: {user_email}")
        return jsonify({
            'status': 'available',
            'code': code
        })
    else:
        # This means no code was found, it expired, or an error occurred during retrieval/clearing
        logger.info(f"No valid verification code available for user: {user_email}")
        return jsonify({'status': 'not_available'})


# Removed /register, /queue, /status, /list_users routes as they relied on UserManager

if __name__ == "__main__":
    # Make sure HOST and PORT are appropriate for your deployment environment
    # Use environment variables for configuration ideally
    app.run(host='0.0.0.0', port=8000, debug=True) # Added debug=True for development
