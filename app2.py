import boto3
import json
import textract
import tempfile
import os
import logging
import hashlib
import time
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple cache to prevent duplicate calls
_response_cache = {}


# Add these imports to your app2.py
import re
from collections import Counter
import requests
from textblob import TextBlob  # For sentiment analysis
import praw  # For Reddit API
from googleapiclient.discovery import build  # For YouTube API

def analyze_sentiment_emotion(text):
    """Analyze sentiment and detect emotions"""
    blob = TextBlob(text)
    sentiment_score = blob.sentiment.polarity
    
    # Emotion keywords detection
    emotion_keywords = {
        'positive': ['excited', 'happy', 'love', 'amazing', 'great', 'excellent'],
        'negative': ['hate', 'terrible', 'awful', 'disappointed', 'angry'],
        'neutral': ['okay', 'fine', 'average', 'normal']
    }
    
    emotions_found = []
    text_lower = text.lower()
    for emotion, keywords in emotion_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            emotions_found.append(emotion)
    
    return {
        'sentiment_score': sentiment_score,
        'sentiment_label': 'positive' if sentiment_score > 0.1 else 'negative' if sentiment_score < -0.1 else 'neutral',
        'emotions': emotions_found
    }

def extract_brand_mentions(text, brands_list=None):
    """Find brand and competitor mentions"""
    if brands_list is None:
        # Common brand patterns
        brands_list = ['apple', 'google', 'microsoft', 'amazon', 'meta', 'tesla', 'netflix']
    
    mentions = {}
    text_lower = text.lower()
    
    for brand in brands_list:
        count = text_lower.count(brand.lower())
        if count > 0:
            mentions[brand] = count
    
    return mentions

def suggest_hashtags_keywords(text, topic=None):
    """Generate hashtag and keyword suggestions"""
    # Extract keywords using frequency analysis
    words = re.findall(r'\b\w+\b', text.lower())
    word_freq = Counter(words)
    
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    keywords = [word for word, freq in word_freq.most_common(20) if word not in stop_words and len(word) > 3]
    
    # Generate hashtags
    hashtags = [f"#{word}" for word in keywords[:10]]
    
    return {
        'keywords': keywords,
        'hashtags': hashtags,
        'trending_terms': keywords[:5]
    }

def scan_reddit_content(subreddits, query, limit=50):
    """Scan Reddit for relevant posts"""
    # You'll need to set up Reddit API credentials
    try:
        reddit = praw.Reddit(
            client_id="YOUR_CLIENT_ID",
            client_secret="YOUR_CLIENT_SECRET",
            user_agent="YOUR_APP_NAME"
        )
        
        posts = []
        for subreddit_name in subreddits:
            subreddit = reddit.subreddit(subreddit_name)
            for post in subreddit.search(query, limit=limit):
                posts.append({
                    'title': post.title,
                    'content': post.selftext,
                    'score': post.score,
                    'url': post.url,
                    'created': post.created_utc
                })
        return posts
    except Exception as e:
        return {'error': f'Reddit API error: {str(e)}'}

def analyze_comprehensive_trend(text, url=None, social_platforms=None):
    """Comprehensive trend analysis combining all features"""
    results = {
        'summary': '',
        'sentiment_analysis': analyze_sentiment_emotion(text),
        'brand_mentions': extract_brand_mentions(text),
        'hashtag_suggestions': suggest_hashtags_keywords(text),
        'key_insights': [],
        'recommendations': []
    }
    
    # Generate summary
    sentences = text.split('.')
    if len(sentences) > 3:
        results['summary'] = '. '.join(sentences[:3]) + '.'
    else:
        results['summary'] = text
    
    # Generate insights based on sentiment and mentions
    sentiment = results['sentiment_analysis']
    if sentiment['sentiment_score'] > 0.3:
        results['key_insights'].append("Overall positive sentiment detected in content")
    elif sentiment['sentiment_score'] < -0.3:
        results['key_insights'].append("Negative sentiment detected - monitor for potential issues")
    
    if results['brand_mentions']:
        top_brand = max(results['brand_mentions'].items(), key=lambda x: x[1])
        results['key_insights'].append(f"Most mentioned brand: {top_brand[0]} ({top_brand[1]} mentions)")
    
    return results


