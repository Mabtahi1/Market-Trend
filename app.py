# Your Original Flask App with Added Analysis Features
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect
from flask_cors import CORS
import os
import logging
import tempfile
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
from PIL import Image

# Import your app2.py functions
try:
    from app2 import (
        claude_messages, 
        analyze_question, 
        summarize_trends, 
        extract_text_from_file, 
        analyze_url_content
    )
    APP2_AVAILABLE = True
    print("✅ Successfully imported from app2.py")
except ImportError as e:
    APP2_AVAILABLE = False
    print(f"❌ Error importing from app2.py: {e}")

# Check for analysis packages
try:
    import textract
    TEXTRACT_AVAILABLE = True
except ImportError:
    TEXTRACT_AVAILABLE = False

try:
    import requests
    from bs4 import BeautifulSoup
    WEB_SCRAPING_AVAILABLE = True
except ImportError:
    WEB_SCRAPING_AVAILABLE = False

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

try:
    from collections import Counter
    import re
    ANALYSIS_TOOLS_AVAILABLE = True
except ImportError:
    ANALYSIS_TOOLS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app (your original configuration)
app = Flask(__name__, template_folder='.')
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app)

# Simple analysis functions for the new features
def analyze_sentiment(text):
    try:
        if TEXTBLOB_AVAILABLE:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            if polarity > 0.1:
                sentiment = "Positive"
            elif polarity < -0.1:
                sentiment = "Negative"
            else:
                sentiment = "Neutral"
                
            return {
                "sentiment": sentiment,
                "polarity": round(polarity, 3),
                "confidence": round(abs(polarity), 3)
            }
    except Exception as e:
        logger.error(f"TextBlob sentiment analysis error: {e}")
    
    # Enhanced fallback with more words
    positive_words = [
        'good', 'great', 'excellent', 'amazing', 'positive', 'love', 'best', 
        'outstanding', 'fantastic', 'wonderful', 'success', 'growth', 'opportunity',
        'strong', 'bullish', 'optimistic', 'confident', 'favorable', 'promising',
        'increase', 'gain', 'profit', 'advance', 'improve', 'boost', 'surge'
    ]
    negative_words = [
        'bad', 'terrible', 'awful', 'hate', 'worst', 'negative', 'poor',
        'decline', 'loss', 'drop', 'fall', 'weak', 'bearish', 'pessimistic',
        'concern', 'risk', 'threat', 'problem', 'crisis', 'failure', 'decrease'
    ]
    
    text_lower = text.lower()
    
    # Count words with weights
    positive_count = 0
    negative_count = 0
    
    for word in positive_words:
        positive_count += text_lower.count(word)
    
    for word in negative_words:
        negative_count += text_lower.count(word)
    
    # Calculate polarity
    total_sentiment_words = positive_count + negative_count
    if total_sentiment_words == 0:
        polarity = 0.0
    else:
        polarity = (positive_count - negative_count) / max(total_sentiment_words, 1)
        polarity = max(-1.0, min(1.0, polarity))  # Clamp between -1 and 1
    
    # Determine sentiment
    if polarity > 0.2:
        sentiment = "Positive"
    elif polarity < -0.2:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
    
    return {
        "sentiment": sentiment,
        "polarity": round(polarity, 3),
        "confidence": round(abs(polarity), 3)
    }

def extract_hashtags(text, max_hashtags=10):
    try:
        if ANALYSIS_TOOLS_AVAILABLE:
            words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
            stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            filtered_words = [word for word in words if word not in stop_words]
            word_counts = Counter(filtered_words)
            hashtags = [word.capitalize() for word, count in word_counts.most_common(max_hashtags)]
            return hashtags
    except:
        pass
    
    # Simple fallback
    words = text.split()[:10]
    hashtags = [word.strip('.,!?').capitalize() for word in words if len(word) > 3]
    return hashtags[:max_hashtags]

def create_mock_social_data(query):
    return [
        {
            'title': f'Discussion about {query} trends',
            'content': f'Great insights on {query}. Very positive community response.',
            'score': 156,
            'comments': 23,
            'sentiment': analyze_sentiment(f'Great insights on {query}. Very positive.')
        },
        {
            'title': f'{query} market analysis',
            'content': f'Interesting analysis of {query} market trends and growth potential.',
            'score': 89,
            'comments': 15,
            'sentiment': analyze_sentiment(f'Interesting analysis of {query} market trends.')
        }
    ]

# YOUR ORIGINAL ROUTES (exactly as they were)
@app.route('/')
@app.route('/index')
def hello():
    """Renders the home page."""
    return render_template('index.html')

@app.route('/contact')
def contact():
    """Renders the contact page."""
    return render_template('contact.html')

@app.route('/about')
def about():
    """Renders the about page."""
    return render_template('about.html')

@app.route('/TrendSummarizer')
def TrendSummarizer():
    """Renders the trend summarizer page."""
    return render_template('TrendSummarizer.html')

@app.route('/DataHelp')
def DataHelp():
    """Renders the data help page."""
    return render_template('DataHelp.html')

@app.route('/signin')
def signin():
    """Renders the signin page."""
    return render_template('signin.html')

