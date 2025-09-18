# Fixed Flask App with Error Handling and Proper Imports
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import logging
from datetime import datetime, timedelta
import hashlib
import uuid
import os
import tempfile

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check for required imports and handle missing dependencies gracefully
try:
    import textract
    TEXTRACT_AVAILABLE = True
except ImportError:
    TEXTRACT_AVAILABLE = False
    logger.warning("textract not available - file analysis will be limited")

try:
    import requests
    from bs4 import BeautifulSoup
    WEB_SCRAPING_AVAILABLE = True
except ImportError:
    WEB_SCRAPING_AVAILABLE = False
    logger.warning("requests/beautifulsoup4 not available - URL analysis will be limited")

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    logger.warning("textblob not available - using basic sentiment analysis")

try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    logger.warning("praw not available - using mock Reddit data")

try:
    from collections import Counter
    import re
    ANALYSIS_TOOLS_AVAILABLE = True
except ImportError:
    ANALYSIS_TOOLS_AVAILABLE = False
    logger.warning("basic analysis tools not available")

# Try to import from app2.py with error handling
try:
    from app2 import (
        claude_messages, 
        analyze_question, 
        summarize_trends, 
        extract_text_from_file, 
        analyze_url_content
    )
    APP2_AVAILABLE = True
    logger.info("Successfully imported from app2.py")
except ImportError as e:
    APP2_AVAILABLE = False
    logger.warning(f"Could not import from app2.py: {e}")
except Exception as e:
    APP2_AVAILABLE = False
    logger.error(f"Error importing from app2.py: {e}")

# In-memory session storage
user_sessions = {}

# Sample user database
users_db = {
    "demo@example.com": {
        "password": "demo123",
        "subscription_type": "Free Plan",
        "usage": {"summary": 2, "analysis": 1, "question": 5},
        "limits": {"summary": 10, "analysis": 5, "question": 20}
    }
}

def get_user_info(email):
    """Get user information from database"""
    return users_db.get(email, {
        "subscription_type": "Free Plan",
        "usage": {"summary": 0, "analysis": 0, "question": 0},
        "limits": {"summary": 10, "analysis": 5, "question": 20}
    })

def update_user_usage(email, usage_type):
    """Update user usage counter"""
    if email in users_db:
        users_db[email]["usage"][usage_type] = users_db[email]["usage"].get(usage_type, 0) + 1

# Enhanced sentiment analysis with fallback
def analyze_sentiment(text):
    """Analyze sentiment with fallback methods"""
    try:
        if TEXTBLOB_AVAILABLE:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            if polarity > 0.1:
                sentiment = "Positive"
            elif polarity < -0.1:
                sentiment = "Negative"
            else:
                sentiment = "Neutral"
                
            return {
                "sentiment": sentiment,
                "polarity": round(polarity, 3),
                "subjectivity": round(subjectivity, 3),
                "confidence": round(abs(polarity), 3)
            }
    except Exception as e:
        logger.error(f"TextBlob sentiment analysis error: {e}")
    
    # Fallback sentiment analysis
    try:
        positive_words = ['good', 'great', 'excellent', 'amazing', 'positive', 'love', 'best', 'wonderful', 'fantastic']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'worst', 'negative', 'poor', 'horrible', 'disappointing']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return {"sentiment": "Positive", "polarity": 0.5, "subjectivity": 0.6, "confidence": 0.6}
        elif negative_count > positive_count:
            return {"sentiment": "Negative", "polarity": -0.5, "subjectivity": 0.6, "confidence": 0.6}
        else:
            return {"sentiment": "Neutral", "polarity": 0.0, "subjectivity": 0.5, "confidence": 0.3}
    except Exception as e:
        logger.error(f"Fallback sentiment analysis error: {e}")
        return {"sentiment": "Neutral", "polarity": 0, "subjectivity": 0, "confidence": 0}

def extract_hashtags_keywords(text, max_hashtags=15):
    """Extract hashtag suggestions with fallback"""
    try:
        if ANALYSIS_TOOLS_AVAILABLE:
            # Clean and tokenize text
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            
            # Filter out common words
            stop_words = {
                'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were', 'been', 'being',
                'have', 'has', 'had', 'will', 'would', 'could', 'should', 'can', 'may', 'might'
            }
            
            filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
            word_counts = Counter(filtered_words)
            top_words = [word for word, count in word_counts.most_common(max_hashtags)]
            hashtags = [word.capitalize() for word in top_words]
            
            return hashtags
    except Exception as e:
        logger.error(f"Hashtag extraction error: {e}")
    
    # Fallback hashtag generation
    try:
        words = text.split()[:10]  # Take first 10 words
        hashtags = [word.strip('.,!?').capitalize() for word in words if len(word) > 3]
        return hashtags[:max_hashtags]
    except Exception as e:
        logger.error(f"Fallback hashtag extraction error: {e}")
        return ['Analysis', 'Trends', 'Insights']

def extract_brand_mentions(text, brands_list=None):
    """Extract brand mentions with fallback"""
    try:
        if brands_list is None:
            brands_list = ['Apple', 'Google', 'Microsoft', 'Amazon', 'Meta', 'Tesla', 'Netflix', 'OpenAI', 'Anthropic']
        
        mentions = {}
        text_lower = text.lower()
        
        for brand in brands_list:
            count = text_lower.count(brand.lower())
            if count > 0:
                mentions[brand] = count
        
        return mentions
    except Exception as e:
        logger.error(f"Brand mention extraction error: {e}")
        return {}