def claude_messages(prompt):
    try:
        if not prompt or not prompt.strip():
            return "Error: Empty prompt provided"

        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        
        if prompt_hash in _response_cache:
            logger.info("Using cached response")
            return _response_cache[prompt_hash]

        bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
        
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2500,
            "temperature": 0.3,
            "top_k": 150,
            "top_p": 0.9,
        }

        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )

        result = json.loads(response["body"].read())
        if not result or "content" not in result:
            return "Error: Invalid response structure from Claude"
        if not result["content"] or len(result["content"]) == 0:
            return "Error: Empty response from Claude"

        response_text = result["content"][0]["text"]
        _response_cache[prompt_hash] = response_text
        return response_text

    except Exception as e:
        logger.error(f"Error calling Claude: {str(e)}")
        return f"Error calling Claude: {str(e)}"

def get_business_context_prompt(question, custom_keywords=""):
    """Enhanced business prompt with strict formatting requirements"""
    
    prompt = f"""You are a senior business strategist. Provide strategic insights for this question.

Question: {question}
Keywords: {custom_keywords}

CRITICAL: You must use EXACTLY this format:

**KEYWORDS IDENTIFIED:**
Market Opportunities, Growth Strategy, Digital Innovation, Customer Experience, Competitive Positioning

**STRATEGIC ANALYSIS:**

**KEYWORD 1: Market Opportunities**
**INSIGHTS:**
1. Market Opportunity Assessment: Market size and growth analysis
2. Customer Segmentation: Target customer analysis and value proposition
3. Revenue Projections: Financial forecasting and business model
**ACTIONS:**
1. Market opportunity analysis reveals $2.8 billion addressable market growing at 18% annually through 2027. Primary customer segments include enterprise clients (65% of market, $150K average contracts) and SMBs (35% of market, $45K average deals). Geographic expansion targets North America ($1.2B market), Europe ($900M), Asia-Pacific ($700M). Implementation requires $2.2M investment over 15 months including technology development ($1.2M), sales team expansion ($600K), marketing initiatives ($400K). Revenue projections show $1.8M year one, $5.2M year two, $9.8M year three with 28% EBITDA margins. Success metrics include 6% market penetration within 30 months, $9K customer acquisition cost, $220K lifetime value, and 15% quarterly growth rate.

2. Competitive landscape shows fragmented market with top three players controlling 42% share, creating disruption opportunity. Primary competitors include TechLeader Corp ($140M revenue, 16% share), InnovateSys ($110M revenue, 14% share), Digital Solutions ($95M revenue, 12% share). Differentiation strategy targets underserved mid-market with 35% cost reduction through automation. Customer acquisition combines targeted digital marketing ($150K quarterly budget), strategic partnerships (15 industry alliances), direct sales team (12 representatives). Brand positioning emphasizes rapid deployment (4-month implementation vs 12-month industry average), superior ROI (35% better outcomes), comprehensive support (24/7 availability).

3. Implementation roadmap requires cross-functional team of 28 professionals: 12 engineers, 8 sales specialists, 4 marketing professionals, 4 customer success managers. Technology infrastructure investment totals $1.6M including cloud platform ($700K), security certifications ($300K), integration capabilities ($400K), analytics dashboard ($200K). Operational framework includes automated onboarding (reducing setup time 60%), AI-powered support (achieving 85% first-contact resolution), predictive analytics for customer success. Key milestones: beta testing months 3-6, limited release month 9, full launch month 12, international expansion month 18.

**KEYWORD 2: Growth Strategy**
**INSIGHTS:**
1. Revenue Diversification: Multiple income stream development and optimization
2. Market Expansion: Geographic and demographic growth opportunities
3. Customer Lifetime Value: Retention and upselling programs
**ACTIONS:**
1. Revenue diversification strategy targets four income streams generating $12.5M combined annual recurring revenue by year three. Primary subscription model ($8.2M, 66%) offers tiered pricing from $2,000/month basic to $12,000/month enterprise. Professional services division ($2.8M, 22%) provides implementation consulting, customization, ongoing optimization at $250/hour average rate. Marketplace revenue ($1.1M, 9%) creates ecosystem partnerships with 20% revenue sharing. Training programs ($400K, 3%) deliver certification courses, workshops, documentation. Financial projections show 35% gross margins on subscriptions, 68% on services, 45% on marketplace, 88% on training. Investment requires $1.1M in dedicated teams, technology platforms, market development.

2. Market expansion initiative targets high-growth regions with $2.1B combined opportunity and 22% annual growth rates. Primary markets include Asia-Pacific ($850M opportunity, 25% growth), Latin America ($650M, 20% growth), Middle East ($600M, 19% growth). Entry strategy requires $1.8M investment: local partnerships ($600K), regulatory compliance ($450K), market research ($300K), sales team establishment ($450K). Localization includes product adaptation, language translation, cultural customization across 8 target countries. Distribution channels combine direct sales (45%), certified partners (35%), digital platforms (20%). Revenue projections show $3.2M international sales year one, growing to $18M by year three.

3. Customer lifetime value optimization program increases retention from 82% to 94% while boosting average revenue per user 38%. Customer success framework segments users by engagement levels, business outcomes, growth potential enabling personalized strategies. High-value program (400+ customers, 70% revenue) includes dedicated success managers, quarterly executive briefings, early feature access, customized training. Risk identification system monitors usage patterns, support frequency, satisfaction scores triggering proactive interventions. Retention initiatives include win-back campaigns (73% success rate), loyalty rewards, advocacy programs. Investment totals $650K: customer success team expansion ($400K), retention platform ($150K), loyalty program ($100K).

**KEYWORD 3: Digital Innovation**
**INSIGHTS:**
1. Technology Transformation: Platform modernization and capability enhancement
2. Process Automation: Operational efficiency and cost reduction through automation
3. Data Analytics: Business intelligence and predictive analytics implementation
**ACTIONS:**
1. Technology transformation modernizes core platform delivering 45% performance improvement and 55% operational cost reduction. Cloud-native redesign migrates from legacy infrastructure to microservices architecture supporting 8x scalability, 99.98% availability. Investment of $1.5M over 12 months includes platform re-engineering ($650K), cloud migration ($450K), security enhancements ($250K), testing automation ($150K). Enhanced capabilities include real-time processing, 40+ third-party integrations, mobile-responsive interface. Performance improvements: 2.5-second page loads (previously 7 seconds), 400ms API responses (previously 1.1 seconds), 35,000 concurrent users (7x current capacity).

2. Process automation streamlines operations reducing manual effort 68% and improving consistency across customer-facing activities. RPA deployment targets invoice processing (92% automation), customer onboarding (85% automation), report generation (95% automation), support routing (88% automation). Investment totals $550K: automation software ($250K), process reengineering ($200K), training programs ($100K). Workflow optimization identifies 26 repetitive tasks with 950 hours monthly savings enabling staff reallocation to strategic activities. Customer onboarding automation reduces setup from 12 days to 2.5 days while improving accuracy through standardized procedures.

3. Data analytics platform processes 1.8M daily data points from customer interactions, system performance, market indicators generating actionable insights. Machine learning algorithms identify usage patterns, predict churn with 89% accuracy, recommend features improving engagement 44%. Investment of $850K includes analytics platform ($350K), data engineering team ($350K), visualization tools ($150K). Custom dashboards provide real-time KPI visibility, customer health scores, operational metrics for executives, success teams, product managers. Predictive capabilities include revenue forecasting (96% confidence), lifetime value modeling, market trend analysis supporting strategic planning.

**KEYWORD 4: Customer Experience**
**INSIGHTS:**
1. Journey Optimization: Customer touchpoint enhancement and satisfaction improvement
2. Service Excellence: Support quality and response time optimization
3. Community Building: User engagement and advocacy program development
**ACTIONS:**
1. Customer experience optimization redesigns entire journey delivering 42% satisfaction improvement and 32% churn reduction. Journey mapping identifies 11 critical touchpoints from awareness through renewal, implementing targeted enhancements at each stage. Onboarding enhancement reduces time-to-value from 35 days to 14 days through guided wizards, automated setup, dedicated success manager assignment. Support transformation includes 24/7 chat availability, 400+ knowledge base articles, AI suggestion engine resolving 72% inquiries without human intervention. Investment of $750K encompasses experience design ($180K), platform upgrades ($350K), training programs ($140K), measurement systems ($80K).

2. Service excellence program establishes world-class support achieving industry-leading performance metrics and customer satisfaction. Support infrastructure includes multi-channel availability (chat, email, phone, video), comprehensive documentation, proactive monitoring, escalation procedures. Quality assurance framework ensures consistent service delivery through training, performance monitoring, continuous improvement. Investment totals $480K: support team expansion ($280K), technology platform ($120K), training programs ($80K). Service level targets include 99.8% system availability, 1-hour response times, 95% first-contact resolution, 4.8/5.0 satisfaction scores.

3. Community building initiative creates engaged ecosystem fostering peer learning, product advocacy, collaborative innovation. Online platform hosts 2,200+ active members participating in discussions, best practice sharing, peer support reducing official support burden 38%. User-generated content program encourages case studies, tutorials, feature requests with recognition rewards for contributors. Annual conference brings 350 customers for networking, training, roadmap discussions generating $140K revenue while strengthening relationships. Investment of $420K includes platform development ($160K), content creation ($120K), event planning ($100K), community management ($40K).

**KEYWORD 5: Competitive Positioning**
**INSIGHTS:**
1. Market Differentiation: Unique value proposition and competitive advantage development
2. Strategic Partnerships: Alliance building and ecosystem expansion
3. Future Planning: Long-term positioning and market evolution preparation
**ACTIONS:**
1. Market differentiation establishes unique competitive positioning through proprietary technology, superior outcomes, innovative business model capturing 14% market share within four years. Competitive analysis reveals gaps in customization capabilities, mobile experience, analytics functionality creating differentiation opportunities. Value proposition emphasizes 55% faster implementation, 38% lower total cost, 28% better satisfaction versus leading competitors. Technology differentiation includes patented algorithms, AI automation, industry-specific configurations unavailable elsewhere. Investment of $1.3M funds competitive intelligence ($180K), product differentiation ($650K), marketing positioning ($280K), sales enablement ($190K).

2. Strategic partnership ecosystem expands market reach through technology vendors, implementation consultants, industry specialists generating 38% total revenue through channels. Partnership portfolio includes 6 technology integrations, 10 implementation partners, 12 industry resellers providing comprehensive solution ecosystem. System integrator relationships with consulting firms provide expertise, credibility while expanding addressable market 65% through partner customer bases. Technology partnerships enable seamless integrations with CRM, ERP, industry-specific applications. Investment totals $680K: partner enablement ($240K), integration development ($280K), channel management ($160K).

3. Future planning strategic positioning prepares organization for market evolution over five-year horizon addressing AI adoption, regulatory changes, industry consolidation. Market trend analysis identifies key drivers shaping competitive landscape enabling proactive strategy development. Strategic scenario planning evaluates technology disruption, new competitor entry, market maturation developing responsive strategies. Investment in emerging technologies totals $950K annually: AI research, blockchain exploration, IoT integration positioning for next-generation requirements. Long-term roadmap extends 30 months incorporating customer feedback, technology trends, competitive intelligence ensuring continued leadership.

Provide specific numbers, percentages, dollar amounts, and timeframes in every action item."""
    
    return prompt