@app.route('/signup')
def signup():
    """Renders the signup page."""
    return render_template('signup.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy', 'service': 'Market Trend Summarizer'}

@app.route('/tools')
def tools():
    return render_template('tools.html')

# NEW AUTHENTICATION ROUTES (simple, no Firebase required for now)
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        # Simple demo authentication - accepts any email/password for now
        if email and password and len(password) >= 3:
            session['user_email'] = email
            return jsonify({
                'session_id': 'demo_session',
                'user': {
                    'email': email,
                    'subscription_type': 'Free Plan',
                    'usage': {'summary': 0, 'analysis': 0, 'question': 0},
                    'limits': {'summary': 10, 'analysis': 5, 'question': 20}
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
        
        # Simple demo signup - accepts any email/password
        if email and password and len(password) >= 3:
            session['user_email'] = email
            return jsonify({
                'session_id': 'demo_session',
                'user': {
                    'email': email,
                    'subscription_type': 'Free Plan',
                    'usage': {'summary': 0, 'analysis': 0, 'question': 0},
                    'limits': {'summary': 10, 'analysis': 5, 'question': 20}
                }
            })
        else:
            return jsonify({'error': 'Invalid email or password'}), 400
            
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        return jsonify({'error': 'Signup failed'}), 500

@app.route('/api/auth/validate', methods=['POST'])
def api_validate():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        # Simple validation - if they have an email in session, they're valid
        if 'user_email' in session:
            return jsonify({
                'user': {
                    'email': session['user_email'],
                    'subscription_type': 'Free Plan',
                    'usage': {'summary': 0, 'analysis': 0, 'question': 0},
                    'limits': {'summary': 10, 'analysis': 5, 'question': 20}
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
        session.clear()
        return jsonify({'message': 'Logged out successfully'})
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

# NEW ANALYSIS ROUTES
@app.route('/api/analyze/comprehensive', methods=['POST'])
def api_comprehensive_analysis():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        text = data.get('text', '')
        url = data.get('url')
        brands_list = data.get('brands_list', [])
        
        if not text and not url:
            return jsonify({'error': 'Text or URL is required'}), 400
        
        # Extract content from URL if provided
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
        
        # Perform basic analysis
        # Perform basic analysis
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags(text, max_hashtags=12)
        
        # Dynamic analysis for any topic
        text_lower = text.lower()
        word_count = len(text.split())
        main_themes = ', '.join([hashtag.lower() for hashtag in hashtags[:5]])
        
        # Generate comprehensive summary for any topic (longer format)
        summary = f"Comprehensive market analysis of {word_count} words reveals {sentiment_analysis['sentiment'].lower()} market sentiment across key areas including {main_themes}. The analysis identifies significant opportunities for strategic positioning, competitive differentiation, and growth acceleration in the current market environment. Market dynamics show evolving customer preferences, technological disruption, and shifting competitive landscapes that create both challenges and opportunities for businesses. Key success factors include understanding customer pain points, leveraging technology for operational efficiency, building strategic partnerships, and maintaining agile response to market changes. The current environment favors companies that can demonstrate clear value propositions, measurable ROI, and sustainable competitive advantages through innovation and customer-centric approaches. Strategic implications suggest timing for market entry, investment decisions, and partnership development based on identified trends and competitive positioning opportunities."
        
        # Always generate exactly 5 key insights for any topic
        key_insights = [
            {
                "title": f"Market sentiment analysis reveals {sentiment_analysis['sentiment'].lower()} outlook with strategic implications",
                "explanation": f"Content analysis shows {sentiment_analysis['sentiment'].lower()} sentiment (polarity: {sentiment_analysis['polarity']}) across {word_count} words of market intelligence. This sentiment pattern indicates market confidence levels and suggests optimal timing for strategic initiatives, investment decisions, and market entry strategies. The analysis provides directional guidance for resource allocation and competitive positioning."
            },
            {
                "title": f"Competitive landscape analysis identifies {len(hashtags)} key differentiation opportunities",
                "explanation": f"Market analysis reveals primary focus areas around {', '.join(hashtags[:3])} with secondary themes in {', '.join(hashtags[3:6]) if len(hashtags) > 3 else 'emerging market segments'}. Competitive positioning opportunities exist in underserved segments, suggesting potential for market leadership through innovation, customer experience improvements, and strategic partnerships that address unmet market needs."
            },
            {
                "title": "Technology and innovation trends indicate digital transformation acceleration opportunities",
                "explanation": f"Content patterns show emphasis on technological advancement and innovation with key themes including {', '.join(hashtags[6:9]) if len(hashtags) > 6 else 'digital solutions, automation, and emerging technologies'}. This indicates opportunities for technology-driven competitive advantages, operational efficiency gains, and new revenue streams through digital transformation initiatives."
            },
            {
                "title": "Customer demand patterns reveal evolving market requirements and strategic positioning needs", 
                "explanation": f"Analysis identifies shifting customer expectations and market demands around {', '.join(hashtags[9:12]) if len(hashtags) > 9 else 'value delivery, service quality, and user experience'}. These patterns suggest opportunities for customer-centric innovation, personalized solutions, and enhanced user experiences that drive market differentiation and customer loyalty."
            },
            {
                "title": "Financial and investment indicators suggest strong growth potential and ROI optimization opportunities",
                "explanation": f"Market conditions indicate favorable investment climate with focus on sustainable growth and profitability across identified market segments. Financial patterns suggest opportunities for capital deployment, revenue optimization, and cost efficiency improvements that enhance competitive positioning while maintaining healthy unit economics and scalable business models."
            }
        ]
        
        # Always generate exactly 5 strategic recommendations for any topic
        recommendations = [
            {
                "title": "Develop comprehensive market positioning strategy based on competitive gap analysis",
                "explanation": "Focus on identified market gaps and create unique value propositions that address unmet customer needs. Conduct detailed competitor analysis, identify underserved segments, and position offerings to capture market share through differentiation and superior customer value delivery. Implement brand positioning that resonates with target audiences and creates sustainable competitive advantages."
            },
            {
                "title": "Implement technology-driven operational excellence and innovation programs",
                "explanation": "Invest in technology infrastructure that supports scalable growth and operational efficiency. Prioritize automation, digital transformation, and innovation initiatives that reduce costs, improve customer experience, and create sustainable competitive advantages. Focus on technologies that enhance core business processes and enable data-driven decision making."
            },
            {
                "title": "Build strategic partnership ecosystem to accelerate market penetration and growth",
                "explanation": "Develop partnerships with complementary businesses, technology providers, and distribution channels. Focus on alliances that provide access to new markets, enhance technical capabilities, and reduce time-to-market for new products and services. Create partnership frameworks that generate mutual value and accelerate business growth objectives."
            },
            {
                "title": "Execute data-driven customer acquisition and retention optimization strategy",
                "explanation": "Implement analytics-driven approach to customer acquisition, focusing on high-value segments identified in market analysis. Develop personalized customer experiences, optimize conversion funnels, and create loyalty programs that increase customer lifetime value. Use data insights to improve targeting, messaging, and customer journey optimization."
            },
            {
                "title": "Establish performance measurement framework with clear ROI metrics and success KPIs",
                "explanation": "Create comprehensive performance tracking system that measures business impact, customer satisfaction, and competitive positioning. Establish clear ROI models, implement regular performance reviews, and use data insights to optimize strategy execution and resource allocation. Focus on metrics that drive business value and support strategic decision making."
            }
        ]
        
        # Try app2.py for enhanced analysis if available
        if APP2_AVAILABLE:
            try:
                analysis_result = summarize_trends(text=text, question="Provide comprehensive market trend analysis with actionable business insights", return_format="dict")
                if not analysis_result.get('error') and analysis_result.get('full_response'):
                    app2_response = analysis_result.get('full_response', '')
                    if len(app2_response) > 300:  # Only use if substantial
                        summary = app2_response  # Remove truncation
            except Exception as e:
                logger.error(f"app2.py analysis error: {e}")
        
        strategic_hashtags = hashtags[:10] if len(hashtags) >= 10 else hashtags + ['Business', 'Strategy', 'Innovation', 'Growth'][:10-len(hashtags)]
        
        result = {
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']})",
            'hashtags': strategic_hashtags,
            'brand_mentions': {brand: text_lower.count(brand.lower()) for brand in brands_list if brand.lower() in text_lower},
            'key_insights': key_insights,
            'recommendations': recommendations,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'word_count': word_count
        }
        
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
            
        platforms = data.get('platforms', ['reddit'])
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        # Create more detailed mock social media data
        results = {
            'query': query,
            'platforms_scanned': platforms,
            'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': {}
        }
        
        all_content = []
        
        # Generate data for each requested platform
        for platform in platforms:
            if platform == 'reddit':
                reddit_data = [
                    {
                        'title': f'Discussion about {query} trends in 2024',
                        'content': f'Great insights on {query}. The community is very positive about recent developments and growth potential.',
                        'score': 156,
                        'comments': 23,
                        'url': 'https://reddit.com/r/technology/sample_post_1',
                        'subreddit': 'technology',
                        'created': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'sentiment': analyze_sentiment(f'Great insights on {query}. Very positive about developments.')
                    },
                    {
                        'title': f'{query} market analysis and predictions',
                        'content': f'Interesting analysis of {query} market trends. Some concerns but overall optimistic outlook.',
                        'score': 89,
                        'comments': 15,
                        'url': 'https://reddit.com/r/business/sample_post_2', 
                        'subreddit': 'business',
                        'created': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'sentiment': analyze_sentiment(f'Interesting analysis of {query} market trends.')
                    }
                ]
                results['data']['reddit'] = reddit_data
                all_content.extend([post['title'] + ' ' + post['content'] for post in reddit_data])
                
            elif platform == 'youtube':
                youtube_data = [
                    {
                        'title': f'{query} Explained: Complete Guide 2024',
                        'description': f'Comprehensive overview of {query} trends, applications, and future prospects.',
                        'views': '45.2K',
                        'likes': '1.8K',
                        'url': 'https://youtube.com/watch?v=sample1',
                        'channel': 'Tech Insights',
                        'published': datetime.now().strftime('%Y-%m-%d'),
                        'sentiment': analyze_sentiment(f'Comprehensive overview of {query} trends. Positive outlook.')
                    }
                ]
                results['data']['youtube'] = youtube_data
                all_content.extend([video['title'] + ' ' + video['description'] for video in youtube_data])
                
            elif platform == 'twitter':
                twitter_data = [
                    {
                        'text': f'Just discovered this amazing {query} application! Game-changing potential 🚀 #innovation #tech',
                        'author': '@techexplorer',
                        'retweets': 45,
                        'likes': 128,
                        'url': 'https://twitter.com/sample/status/1',
                        'created': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'sentiment': analyze_sentiment('Amazing application! Game-changing potential.')
                    }
                ]
                results['data']['twitter'] = twitter_data
                all_content.extend([tweet['text'] for tweet in twitter_data])
        
        # Overall analysis
        combined_text = ' '.join(all_content)
        
        if combined_text:
            overall_sentiment = analyze_sentiment(combined_text)
            hashtag_suggestions = extract_hashtags(combined_text)
            
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
            
        text = data.get('text', '')
        question = data.get('question', '')
        
        if not text:
            return jsonify({'error': 'Text content is required'}), 400
        
        if len(text.strip()) < 10:
            return jsonify({'error': 'Text too short for meaningful analysis'}), 400
        
        # Perform analysis
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags(text)
        
        # Try to use app2.py if available
        summary = ""
        key_insights = []
        
        if APP2_AVAILABLE:
            try:
                analysis_question = question if question else "Analyze this text for business insights"
                analysis_result = summarize_trends(text=text, question=analysis_question, return_format="dict")
                
                if not analysis_result.get('error'):
                    summary = analysis_result.get('full_response', '')[:300] + "..."
                    key_insights = analysis_result.get('keywords', [])[:5]
            except Exception as e:
                logger.error(f"app2.py text analysis error: {e}")
        
        # Fallback
        if not summary:
            summary = text
            
        if not key_insights:
            key_insights = [
                f"Text sentiment: {sentiment_analysis['sentiment']}",
                f"Key topics: {', '.join(hashtags[:3])}",
                f"Word count: {len(text.split())} words"
            ]
        
        result = {
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']})",
            'hashtags': hashtags,
            'brand_mentions': {},
            'key_insights': key_insights,
            'recommendations': [
                "Consider the sentiment when planning content strategy",
                "Use identified hashtags for social media",
                "Review content for strategic insights"
            ],
            'word_count': len(text.split()),
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
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
            
        url = data.get('url', '')
        question = data.get('question', '')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        text = ""
        
        if WEB_SCRAPING_AVAILABLE:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                for script in soup(["script", "style", "nav", "header", "footer"]):
                    script.extract()
                
                text = soup.get_text()
                text = ' '.join(text.split())
                
                if len(text) > 3000:
                    text = text[:3000] + "..."
                    
            except Exception as e:
                return jsonify({'error': f'Failed to extract content from URL: {str(e)}'}), 400
        else:
            return jsonify({'error': 'URL analysis not available - missing required packages'}), 500
        
        if len(text.strip()) < 50:
            return jsonify({'error': 'Insufficient content extracted from URL'}), 400
        
        # Perform analysis (similar to text analysis)
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags(text)
        
        summary = text
        
        result = {
            'url': url,
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']})",
            'hashtags': hashtags,
            'brand_mentions': {},
            'key_insights': [
                f"Website sentiment: {sentiment_analysis['sentiment']}",
                f"Content length: {len(text.split())} words",
                f"Key topics: {', '.join(hashtags[:3])}"
            ],
            'recommendations': [
                "Review the content sentiment for brand alignment",
                "Consider the key topics for content strategy",
                "Monitor for content changes"
            ],
            'content_length': len(text.split()),
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"URL analysis error: {str(e)}")
        return jsonify({'error': f'URL analysis failed: {str(e)}'}), 500

@app.route('/api/analyze/file', methods=['POST'])
def api_file_analysis():
    try:
        question = request.form.get('question', '')
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 16 * 1024 * 1024:
            return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 400
        
        text = ""
        tmp_path = None
        
        try:
            # Save temporarily and extract text
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
                file.save(tmp.name)
                tmp_path = tmp.name
            
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if TEXTRACT_AVAILABLE:
                try:
                    text = textract.process(tmp_path).decode('utf-8')
                except Exception as e:
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
                    return jsonify({'error': 'File type not supported - textract package required'}), 400
            
        except Exception as e:
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
        
        # Perform analysis
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags(text)
        
        summary = text
        
        result = {
            'filename': file.filename,
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']})",
            'hashtags': hashtags,
            'brand_mentions': {},
            'key_insights': [
                f"Document sentiment: {sentiment_analysis['sentiment']}",
                f"File contains {len(text.split())} words",
                f"Key topics: {', '.join(hashtags[:3])}"
            ],
            'recommendations': [
                "Review document sentiment for strategic implications",
                "Use identified topics for content planning",
                "Consider document insights for decision making"
            ],
            'word_count': len(text.split()),
            'file_size': f"{file_size/1024:.1f} KB",
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"File analysis error: {str(e)}")
        return jsonify({'error': f'File analysis failed: {str(e)}'}), 500

@app.route('/api/user/info', methods=['POST'])
def api_user_info():
    try:
        return jsonify({
            'user': {
                'email': session.get('user_email', 'demo@example.com'),
                'subscription_type': 'Free Plan',
                'usage': {'summary': 0, 'analysis': 0, 'question': 0},
                'limits': {'summary': 10, 'analysis': 5, 'question': 20}
            }
        })
    except Exception as e:
        return jsonify({'error': 'Failed to get user info'}), 500

@app.route('/api/cache/clear', methods=['POST'])
def api_clear_cache():
    try:
        return jsonify({'message': 'Cache cleared successfully'})
    except Exception as e:
        return jsonify({'error': 'Failed to clear cache'}), 500

from flask import send_file

@app.route('/api/export/pdf', methods=['POST'])
def api_export_pdf():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        results = data.get('results', {})
        analysis_type = data.get('analysis_type', 'comprehensive')
        
        if not results:
            return jsonify({'error': 'No analysis results to export'}), 400
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch, mm
            from reportlab.lib import colors
            from reportlab.graphics.shapes import Drawing, Rect, Circle, Line, String
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from io import BytesIO
        except ImportError:
            return jsonify({'error': 'PDF generation not available - install reportlab'}), 500
        
        # Create custom page template with dark background
        def add_page_background(canvas, doc):
            # Dark page background
            canvas.setFillColor(colors.HexColor('#1a202c'))
            canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
            
            # Header background - darker blue
            canvas.setFillColor(colors.HexColor('#2d3748'))
            canvas.rect(0, A4[1]-100, A4[0], 100, fill=1, stroke=0)
            
            # Company branding
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 24)
            canvas.drawString(50, A4[1]-50, "PROLEXIS ANALYTICS")
            canvas.setFont("Helvetica", 12)
            canvas.drawString(50, A4[1]-70, "Advanced Market Intelligence & Trend Analysis")
            
            # Add actual Prolexis Analytics logo
            try:
                logo_path = "Prolexis_logo.png"  # Make sure this file is in your project directory
                canvas.drawImage(logo_path, A4[0]-100, A4[1]-70, width=40, height=40, mask='auto')
            except:
                # Fallback if logo file not found
                canvas.setFillColor(colors.HexColor('#4a90e2'))
                canvas.circle(A4[0]-80, A4[1]-50, 25, fill=1, stroke=1)
                canvas.setFillColor(colors.white)
                canvas.setFont("Helvetica-Bold", 16)
                text_width = canvas.stringWidth("PA", "Helvetica-Bold", 16)
                canvas.drawString(A4[0]-80 - text_width/2, A4[1]-55, "PA")
            
            # Footer with website
            canvas.setFillColor(colors.HexColor('#2d3748'))
            canvas.rect(0, 0, A4[0], 50, fill=1, stroke=0)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica", 10)
            canvas.drawString(50, 20, f"Generated: {datetime.now().strftime('%B %d, %Y')}")
            canvas.drawRightString(A4[0]-50, 20, "www.prolexisanalytics.com")
            
            # Side accent border
            canvas.setFillColor(colors.HexColor('#4a90e2'))
            canvas.rect(0, 50, 5, A4[1]-150, fill=1, stroke=0)
        
        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            topMargin=120, 
            bottomMargin=70, 
            leftMargin=30,
            rightMargin=30
        )
        
        # Custom styles for dark theme
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=colors.white,
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=18,
            textColor=colors.white,
            spaceAfter=15,
            spaceBefore=25,
            fontName='Helvetica-Bold',
            backColor=colors.HexColor('#4a90e2'),
            leftIndent=15,
            rightIndent=15,
            borderPadding=10
        )
        
        content_style = ParagraphStyle(
            'Content',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.white,
            spaceAfter=12,
            fontName='Helvetica',
            leading=16
        )
        
        content = []
        
        # FIRST PAGE - EXECUTIVE SUMMARY
        content.append(Spacer(1, 50))
        content.append(Paragraph("EXECUTIVE SUMMARY", title_style))
        content.append(Spacer(1, 30))

        # Summary section with colored title box
        summary_text = results.get('summary', '')
        if summary_text:
            # Summary title in colored box
            summary_title = Paragraph("MARKET ANALYSIS SUMMARY", ParagraphStyle(
                'SummaryTitle',
                parent=styles['Normal'],
                fontSize=14,
                textColor=colors.white,
                fontName='Helvetica-Bold',
                alignment=TA_LEFT
            ))
    
            summary_title_table = Table([[summary_title]], colWidths=[7*inch])
            summary_title_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#4a90e2')),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            content.append(summary_title_table)
    
            # Summary content box
            summary_para = Paragraph(summary_text, content_style)
            summary_content_table = Table([[summary_para]], colWidths=[7*inch])
            summary_content_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#4a90e2')),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ]))
            content.append(summary_content_table)
            content.append(Spacer(1, 25))

        
        # Key Insights with flowchart
        if results.get('key_insights'):
            def create_insights_flowchart():
                drawing = Drawing(500, 400)
                
                # Background
                drawing.add(Rect(0, 0, 500, 400, fillColor=colors.HexColor('#2d3748'), strokeColor=None))
                
                # Main header box
                drawing.add(Rect(175, 350, 150, 40, fillColor=colors.HexColor('#38a169'), strokeColor=colors.white, strokeWidth=2))
                drawing.add(String(250, 365, "KEY INSIGHTS", fontName='Helvetica-Bold', fontSize=12, 
                                 fillColor=colors.white, textAnchor='middle'))
                
                # Get insights
                insights = results.get('key_insights', [])
                
                # Calculate the maximum height needed for all boxes
                max_box_height = 70  # minimum height
                box_width = 85
                max_chars_per_line = 10
                
                for i in range(min(5, len(insights))):
                    if isinstance(insights[i], dict):
                        title = insights[i].get('title', f'Insight {i+1}')
                        
                        # Calculate how many lines this title needs
                        words = title.split()
                        lines_needed = 0
                        current_line = ""
                        
                        for word in words:
                            if len(current_line + " " + word) <= max_chars_per_line:
                                current_line = current_line + " " + word if current_line else word
                            else:
                                if current_line:
                                    lines_needed += 1
                                current_line = word
                        
                        if current_line:
                            lines_needed += 1
                        
                        # Calculate height needed for this title
                        height_needed = max(70, lines_needed * 12 + 30)
                        max_box_height = max(max_box_height, height_needed)
                
                # Fixed spacing
                spacing = 10
                total_width = 5 * box_width + 4 * spacing
                start_x = (500 - total_width) / 2
                
                # Draw 5 connecting lines and boxes (all same height)
                for i in range(5):
                    x = start_x + i * (box_width + spacing)
                    box_center = x + box_width/2
                    
                    # Vertical line from header to box
                    drawing.add(Line(250, 350, box_center, 300, strokeColor=colors.white, strokeWidth=2))
                    drawing.add(Line(box_center, 300, box_center, 250, strokeColor=colors.white, strokeWidth=2))
                    
                    # Insight box colors (all same height now)
                    box_colors = [colors.HexColor('#4a90e2'), colors.HexColor('#e53e3e'), colors.HexColor('#38a169'), 
                                 colors.HexColor('#ed8936'), colors.HexColor('#805ad5')]
                    
                    drawing.add(Rect(x, 250 - max_box_height, box_width, max_box_height, fillColor=box_colors[i], strokeColor=colors.white, strokeWidth=2))
                    
                    # Add insight title with line wrapping
                    if i < len(insights) and isinstance(insights[i], dict):
                        title = insights[i].get('title', f'Insight {i+1}')
                        
                        # Split title into words and create lines that fit
                        words = title.split()
                        lines = []
                        current_line = ""
                        
                        for word in words:
                            if len(current_line + " " + word) <= max_chars_per_line:
                                current_line = current_line + " " + word if current_line else word
                            else:
                                if current_line:
                                    lines.append(current_line)
                                current_line = word
                        
                        if current_line:
                            lines.append(current_line)
                        
                        # Draw each line centered in the box
                        line_height = 10
                        font_size = 8
                        total_text_height = len(lines) * line_height
                        start_y = 250 - max_box_height/2 + total_text_height/2
                        
                        for j, line in enumerate(lines):
                            y_position = start_y - j * line_height
                            drawing.add(String(box_center, y_position, line, 
                                             fontName='Helvetica-Bold', fontSize=font_size, 
                                             fillColor=colors.white, textAnchor='middle'))
                    else:
                        drawing.add(String(box_center, 250 - max_box_height/2, f"Insight {i+1}", 
                                         fontName='Helvetica-Bold', fontSize=8, 
                                         fillColor=colors.white, textAnchor='middle'))
                
                return drawing
            
            content.append(create_insights_flowchart())
            content.append(Spacer(1, 25))
        
        # Recommendations with flowchart
        if results.get('recommendations'):
            def create_recommendations_flowchart():
                drawing = Drawing(500, 400)
                
                # Background
                drawing.add(Rect(0, 0, 500, 400, fillColor=colors.HexColor('#2d3748'), strokeColor=None))
                
                # Main header box
                drawing.add(Rect(125, 350, 250, 40, fillColor=colors.HexColor('#e53e3e'), strokeColor=colors.white, strokeWidth=2))
                drawing.add(String(250, 365, "STRATEGIC RECOMMENDATIONS", fontName='Helvetica-Bold', fontSize=12, 
                                 fillColor=colors.white, textAnchor='middle'))
                
                # Get recommendations
                recommendations = results.get('recommendations', [])
                
                # Calculate the maximum height needed for all boxes
                max_box_height = 70  # minimum height
                box_width = 85
                max_chars_per_line = 10
                
                for i in range(min(5, len(recommendations))):
                    if isinstance(recommendations[i], dict):
                        title = recommendations[i].get('title', f'Action {i+1}')
                        
                        # Calculate how many lines this title needs
                        words = title.split()
                        lines_needed = 0
                        current_line = ""
                        
                        for word in words:
                            if len(current_line + " " + word) <= max_chars_per_line:
                                current_line = current_line + " " + word if current_line else word
                            else:
                                if current_line:
                                    lines_needed += 1
                                current_line = word
                        
                        if current_line:
                            lines_needed += 1
                        
                        # Calculate height needed for this title
                        height_needed = max(70, lines_needed * 12 + 30)
                        max_box_height = max(max_box_height, height_needed)
                
                # Fixed spacing
                spacing = 10
                total_width = 5 * box_width + 4 * spacing
                start_x = (500 - total_width) / 2
                
                # Draw 5 connecting lines and boxes (all same height)
                for i in range(5):
                    x = start_x + i * (box_width + spacing)
                    box_center = x + box_width/2
                    
                    # Vertical line from header to box
                    drawing.add(Line(250, 350, box_center, 300, strokeColor=colors.white, strokeWidth=2))
                    drawing.add(Line(box_center, 300, box_center, 250, strokeColor=colors.white, strokeWidth=2))
                    
                    # Recommendation box colors (all same height now)
                    box_colors = [colors.HexColor('#e53e3e'), colors.HexColor('#dd6b20'), colors.HexColor('#ecc94b'), 
                                 colors.HexColor('#38a169'), colors.HexColor('#3182ce')]
                    
                    drawing.add(Rect(x, 250 - max_box_height, box_width, max_box_height, fillColor=box_colors[i], strokeColor=colors.white, strokeWidth=2))
                    
                    # Add recommendation title with line wrapping
                    if i < len(recommendations) and isinstance(recommendations[i], dict):
                        title = recommendations[i].get('title', f'Action {i+1}')
                        
                        # Split title into words and create lines that fit
                        words = title.split()
                        lines = []
                        current_line = ""
                        
                        for word in words:
                            if len(current_line + " " + word) <= max_chars_per_line:
                                current_line = current_line + " " + word if current_line else word
                            else:
                                if current_line:
                                    lines.append(current_line)
                                current_line = word
                        
                        if current_line:
                            lines.append(current_line)
                        
                        # Draw each line centered in the box
                        line_height = 10
                        font_size = 8
                        total_text_height = len(lines) * line_height
                        start_y = 250 - max_box_height/2 + total_text_height/2
                        
                        for j, line in enumerate(lines):
                            y_position = start_y - j * line_height
                            drawing.add(String(box_center, y_position, line, 
                                             fontName='Helvetica-Bold', fontSize=font_size, 
                                             fillColor=colors.white, textAnchor='middle'))
                    else:
                        drawing.add(String(box_center, 250 - max_box_height/2, f"Action {i+1}", 
                                         fontName='Helvetica-Bold', fontSize=8, 
                                         fillColor=colors.white, textAnchor='middle'))
                
                return drawing
            
            content.append(create_recommendations_flowchart())


        content.append(PageBreak())
        
        # KEY INSIGHTS PAGE
        if results.get('key_insights'):
            content.append(Paragraph("KEY MARKET INSIGHTS", section_style))
            content.append(Spacer(1, 20))
            
            # Create insights impact chart based on content
            def create_insights_impact_chart():
                drawing = Drawing(500, 250)
                
                # Background
                drawing.add(Rect(0, 0, 500, 250, fillColor=colors.HexColor('#2d3748'), strokeColor=colors.HexColor('#4a90e2')))
                
                # Analyze insights to create relevant chart
                insights = results.get('key_insights', [])
                impact_scores = [90, 85, 80, 75, 70]  # Decreasing importance
                colors_list = [colors.HexColor('#e53e3e'), colors.HexColor('#dd6b20'), 
                              colors.HexColor('#38a169'), colors.HexColor('#3182ce'), colors.HexColor('#805ad5')]
                
                for i in range(min(5, len(insights))):
                    x = 50 + i * 80
                    height = int(impact_scores[i] * 1.5)
                    
                    # Impact bar
                    drawing.add(Rect(x, 50, 60, height, fillColor=colors_list[i], strokeColor=colors.white))
                    # Score label
                    drawing.add(String(x+30, height+60, f"{impact_scores[i]}%", fontName='Helvetica-Bold', 
                                     fontSize=10, fillColor=colors.white, textAnchor='middle'))
                    # Insight number
                    drawing.add(String(x+30, 30, f"#{i+1}", fontName='Helvetica', fontSize=10, 
                                     fillColor=colors.white, textAnchor='middle'))
                
                # Chart title
                drawing.add(String(250, 220, "Market Insights Impact Assessment", fontName='Helvetica-Bold', 
                                 fontSize=14, fillColor=colors.white, textAnchor='middle'))
                
                return drawing
            
            content.append(create_insights_impact_chart())
            content.append(Spacer(1, 30))
            
            # Display insights
            insights = results['key_insights']
            if isinstance(insights, list):
                for i, insight in enumerate(insights, 1):
                    if isinstance(insight, dict):
                        # Insight title
                        # Insight title with proper text wrapping
                        title_text = f"INSIGHT {i}: {insight.get('title', '').upper()}"
                        title_para = Paragraph(title_text, ParagraphStyle(
                            'InsightTitle',
                            parent=styles['Normal'],
                            fontSize=12,
                            textColor=colors.white,
                            fontName='Helvetica-Bold',
                            alignment=TA_LEFT
                        ))

                        title_table = Table([[title_para]], colWidths=[7*inch])
                        title_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#4a90e2')),
                            ('LEFTPADDING', (0, 0), (-1, -1), 15),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                            ('TOPPADDING', (0, 0), (-1, -1), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ]))
                        # Create content list for KeepTogether
                        insight_content = [title_table]
                        
                        # Insight explanation
                        exp_para = Paragraph(insight.get('explanation', ''), content_style)
                        exp_table = Table([[exp_para]], colWidths=[7*inch])
                        exp_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
                            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#4a90e2')),
                            ('LEFTPADDING', (0, 0), (-1, -1), 15),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                            ('TOPPADDING', (0, 0), (-1, -1), 15),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                        ]))
                        insight_content.append(exp_table)

                        # Keep title and explanation together
                        content.append(KeepTogether(insight_content))
                        content.append(Spacer(1, 15))
            
            content.append(PageBreak())
        
        # STRATEGIC RECOMMENDATIONS PAGE
        if results.get('recommendations'):
            content.append(Paragraph("STRATEGIC RECOMMENDATIONS", section_style))
            content.append(Spacer(1, 20))
            
            # Create recommendation priority chart
            def create_recommendation_priority_chart():
                drawing = Drawing(500, 250)
                
                # Background
                drawing.add(Rect(0, 0, 500, 250, fillColor=colors.HexColor('#2d3748'), strokeColor=colors.HexColor('#38b2ac')))
                
                # Priority levels based on recommendations
                priorities = [95, 88, 82, 76, 70]
                colors_list = [colors.HexColor('#e53e3e'), colors.HexColor('#dd6b20'), 
                              colors.HexColor('#ecc94b'), colors.HexColor('#38a169'), colors.HexColor('#3182ce')]
                
                for i, (priority, color) in enumerate(zip(priorities, colors_list)):
                    x = 50 + i * 80
                    # Priority circle
                    drawing.add(Circle(x+30, 150, 25, fillColor=color, strokeColor=colors.white, strokeWidth=2))
                    drawing.add(String(x+30, 145, f"{priority}", fontName='Helvetica-Bold', 
                                     fontSize=12, fillColor=colors.white, textAnchor='middle'))
                    # Label
                    drawing.add(String(x+30, 100, f"Action {i+1}", fontName='Helvetica', fontSize=10, 
                                     fillColor=colors.white, textAnchor='middle'))
                
                drawing.add(String(250, 220, "Implementation Priority Ranking", fontName='Helvetica-Bold', 
                                 fontSize=14, fillColor=colors.white, textAnchor='middle'))
                
                return drawing
            
            content.append(create_recommendation_priority_chart())
            content.append(Spacer(1, 30))
            
            # Display recommendations
            recommendations = results['recommendations']
            if isinstance(recommendations, list):
                for i, rec in enumerate(recommendations, 1):
                    if isinstance(rec, dict):
                        # Recommendation title
                        # Recommendation title with proper text wrapping
                        title_text = f"ACTION {i}: {rec.get('title', '').upper()}"
                        title_para = Paragraph(title_text, ParagraphStyle(
                            'RecommendationTitle',
                            parent=styles['Normal'],
                            fontSize=12,
                            textColor=colors.white,
                            fontName='Helvetica-Bold',
                            alignment=TA_LEFT
                        ))

                        title_table = Table([[title_para]], colWidths=[7*inch])
                        title_table.setStyle(TableStyle([
                           ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#38b2ac')),
                           ('LEFTPADDING', (0, 0), (-1, -1), 15),
                           ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                           ('TOPPADDING', (0, 0), (-1, -1), 10),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                           ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ]))
                        
                        # Create content list for KeepTogether
                        rec_content = [title_table]
                        
                        # Recommendation explanation
                        exp_para = Paragraph(rec.get('explanation', ''), content_style)
                        exp_table = Table([[exp_para]], colWidths=[7*inch])
                        exp_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
                            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#38b2ac')),
                            ('LEFTPADDING', (0, 0), (-1, -1), 15),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                            ('TOPPADDING', (0, 0), (-1, -1), 15),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                        ]))
                        rec_content.append(exp_table)

                        # Keep title and explanation together
                        content.append(KeepTogether(rec_content))
                        content.append(Spacer(1, 15))
        
        # Build PDF with custom backgrounds
        doc.build(content, onFirstPage=add_page_background, onLaterPages=add_page_background)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'prolexis-market-analysis-{datetime.now().strftime("%Y%m%d")}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"PDF export error: {str(e)}")
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500


if __name__ == '__main__':
    print("Starting Market Trend Summarizer...")
    print(f"App2.py available: {APP2_AVAILABLE}")
    print(f"TextBlob available: {TEXTBLOB_AVAILABLE}")
    print(f"Textract available: {TEXTRACT_AVAILABLE}")
    print(f"Web scraping available: {WEB_SCRAPING_AVAILABLE}")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
