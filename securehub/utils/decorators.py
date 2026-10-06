from functools import wraps
from flask import render_template, request, jsonify
from flask_login import current_user

def role_required(*roles):
    """
    Decorator requiring the current user to have one of the specified roles.
    If unauthorized:
      - Returns 403 Forbidden page for HTML web requests.
      - Returns 403 JSON response for API requests.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': 'Unauthorized', 'message': 'Authentication required'}), 401
                return render_template('errors/403.html'), 403

            if current_user.role not in roles:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': 'Forbidden', 'message': 'Permission denied'}), 403
                return render_template('errors/403.html'), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
