from flask import Blueprint, jsonify, current_app
from datetime import datetime
import pytz

health_bp = Blueprint("health", __name__)

@health_bp.route("/health")
def health_check():
    """
    Health check endpoint for monitoring and Docker healthchecks.
    Returns a 200 status code with a simple JSON response.
    Also checks database connection.
    """
    status = "healthy"
    db_status = "connected"
    message = "All systems operational"
    checks = {}
    
    # Check database connection
    try:
        db = current_app.extensions['sqlalchemy'].db
        # Test a simple query
        from sqlalchemy import text
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            checks["database"] = "connected"
    except Exception as e:
        status = "degraded"
        db_status = "disconnected"
        message = f"Database connection issue: {str(e)}"
        checks["database"] = db_status
    
    # Add more system checks here if needed
    response = {
        "status": status,
        "timestamp": datetime.now(pytz.UTC).isoformat(),
        "message": message,
        "checks": checks
    }
    
    return jsonify(response)