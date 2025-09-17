from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import sys
import json
import uuid
from datetime import datetime, timedelta
import logging

# Add the current directory to the path to import your modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your existing modules
try:
    from auth import (
        show_login, 
        is_logged_in, 
        show_usage_info, 
        check_usage_limits, 
        increment_usage,
        get_user_info,
        initialize_user_data
    )
    from app2 import (
        analyze_question, 
        summarize_trends, 
        extract_text_from_file, 
        analyze_url_content,
        safe_get_insight,
        clear_cache,
        get_insight_quality_score
    )
    print("✅ All modules loaded successfully!")
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Make sure auth.py and app2.py are in the same directory as this file")

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Enable CORS for all routes
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for demo (use database in production)
user_sessions = {}
analysis_cache = {}

# Authentication endpoints
@app.route('/api/auth/login', methods=['POST'])
def login():
    """Handle user login"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Here you would normally validate against your user database
        # For demo purposes, we'll accept any valid email format
        if '@' not in email:
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Initialize user data
        initialize_user_data(email)
        user_info = get_user_info(email)
        
        # Create session
        session_id = str(uuid.uuid4())
        user_sessions[session_id] = {
            'email': email,
            'login_time': datetime.now(),
            'user_info': user_info
        }
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'user': user_info,
            'message': 'Login successful'
        })
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """Handle user signup"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        if '@' not in email:
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Initialize user data
        initialize_user_data(email)
        user_info = get_user_info(email)
        
        # Create session
        session_id = str(uuid.uuid4())
        user_sessions[session_id] = {
            'email': email,
            'login_time': datetime.now(),
            'user_info': user_info
        }
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'user': user_info,
            'message': 'Account created successfully'
        })
        
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return jsonify({'error': 'Signup failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Handle user logout"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if session_id in user_sessions:
            del user_sessions[session_id]
        
        return jsonify({'success': True, 'message': 'Logged out successfully'})
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

@app.route('/api/auth/validate', methods=['POST'])
def validate_session():
    """Validate user session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if session_id not in user_sessions:
            return jsonify({'valid': False, 'error': 'Invalid session'}), 401
        
        session_data = user_sessions[session_id]
        
        # Check if session is expired (24 hours)
        if datetime.now() - session_data['login_time'] > timedelta(hours=24):
            del user_sessions[session_id]
            return jsonify({'valid': False, 'error': 'Session expired'}), 401
        
        # Update user info
        email = session_data['email']
        user_info = get_user_info(email)
        session_data['user_info'] = user_info
        
        return jsonify({
            'valid': True,
            'user': user_info
        })
        
    except Exception as e:
        logger.error(f"Session validation error: {str(e)}")
        return jsonify({'valid': False, 'error': 'Validation failed'}), 500

# Analysis endpoints
@app.route('/api/analyze/question', methods=['POST'])
def api_analyze_question():
    """Analyze a business question"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        question = data.get('question')
        keywords = data.get('keywords', '')
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        session_data = user_sessions[session_id]
        email = session_data['email']
        
        # Check usage limits
        can_use, message = check_usage_limits(email, "summary")
        if not can_use:
            return jsonify({'error': message, 'upgrade_required': True}), 429
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        # Perform analysis
        result = analyze_question(question, keywords)
        
        # Increment usage
        increment_usage(email, "summary")
        
        # Update session user info
        session_data['user_info'] = get_user_info(email)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Question analysis error: {str(e)}")
        return jsonify({'error': 'Analysis failed'}), 500

@app.route('/api/analyze/text', methods=['POST'])
def api_analyze_text():
    """Analyze text content"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        text = data.get('text')
        question = data.get('question', '')
        keywords = data.get('keywords', '')
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        session_data = user_sessions[session_id]
        email = session_data['email']
        
        # Check usage limits
        can_use, message = check_usage_limits(email, "summary")
        if not can_use:
            return jsonify({'error': message, 'upgrade_required': True}), 429
        
        if not text:
            return jsonify({'error': 'Text content is required'}), 400
        
        # Perform analysis
        result = summarize_trends(
            text=text,
            question=question,
            keyword=keywords,
            return_format="dict"
        )
        
        # Increment usage
        increment_usage(email, "summary")
        
        # Update session user info
        session_data['user_info'] = get_user_info(email)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Text analysis error: {str(e)}")
        return jsonify({'error': 'Analysis failed'}), 500

@app.route('/api/analyze/url', methods=['POST'])
def api_analyze_url():
    """Analyze URL content"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        url = data.get('url')
        question = data.get('question', '')
        keywords = data.get('keywords', '')
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        session_data = user_sessions[session_id]
        email = session_data['email']
        
        # Check usage limits
        can_use, message = check_usage_limits(email, "summary")
        if not can_use:
            return jsonify({'error': message, 'upgrade_required': True}), 429
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        if not url.startswith(('http://', 'https://')):
            return jsonify({'error': 'Invalid URL format'}), 400
        
        # Perform analysis
        result = analyze_url_content(url, question, keywords)
        
        # Increment usage
        increment_usage(email, "summary")
        
        # Update session user info
        session_data['user_info'] = get_user_info(email)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"URL analysis error: {str(e)}")
        return jsonify({'error': 'Analysis failed'}), 500

@app.route('/api/analyze/file', methods=['POST'])
def api_analyze_file():
    """Analyze uploaded file"""
    try:
        session_id = request.form.get('session_id')
        question = request.form.get('question', '')
        keywords = request.form.get('keywords', '')
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        session_data = user_sessions[session_id]
        email = session_data['email']
        
        # Check usage limits
        can_use, message = check_usage_limits(email, "summary")
        if not can_use:
            return jsonify({'error': message, 'upgrade_required': True}), 429
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'.pdf', '.docx', '.txt', '.png', '.jpg', '.jpeg'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return jsonify({'error': 'Unsupported file type'}), 400
        
        # Perform analysis
        result = extract_text_from_file(file, return_format="dict")
        
        if not result.get("error"):
            # If we have custom parameters, re-analyze with them
            if question or keywords:
                file.seek(0)  # Reset file pointer
                text_result = extract_text_from_file(file, return_format="string")
                if not text_result.startswith("Error:"):
                    result = summarize_trends(
                        text=text_result,
                        question=question,
                        keyword=keywords,
                        return_format="dict"
                    )
        
        # Increment usage
        increment_usage(email, "summary")
        
        # Update session user info
        session_data['user_info'] = get_user_info(email)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"File analysis error: {str(e)}")
        return jsonify({'error': 'Analysis failed'}), 500

