import os
import logging
from app import app, db
from models import User
from flask import jsonify

@app.route('/debug_users_list')
def debug_users_list():
    """Debug endpoint to list all users in the system. Only enabled in debug mode."""
    if not app.debug:
        return "Debug mode is disabled", 403
    
    # Get all users and format their info
    users = User.query.all()
    user_info = []
    for user in users:
        user_info.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin
        })
    
    return jsonify(user_info)

if __name__ == "__main__":
    # Check for important environment variables
    if not os.environ.get('SENDGRID_API_KEY'):
        app.logger.warning("SENDGRID_API_KEY is not set. Email notifications will not be sent.")
    
    app.run(host="0.0.0.0", port=5000, debug=True)