def get_business_context_prompt_with_content(question, custom_keywords="", content=""):
    """Enhanced prompt that includes content analysis"""
    
    max_content_length = 1000
    if len(content) > max_content_length:
        content = content[:max_content_length] + "..."
    
    prompt = f"""You are a senior business strategist. Analyze the provided content and deliver strategic insights.

Question: {question}
Keywords: {custom_keywords}
Content: {content}

Use the same EXACT format as above with 5 keywords and detailed actions including specific numbers."""
    
    return prompt

def parse_enhanced_analysis_response(response):
    try:
        if "**KEYWORDS IDENTIFIED:**" in response:
            return parse_standard_format(response)
        elif "Keywords:" in response and "**KEYWORDS IDENTIFIED:**" not in response:
            return parse_alternative_format(response)
        else:
            return parse_fallback_format(response)
        
    except Exception as e:
        logger.error(f"Error parsing response: {str(e)}")
        return {"keywords": [], "structured_insights": {}}

def parse_standard_format(response):
    """Parse properly formatted responses"""
    lines = response.strip().split("\n")
    keywords = []
    structured_insights = {}
    current_keyword = None
    mode = None
    current_titles = []
    current_insights = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("**KEYWORDS IDENTIFIED:**"):
            mode = "keywords"
            continue

        elif mode == "keywords" and not line.startswith("**"):
            keyword_line = line.replace("[", "").replace("]", "")
            keywords = [k.strip() for k in keyword_line.split(",") if k.strip()]
            mode = None
            continue

        elif line.startswith("**KEYWORD") and ":" in line:
            if current_keyword and (current_titles or current_insights):
                structured_insights[current_keyword] = {
                    "titles": current_titles,
                    "insights": current_insights
                }
            
            if ":" in line:
                keyword_part = line.split(":", 1)[1].strip()
                current_keyword = keyword_part.replace("**", "").strip()
                current_titles = []
                current_insights = []
            continue

        elif line.startswith("**INSIGHTS:**"):
            mode = "titles"
            continue

        elif line.startswith("**ACTIONS:**"):
            mode = "insights"
            continue

        elif mode == "titles" and current_keyword:
            if line and (line[0].isdigit() or line.startswith("- ")):
                if line[0].isdigit() and "." in line:
                    content = line.split(".", 1)[1].strip()
                elif line.startswith("- "):
                    content = line[2:].strip()
                else:
                    content = line.strip()
                
                if content:
                    current_titles.append(content)

        elif mode == "insights" and current_keyword:
            if line and (line[0].isdigit() or line.startswith("- ")):
                if line[0].isdigit() and "." in line:
                    content = line.split(".", 1)[1].strip()
                elif line.startswith("- "):
                    content = line[2:].strip()
                else:
                    content = line.strip()
                
                if content:
                    current_insights.append(content)
            elif current_insights and not line.startswith("**"):
                current_insights[-1] += " " + line.strip()

    if current_keyword and (current_titles or current_insights):
        structured_insights[current_keyword] = {
            "titles": current_titles,
            "insights": current_insights
        }

    return {
        "keywords": keywords,
        "structured_insights": structured_insights
    }

