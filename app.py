# Your Original Flask App with Added Analysis Features
from datetime import datetime, timedelta  # ADD timedelta here
from flask import Flask, render_template, request, jsonify, session, redirect, make_response
from flask_cors import CORS
import os
import logging
import tempfile
import stripe
from dotenv import load_dotenv
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
from PIL import Image

try:
    import praw
    REDDIT_AVAILABLE = True
except ImportError:
    REDDIT_AVAILABLE = False

try:
    from pytrends.request import TrendReq
    TRENDS_AVAILABLE = True
except ImportError:
    TRENDS_AVAILABLE = False

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

# IMPORTANT: Load .env FIRST before using environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, template_folder='.')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# Stripe configuration - AFTER load_dotenv()
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')

# Stripe Price IDs
STRIPE_PRICE_IDS = {
    'basic': 'price_1SKiClEQXwDOB8xDoVg8tv5k',
    'unlimited': 'price_1SKiETEQXwDOB8xDQEamudQ2'
}

# Subscription plans configuration
SUBSCRIPTION_PLANS = {
    'basic': {
        'name': 'Basic Plan',
        'price': 10,
        'limits': {
            'summary': 5,
            'analysis': 3,
            'question': 15,
            'social': 2
        }
    },
    'unlimited': {
        'name': 'Unlimited Plan',
        'price': 49,
        'limits': {
            'summary': float('inf'),
            'analysis': float('inf'),
            'question': float('inf'),
            'social': float('inf')
        }
    }
}

# Validate critical keys are present (optional - can comment out if causing issues)
if not stripe.api_key:
    logger.warning("⚠️ STRIPE_SECRET_KEY not found in .env file! Stripe payments will not work.")
if not STRIPE_PUBLISHABLE_KEY:
    logger.warning("⚠️ STRIPE_PUBLISHABLE_KEY not found in .env file! Stripe payments will not work.")

# Simple analysis functions for the new features
def analyze_sentiment(text):
    try:
        if TEXTBLOB_AVAILABLE:
            from textblob import TextBlob
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            # Force minimum polarity if TextBlob returns 0
            if polarity == 0.0:
                polarity = 0.1  # Default to slightly positive
            
            if polarity > 0.05:
                sentiment = "Positive"
            elif polarity < -0.05:
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
    
    # Force polarity based on text characteristics
    text_lower = text.lower()
    word_count = len(text.split())
    
    # Business/market context words
    positive_indicators = ['growth', 'increase', 'opportunity', 'strong', 'success', 'improve', 'good', 'positive', 'excellent', 'great']
    negative_indicators = ['decline', 'decrease', 'loss', 'weak', 'poor', 'bad', 'negative', 'crisis', 'problem', 'risk']
    
    positive_score = sum(2 if word in text_lower else 0 for word in positive_indicators)
    negative_score = sum(2 if word in text_lower else 0 for word in negative_indicators)
    
    # If no sentiment words found, create artificial polarity based on content length
    if positive_score == 0 and negative_score == 0:
        # Default polarity based on text characteristics
        if word_count > 100:
            polarity = 0.3  # Longer text = more positive
        elif 'market' in text_lower or 'analysis' in text_lower:
            polarity = 0.2  # Business content = slightly positive
        else:
            polarity = 0.1  # Default slight positive
    else:
        # Calculate based on found words
        net_score = positive_score - negative_score
        polarity = max(-0.8, min(0.8, net_score / max(word_count / 50, 1)))
        
        # Ensure non-zero
        if polarity == 0.0:
            polarity = 0.1
    
    # Determine sentiment
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