# Utility endpoints
@app.route('/api/cache/clear', methods=['POST'])
def api_clear_cache():
    """Clear analysis cache"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        clear_cache()
        analysis_cache.clear()
        
        return jsonify({'success': True, 'message': 'Cache cleared successfully'})
        
    except Exception as e:
        logger.error(f"Cache clear error: {str(e)}")
        return jsonify({'error': 'Failed to clear cache'}), 500

@app.route('/api/user/info', methods=['POST'])
def api_user_info():
    """Get user information"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        session_data = user_sessions[session_id]
        email = session_data['email']
        
        # Get fresh user info
        user_info = get_user_info(email)
        session_data['user_info'] = user_info
        
        return jsonify({
            'success': True,
            'user': user_info
        })
        
    except Exception as e:
        logger.error(f"User info error: {str(e)}")
        return jsonify({'error': 'Failed to get user info'}), 500

# Serve the main application
@app.route('/')
def index():
    """Serve the main web application"""
    # Read the HTML file content (you would save the previous artifact as index.html)
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return """
        <h1>Business Intelligence Analyzer</h1>
        <p>Please save the HTML artifact as 'index.html' in the same directory as this Flask app.</p>
        <p>Then restart the Flask server.</p>
        """
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)
    
# Health check endpoint
@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

# Error handlers
@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Create required directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',  # Allow external connections
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    )