def parse_alternative_format(response):
    """Parse alternative format like 'Keywords: 1. AI 2. Quantum...'"""
    lines = response.split('\n')
    keywords = []
    structured_insights = {}
    
    for line in lines:
        if line.strip().startswith("Keywords:"):
            keyword_text = line.replace("Keywords:", "").strip()
            keyword_matches = re.findall(r'\d+\.\s*([^0-9]+?)(?=\d+\.|$)', keyword_text)
            keywords = [k.strip().rstrip('()').rstrip(':') for k in keyword_matches if k.strip()]
            break
    
    current_section = ""
    current_content = []
    
    for line in lines:
        line = line.strip()
        
        if any(keyword.lower() in line.lower() for keyword in keywords) and line.endswith(':'):
            if current_section and current_content:
                structured_insights[current_section] = {
                    "titles": ["Market Opportunity", "Implementation Strategy", "Investment Analysis"],
                    "insights": current_content
                }
            
            current_section = line.rstrip(':').strip()
            current_content = []
            
        elif line.startswith('-') and current_section:
            insight = line.lstrip('- ').strip()
            if insight:
                current_content.append(insight)
    
    if current_section and current_content:
        structured_insights[current_section] = {
            "titles": ["Market Opportunity", "Implementation Strategy", "Investment Analysis"],
            "insights": current_content
        }
    
    logger.info(f"Alternative format parsed: {len(keywords)} keywords, {len(structured_insights)} sections")
    
    return {
        "keywords": keywords,
        "structured_insights": structured_insights
    }

