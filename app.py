# Fixed Flask App with All Analysis Features
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

# Check for required imports
try:
    import textract
    TEXTRACT_AVAILABLE = True
except ImportError:
    TEXTRACT_AVAILABLE = False
    logger.warning("textract not available")

try:
    import requests
    from bs4 import BeautifulSoup
    WEB_SCRAPING_AVAILABLE = True
except ImportError:
    WEB_SCRAPING_AVAILABLE = False
    logger.warning("requests/beautifulsoup4 not available")

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    logger.warning("textblob not available")

try:
    from collections import Counter
    import re
    ANALYSIS_TOOLS_AVAILABLE = True
except ImportError:
    ANALYSIS_TOOLS_AVAILABLE = False

try:
    from app2 import claude_messages, analyze_question, summarize_trends, extract_text_from_file, analyze_url_content
    APP2_AVAILABLE = True
    logger.info("Successfully imported from app2.py")
except ImportError as e:
    APP2_AVAILABLE = False
    logger.warning(f"Could not import from app2.py: {e}")
except Exception as e:
    APP2_AVAILABLE = False
    logger.error(f"Error importing from app2.py: {e}")

# In-memory storage
user_sessions = {}
users_db = {
    "demo@example.com": {
        "password": "demo123",
        "subscription_type": "Free Plan", 
        "usage": {"summary": 2, "analysis": 1, "question": 5},
        "limits": {"summary": 10, "analysis": 5, "question": 20}
    }
}

def get_user_info(email):
    return users_db.get(email, {
        "subscription_type": "Free Plan",
        "usage": {"summary": 0, "analysis": 0, "question": 0},
        "limits": {"summary": 10, "analysis": 5, "question": 20}
    })

def update_user_usage(email, usage_type):
    if email in users_db:
        users_db[email]["usage"][usage_type] = users_db[email]["usage"].get(usage_type, 0) + 1

def analyze_sentiment(text):
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
        positive_words = ['good', 'great', 'excellent', 'amazing', 'positive', 'love', 'best']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'worst', 'negative', 'poor']
        
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
    try:
        if ANALYSIS_TOOLS_AVAILABLE:
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
            word_counts = Counter(filtered_words)
            top_words = [word for word, count in word_counts.most_common(max_hashtags)]
            hashtags = [word.capitalize() for word in top_words]
            return hashtags
    except Exception as e:
        logger.error(f"Hashtag extraction error: {e}")
    
    try:
        words = text.split()[:10]
        hashtags = [word.strip('.,!?').capitalize() for word in words if len(word) > 3]
        return hashtags[:max_hashtags]
    except Exception as e:
        logger.error(f"Fallback hashtag extraction error: {e}")
        return ['Analysis', 'Trends', 'Insights']