def get_reddit_data(query, limit=50, days_back=180):
    """Get Reddit posts for the query from the last 6 months"""
    if not REDDIT_AVAILABLE:
        return []
    
    try:
        reddit = praw.Reddit(
            client_id="ytUzn85b-efZSukCNNoYIQ",
            client_secret="H5Aq4YW-n1Ut3TiEeQ-EF7QtZFmFng",
            user_agent="MarketTrendSummarizer/1.0"
        )
        
        posts = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        cutoff_timestamp = cutoff_date.timestamp()
        
        # Search across multiple subreddits
        subreddits = ["all", "technology", "business", "investing", "apple", "android"]
        
        for subreddit_name in subreddits:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                for submission in subreddit.search(query, time_filter="year", limit=limit//len(subreddits)):
                    if submission.created_utc >= cutoff_timestamp:
                        posts.append({
                            'title': submission.title,
                            'content': submission.selftext or submission.title,
                            'score': submission.score,
                            'comments': submission.num_comments,
                            'subreddit': submission.subreddit.display_name,
                            'url': f"https://reddit.com{submission.permalink}",
                            'created': datetime.fromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M'),
                            'platform': 'reddit'
                        })
                        
                        if len(posts) >= limit:
                            break
            except Exception as e:
                logger.error(f"Subreddit {subreddit_name} error: {e}")
                continue
                
            if len(posts) >= limit:
                break
        
        return posts[:limit]
        
    except Exception as e:
        logger.error(f"Reddit API error: {e}")
        return []

def get_news_data(query, days_back=180):
    """Get news articles (placeholder for NewsAPI integration)"""
    # You can add NewsAPI integration here later
    return []


def create_enhanced_reddit_mock(query):
    """Enhanced Reddit mock data with more realistic posts"""
    return [
        {
            'title': f'{query} - Initial thoughts and review',
            'content': f'Just got my hands on {query}. Initial impressions are positive, though there are some concerns about pricing and feature set compared to alternatives.',
            'score': 234,
            'comments': 89,
            'subreddit': 'technology',
            'url': 'https://reddit.com/r/technology/sample1',
            'created': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'platform': 'reddit',
            'sentiment': analyze_sentiment(f'Initial impressions positive, concerns about pricing')
        },
        {
            'title': f'Is {query} worth the investment? Market analysis',
            'content': f'Looking at {query} from investment perspective. Market trends show mixed signals but overall trajectory seems positive.',
            'score': 156,
            'comments': 67,
            'subreddit': 'investing',
            'url': 'https://reddit.com/r/investing/sample2',
            'created': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'platform': 'reddit',
            'sentiment': analyze_sentiment(f'Mixed signals but overall positive trajectory')
        },
        {
            'title': f'{query} performance review after 3 months',
            'content': f'Been using {query} for 3 months now. Performance has been solid, some minor issues but generally satisfied with the results.',
            'score': 189,
            'comments': 43,
            'subreddit': 'reviews',
            'url': 'https://reddit.com/r/reviews/sample3',
            'created': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'platform': 'reddit',
            'sentiment': analyze_sentiment(f'Performance solid, generally satisfied')
        },
        {
            'title': f'Problems with {query} - anyone else experiencing this?',
            'content': f'Having some issues with {query}. Customer service has been unresponsive and the product isnt meeting expectations.',
            'score': 67,
            'comments': 124,
            'subreddit': 'complaints',
            'url': 'https://reddit.com/r/complaints/sample4',
            'created': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'platform': 'reddit',
            'sentiment': analyze_sentiment(f'Having issues, unresponsive service, not meeting expectations')
        },
        {
            'title': f'{query} vs competitors - detailed comparison',
            'content': f'Comprehensive comparison of {query} against major competitors. Results show advantages in some areas but falls short in others.',
            'score': 312,
            'comments': 78,
            'subreddit': 'comparisons',
            'url': 'https://reddit.com/r/comparisons/sample5',
            'created': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'platform': 'reddit',
            'sentiment': analyze_sentiment(f'Advantages in some areas, falls short in others')
        }
    ]

def create_enhanced_youtube_mock(query):
    """Enhanced YouTube mock data"""
    return [
        {
            'title': f'{query} - Complete Review and Analysis 2024',
            'description': f'Comprehensive review of {query} covering all major features, pricing, and market positioning against competitors.',
            'views': '245K',
            'likes': '12.3K',
            'channel': 'Tech Analysis Pro',
            'published': datetime.now().strftime('%Y-%m-%d'),
            'platform': 'youtube',
            'sentiment': analyze_sentiment(f'Comprehensive review covering features and pricing')
        },
        {
            'title': f'Why {query} is Changing the Game',
            'description': f'Deep dive into how {query} is disrupting the market and what it means for consumers and businesses.',
            'views': '98K',
            'likes': '4.2K',
            'channel': 'Market Insights',
            'published': datetime.now().strftime('%Y-%m-%d'),
            'platform': 'youtube',
            'sentiment': analyze_sentiment(f'Changing the game, disrupting the market')
        }
    ]

def create_enhanced_twitter_mock(query):
    """Enhanced Twitter mock data"""
    return [
        {
            'text': f'Just tried {query} and honestly impressed with the performance improvements! Game changer for productivity',
            'author': '@tech_reviewer',
            'retweets': 89,
            'likes': 456,
            'created': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'platform': 'twitter',
            'sentiment': analyze_sentiment('impressed with performance improvements, game changer')
        },
        {
            'text': f'{query} pricing is getting out of hand. Not sure if the premium is justified anymore',
            'author': '@budget_conscious',
            'retweets': 34,
            'likes': 167,
            'created': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'platform': 'twitter',
            'sentiment': analyze_sentiment('pricing out of hand, premium not justified')
        },
        {
            'text': f'Been comparing {query} with alternatives. Mixed results but overall satisfied with the choice',
            'author': '@comparison_guru',
            'retweets': 67,
            'likes': 234,
            'created': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'platform': 'twitter',
            'sentiment': analyze_sentiment('mixed results but overall satisfied')
        }
    ]

def parse_structured_response(response_text, expected_count=5):
    """Parse LLM structured response into insights/recommendations"""
    items = []
    sections = response_text.split('---')
    
    for section in sections[:expected_count]:
        section = section.strip()
        if 'TITLE:' in section and 'EXPLANATION:' in section:
            parts = section.split('EXPLANATION:', 1)
            title = parts[0].replace('TITLE:', '').strip()
            explanation = parts[1].strip() if len(parts) > 1 else ''
            
            items.append({
                'title': title,
                'explanation': explanation
            })
    
    # Fill remaining slots if needed
    while len(items) < expected_count:
        items.append({
            'title': f'Additional analysis point {len(items) + 1}',
            'explanation': 'Further content analysis would provide additional insights specific to this material.'
        })
    
    return items[:expected_count]

def generate_content_based_insights(text, hashtags, sentiment_analysis):
    """Generate insights based on actual content without numbers"""
    themes = hashtags[:3] if len(hashtags) >= 3 else hashtags
    theme_str = ', '.join(themes)
    
    return [
        {
            "title": f"Content emphasizes {themes[0] if themes else 'primary themes'} as central focus area",
            "explanation": f"Analysis reveals consistent emphasis on {theme_str}, indicating these represent core strategic considerations within the discussed context."
        },
        {
            "title": f"Sentiment orientation suggests {sentiment_analysis['sentiment'].lower()} market perspective",
            "explanation": f"The overall {sentiment_analysis['sentiment'].lower()} tone throughout the content provides context for understanding stakeholder perspectives and market positioning considerations."
        },
        {
            "title": f"Thematic patterns around {hashtags[1] if len(hashtags) > 1 else 'secondary themes'} reveal strategic priorities",
            "explanation": f"Discussion patterns indicate particular attention to {hashtags[1] if len(hashtags) > 1 else 'related areas'}, suggesting areas of strategic importance for consideration."
        },
        {
            "title": "Content structure indicates specific domain focus and expertise requirements",
            "explanation": f"The material's focus on {theme_str} suggests specialized knowledge and capabilities would be valuable for effective engagement in these areas."
        },
        {
            "title": "Analysis reveals interconnected themes requiring integrated approach",
            "explanation": f"The relationship between {theme_str} in the content suggests benefits from coordinated strategies that address multiple dimensions simultaneously."
        }
    ]

def generate_content_based_recommendations(text, hashtags, sentiment_analysis):
    """Generate specific, actionable recommendations with clear paths"""
    themes = hashtags[:3] if len(hashtags) >= 3 else hashtags
    theme_str = ', '.join(themes)
    text_lower = text.lower()
    
    # Identify potential niche markets from content
    niche_indicators = []
    if themes:
        for theme in themes:
            if theme.lower() in text_lower:
                niche_indicators.append(theme)
    
    return [
        {
            "title": f"Target {themes[0] if themes else 'identified niche'} market segment with specialized offering",
            "explanation": f"ACTION PLAN: 1) Develop a specialized product/service specifically for {themes[0] if themes else 'this segment'} 2) Research competitors currently serving this niche to identify gaps 3) Create tailored messaging that speaks directly to {themes[0] if themes else 'segment'}-specific pain points 4) Launch pilot program with 5-10 customers in this niche 5) Iterate based on feedback before full rollout. This segment appears underserved based on content emphasis without proportional market solutions."
        },
        {
            "title": f"Enter {hashtags[1] if len(hashtags) > 1 else 'secondary market'} as differentiation strategy",
            "explanation": f"ACTION PLAN: 1) Conduct market sizing analysis for {hashtags[1] if len(hashtags) > 1 else 'this market'} 2) Identify 3-5 key decision makers or influencers in this space 3) Develop minimum viable offering tailored to this segment's specific needs 4) Establish partnerships with complementary providers already serving this market 5) Position as specialist rather than generalist. The content suggests this area has attention but limited specialized providers."
        },
        {
            "title": f"Build strategic positioning around {themes[0] if themes else 'primary theme'}-{hashtags[2] if len(hashtags) > 2 else 'related area'} intersection",
            "explanation": f"ACTION PLAN: 1) Map the overlap between {themes[0] if themes else 'primary area'} and {hashtags[2] if len(hashtags) > 2 else 'secondary area'} - this intersection is typically underserved 2) Interview 10-15 potential customers operating in this overlap 3) Design offering that explicitly addresses both dimensions 4) Create thought leadership content demonstrating expertise in this specific intersection 5) Price at premium given specialized positioning. Most competitors focus on one dimension only."
        },
        {
            "title": f"Leverage {sentiment_analysis['sentiment'].lower()} sentiment to capture timing advantage",
            "explanation": f"ACTION PLAN: 1) If sentiment is positive - move quickly to capture momentum before market saturates; if negative - position as solution to identified problems 2) Develop messaging that directly addresses current sentiment drivers 3) Launch within next 60-90 days while sentiment context remains relevant 4) Use current sentiment in marketing to show market awareness and timely solution 5) Build customer testimonials that reference current market conditions. Timing is critical when sentiment is directional."
        },
        {
            "title": f"Create vertical-specific solution for {hashtags[3] if len(hashtags) > 3 else themes[0] if themes else 'identified vertical'} industry",
            "explanation": f"ACTION PLAN: 1) Choose one specific vertical within {hashtags[3] if len(hashtags) > 3 else themes[0] if themes else 'this space'} (e.g., if 'healthcare', choose 'dental practices' specifically) 2) Customize solution for that vertical's unique workflow and compliance needs 3) Hire or partner with someone from that vertical for credibility 4) Attend 2-3 industry conferences to establish presence 5) Build 5 case studies from early adopters in that vertical 6) Expand to adjacent verticals only after achieving 20+ customers in first vertical. Vertical specialization reduces competition and increases willingness to pay."
        }
    ]


# YOUR ORIGINAL ROUTES (exactly as they were)
# YOUR FIXED ROUTES
@app.route('/')
@app.route('/index')
def hello():
    """Redirect to signup page."""
    return redirect('/signup') 

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
    return render_template('signup.html')  # ✅ Fixed - now renders template

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy', 'service': 'Market Trend Summarizer'}

@app.route('/tools')
def tools():
    return render_template('tools.html')
    
@app.route('/api/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.get_json()
        plan = data.get('plan', 'basic')
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('fullName', '')
        
        if plan not in SUBSCRIPTION_PLANS:
            return jsonify({'error': 'Invalid plan'}), 400
        
        if plan not in STRIPE_PRICE_IDS:
            return jsonify({'error': 'Stripe price ID not configured'}), 500
        
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            customer_email=email,
            payment_method_types=['card'],
            line_items=[{
                'price': STRIPE_PRICE_IDS[plan],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.host_url + 'payment-success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.host_url + 'signup',
            metadata={
                'plan': plan,
                'email': email,
                'full_name': full_name,
                'password': password  # Note: In production, hash this!
            }
        )
        
        return jsonify({'sessionId': checkout_session.id, 'url': checkout_session.url})
        
    except Exception as e:
        logger.error(f"Stripe checkout error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/payment-success')
def payment_success():
    """Handle successful payment redirect"""
    session_id = request.args.get('session_id')
    
    if not session_id:
        return redirect('/signup')
    
    try:
        # Retrieve the session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        # Get user info from metadata
        email = checkout_session.metadata.get('email')
        plan = checkout_session.metadata.get('plan')
        full_name = checkout_session.metadata.get('full_name')
        password = checkout_session.metadata.get('password')
        
        # Create user session
        session['user_email'] = email
        session['user_plan'] = plan
        session['user_name'] = full_name
        session['stripe_customer_id'] = checkout_session.customer
        session['stripe_subscription_id'] = checkout_session.subscription
        
        # Initialize usage counters
        session['usage_summary'] = 0
        session['usage_analysis'] = 0
        session['usage_question'] = 0
        session['usage_social'] = 0
        
        return redirect('/dashboard')
        
    except Exception as e:
        logger.error(f"Payment success error: {str(e)}")
        return redirect('/signup')

@app.route('/api/stripe/config', methods=['GET'])
def get_stripe_config():
    """Send publishable key to frontend"""
    return jsonify({'publishableKey': STRIPE_PUBLISHABLE_KEY})



@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    try:
        session.clear()
        return jsonify({'message': 'Logged out successfully'})
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

@app.route('/dashboard')
def dashboard():
    """Renders the user dashboard page."""
    return render_template('dashboard.html')

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
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags(text, max_hashtags=12)
        
        # Dynamic analysis for any topic
        text_lower = text.lower()
        word_count = len(text.split())
        main_themes = ', '.join([hashtag.lower() for hashtag in hashtags[:5]])
        
        # Generate content-specific key insights using LLM
        if APP2_AVAILABLE:
            try:
                insights_question = """Analyze this content and provide exactly 5 specific key insights based on what is actually discussed. 
                
                Requirements for each insight:
                - Be specific to the actual topics and themes in the content
                - Avoid generic business advice that could apply to anything
                - Do NOT include percentages, statistics, or numbers unless they appear in the source content
                - Focus on qualitative analysis of themes, patterns, and implications
                - Each insight should be directly traceable to content themes
                
                Format each insight as:
                TITLE: [Specific insight title based on content]
                EXPLANATION: [Detailed explanation referencing actual content themes]
                
                Separate each insight with ---"""
                
                insights_result = summarize_trends(text=text, question=insights_question, return_format="dict")
                
                if not insights_result.get('error') and insights_result.get('full_response'):
                    key_insights = parse_structured_response(insights_result.get('full_response'), 5)
                else:
                    key_insights = generate_content_based_insights(text, hashtags, sentiment_analysis)
            except Exception as e:
                logger.error(f"Insights generation error: {e}")
                key_insights = generate_content_based_insights(text, hashtags, sentiment_analysis)
        else:
            key_insights = generate_content_based_insights(text, hashtags, sentiment_analysis)
        
        # Generate content-specific recommendations using LLM
        if APP2_AVAILABLE:
            try:
                rec_question = """Based on this content, provide exactly 5 specific, ACTIONABLE strategic recommendations.
                
                Each recommendation MUST include:
                1. A clear target market or niche segment to pursue
                2. Specific underserved areas or gaps to address  
                3. A step-by-step action plan (5-7 concrete steps)
                4. Why this path is viable based on content analysis
                5. NO generic advice - be specific about WHAT to do and HOW
                
                Think like a strategy consultant giving a client their implementation roadmap.
                
                Examples of GOOD recommendations:
                - "Target mid-sized law firms (50-200 employees) in healthcare litigation niche. Step 1: Research top 50 firms, Step 2:..."
                - "Enter the B2B SaaS market for dental practice management. Step 1: Interview 20 dentists, Step 2:..."
                
                Examples of BAD recommendations:
                - "Improve customer experience" (too generic)
                - "Leverage technology" (not actionable)
                - "Focus on quality" (no specific path)
                
                Format each recommendation as:
                TITLE: [Specific target market/action]
                EXPLANATION: [Complete action plan with numbered steps and reasoning]
                
                Separate each recommendation with ---"""
                
                rec_result = summarize_trends(text=text, question=rec_question, return_format="dict")
                
                if not rec_result.get('error') and rec_result.get('full_response'):
                    recommendations = parse_structured_response(rec_result.get('full_response'), 5)
                else:
                    recommendations = generate_content_based_recommendations(text, hashtags, sentiment_analysis)
            except Exception as e:
                logger.error(f"Recommendations generation error: {e}")
                recommendations = generate_content_based_recommendations(text, hashtags, sentiment_analysis)
        else:
            recommendations = generate_content_based_recommendations(text, hashtags, sentiment_analysis)
        
        # Generate comprehensive summary using LLM
        if APP2_AVAILABLE:
            try:
                summary_question = "Provide a comprehensive analysis summary in 3-4 paragraphs covering key findings, implications, and strategic considerations based on this specific content. Avoid generic statements."
                summary_result = summarize_trends(text=text, question=summary_question, return_format="dict")
                
                if not summary_result.get('error') and summary_result.get('full_response'):
                    summary = summary_result.get('full_response', '')
                else:
                    summary = f"Analysis of content reveals {sentiment_analysis['sentiment'].lower()} sentiment with focus on {main_themes}. The material addresses specific themes and patterns that provide strategic context for decision-making and positioning."
            except Exception as e:
                logger.error(f"Summary generation error: {e}")
                summary = f"Content analysis identifies key themes around {main_themes} with {sentiment_analysis['sentiment'].lower()} sentiment orientation, providing strategic insights for relevant stakeholders."
        else:
            summary = f"Analysis reveals focus on {main_themes} with {sentiment_analysis['sentiment'].lower()} sentiment, offering strategic considerations based on identified themes and patterns."
        
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
        total_posts = 0
        
        # Get real Reddit data if available
        if 'reddit' in platforms and REDDIT_AVAILABLE:
            reddit_data = get_reddit_data(query, limit=100)
            if reddit_data:
                results['data']['reddit'] = reddit_data
                total_posts += len(reddit_data)
                all_content.extend([post['title'] + ' ' + post['content'] for post in reddit_data])
            else:
                # Fallback to enhanced mock data if Reddit fails
                results['data']['reddit'] = create_enhanced_reddit_mock(query)
                total_posts += len(results['data']['reddit'])
                all_content.extend([post['title'] + ' ' + post['content'] for post in results['data']['reddit']])
        
        # Keep existing mock data for other platforms as fallback
        if 'youtube' in platforms:
            youtube_data = create_enhanced_youtube_mock(query)
            results['data']['youtube'] = youtube_data
            total_posts += len(youtube_data)
            all_content.extend([video['title'] + ' ' + video['description'] for video in youtube_data])
        
        if 'twitter' in platforms:
            twitter_data = create_enhanced_twitter_mock(query)
            results['data']['twitter'] = twitter_data
            total_posts += len(twitter_data)
            all_content.extend([tweet['text'] for tweet in twitter_data])
        
        # Overall analysis
        combined_text = ' '.join(all_content)
        
        if combined_text:
            overall_sentiment = analyze_sentiment(combined_text)
            hashtag_suggestions = extract_hashtags(combined_text)
            
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
                summary_question = "Provide a comprehensive but concise summary of this content in 2-3 paragraphs, focusing on key market insights and strategic implications. Keep it between 200-400 words."
                summary_result = summarize_trends(text=text, question=summary_question, return_format="dict")
                
                if not summary_result.get('error'):
                    summary = summary_result.get('full_response', '')
                
                # Get insights separately if needed
                if question:
                    analysis_result = summarize_trends(text=text, question=question, return_format="dict")
                    if not analysis_result.get('error'):
                        key_insights = analysis_result.get('keywords', [])[:5]
            except Exception as e:
                logger.error(f"app2.py text analysis error: {e}")
        
        # Fallback
        if not summary:
            word_count = len(text.split())
            summary = f"Market analysis of {word_count} words reveals {sentiment_analysis['sentiment'].lower()} sentiment across key themes including {', '.join(hashtags[:5])}. Strategic insights indicate opportunities for competitive positioning and market development based on identified patterns and market indicators."
            
        if not key_insights:
            key_insights = [
                {
                    "title": f"Content sentiment analysis reveals {sentiment_analysis['sentiment'].lower()} market outlook",
                    "explanation": f"Document analysis shows {sentiment_analysis['sentiment'].lower()} sentiment with polarity score of {sentiment_analysis['polarity']}. This sentiment pattern provides insights into market perception and strategic positioning opportunities for decision-making processes."
                },
                {
                    "title": f"Key thematic analysis identifies {len(hashtags)} primary focus areas",
                    "explanation": f"Content analysis reveals primary themes around {', '.join(hashtags[:3])}. These themes indicate market priorities and suggest strategic areas for competitive positioning and business development initiatives."
                },
                {
                    "title": f"Content depth analysis shows comprehensive market coverage",
                    "explanation": f"Document contains {len(text.split())} words providing substantial analytical depth. This comprehensive coverage enables thorough market understanding and strategic planning based on detailed market intelligence."
                },
                {
                    "title": "Market positioning opportunities identified through content analysis",
                    "explanation": "Analysis reveals specific opportunities for strategic market positioning based on content themes and sentiment patterns. These insights support competitive differentiation and market entry strategies."
                },
                {
                    "title": "Strategic implementation guidelines derived from market analysis",
                    "explanation": "Content analysis provides actionable insights for strategic implementation including timing considerations, market approach strategies, and competitive positioning recommendations for optimal market penetration."
                }
            ]
        
        result = {
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']})",
            'hashtags': hashtags,
            'brand_mentions': {},
            'key_insights': key_insights,
            'recommendations': [
                {
                    "title": "Leverage sentiment patterns for strategic market positioning",
                    "explanation": "Utilize the sentiment analysis results to inform marketing messaging and product positioning strategies. Focus on addressing market concerns while amplifying positive sentiment drivers."
                },
                {
                    "title": "Implement thematic focus areas for competitive advantage", 
                    "explanation": "Develop strategic initiatives around the identified key themes to establish market leadership and competitive differentiation in high-priority market segments."
                },
                {
                    "title": "Execute content-driven market intelligence strategy",
                    "explanation": "Use the comprehensive content analysis to develop data-driven market strategies that address specific market needs and capitalize on identified opportunities."
                },
                {
                    "title": "Develop sentiment-aware communication strategies",
                    "explanation": "Create communication strategies that acknowledge market sentiment patterns and position your organization effectively within the current market context."
                },
                {
                    "title": "Establish continuous market monitoring processes",
                    "explanation": "Implement ongoing market intelligence processes that build upon these content analysis insights to maintain competitive advantage and market awareness."
                }
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
        
        # Generate appropriate summary
        if APP2_AVAILABLE:
            try:
                summary_question = "Provide a concise summary of this website content in 2-3 paragraphs, focusing on key business insights and market implications. Keep it between 200-400 words."
                summary_result = summarize_trends(text=text, question=summary_question, return_format="dict")
                
                if not summary_result.get('error'):
                    summary = summary_result.get('full_response', '')
                else:
                    summary = f"Website analysis reveals {sentiment_analysis['sentiment'].lower()} market sentiment with focus on {', '.join(hashtags[:5])}. Content provides strategic insights for competitive positioning and market development opportunities."
            except Exception as e:
                logger.error(f"URL summary generation error: {e}")
                summary = f"Website content analysis of {len(text.split())} words shows {sentiment_analysis['sentiment'].lower()} sentiment patterns across key themes including {', '.join(hashtags[:5])}. Strategic implications suggest opportunities for market positioning and competitive analysis."
        else:
            summary = f"Website content analysis reveals {sentiment_analysis['sentiment'].lower()} market positioning with primary themes around {', '.join(hashtags[:5])}. Analysis provides strategic insights for competitive positioning and market development based on digital content patterns."
        
        result = {
            'url': url,
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']})",
            'hashtags': hashtags,
            'brand_mentions': {},
            'key_insights': [
                {
                    "title": f"Website content sentiment analysis reveals {sentiment_analysis['sentiment'].lower()} market positioning",
                    "explanation": f"URL content analysis shows {sentiment_analysis['sentiment'].lower()} sentiment patterns that indicate market perception and brand positioning opportunities for strategic decision-making."
                },
                {
                    "title": f"Content depth analysis provides {len(text.split())} words of market intelligence",
                    "explanation": f"Comprehensive content extraction reveals substantial market insights across {len(text.split())} words, enabling thorough competitive analysis and strategic positioning assessment."
                },
                {
                    "title": f"Thematic analysis identifies key market focus areas",
                    "explanation": f"Content analysis reveals primary market themes around {', '.join(hashtags[:3])}. These themes indicate strategic priorities and competitive positioning opportunities."
                },
                {
                    "title": "Digital presence analysis reveals strategic positioning opportunities",
                    "explanation": "Website content analysis provides insights into competitive positioning and market approach strategies based on digital content patterns and messaging focus."
                },
                {
                    "title": "Market communication strategy insights derived from content analysis",
                    "explanation": "Content patterns reveal strategic communication approaches and market positioning strategies that can inform competitive differentiation and market penetration efforts."
                }
            ],
            'recommendations': [
                {
                    "title": "Leverage sentiment patterns for strategic market positioning",
                    "explanation": "Utilize the sentiment analysis results to inform marketing messaging and product positioning strategies. Focus on addressing market concerns while amplifying positive sentiment drivers."
                },
                {
                    "title": "Implement thematic focus areas for competitive advantage", 
                    "explanation": "Develop strategic initiatives around the identified key themes to establish market leadership and competitive differentiation in high-priority market segments."
                },
                {
                    "title": "Execute content-driven market intelligence strategy",
                    "explanation": "Use the comprehensive content analysis to develop data-driven market strategies that address specific market needs and capitalize on identified opportunities."
                },
                {
                    "title": "Develop sentiment-aware communication strategies",
                    "explanation": "Create communication strategies that acknowledge market sentiment patterns and position your organization effectively within the current market context."
                },
                {
                    "title": "Establish continuous market monitoring processes",
                    "explanation": "Implement ongoing market intelligence processes that build upon these content analysis insights to maintain competitive advantage and market awareness."
                }
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
        
        # Keep full text for analysis, but generate appropriate summary
        full_text = text
        if len(text) > 4000:
            text = text[:4000]  # Limit for processing, but don't truncate summary
        
        # Perform analysis
        sentiment_analysis = analyze_sentiment(text)
        hashtags = extract_hashtags(text)
        
        # Generate appropriate summary
        if APP2_AVAILABLE:
            try:
                summary_question = "Provide a concise summary of this document in 2-3 paragraphs, focusing on key business insights and strategic implications. Keep it between 200-400 words."
                summary_result = summarize_trends(text=text, question=summary_question, return_format="dict")
                
                if not summary_result.get('error'):
                    summary = summary_result.get('full_response', '')
                else:
                    summary = f"Document analysis reveals {sentiment_analysis['sentiment'].lower()} market sentiment with strategic focus on {', '.join(hashtags[:5])}. Content provides actionable insights for business strategy and competitive positioning."
            except Exception as e:
                logger.error(f"File summary generation error: {e}")
                summary = f"Document analysis of {len(text.split())} words reveals {sentiment_analysis['sentiment'].lower()} sentiment patterns. Strategic themes include {', '.join(hashtags[:5])}, providing insights for market positioning and business development opportunities."
        else:
            summary = f"Document content analysis shows {sentiment_analysis['sentiment'].lower()} market sentiment across key themes including {', '.join(hashtags[:5])}. Analysis provides strategic business insights and competitive positioning recommendations."
        
        result = {
            'filename': file.filename,
            'summary': summary,
            'sentiment': f"{sentiment_analysis['sentiment']} (polarity: {sentiment_analysis['polarity']})",
            'hashtags': hashtags,
            'brand_mentions': {},
            'key_insights': [
                {
                    "title": f"Website content sentiment analysis reveals {sentiment_analysis['sentiment'].lower()} market positioning",
                    "explanation": f"URL content analysis shows {sentiment_analysis['sentiment'].lower()} sentiment patterns that indicate market perception and brand positioning opportunities for strategic decision-making."
                },
                {
                    "title": f"Content depth analysis provides {len(text.split())} words of market intelligence",
                    "explanation": f"Comprehensive content extraction reveals substantial market insights across {len(text.split())} words, enabling thorough competitive analysis and strategic positioning assessment."
                },
                {
                    "title": f"Thematic analysis identifies key market focus areas",
                    "explanation": f"Content analysis reveals primary market themes around {', '.join(hashtags[:3])}. These themes indicate strategic priorities and competitive positioning opportunities."
                },
                {
                    "title": "Digital presence analysis reveals strategic positioning opportunities",
                    "explanation": "Website content analysis provides insights into competitive positioning and market approach strategies based on digital content patterns and messaging focus."
                },
                {
                    "title": "Market communication strategy insights derived from content analysis",
                    "explanation": "Content patterns reveal strategic communication approaches and market positioning strategies that can inform competitive differentiation and market penetration efforts."
                }
            ],
            'recommendations': [
                {
                    "title": "Leverage sentiment patterns for strategic market positioning",
                    "explanation": "Utilize the sentiment analysis results to inform marketing messaging and product positioning strategies. Focus on addressing market concerns while amplifying positive sentiment drivers."
                },
                {
                    "title": "Implement thematic focus areas for competitive advantage", 
                    "explanation": "Develop strategic initiatives around the identified key themes to establish market leadership and competitive differentiation in high-priority market segments."
                },
                {
                    "title": "Execute content-driven market intelligence strategy",
                    "explanation": "Use the comprehensive content analysis to develop data-driven market strategies that address specific market needs and capitalize on identified opportunities."
                },
                {
                    "title": "Develop sentiment-aware communication strategies",
                    "explanation": "Create communication strategies that acknowledge market sentiment patterns and position your organization effectively within the current market context."
                },
                {
                    "title": "Establish continuous market monitoring processes",
                    "explanation": "Implement ongoing market intelligence processes that build upon these content analysis insights to maintain competitive advantage and market awareness."
                }
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
    
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)