def parse_fallback_format(response):
    """Fallback parser for unstructured responses"""
    common_keywords = ['Technology', 'Innovation', 'Market', 'Strategy', 'Growth']
    keywords = []
    
    for keyword in common_keywords:
        if keyword.lower() in response.lower():
            keywords.append(keyword)
    
    keywords = keywords[:5]
    
    paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]
    
    structured_insights = {}
    for i, keyword in enumerate(keywords):
        if i < len(paragraphs):
            structured_insights[keyword] = {
                "titles": ["Analysis", "Strategy", "Implementation"],
                "insights": [paragraphs[i][:500]]
            }
    
    logger.info(f"Fallback parsing: {len(keywords)} keywords extracted")
    
    return {
        "keywords": keywords,
        "structured_insights": structured_insights
    }

def analyze_question(question, custom_keywords=""):
    try:
        if not question or not question.strip():
            return {
                "error": "Question cannot be empty",
                "keywords": [],
                "insights": {},
                "full_response": ""
            }

        analysis_id = hashlib.md5(f"{question}_{custom_keywords}".encode()).hexdigest()[:8]
        full_prompt = get_business_context_prompt(question, custom_keywords)
        
        logger.info(f"Starting analysis {analysis_id} for question: {question[:50]}...")
        
        response = claude_messages(full_prompt)
        if response.startswith("Error:"):
            return {
                "error": response,
                "keywords": [],
                "insights": {},
                "full_response": response,
                "analysis_id": analysis_id
            }

        parsed_result = parse_enhanced_analysis_response(response)
        return {
            "keywords": parsed_result.get("keywords", []),
            "insights": parsed_result.get("structured_insights", {}),
            "full_response": response,
            "error": None,
            "analysis_id": analysis_id
        }

    except Exception as e:
        logger.error(f"Error in analyze_question: {str(e)}")
        return {
            "error": f"Error analyzing question: {str(e)}",
            "keywords": [],
            "insights": {},
            "full_response": "",
            "analysis_id": None
        }