def extract_brand_mentions(text, brands_list=None):
    try:
        if brands_list is None:
            brands_list = ['Apple', 'Google', 'Microsoft', 'Amazon', 'Meta', 'Tesla', 'Netflix']
        
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
    try:
        sample_posts = [
            {
                'title': f'Discussion about {query} trends in 2024',
                'content': f'Great insights on {query}. The community is very positive about recent developments.',
                'score': 156,
                'comments': 23,
                'url': 'https://reddit.com/r/technology/sample_post_1',
                'subreddit': 'technology',
                'created': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
        ]
        
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

# Analysis routes
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
        
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if not text and not url:
            return jsonify({'error': 'Text or URL is required'}), 400
        
        session_data = user_sessions[session_id]
        user_info = session_data.get('user_info', {})
        usage = user_info.get('usage', {})
        limits = user_info.get('limits', {})
        
        if usage.get('summary', 0) >= limits.get('summary', 10):
            return jsonify({'error': 'Usage limit exceeded'}), 403
        
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
                if not text:
                    return jsonify({'error': f'Failed to extract content from URL: {str(e)}'}), 400
        
        if len(text.strip()) < 10:
            return jsonify({'error': 'Content too short for analysis'}), 400
        
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags_keywords(text)
        brand_mentions = extract_brand_mentions(text, brands_list)
        
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
        
        if not key_insights:
            key_insights = [
                f"Sentiment analysis shows {sentiment_analysis['sentiment'].lower()} sentiment",
                f"Identified {len(hashtags)} key topics for trend monitoring",
                f"Found {len(brand_mentions)} brand mentions in the content",
                "Content analysis completed successfully"
            ]
        
        if not recommendations:
            recommendations = [
                "Monitor trending hashtags for engagement opportunities",
                "Track sentiment changes over time",
                "Engage with positive sentiment content",
                "Address any negative sentiment concerns"
            ]
        
        if not summary:
            summary = text[:200] + "..." if len(text) > 200 else text
        
        result = {
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']})",
            'hashtags': hashtags,
            'brand_mentions': brand_mentions,
            'key_insights': key_insights,
            'recommendations': recommendations,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
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
        
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
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
        
        for platform in platforms:
            if platform == 'reddit':
                reddit_data = create_mock_social_data(query)
                results['data']['reddit'] = reddit_data
                all_content.extend([post['title'] + ' ' + post['content'] for post in reddit_data])
            elif platform == 'youtube':
                youtube_data = [{
                    'title': f'{query} Explained: Complete Guide 2024',
                    'description': f'Comprehensive overview of {query} trends and prospects.',
                    'views': '45.2K',
                    'sentiment': analyze_sentiment(f'Comprehensive overview of {query} trends.')
                }]
                results['data']['youtube'] = youtube_data
                all_content.extend([video['title'] + ' ' + video['description'] for video in youtube_data])
            elif platform == 'twitter':
                twitter_data = [{
                    'text': f'Amazing {query} application! Game-changing potential',
                    'author': '@techexplorer',
                    'retweets': 45,
                    'sentiment': analyze_sentiment('Amazing application! Game-changing potential.')
                }]
                results['data']['twitter'] = twitter_data
                all_content.extend([tweet['text'] for tweet in twitter_data])
        
        combined_text = ' '.join(all_content)
        
        if combined_text:
            overall_sentiment = analyze_sentiment(combined_text)
            hashtag_suggestions = extract_hashtags_keywords(combined_text)
            
            total_posts = sum(len(data) for data in results['data'].values())
            positive_sentiment = sum(1 for platform_data in results['data'].values() 
                                   for item in platform_data 
                                   if item.get('sentiment', {}).get('sentiment') == 'Positive')
            
            results.update({
                'summary': f"Found {total_posts} posts across {len(platforms)} platforms about '{query}'. Overall sentiment is {overall_sentiment['sentiment']}.",
                'overall_sentiment': overall_sentiment,
                'hashtags': hashtag_suggestions,
                'key_insights': [
                    f"Scanned {total_posts} posts across {', '.join(platforms)}",
                    f"Overall sentiment: {overall_sentiment['sentiment']}",
                    f"Positive mentions: {positive_sentiment}/{total_posts}"
                ],
                'recommendations': [
                    "Monitor trending hashtags for engagement opportunities",
                    "Engage with positive sentiment posts",
                    "Create content around trending topics"
                ]
            })
        
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
        
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if not text:
            return jsonify({'error': 'Text content is required'}), 400
        
        if len(text.strip()) < 10:
            return jsonify({'error': 'Text too short for meaningful analysis'}), 400
        
        session_data = user_sessions[session_id]
        user_info = session_data.get('user_info', {})
        usage = user_info.get('usage', {})
        limits = user_info.get('limits', {})
        
        if usage.get('question', 0) >= limits.get('question', 20):
            return jsonify({'error': 'Usage limit exceeded'}), 403
        
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags_keywords(text)
        brand_mentions = extract_brand_mentions(text)
        
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
        
        if not summary:
            summary = text[:200] + "..." if len(text) > 200 else text
            
        if not key_insights:
            key_insights = [
                f"Text sentiment: {sentiment_analysis['sentiment']}",
                f"Key topics identified: {', '.join(hashtags[:3])}",
                f"Word count: {len(text.split())} words"
            ]
            
        if not recommendations:
            recommendations = [
                "Consider the sentiment when planning content strategy",
                "Use identified hashtags for social media",
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
        
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        session_data = user_sessions[session_id]
        user_info = session_data.get('user_info', {})
        usage = user_info.get('usage', {})
        limits = user_info.get('limits', {})
        
        if usage.get('question', 0) >= limits.get('question', 20):
            return jsonify({'error': 'Usage limit exceeded'}), 403
        
        text = ""
        
        if WEB_SCRAPING_AVAILABLE:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                    script.extract()
                
                text = soup.get_text()
                text = ' '.join(text.split())
                
                if len(text) > 3000:
                    text = text[:3000] + "..."
                    
            except Exception as e:
                logger.error(f"URL extraction error: {e}")
                return jsonify({'error': f'Failed to extract content from URL: {str(e)}'}), 400
        else:
            return jsonify({'error': 'URL analysis not available - missing required packages'}), 500
        
        if len(text.strip()) < 50:
            return jsonify({'error': 'Insufficient content extracted from URL'}), 400
        
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags_keywords(text)
        brand_mentions = extract_brand_mentions(text)
        
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
        
        if not summary:
            summary = text[:200] + "..." if len(text) > 200 else text
            
        if not key_insights:
            key_insights = [
                f"Website sentiment: {sentiment_analysis['sentiment']}",
                f"Content length: {len(text.split())} words",
                f"Key topics: {', '.join(hashtags[:3])}"
            ]
            
        if not recommendations:
            recommendations = [
                "Review the content sentiment for brand alignment",
                "Consider the key topics for content strategy",
                "Monitor any brand mentions found"
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
        
        if session_id not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 401
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 16 * 1024 * 1024:
            return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 400
        
        session_data = user_sessions[session_id]
        user_info = session_data.get('user_info', {})
        usage = user_info.get('usage', {})
        limits = user_info.get('limits', {})
        
        if usage.get('question', 0) >= limits.get('question', 20):
            return jsonify({'error': 'Usage limit exceeded'}), 403
        
        text = ""
        tmp_path = None
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name
            
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if TEXTRACT_AVAILABLE:
                try:
                    text = textract.process(tmp_path).decode('utf-8')
                except Exception as e:
                    logger.error(f"Textract error: {e}")
                    if file_ext in ['.txt', '.md']:
                        with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                            text = f.read()
                    else:
                        raise e
            else:
                if file_ext in ['.txt', '.md']:
                    with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                else:
                    return jsonify({'error': 'File type not supported - textract package required for PDF/Word files'}), 400
            
        except Exception as e:
            logger.error(f"File processing error: {e}")
            return jsonify({'error': f'File processing error: {str(e)}'}), 400
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        
        if len(text.strip()) < 20:
            return jsonify({'error': 'Insufficient text content in file'}), 400
        
        if len(text) > 4000:
            text = text[:4000] + "..."
        
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags_keywords(text)
        brand_mentions = extract_brand_mentions(text)
        
        key_insights = []
        recommendations = []
        summary = ""
        
        if APP2_AVAILABLE:
            try:
                file.seek(0)
                analysis_result = extract_text_from_file(file, return_format="dict")
                
                if not analysis_result.get('error'):
                    summary = analysis_result.get('full_response', '')[:300] + "..."
                    key_insights = analysis_result.get('keywords', [])[:5]
                    recommendations = list(analysis_result.get('insights', {}).keys())[:4]
                    
            except Exception as e:
                logger.error(f"app2.py file analysis error: {e}")
        
        if not summary:
            summary = text[:200] + "..." if len(text) > 200 else text
            
        if not key_insights:
            key_insights = [
                f"Document analysis completed with {sentiment_analysis['sentiment']} sentiment",
                f"File contains {len(text.split())} words",
                f"Key topics identified: {', '.join(hashtags[:3])}"
            ]
            
        if not recommendations:
            recommendations = [
                "Review document sentiment for strategic implications",
                "Use identified topics for content planning",
                "Consider document insights for decision making"
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

# Web routes
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
            'web_scraping': WEB_SCRAPING_AVAILABLE
        }
    }

@app.route('/tools')
def tools():
    try:
        return render_template('tools.html')
    except Exception as e:
        logger.error(f"Tools route error: {str(e)}")
        return f"Error loading page: {str(e)}", 500

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
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
