from flask import Flask, request, jsonify
import json
import time
from user_manager import UserManager
from collections import deque
from datetime import datetime, timedelta

app = Flask(__name__)
user_manager = UserManager()

# Store recent verification codes with timestamps
verification_codes = deque(maxlen=10)  # Keep only last 10 codes

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    user_id = user_manager.create_session(email, password)
    return jsonify({"user_id": user_id}), 200

@app.route('/sms', methods=['POST'])
def sms():
    data = request.json
    code = data.get('code')
    
    if not code:
        return jsonify({"error": "Code is required"}), 400
    
    # Extract just the numbers from the code
    import re
    numbers = re.findall(r'\d+', code)
    if numbers:
        code = numbers[-1]
        # Store code with timestamp
        verification_codes.appendleft({
            'code': code,
            'timestamp': datetime.now(),
            'used': False
        })
        return jsonify({"status": "received"}), 200
    else:
        return jsonify({"error": "No verification code found"}), 400

@app.route('/get_code', methods=['GET'])
def get_code():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'user_id is required'}), 400
    
    # Clean up old codes (older than 5 minutes)
    current_time = datetime.now()
    
    # Look for the most recent unused code
    for code_data in verification_codes:
        if (current_time - code_data['timestamp']) < timedelta(minutes=2) and not code_data['used']:
            code_data['used'] = True  # Mark as used
            user_manager.update_verification_code(user_id, code_data['code'])
            return jsonify({
                'status': 'available',
                'code': code_data['code']
            })
    
    return jsonify({'status': 'not_available'})

@app.route('/queue', methods=['POST'])
def add_to_queue():
    data = request.json
    user_id = data.get('user_id')
    reservation_details = data.get('reservation_details')
    
    if not user_id or not reservation_details:
        return jsonify({"error": "User ID and reservation details are required"}), 400
    
    user_manager.add_to_queue(user_id, reservation_details)
    return jsonify({"status": "added_to_queue"}), 200

@app.route('/status', methods=['GET'])
def get_status():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
    
    session = user_manager.get_session(user_id)
    if session:
        return jsonify({
            "status": session.reservation_status,
            "details": session.reservation_details
        })
    return jsonify({"error": "User not found"}), 404

@app.route('/list_users', methods=['GET'])
def list_users():
    users = []
    for user_id, session in user_manager.sessions.items():
        users.append({
            'user_id': user_id,
            'email': session.email,
            'has_code': bool(session.verification_code)
        })
    return jsonify({'users': users})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