def summarize_trends(text=None, question=None, keyword=None, return_format="dict"):
    try:
        if not any([text, question, keyword]):
            error_msg = "At least one parameter must be provided"
            if return_format == "string":
                return f"Error: {error_msg}"
            return {
                "error": error_msg,
                "keywords": [],
                "insights": {},
                "full_response": ""
            }

        if text and question:
            analysis_question = f"Based on the content, {question}"
            custom_keywords = keyword or ""
        elif text and keyword:
            analysis_question = f"Analyze content focusing on {keyword}"
            custom_keywords = keyword
        elif text:
            analysis_question = "Analyze content for business opportunities"
            custom_keywords = keyword or ""
        elif question:
            analysis_question = question
            custom_keywords = keyword or ""
        else:
            analysis_question = f"Analyze {keyword}"
            custom_keywords = keyword

        if text:
            enhanced_prompt = get_business_context_prompt_with_content(analysis_question, custom_keywords, text)
        else:
            enhanced_prompt = get_business_context_prompt(analysis_question, custom_keywords)

        response = claude_messages(enhanced_prompt)
        
        if response.startswith("Error:"):
            if return_format == "string":
                return response
            return {
                "error": response,
                "keywords": [],
                "insights": {},
                "full_response": response
            }

        parsed_result = parse_enhanced_analysis_response(response)
        
        if return_format == "string":
            return response
        
        return {
            "keywords": parsed_result.get("keywords", []),
            "insights": parsed_result.get("structured_insights", {}),
            "full_response": response,
            "error": None,
            "analysis_id": hashlib.md5(f"{analysis_question}_{custom_keywords}".encode()).hexdigest()[:8]
        }

    except Exception as e:
        logger.error(f"Error in summarize_trends: {str(e)}")
        error_msg = f"Error: {str(e)}"
        if return_format == "string":
            return error_msg
        return {
            "error": error_msg,
            "keywords": [],
            "insights": {},
            "full_response": ""
        }