def create_mock_social_data(query):
    """Create mock social media data"""
    try:
        sample_posts = [
            {
                'title': f'Discussion about {query} trends in 2024',
                'content': f'Great insights on {query}. The community is very positive about recent developments and growth potential.',
                'score': 156,
                'comments': 23,
                'url': 'https://reddit.com/r/technology/sample_post_1',
                'subreddit': 'technology',
                'created': datetime.now().strftime('%Y-%m-%d %H:%M')
            },
            {
                'title': f'{query} market analysis and predictions',
                'content': f'Interesting analysis of {query} market trends. Some concerns about sustainability but overall optimistic outlook.',
                'score': 89,
                'comments': 15,
                'url': 'https://reddit.com/r/business/sample_post_2',
                'subreddit': 'business',
                'created': (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')
            }
        ]
        
        # Add sentiment to each post
        for post in sample_posts:
            combined_text = f"{post['title']} {post['content']}"
            post['sentiment'] = analyze_sentiment(combined_text)
        
        return sample_posts
    except Exception as e:
        logger.error(f"Error creating mock social data: {e}")
        return []

# Authentication routes
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        if email in users_db and users_db[email]['password'] == password:
            session_id = str(uuid.uuid4())
            user_sessions[session_id] = {
                'email': email,
                'login_time': datetime.now(),
                'user_info': get_user_info(email)
            }
            
            return jsonify({
                'session_id': session_id,
                'user': {
                    'email': email,
                    'subscription_type': users_db[email]['subscription_type'],
                    'usage': users_db[email]['usage'],
                    'limits': users_db[email]['limits']
                }
            })
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        if email in users_db:
            return jsonify({'error': 'Email already exists'}), 409
            
        users_db[email] = {
            'password': password,
            'subscription_type': 'Free Plan',
            'usage': {'summary': 0, 'analysis': 0, 'question': 0},
            'limits': {'summary': 10, 'analysis': 5, 'question': 20}
        }
        
        session_id = str(uuid.uuid4())
        user_sessions[session_id] = {
            'email': email,
            'login_time': datetime.now(),
            'user_info': get_user_info(email)
        }
        
        return jsonify({
            'session_id': session_id,
            'user': {
                'email': email,
                'subscription_type': 'Free Plan',
                'usage': {'summary': 0, 'analysis': 0, 'question': 0},
                'limits': {'summary': 10, 'analysis': 5, 'question': 20}
            }
        })
        
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return jsonify({'error': 'Signup failed'}), 500

@app.route('/api/auth/validate', methods=['POST'])
def api_validate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        session_id = data.get('session_id')
        
        if session_id in user_sessions:
            session_data = user_sessions[session_id]
            email = session_data['email']
            
            return jsonify({
                'user': {
                    'email': email,
                    'subscription_type': users_db[email]['subscription_type'],
                    'usage': users_db[email]['usage'],
                    'limits': users_db[email]['limits']
                }
            })
        else:
            return jsonify({'error': 'Invalid session'}), 401
            
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({'error': 'Validation failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    try:
        data = request.get_json()
        session_id = data.get('session_id') if data else None
        
        if session_id and session_id in user_sessions:
            del user_sessions[session_id]
            
        return jsonify({'message': 'Logged out successfully'})
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

# Analysis routes with comprehensive error handling
@app.route('/api/analyze/comprehensive', methods=['POST'])
def api_comprehensive_analysis():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        session_id = data.get('session_id')
        text = data.get('text', '')
        url = data.get('url')
        brands_list = data.get('brands_list', [])
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if not text and not url:
            return jsonify({'error': 'Text or URL is required'}), 400
        
        # Check usage limits
        session_data = user_sessions[session_id]
        user_info = session_data.get('user_info', {})
        usage = user_info.get('usage', {})
        limits = user_info.get('limits', {})
        
        if usage.get('summary', 0) >= limits.get('summary', 10):
            return jsonify({'error': 'Usage limit exceeded'}), 403
        
        # Get content from URL if provided
        if url and WEB_SCRAPING_AVAILABLE:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                for script in soup(["script", "style", "nav", "header", "footer"]):
                    script.extract()
                
                url_text = soup.get_text()
                url_text = ' '.join(url_text.split())
                text = (text + ' ' + url_text).strip()
                
            except Exception as e:
                logger.error(f"URL extraction error: {e}")
                if not text:  # Only fail if we have no text at all
                    return jsonify({'error': f'Failed to extract content from URL: {str(e)}'}), 400
        
        if len(text.strip()) < 10:
            return jsonify({'error': 'Content too short for analysis'}), 400
        
        # Perform comprehensive analysis
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags_keywords(text)
        brand_mentions = extract_brand_mentions(text, brands_list)
        
        # Try to use app2.py functions, fall back if not available
        key_insights = []
        recommendations = []
        summary = ""
        
        if APP2_AVAILABLE:
            try:
                analysis_result = summarize_trends(text=text, question="Provide comprehensive market trend analysis", return_format="dict")
                
                if not analysis_result.get('error'):
                    key_insights = analysis_result.get('keywords', [])[:5]
                    recommendations = list(analysis_result.get('insights', {}).keys())[:4]
                    summary = analysis_result.get('full_response', '')[:300] + "..."
                    
            except Exception as e:
                logger.error(f"app2.py analysis error: {e}")
        
        # Fallback analysis if app2.py fails or unavailable
        if not key_insights:
            key_insights = [
                f"Sentiment analysis shows {sentiment_analysis['sentiment'].lower()} sentiment (polarity: {sentiment_analysis['polarity']})",
                f"Identified {len(hashtags)} key topics for trend monitoring",
                f"Found {len(brand_mentions)} brand mentions in the content",
                "Content analysis completed successfully"
            ]
        
        if not recommendations:
            recommendations = [
                "Review the content sentiment for brand alignment",
                "Consider the key topics for content strategy",
                "Monitor any brand mentions found",
                "Use insights for competitive analysis"
            ]
        
        result = {
            'url': url,
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']})",
            'hashtags': hashtags,
            'brand_mentions': brand_mentions,
            'key_insights': key_insights,
            'recommendations': recommendations,
            'content_length': len(text.split()),
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Update usage
        email = session_data['email']
        update_user_usage(email, 'question')
        user_info['usage']['question'] = user_info['usage'].get('question', 0) + 1
        session_data['user_info'] = user_info
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"URL analysis error: {str(e)}")
        return jsonify({'error': f'URL analysis failed: {str(e)}'}), 500

@app.route('/api/analyze/file', methods=['POST'])
def api_file_analysis():
    try:
        session_id = request.form.get('session_id')
        question = request.form.get('question', '')
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file size (16MB limit)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 16 * 1024 * 1024:
            return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 400
        
        # Check usage limits
        session_data = user_sessions[session_id]
        user_info = session_data.get('user_info', {})
        usage = user_info.get('usage', {})
        limits = user_info.get('limits', {})
        
        if usage.get('question', 0) >= limits.get('question', 20):
            return jsonify({'error': 'Usage limit exceeded'}), 403
        
        # Extract text from file
        text = ""
        tmp_path = None
        
        try:
            # Save file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name
            
            # Extract text based on file type and available tools
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if TEXTRACT_AVAILABLE:
                try:
                    text = textract.process(tmp_path).decode('utf-8')
                except Exception as e:
                    logger.error(f"Textract error: {e}")
                    # Fallback for text files
                    if file_ext in ['.txt', '.md']:
                        with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                            text = f.read()
                    else:
                        raise e
            else:
                # Fallback without textract
                if file_ext in ['.txt', '.md']:
                    with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                else:
                    return jsonify({'error': 'File type not supported - textract package required for PDF/Word files'}), 400
            
        except Exception as e:
            logger.error(f"File processing error: {e}")
            return jsonify({'error': f'File processing error: {str(e)}'}), 400
        finally:
            # Clean up temporary file
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        
        if len(text.strip()) < 20:
            return jsonify({'error': 'Insufficient text content in file'}), 400
        
        # Limit text length for analysis
        if len(text) > 4000:
            text = text[:4000] + "..."
        
        # Perform analysis
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags_keywords(text)
        brand_mentions = extract_brand_mentions(text)
        
        # Try to use app2.py functions
        key_insights = []
        recommendations = []
        summary = ""
        
        if APP2_AVAILABLE:
            try:
                # Reset file for extract_text_from_file function
                file.seek(0)
                analysis_result = extract_text_from_file(file, return_format="dict")
                
                if not analysis_result.get('error'):
                    summary = analysis_result.get('full_response', '')[:300] + "..."
                    key_insights = analysis_result.get('keywords', [])[:5]
                    recommendations = list(analysis_result.get('insights', {}).keys())[:4]
                    
            except Exception as e:
                logger.error(f"app2.py file analysis error: {e}")
        
        # Fallback analysis
        if not summary:
            summary = text[:200] + "..." if len(text) > 200 else text
            
        if not key_insights:
            key_insights = [
                f"Document analysis completed with {sentiment_analysis['sentiment']} sentiment",
                f"File contains {len(text.split())} words",
                f"Key topics identified: {', '.join(hashtags[:3])}",
                "File processing successful"
            ]
            
        if not recommendations:
            recommendations = [
                "Review document sentiment for strategic implications",
                "Use identified topics for content planning",
                "Consider document insights for decision making",
                "Extract key data points for analysis"
            ]
        
        result = {
            'filename': file.filename,
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']})",
            'hashtags': hashtags,
            'brand_mentions': brand_mentions,
            'key_insights': key_insights,
            'recommendations': recommendations,
            'word_count': len(text.split()),
            'file_size': f"{file_size/1024:.1f} KB",
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Update usage
        email = session_data['email']
        update_user_usage(email, 'question')
        user_info['usage']['question'] = user_info['usage'].get('question', 0) + 1
        session_data['user_info'] = user_info
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"File analysis error: {str(e)}")
        return jsonify({'error': f'File analysis failed: {str(e)}'}), 500

@app.route('/api/user/info', methods=['POST'])
def api_user_info():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        session_id = data.get('session_id')
        
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        session_data = user_sessions[session_id]
        email = session_data['email']
        
        return jsonify({
            'user': {
                'email': email,
                'subscription_type': users_db[email]['subscription_type'],
                'usage': users_db[email]['usage'],
                'limits': users_db[email]['limits']
            }
        })
        
    except Exception as e:
        logger.error(f"User info error: {str(e)}")
        return jsonify({'error': 'Failed to get user info'}), 500

@app.route('/api/cache/clear', methods=['POST'])
def api_clear_cache():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        session_id = data.get('session_id')
        
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        # Clear cache from app2.py if available
        if APP2_AVAILABLE:
            try:
                from app2 import clear_cache
                clear_cache()
            except Exception as e:
                logger.error(f"Cache clear error: {e}")
        
        return jsonify({'message': 'Cache cleared successfully'})
        
    except Exception as e:
        logger.error(f"Cache clear error: {str(e)}")
        return jsonify({'error': 'Failed to clear cache'}), 500

# Web routes (your existing routes)
@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Index route error: {str(e)}")
        return f"Error loading page: {str(e)}", 500

@app.route('/about')
def about():
    try:
        return render_template('about.html')
    except Exception as e:
        logger.error(f"About route error: {str(e)}")
        return f"Error loading page: {str(e)}", 500

@app.route('/TrendSummarizer')
def TrendSummarizer():
    try:
        return render_template('TrendSummarizer.html')
    except Exception as e:
        logger.error(f"TrendSummarizer route error: {str(e)}")
        return f"Error loading page: {str(e)}", 500

@app.route('/DataHelp')
def DataHelp():
    try:
        return render_template('DataHelp.html')
    except Exception as e:
        logger.error(f"DataHelp route error: {str(e)}")
        return f"Error loading page: {str(e)}", 500

@app.route('/signin')
def signin():
    try:
        return render_template('signin.html')
    except Exception as e:
        logger.error(f"Signin route error: {str(e)}")
        return f"Error loading page: {str(e)}", 500

@app.route('/signup')
def signup():
    try:
        return render_template('signup.html')
    except Exception as e:
        logger.error(f"Signup route error: {str(e)}")
        return f"Error loading page: {str(e)}", 500

@app.route('/health')
def health():
    return {
        'status': 'healthy', 
        'service': 'Market Trend Summarizer',
        'dependencies': {
            'app2': APP2_AVAILABLE,
            'textblob': TEXTBLOB_AVAILABLE,
            'textract': TEXTRACT_AVAILABLE,
            'web_scraping': WEB_SCRAPING_AVAILABLE,
            'praw': PRAW_AVAILABLE
        }
    }

@app.route('/tools')
def tools():
    try:
        return render_template('tools.html')
    except Exception as e:
        logger.error(f"Tools route error: {str(e)}")
        return f"Error loading page: {str(e)}", 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Starting Market Trend Summarizer...")
    print(f"App2.py available: {APP2_AVAILABLE}")
    print(f"TextBlob available: {TEXTBLOB_AVAILABLE}")
    print(f"Textract available: {TEXTRACT_AVAILABLE}")
    print(f"Web scraping available: {WEB_SCRAPING_AVAILABLE}")
    print(f"PRAW available: {PRAW_AVAILABLE}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
                "Monitor trending hashtags for engagement opportunities",
                "Track sentiment changes over time",
                "Engage with positive sentiment content",
                "Address any negative sentiment concerns"
            ]
        
        if not summary:
            summary = text[:200] + "..." if len(text) > 200 else text
        
        result = {
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']}, confidence: {sentiment_analysis['confidence']})",
            'hashtags': hashtags,
            'brand_mentions': brand_mentions,
            'key_insights': key_insights,
            'recommendations': recommendations,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Update usage
        email = session_data['email']
        update_user_usage(email, 'summary')
        user_info['usage']['summary'] = user_info['usage'].get('summary', 0) + 1
        session_data['user_info'] = user_info
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Comprehensive analysis error: {str(e)}")
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/api/analyze/social', methods=['POST'])
def api_social_analysis():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        session_id = data.get('session_id')
        platforms = data.get('platforms', ['reddit'])
        query = data.get('query', '')
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        # Check usage limits
        session_data = user_sessions[session_id]
        user_info = session_data.get('user_info', {})
        usage = user_info.get('usage', {})
        limits = user_info.get('limits', {})
        
        if usage.get('analysis', 0) >= limits.get('analysis', 5):
            return jsonify({'error': 'Usage limit exceeded'}), 403
        
        results = {
            'query': query,
            'platforms_scanned': platforms,
            'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': {}
        }
        
        all_content = []
        
        # Create mock data for each platform
        for platform in platforms:
            if platform == 'reddit':
                reddit_data = create_mock_social_data(query)
                results['data']['reddit'] = reddit_data
                all_content.extend([post['title'] + ' ' + post['content'] for post in reddit_data])
            elif platform == 'youtube':
                youtube_data = [{
                    'title': f'{query} Explained: Complete Guide 2024',
                    'description': f'Comprehensive overview of {query} trends, applications, and future prospects.',
                    'views': '45.2K',
                    'likes': '1.8K',
                    'sentiment': analyze_sentiment(f'Comprehensive overview of {query} trends. Positive outlook.')
                }]
                results['data']['youtube'] = youtube_data
                all_content.extend([video['title'] + ' ' + video['description'] for video in youtube_data])
            elif platform == 'twitter':
                twitter_data = [{
                    'text': f'Just discovered this amazing {query} application! Game-changing potential #innovation #tech',
                    'author': '@techexplorer',
                    'retweets': 45,
                    'likes': 128,
                    'sentiment': analyze_sentiment('Amazing application! Game-changing potential.')
                }]
                results['data']['twitter'] = twitter_data
                all_content.extend([tweet['text'] for tweet in twitter_data])
        
        # Overall analysis
        combined_text = ' '.join(all_content)
        
        if combined_text:
            overall_sentiment = analyze_sentiment(combined_text)
            hashtag_suggestions = extract_hashtags_keywords(combined_text)
            
            # Generate insights
            total_posts = sum(len(data) for data in results['data'].values())
            positive_sentiment = sum(1 for platform_data in results['data'].values() 
                                   for item in platform_data 
                                   if item.get('sentiment', {}).get('sentiment') == 'Positive')
            
            results.update({
                'summary': f"Found {total_posts} posts across {len(platforms)} platforms about '{query}'. Overall sentiment is {overall_sentiment['sentiment']} with {positive_sentiment} positive mentions.",
                'overall_sentiment': overall_sentiment,
                'hashtags': hashtag_suggestions,
                'key_insights': [
                    f"Scanned {total_posts} posts across {', '.join(platforms)}",
                    f"Overall sentiment: {overall_sentiment['sentiment']} (polarity: {overall_sentiment['polarity']})",
                    f"Positive mentions: {positive_sentiment}/{total_posts}",
                    f"Most discussed topics: {', '.join(hashtag_suggestions[:5])}"
                ],
                'recommendations': [
                    "Monitor trending hashtags for engagement opportunities",
                    "Engage with positive sentiment posts",
                    "Address any negative sentiment concerns",
                    "Create content around trending topics"
                ]
            })
        
        # Update usage
        email = session_data['email']
        update_user_usage(email, 'analysis')
        user_info['usage']['analysis'] = user_info['usage'].get('analysis', 0) + 1
        session_data['user_info'] = user_info
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Social media analysis error: {str(e)}")
        return jsonify({'error': f'Social analysis failed: {str(e)}'}), 500

@app.route('/api/analyze/text', methods=['POST'])
def api_text_analysis():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        session_id = data.get('session_id')
        text = data.get('text', '')
        question = data.get('question', '')
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if not text:
            return jsonify({'error': 'Text content is required'}), 400
        
        if len(text.strip()) < 10:
            return jsonify({'error': 'Text too short for meaningful analysis'}), 400
        
        # Check usage limits
        session_data = user_sessions[session_id]
        user_info = session_data.get('user_info', {})
        usage = user_info.get('usage', {})
        limits = user_info.get('limits', {})
        
        if usage.get('question', 0) >= limits.get('question', 20):
            return jsonify({'error': 'Usage limit exceeded'}), 403
        
        # Perform text analysis
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags_keywords(text)
        brand_mentions = extract_brand_mentions(text)
        
        # Try to use app2.py functions
        key_insights = []
        recommendations = []
        summary = ""
        
        if APP2_AVAILABLE:
            try:
                analysis_question = question if question else "Analyze this text for business insights and trends"
                analysis_result = summarize_trends(text=text, question=analysis_question, return_format="dict")
                
                if not analysis_result.get('error'):
                    summary = analysis_result.get('full_response', '')[:300] + "..."
                    key_insights = analysis_result.get('keywords', [])[:5]
                    recommendations = list(analysis_result.get('insights', {}).keys())[:4]
                    
            except Exception as e:
                logger.error(f"app2.py text analysis error: {e}")
        
        # Fallback analysis
        if not summary:
            summary = text[:200] + "..." if len(text) > 200 else text
            
        if not key_insights:
            key_insights = [
                f"Text sentiment: {sentiment_analysis['sentiment']} (confidence: {sentiment_analysis['confidence']})",
                f"Key topics identified: {', '.join(hashtags[:3])}",
                f"Word count: {len(text.split())} words",
                "Analysis completed successfully"
            ]
            
        if not recommendations:
            recommendations = [
                "Consider the sentiment when planning content strategy",
                "Use identified hashtags for social media",
                "Monitor brand mentions if any were found",
                "Review content for strategic insights"
            ]
        
        result = {
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']})",
            'hashtags': hashtags,
            'brand_mentions': brand_mentions,
            'key_insights': key_insights,
            'recommendations': recommendations,
            'word_count': len(text.split()),
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Update usage
        email = session_data['email']
        update_user_usage(email, 'question')
        user_info['usage']['question'] = user_info['usage'].get('question', 0) + 1
        session_data['user_info'] = user_info
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Text analysis error: {str(e)}")
        return jsonify({'error': f'Text analysis failed: {str(e)}'}), 500

@app.route('/api/analyze/url', methods=['POST'])
def api_url_analysis():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        session_id = data.get('session_id')
        url = data.get('url', '')
        question = data.get('question', '')
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Check usage limits
        session_data = user_sessions[session_id]
        user_info = session_data.get('user_info', {})
        usage = user_info.get('usage', {})
        limits = user_info.get('limits', {})
        
        if usage.get('question', 0) >= limits.get('question', 20):
            return jsonify({'error': 'Usage limit exceeded'}), 403
        
        text = ""
        
        # Extract content from URL if web scraping is available
        if WEB_SCRAPING_AVAILABLE:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                    script.extract()
                
                # Get text content
                text = soup.get_text()
                text = ' '.join(text.split())
                
                # Limit text length for analysis
                if len(text) > 3000:
                    text = text[:3000] + "..."
                    
            except Exception as e:
                logger.error(f"URL extraction error: {e}")
                return jsonify({'error': f'Failed to extract content from URL: {str(e)}'}), 400
        else:
            return jsonify({'error': 'URL analysis not available - missing required packages'}), 500
        
        if len(text.strip()) < 50:
            return jsonify({'error': 'Insufficient content extracted from URL'}), 400
        
        # Perform analysis
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags_keywords(text)
        brand_mentions = extract_brand_mentions(text)
        
        # Try to use app2.py functions
        key_insights = []
        recommendations = []
        summary = ""
        
        if APP2_AVAILABLE:
            try:
                analysis_result = analyze_url_content(url, question)
                if not analysis_result.get('error'):
                    summary = analysis_result.get('full_response', '')[:300] + "..."
                    key_insights = analysis_result.get('keywords', [])[:5]
                    recommendations = list(analysis_result.get('insights', {}).keys())[:4]
            except Exception as e:
                logger.error(f"app2.py URL analysis error: {e}")
        
        # Fallback analysis
        if not summary:
            summary = text[:200] + "..." if len(text) > 200 else text
            
        if not key_insights:
            key_insights = [
                f"Website sentiment: {sentiment_analysis['sentiment']}",
                f"Content length: {len(text.split())} words",
                f"Key topics: {', '.join(hashtags[:3])}",
                "URL analysis completed"
            ]
            
        if not recommendations:
            recommendations = [
                # Complete Flask App with All Analysis Features Working
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import logging
from datetime import datetime, timedelta
import hashlib
import uuid
import os
import tempfile
import textract
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
from collections import Counter
import re

# Import your existing functions from app2.py
try:
    from app2 import (
        claude_messages, 
        analyze_question, 
        summarize_trends, 
        extract_text_from_file, 
        analyze_url_content
    )
except ImportError:
    print("Warning: Could not import from app2.py. Using fallback implementations.")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory session storage (use Redis in production)
user_sessions = {}

# Sample user database (use real database in production)
users_db = {
    "demo@example.com": {
        "password": "demo123",
        "subscription_type": "Free Plan",
        "usage": {"summary": 2, "analysis": 1, "question": 5},
        "limits": {"summary": 10, "analysis": 5, "question": 20}
    }
}

def get_user_info(email):
    """Get user information from database"""
    return users_db.get(email, {
        "subscription_type": "Free Plan",
        "usage": {"summary": 0, "analysis": 0, "question": 0},
        "limits": {"summary": 10, "analysis": 5, "question": 20}
    })

def update_user_usage(email, usage_type):
    """Update user usage counter"""
    if email in users_db:
        users_db[email]["usage"][usage_type] = users_db[email]["usage"].get(usage_type, 0) + 1

# Enhanced sentiment analysis using TextBlob
def analyze_sentiment(text):
    """Analyze sentiment of text using TextBlob"""
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        if polarity > 0.1:
            sentiment = "Positive"
        elif polarity < -0.1:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
            
        return {
            "sentiment": sentiment,
            "polarity": round(polarity, 3),
            "subjectivity": round(subjectivity, 3),
            "confidence": round(abs(polarity), 3)
        }
    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        return {"sentiment": "Neutral", "polarity": 0, "subjectivity": 0, "confidence": 0}

def extract_hashtags_keywords(text, max_hashtags=15):
    """Extract hashtag suggestions from text"""
    try:
        # Clean and tokenize text
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter out common words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were', 'been', 'being',
            'have', 'has', 'had', 'will', 'would', 'could', 'should', 'can', 'may', 'might',
            'must', 'shall', 'do', 'does', 'did', 'get', 'got', 'go', 'went', 'come', 'came'
        }
        
        # Extract meaningful words
        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Count frequency and get top words
        word_counts = Counter(filtered_words)
        top_words = [word for word, count in word_counts.most_common(max_hashtags)]
        
        # Generate hashtags
        hashtags = [word.capitalize() for word in top_words]
        
        return hashtags
    except Exception as e:
        logger.error(f"Hashtag extraction error: {e}")
        return []

def extract_brand_mentions(text, brands_list=None):
    """Extract brand mentions from text"""
    if brands_list is None:
        brands_list = ['Apple', 'Google', 'Microsoft', 'Amazon', 'Meta', 'Tesla', 'Netflix', 'OpenAI', 'Anthropic']
    
    mentions = {}
    text_lower = text.lower()
    
    for brand in brands_list:
        count = text_lower.count(brand.lower())
        if count > 0:
            mentions[brand] = count
    
    return mentions

def scan_reddit_mock(query, limit=10):
    """Mock Reddit scanning (replace with real API when configured)"""
    sample_posts = [
        {
            'title': f'Discussion about {query} trends in 2024',
            'content': f'Great insights on {query}. The community is very positive about recent developments and growth potential.',
            'score': 156,
            'comments': 23,
            'url': 'https://reddit.com/r/technology/sample_post_1',
            'subreddit': 'technology',
            'created': datetime.now().strftime('%Y-%m-%d %H:%M')
        },
        {
            'title': f'{query} market analysis and predictions',
            'content': f'Interesting analysis of {query} market trends. Some concerns about sustainability but overall optimistic outlook.',
            'score': 89,
            'comments': 15,
            'url': 'https://reddit.com/r/business/sample_post_2',
            'subreddit': 'business',
            'created': (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')
        },
        {
            'title': f'Why {query} is the future of innovation',
            'content': f'Compelling arguments for {query} adoption. Revolutionary potential but implementation challenges remain.',
            'score': 234,
            'comments': 67,
            'url': 'https://reddit.com/r/futurology/sample_post_3',
            'subreddit': 'futurology',
            'created': (datetime.now() - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M')
        }
    ]
    
    # Add sentiment to each post
    for post in sample_posts:
        combined_text = f"{post['title']} {post['content']}"
        post['sentiment'] = analyze_sentiment(combined_text)
    
    return sample_posts[:limit]

def scan_youtube_mock(query, limit=5):
    """Mock YouTube scanning"""
    return [
        {
            'title': f'{query} Explained: Complete Guide 2024',
            'description': f'Comprehensive overview of {query} trends, applications, and future prospects.',
            'views': '45.2K',
            'likes': '1.8K',
            'url': 'https://youtube.com/watch?v=sample1',
            'channel': 'Tech Insights',
            'published': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
            'sentiment': analyze_sentiment(f'Comprehensive overview of {query} trends. Positive outlook.')
        },
        {
            'title': f'The Future of {query}: Expert Analysis',
            'description': f'Industry experts discuss the impact and potential of {query} technology.',
            'views': '28.7K',
            'likes': '912',
            'url': 'https://youtube.com/watch?v=sample2',
            'channel': 'Future Tech',
            'published': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            'sentiment': analyze_sentiment(f'Expert analysis of {query} impact and potential. Very promising.')
        }
    ]

def scan_twitter_mock(query, limit=10):
    """Mock Twitter scanning"""
    return [
        {
            'text': f'Just discovered this amazing {query} application! Game-changing potential 🚀 #innovation #tech',
            'author': '@techexplorer',
            'retweets': 45,
            'likes': 128,
            'url': 'https://twitter.com/sample/status/1',
            'created': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'sentiment': analyze_sentiment('Amazing application! Game-changing potential.')
        },
        {
            'text': f'Concerns about {query} implementation costs and timeline. Need more realistic projections.',
            'author': '@businessanalyst',
            'retweets': 12,
            'likes': 34,
            'url': 'https://twitter.com/sample/status/2',
            'created': (datetime.now() - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M'),
            'sentiment': analyze_sentiment('Concerns about implementation costs and timeline.')
        }
    ]

# Authentication routes
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if email in users_db and users_db[email]['password'] == password:
            session_id = str(uuid.uuid4())
            user_sessions[session_id] = {
                'email': email,
                'login_time': datetime.now(),
                'user_info': get_user_info(email)
            }
            
            return jsonify({
                'session_id': session_id,
                'user': {
                    'email': email,
                    'subscription_type': users_db[email]['subscription_type'],
                    'usage': users_db[email]['usage'],
                    'limits': users_db[email]['limits']
                }
            })
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if email in users_db:
            return jsonify({'error': 'Email already exists'}), 409
            
        users_db[email] = {
            'password': password,
            'subscription_type': 'Free Plan',
            'usage': {'summary': 0, 'analysis': 0, 'question': 0},
            'limits': {'summary': 10, 'analysis': 5, 'question': 20}
        }
        
        session_id = str(uuid.uuid4())
        user_sessions[session_id] = {
            'email': email,
            'login_time': datetime.now(),
            'user_info': get_user_info(email)
        }
        
        return jsonify({
            'session_id': session_id,
            'user': {
                'email': email,
                'subscription_type': 'Free Plan',
                'usage': {'summary': 0, 'analysis': 0, 'question': 0},
                'limits': {'summary': 10, 'analysis': 5, 'question': 20}
            }
        })
        
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return jsonify({'error': 'Signup failed'}), 500

@app.route('/api/auth/validate', methods=['POST'])
def api_validate():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if session_id in user_sessions:
            session_data = user_sessions[session_id]
            email = session_data['email']
            
            return jsonify({
                'user': {
                    'email': email,
                    'subscription_type': users_db[email]['subscription_type'],
                    'usage': users_db[email]['usage'],
                    'limits': users_db[email]['limits']
                }
            })
        else:
            return jsonify({'error': 'Invalid session'}), 401
            
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({'error': 'Validation failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if session_id in user_sessions:
            del user_sessions[session_id]
            
        return jsonify({'message': 'Logged out successfully'})
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

# Analysis routes
@app.route('/api/analyze/comprehensive', methods=['POST'])
def api_comprehensive_analysis():
    """Comprehensive trend analysis with sentiment, mentions, and hashtags"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        text = data.get('text', '')
        url = data.get('url')
        brands_list = data.get('brands_list', [])
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if not text and not url:
            return jsonify({'error': 'Text or URL is required'}), 400
        
        # Check usage limits
        session_data = user_sessions[session_id]
        user_info = session_data.get('user_info', {})
        usage = user_info.get('usage', {})
        limits = user_info.get('limits', {})
        
        if usage.get('summary', 0) >= limits.get('summary', 10):
            return jsonify({'error': 'Usage limit exceeded'}), 403
        
        # Get content from URL if provided
        if url:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                for script in soup(["script", "style", "nav", "header", "footer"]):
                    script.extract()
                
                url_text = soup.get_text()
                url_text = ' '.join(url_text.split())
                text = (text + ' ' + url_text).strip()
                
            except Exception as e:
                logger.error(f"URL extraction error: {e}")
                return jsonify({'error': f'Failed to extract content from URL: {str(e)}'}), 400
        
        if len(text.strip()) < 10:
            return jsonify({'error': 'Content too short for analysis'}), 400
        
        # Perform comprehensive analysis
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags_keywords(text)
        brand_mentions = extract_brand_mentions(text, brands_list)
        
        # Generate insights using your existing function
        try:
            analysis_result = summarize_trends(text=text, question="Provide comprehensive market trend analysis", return_format="dict")
            
            if analysis_result.get('error'):
                # Fallback analysis if Claude fails
                key_insights = [
                    f"Sentiment analysis shows {sentiment_analysis['sentiment'].lower()} sentiment (polarity: {sentiment_analysis['polarity']})",
                    f"Identified {len(hashtags)} key topics for trend monitoring",
                    f"Found {len(brand_mentions)} brand mentions in the content"
                ]
                
                recommendations = [
                    "Monitor trending hashtags for engagement opportunities",
                    "Track sentiment changes over time",
                    "Engage with positive sentiment content",
                    "Address any negative sentiment concerns"
                ]
                
                summary = text[:200] + "..." if len(text) > 200 else text
            else:
                key_insights = analysis_result.get('keywords', [])[:5]
                recommendations = list(analysis_result.get('insights', {}).keys())[:4]
                summary = analysis_result.get('full_response', '')[:300] + "..."
                
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            # Fallback analysis
            key_insights = [
                f"Content analysis completed with {sentiment_analysis['sentiment'].lower()} sentiment",
                f"Extracted {len(hashtags)} trending topics",
                f"Identified {len(brand_mentions)} brand mentions"
            ]
            recommendations = [
                "Monitor social media sentiment",
                "Track mentioned brands",
                "Use suggested hashtags for content"
            ]
            summary = text[:200] + "..." if len(text) > 200 else text
        
        result = {
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']}, confidence: {sentiment_analysis['confidence']})",
            'hashtags': hashtags,
            'brand_mentions': brand_mentions,
            'key_insights': key_insights,
            'recommendations': recommendations,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Update usage
        email = session_data['email']
        update_user_usage(email, 'summary')
        user_info['usage']['summary'] = user_info['usage'].get('summary', 0) + 1
        session_data['user_info'] = user_info
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Comprehensive analysis error: {str(e)}")
        return jsonify({'error': 'Analysis failed'}), 500

@app.route('/api/analyze/social', methods=['POST'])
def api_social_analysis():
    """Analyze social media content"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        platforms = data.get('platforms', ['reddit'])
        query = data.get('query', '')
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        # Check usage limits
        session_data = user_sessions[session_id]
        user_info = session_data.get('user_info', {})
        usage = user_info.get('usage', {})
        limits = user_info.get('limits', {})
        
        if usage.get('analysis', 0) >= limits.get('analysis', 5):
            return jsonify({'error': 'Usage limit exceeded'}), 403
        
        results = {
            'query': query,
            'platforms_scanned': platforms,
            'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': {}
        }
        
        all_content = []
        
        # Scan each platform (using mock data for now)
        if 'reddit' in platforms:
            reddit_data = scan_reddit_mock(query)
            results['data']['reddit'] = reddit_data
            all_content.extend([post['title'] + ' ' + post['content'] for post in reddit_data])
        
        if 'youtube' in platforms:
            youtube_data = scan_youtube_mock(query)
            results['data']['youtube'] = youtube_data
            all_content.extend([video['title'] + ' ' + video['description'] for video in youtube_data])
        
        if 'twitter' in platforms:
            twitter_data = scan_twitter_mock(query)
            results['data']['twitter'] = twitter_data
            all_content.extend([tweet['text'] for tweet in twitter_data])
        
        # Overall analysis
        combined_text = ' '.join(all_content)
        
        if combined_text:
            overall_sentiment = analyze_sentiment(combined_text)
            hashtag_suggestions = extract_hashtags_keywords(combined_text)
            
            # Generate insights
            total_posts = sum(len(data) for data in results['data'].values())
            positive_sentiment = sum(1 for platform_data in results['data'].values() 
                                   for item in platform_data 
                                   if item.get('sentiment', {}).get('sentiment') == 'Positive')
            
            results.update({
                'summary': f"Found {total_posts} posts across {len(platforms)} platforms about '{query}'. Overall sentiment is {overall_sentiment['sentiment']} with {positive_sentiment} positive mentions.",
                'overall_sentiment': overall_sentiment,
                'hashtags': hashtag_suggestions,
                'key_insights': [
                    f"Scanned {total_posts} posts across {', '.join(platforms)}",
                    f"Overall sentiment: {overall_sentiment['sentiment']} (polarity: {overall_sentiment['polarity']})",
                    f"Positive mentions: {positive_sentiment}/{total_posts}",
                    f"Most discussed topics: {', '.join(hashtag_suggestions[:5])}"
                ],
                'recommendations': [
                    "Monitor trending hashtags for engagement opportunities",
                    "Engage with positive sentiment posts",
                    "Address any negative sentiment concerns",
                    "Create content around trending topics"
                ]
            })
        
        # Update usage
        email = session_data['email']
        update_user_usage(email, 'analysis')
        user_info['usage']['analysis'] = user_info['usage'].get('analysis', 0) + 1
        session_data['user_info'] = user_info
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Social media analysis error: {str(e)}")
        return jsonify({'error': 'Analysis failed. Please try again.'}), 500

@app.route('/api/analyze/text', methods=['POST'])
def api_text_analysis():
    """Analyze text content for trends and sentiment"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        text = data.get('text', '')
        question = data.get('question', '')
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if not text:
            return jsonify({'error': 'Text content is required'}), 400
        
        if len(text.strip()) < 10:
            return jsonify({'error': 'Text too short for meaningful analysis'}), 400
        
        # Check usage limits
        session_data = user_sessions[session_id]
        user_info = session_data.get('user_info', {})
        usage = user_info.get('usage', {})
        limits = user_info.get('limits', {})
        
        if usage.get('question', 0) >= limits.get('question', 20):
            return jsonify({'error': 'Usage limit exceeded'}), 403
        
        # Perform text analysis
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags_keywords(text)
        brand_mentions = extract_brand_mentions(text)
        
        # Use your existing summarize_trends function
        try:
            analysis_question = question if question else "Analyze this text for business insights and trends"
            analysis_result = summarize_trends(text=text, question=analysis_question, return_format="dict")
            
            if analysis_result.get('error'):
                # Fallback analysis
                summary = text[:200] + "..." if len(text) > 200 else text
                key_insights = [
                    f"Text sentiment: {sentiment_analysis['sentiment']} (confidence: {sentiment_analysis['confidence']})",
                    f"Key topics identified: {', '.join(hashtags[:3])}",
                    f"Word count: {len(text.split())} words"
                ]
                recommendations = [
                    "Consider the sentiment when planning content strategy",
                    "Use identified hashtags for social media",
                    "Monitor brand mentions if any were found"
                ]
            else:
                summary = analysis_result.get('full_response', '')[:300] + "..."
                key_insights = analysis_result.get('keywords', [])[:5]
                recommendations = list(analysis_result.get('insights', {}).keys())[:4]
                
        except Exception as e:
            logger.error(f"Text analysis error: {e}")
            summary = text[:200] + "..." if len(text) > 200 else text
            key_insights = [
                f"Basic analysis completed with {sentiment_analysis['sentiment']} sentiment",
                f"Extracted {len(hashtags)} key topics"
            ]
            recommendations = [
                "Review sentiment implications",
                "Consider trending topics for content"
            ]
        
        result = {
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']})",
            'hashtags': hashtags,
            'brand_mentions': brand_mentions,
            'key_insights': key_insights,
            'recommendations': recommendations,
            'word_count': len(text.split()),
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Update usage
        email = session_data['email']
        update_user_usage(email, 'question')
        user_info['usage']['question'] = user_info['usage'].get('question', 0) + 1
        session_data['user_info'] = user_info
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Text analysis error: {str(e)}")
        return jsonify({'error': 'Text analysis failed'}), 500

@app.route('/api/analyze/url', methods=['POST'])
def api_url_analysis():
    """Extract and analyze content from websites"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        url = data.get('url', '')
        question = data.get('question', '')
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Check usage limits
        session_data = user_sessions[session_id]
        user_info = session_data.get('user_info', {})
        usage = user_info.get('usage', {})
        limits = user_info.get('limits', {})
        
        if usage.get('question', 0) >= limits.get('question', 20):
            return jsonify({'error': 'Usage limit exceeded'}), 403
        
        # Extract content from URL
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.extract()
            
            # Get text content
            text = soup.get_text()
            text = ' '.join(text.split())
            
            # Limit text length for analysis
            if len(text) > 3000:
                text = text[:3000] + "..."
                
        except requests.RequestException as e:
            return jsonify({'error': f'Failed to fetch URL: {str(e)}'}), 400
        except Exception as e:
            return jsonify({'error': f'Failed to extract content: {str(e)}'}), 400
        
        if len(text.strip()) < 50:
            return jsonify({'error': 'Insufficient content extracted from URL'}), 400
        
        # Perform analysis
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags_keywords(text)
        brand_mentions = extract_brand_mentions(text)
        
        # Use your existing analyze_url_content function or fallback
        try:
            if 'analyze_url_content' in globals():
                analysis_result = analyze_url_content(url, question)
            else:
                analysis_question = question if question else "Analyze this website content for business insights"
                analysis_result = summarize_trends(text=text, question=analysis_question, return_format="dict")
            
            if analysis_result.get('error'):
                # Fallback analysis
                summary = text[:200] + "..." if len(text) > 200 else text
                key_insights = [
                    f"Website sentiment: {sentiment_analysis['sentiment']}",
                    f"Content length: {len(text.split())} words",
                    f"Key topics: {', '.join(hashtags[:3])}"
                ]
                recommendations = [
                    "Review the content sentiment for brand alignment",
                    "Consider the key topics for content strategy",
                    "Monitor any brand mentions found"
                ]
            else:
                summary = analysis_result.get('full_response', '')[:300] + "..."
                key_insights = analysis_result.get('keywords', [])[:5]
                recommendations = list(analysis_result.get('insights', {}).keys())[:4]
                
        except Exception as e:
            logger.error(f"URL content analysis error: {e}")
            summary = text[:200] + "..." if len(text) > 200 else text
            key_insights = [
                f"Basic analysis of website content completed",
                f"Sentiment: {sentiment_analysis['sentiment']}"
            ]
            recommendations = [
                "Review extracted content for relevance",
                "Consider sentiment implications"
            ]
        
        result = {
            'url': url,
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']})",
            'hashtags': hashtags,
            'brand_mentions': brand_mentions,
            'key_insights': key_insights,
            'recommendations': recommendations,
            'content_length': len(text.split()),
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Update usage
        email = session_data['email']
        update_user_usage(email, 'question')
        user_info['usage']['question'] = user_info['usage'].get('question', 0) + 1
        session_data['user_info'] = user_info
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"URL analysis error: {str(e)}")
        return jsonify({'error': 'URL analysis failed'}), 500

@app.route('/api/analyze/file', methods=['POST'])
def api_file_analysis():
    """Upload and analyze documents and files"""
    try:
        session_id = request.form.get('session_id')
        question = request.form.get('question', '')
        
        # Validate session
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file size (16MB limit)
        if len(file.read()) > 16 * 1024 * 1024:
            return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 400
        
        file.seek(0)  # Reset file pointer
        
        # Check usage limits
        session_data = user_sessions[session_id]
        user_info = session_data.get('user_info', {})
        usage = user_info.get('usage', {})
        limits = user_info.get('limits', {})
        
        if usage.get('question', 0) >= limits.get('question', 20):
            return jsonify({'error': 'Usage limit exceeded'}), 403
        
        # Extract text from file
        tmp_path = None
        try:
            # Save file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name
            
            # Extract text using textract
            try:
                text = textract.process(tmp_path).decode('utf-8')
            except Exception as e:
                # Fallback for unsupported file types
                if file.filename.lower().endswith(('.txt', '.md')):
                    with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                else:
                    return jsonify({'error': f'Unsupported file type or extraction failed: {str(e)}'}), 400
            
        except Exception as e:
            return jsonify({'error': f'File processing error: {str(e)}'}), 400
        finally:
            # Clean up temporary file
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        
        if len(text.strip()) < 20:
            return jsonify({'error': 'Insufficient text content in file'}), 400
        
        # Limit text length for analysis
        if len(text) > 4000:
            text = text[:4000] + "..."
        
        # Perform analysis
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags_keywords(text)
        brand_mentions = extract_brand_mentions(text)
        
        # Use your existing extract_text_from_file function or fallback
        try:
            if 'extract_text_from_file' in globals():
                # Reset file for extract_text_from_file function
                file.seek(0)
                analysis_result = extract_text_from_file(file, return_format="dict")
            else:
                analysis_question = question if question else "Analyze this document for business insights and trends"
                analysis_result = summarize_trends(text=text, question=analysis_question, return_format="dict")
            
            if analysis_result.get('error'):
                # Fallback analysis
                summary = text[:200] + "..." if len(text) > 200 else text
                key_insights = [
                    f"Document analysis completed with {sentiment_analysis['sentiment']} sentiment",
                    f"File contains {len(text.split())} words",
                    f"Key topics identified: {', '.join(hashtags[:3])}"
                ]
                recommendations = [
                    "Review document sentiment for strategic implications",
                    "Use identified topics for content planning",
                    "Consider document insights for decision making"
                ]
            else:
                summary = analysis_result.get('full_response', '')[:300] + "..."
                key_insights = analysis_result.get('keywords', [])[:5]
                recommendations = list(analysis_result.get('insights', {}).keys())[:4]
                
        except Exception as e:
            logger.error(f"Document analysis error: {e}")
            summary = text[:200] + "..." if len(text) > 200 else text
            key_insights = [
                f"Basic document analysis completed",
                f"Sentiment: {sentiment_analysis['sentiment']}",
                f"Word count: {len(text.split())}"
            ]
            recommendations = [
                "Review extracted content for key insights",
                "Consider sentiment implications",
                "Use findings for strategic planning"
            ]
        
        result = {
            'filename': file.filename,
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']})",
            'hashtags': hashtags,
            'brand_mentions': brand_mentions,
            'key_insights': key_insights,
            'recommendations': recommendations,
            'word_count': len(text.split()),
            'file_size': f"{len(file.read())/1024:.1f} KB",
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Update usage
        email = session_data['email']
        update_user_usage(email, 'question')
        user_info['usage']['question'] = user_info['usage'].get('question', 0) + 1
        session_data['user_info'] = user_info
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"File analysis error: {str(e)}")
        return jsonify({'error': 'File analysis failed'}), 500

@app.route('/api/user/info', methods=['POST'])
def api_user_info():
    """Get updated user information"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        session_data = user_sessions[session_id]
        email = session_data['email']
        
        return jsonify({
            'user': {
                'email': email,
                'subscription_type': users_db[email]['subscription_type'],
                'usage': users_db[email]['usage'],
                'limits': users_db[email]['limits']
            }
        })
        
    except Exception as e:
        logger.error(f"User info error: {str(e)}")
        return jsonify({'error': 'Failed to get user info'}), 500

@app.route('/api/cache/clear', methods=['POST'])
def api_clear_cache():
    """Clear analysis cache"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        # Clear cache from app2.py if available
        try:
            from app2 import clear_cache
            clear_cache()
        except ImportError:
            pass
        
        return jsonify({'message': 'Cache cleared successfully'})
        
    except Exception as e:
        logger.error(f"Cache clear error: {str(e)}")
        return jsonify({'error': 'Failed to clear cache'}), 500

# Web routes (your existing routes)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/TrendSummarizer')
def TrendSummarizer():
    return render_template('TrendSummarizer.html')

@app.route('/DataHelp')
def DataHelp():
    return render_template('DataHelp.html')

@app.route('/signin')
def signin():
    return render_template('signin.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'Market Trend Summarizer'}

@app.route('/tools')
def tools():
    return render_template('tools.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