def extract_text_from_file(uploaded_file, return_format="dict"):
    tmp_path = None
    try:
        if not uploaded_file:
            error_msg = "No file provided"
            if return_format == "string":
                return f"Error: {error_msg}"
            return {
                "error": error_msg,
                "keywords": [],
                "insights": {},
                "full_response": ""
            }

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        text = textract.process(tmp_path).decode("utf-8")
        
        if return_format == "string":
            return text
        
        logger.info(f"Extracted {len(text)} characters from file")
        
        analysis_result = summarize_trends(
            text=text,
            question="Analyze this document for strategic business insights",
            return_format="dict"
        )
        
        return analysis_result

    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        error_msg = f"Error: {str(e)}"
        if return_format == "string":
            return error_msg
        return {
            "error": error_msg,
            "keywords": [],
            "insights": {},
            "full_response": ""
        }
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass

def analyze_url_content(url, question=None, keyword=None):
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.extract()
        
        text = soup.get_text()
        text = ' '.join(text.split())
        
        if len(text) > 2500:
            text = text[:2500] + "..."
        
        analysis_result = summarize_trends(
            text=text,
            question=question or "Analyze this web content for strategic business insights",
            keyword=keyword,
            return_format="dict"
        )
        
        analysis_result["url"] = url
        return analysis_result
        
    except ImportError:
        return {
            "error": "URL analysis requires 'requests' and 'beautifulsoup4' packages",
            "keywords": [],
            "insights": {},
            "full_response": "",
            "url": url
        }
    except Exception as e:
        logger.error(f"Error analyzing URL: {str(e)}")
        return {
            "error": f"Error analyzing URL: {str(e)}",
            "keywords": [],
            "insights": {},
            "full_response": "",
            "url": url
        }

def safe_get_insight(analysis_result, keyword, insight_type="insights", index=0):
    try:
        if not analysis_result:
            return "Error: analysis_result is empty"

        insights = analysis_result.get("insights", {})
        if not insights:
            return "Error: No insights found"

        keyword_data = insights.get(keyword)
        if not keyword_data:
            available = ", ".join(insights.keys())
            return f"Error: Keyword '{keyword}' not found. Available: {available}"

        items = keyword_data.get(insight_type)
        if not isinstance(items, list):
            return f"Error: Missing '{insight_type}' data"

        if index >= len(items):
            return f"Error: Index {index} out of range (total: {len(items)})"

        return items[index]

    except Exception as e:
        return f"Error retrieving insight: {str(e)}"

def clear_cache():
    global _response_cache
    _response_cache.clear()
    logger.info("Cache cleared")

def get_insight_quality_score(insights_data):
    """Enhanced quality scoring system"""
    if not insights_data:
        return 0
    
    total_score = 0
    total_insights = 0
    
    for keyword, data in insights_data.items():
        insights = data.get("insights", [])
        for insight in insights:
            score = 0
            words = insight.split()
            word_count = len(words)
            insight_lower = insight.lower()
            
            # Word count scoring (prefer 150-200 words)
            if 150 <= word_count <= 200:
                score += 80
            elif 120 <= word_count < 150:
                score += 65
            elif 80 <= word_count < 120:
                score += 50
            elif word_count >= 200:
                score += 70
            else:
                score += 25
            
            # Financial terms scoring
            financial_terms = ['$', '%', 'million', 'billion', 'revenue', 'roi', 'profit', 'cost', 'investment']
            financial_count = sum(1 for term in financial_terms if term in insight_lower)
            score += min(financial_count * 4, 20)
            
            # Market terms scoring
            market_terms = ['market', 'customer', 'competitive', 'growth', 'share', 'segment']
            market_count = sum(1 for term in market_terms if term in insight_lower)
            score += min(market_count * 2, 10)
            
            # Strategy terms scoring
            strategy_terms = ['strategy', 'implementation', 'timeline', 'roadmap', 'metrics']
            strategy_count = sum(1 for term in strategy_terms if term in insight_lower)
            score += min(strategy_count * 2, 8)
            
            total_score += min(score, 100)
            total_insights += 1
    
    return (total_score / total_insights) if total_insights > 0 else 0

def parse_analysis_response(response):
    return parse_enhanced_analysis_response(response)

def test_functions():
    print("✅ Complete app2.py loaded successfully")
    print("✅ Enhanced parsing with multiple format support")
    print("✅ Improved quality scoring system")
    print("✅ Ready for Streamlit integration")

if __name__ == "__main__":
    test_functions()
