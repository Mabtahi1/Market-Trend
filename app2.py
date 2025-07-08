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
            "max_tokens": 2500,  # Increased slightly for better responses
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
    
    prompt = f"""You are a senior business strategist providing executive-level insights. You MUST follow the exact format specified below.

ANALYSIS REQUEST:
Question: {question}
Focus Keywords: {custom_keywords}

CRITICAL FORMATTING REQUIREMENTS:
- Use the EXACT format shown below
- Each Business Action must be 150-200 words
- Include specific dollar amounts, percentages, timeframes
- Provide market data, ROI calculations, implementation costs
- Focus on actionable strategies with measurable outcomes

RESPOND USING EXACTLY THIS FORMAT:

**KEYWORDS IDENTIFIED:**
Market Opportunities, Growth Strategy, Digital Innovation, Customer Experience, Competitive Positioning

**STRATEGIC ANALYSIS:**

**KEYWORD 1: Market Opportunities**
**INSIGHTS:**
1. Market Opportunity Assessment: Total addressable market size and growth potential analysis
2. Customer Segmentation: Target customer analysis and value proposition development
3. Revenue Projections: Financial forecasting and business model optimization
**ACTIONS:**
1. Market opportunity analysis reveals $2.8 billion addressable market growing at 18% annually through 2027. Primary customer segments include enterprise clients (65% of market, $150K average contracts) and SMBs (35% of market, $45K average deals). Geographic expansion targets North America ($1.2B market), Europe ($900M), Asia-Pacific ($700M). Implementation requires $2.2M investment over 15 months including technology development ($1.2M), sales team expansion ($600K), marketing initiatives ($400K). Revenue projections show $1.8M year one, $5.2M year two, $9.8M year three with 28% EBITDA margins. Success metrics include 6% market penetration within 30 months, $9K customer acquisition cost, $220K lifetime value, and 15% quarterly growth rate.

2. Competitive landscape shows fragmented market with top three players controlling 42% share, creating disruption opportunity. Primary competitors include TechLeader Corp ($140M revenue, 16% share), InnovateSys ($110M revenue, 14% share), Digital Solutions ($95M revenue, 12% share). Differentiation strategy targets underserved mid-market with 35% cost reduction through automation and cloud architecture. Customer acquisition combines targeted digital marketing ($150K quarterly budget), strategic partnerships (15 industry alliances), direct sales team (12 representatives covering key regions). Brand positioning emphasizes rapid deployment (4-month implementation vs 12-month industry average), superior ROI (35% better outcomes), and comprehensive support (24/7 availability).

3. Implementation roadmap requires cross-functional team of 28 professionals: 12 engineers, 8 sales specialists, 4 marketing professionals, 4 customer success managers. Technology infrastructure investment totals $1.6M including cloud platform ($700K), security certifications ($300K), integration capabilities ($400K), analytics dashboard ($200K). Operational framework includes automated onboarding (reducing setup time 60%), AI-powered support (achieving 85% first-contact resolution), predictive analytics for customer success. Key milestones: beta testing months 3-6, limited release month 9, full launch month 12, international expansion month 18. Risk mitigation addresses development delays, competitive pressure, talent acquisition through agile methodology, flexible pricing models, comprehensive retention programs.

**KEYWORD 2: Growth Strategy**
**INSIGHTS:**
1. Revenue Diversification: Multiple income stream development and optimization strategies
2. Market Expansion: Geographic and demographic growth opportunity identification
3. Customer Lifetime Value: Retention and upselling program development
**ACTIONS:**
1. Revenue diversification strategy targets four income streams generating $12.5M combined annual recurring revenue by year three. Primary subscription model ($8.2M, 66%) offers tiered pricing from $2,000/month basic to $12,000/month enterprise. Professional services division ($2.8M, 22%) provides implementation consulting, customization, ongoing optimization at $250/hour average rate. Marketplace revenue ($1.1M, 9%) creates ecosystem partnerships with 20% revenue sharing. Training programs ($400K, 3%) deliver certification courses, workshops, documentation. Financial projections show 35% gross margins on subscriptions, 68% on services, 45% on marketplace, 88% on training. Investment requires $1.1M in dedicated teams, technology platforms, market development. Success metrics include revenue diversification index (no stream exceeding 70%), customer lifetime value improvement (45% increase), cross-selling rates (2.5 products per customer).

2. Market expansion initiative targets high-growth regions with $2.1B combined opportunity and 22% annual growth rates. Primary markets include Asia-Pacific ($850M opportunity, 25% growth), Latin America ($650M, 20% growth), Middle East ($600M, 19% growth). Entry strategy requires $1.8M investment: local partnerships ($600K), regulatory compliance ($450K), market research ($300K), sales team establishment ($450K). Localization includes product adaptation, language translation, cultural customization across 8 target countries. Distribution channels combine direct sales (45%), certified partners (35%), digital platforms (20%). Revenue projections show $3.2M international sales year one, growing to $18M by year three. Success metrics include 4% market penetration within 24 months, $7K acquisition costs, 28% local revenue contribution by year three.

3. Customer lifetime value optimization program increases retention from 82% to 94% while boosting average revenue per user 38%. Customer success framework segments users by engagement levels, business outcomes, growth potential enabling personalized strategies. High-value program (400+ customers, 70% revenue) includes dedicated success managers, quarterly executive briefings, early feature access, customized training. Risk identification system monitors usage patterns, support frequency, satisfaction scores triggering proactive interventions. Retention initiatives include win-back campaigns (73% success rate), loyalty rewards, advocacy programs. Investment totals $650K: customer success team expansion ($400K), retention platform ($150K), loyalty program ($100K). Success indicators include gross retention (95%), net retention (125%), lifetime value ($275K average), advocacy participation (30% customer base).

**KEYWORD 3: Digital Innovation**
**INSIGHTS:**
1. Technology Transformation: Platform modernization and capability enhancement initiatives
2. Process Automation: Operational efficiency and cost reduction through automation
3. Data Analytics: Business intelligence and predictive analytics implementation
**ACTIONS:**
1. Technology transformation modernizes core platform delivering 45% performance improvement and 55% operational cost reduction. Cloud-native redesign migrates from legacy infrastructure to microservices architecture supporting 8x scalability, 99.98% availability. Investment of $1.5M over 12 months includes platform re-engineering ($650K), cloud migration ($450K), security enhancements ($250K), testing automation ($150K). Enhanced capabilities include real-time processing, 40+ third-party integrations, mobile-responsive interface. Performance improvements: 2.5-second page loads (previously 7 seconds), 400ms API responses (previously 1.1 seconds), 35,000 concurrent users (7x current capacity). Implementation follows agile methodology with bi-weekly sprints, CI/CD pipeline, comprehensive testing. Success metrics include 99.95% uptime, 4.8/5.0 customer satisfaction with performance, 32% operational cost reduction within 10 months.

2. Process automation streamlines operations reducing manual effort 68% and improving consistency across customer-facing activities. RPA deployment targets invoice processing (92% automation), customer onboarding (85% automation), report generation (95% automation), support routing (88% automation). Investment totals $550K: automation software ($250K), process reengineering ($200K), training programs ($100K). Workflow optimization identifies 26 repetitive tasks with 950 hours monthly savings enabling staff reallocation to strategic activities. Customer onboarding automation reduces setup from 12 days to 2.5 days while improving accuracy through standardized procedures. Support automation includes chatbot handling 75% routine inquiries, automated classification, intelligent routing reducing response times 52%. Success metrics include 65% processing time reduction, 85% fewer manual errors, 4.3/5.0 employee satisfaction, $350K annual savings.

3. Data analytics platform processes 1.8M daily data points from customer interactions, system performance, market indicators generating actionable insights. Machine learning algorithms identify usage patterns, predict churn with 89% accuracy, recommend features improving engagement 44%. Investment of $850K includes analytics platform ($350K), data engineering team ($350K), visualization tools ($150K). Custom dashboards provide real-time KPI visibility, customer health scores, operational metrics for executives, success teams, product managers. Predictive capabilities include revenue forecasting (96% confidence), lifetime value modeling, market trend analysis supporting strategic planning. Data governance ensures privacy compliance, security protocols, ethical AI practices. Success indicators include 99% data accuracy, 88% analytics adoption, 55% faster decision-making, 30% KPI achievement improvement. Implementation spans 8 months including infrastructure setup, model development, user training, continuous optimization.

**KEYWORD 4: Customer Experience**
**INSIGHTS:**
1. Journey Optimization: Customer touchpoint enhancement and satisfaction improvement
2. Service Excellence: Support quality and response time optimization
3. Community Building: User engagement and advocacy program development
**ACTIONS:**
1. Customer experience optimization redesigns entire journey delivering 42% satisfaction improvement and 32% churn reduction. Journey mapping identifies 11 critical touchpoints from awareness through renewal, implementing targeted enhancements at each stage. Onboarding enhancement reduces time-to-value from 35 days to 14 days through guided wizards, automated setup, dedicated success manager assignment. Support transformation includes 24/7 chat availability, 400+ knowledge base articles, AI suggestion engine resolving 72% inquiries without human intervention. Investment of $750K encompasses experience design ($180K), platform upgrades ($350K), training programs ($140K), measurement systems ($80K). Personalization engine delivers customized content, feature recommendations based on usage patterns improving engagement 48%. Success indicators include NPS improvement (38 to 61), customer effort score reduction (45% improvement), satisfaction ratings (4.7/5.0), support resolution 30% faster.

2. Service excellence program establishes world-class support achieving industry-leading performance metrics and customer satisfaction. Support infrastructure includes multi-channel availability (chat, email, phone, video), comprehensive documentation, proactive monitoring, escalation procedures. Quality assurance framework ensures consistent service delivery through training, performance monitoring, continuous improvement. Investment totals $480K: support team expansion ($280K), technology platform ($120K), training programs ($80K). Service level targets include 99.8% system availability, 1-hour response times, 95% first-contact resolution, 4.8/5.0 satisfaction scores. Proactive support identifies potential issues before customer impact through predictive analytics, automated monitoring, early warning systems. Success metrics encompass customer satisfaction (4.8/5.0), support ticket reduction (40% decrease), resolution time improvement (50% faster), team productivity increase (35% more efficient).

3. Community building initiative creates engaged ecosystem fostering peer learning, product advocacy, collaborative innovation. Online platform hosts 2,200+ active members participating in discussions, best practice sharing, peer support reducing official support burden 38%. User-generated content program encourages case studies, tutorials, feature requests with recognition rewards for contributors. Annual conference brings 350 customers for networking, training, roadmap discussions generating $140K revenue while strengthening relationships. Investment of $420K includes platform development ($160K), content creation ($120K), event planning ($100K), community management ($40K). Customer advisory board (12 strategic accounts) provides product feedback, market insights influencing 68% major decisions. Success measurements include community engagement (88% monthly active), user content (45 posts weekly), advocacy participation (32% customer base), community-driven support (42% inquiries).

**KEYWORD 5: Competitive Positioning**
**INSIGHTS:**
1. Market Differentiation: Unique value proposition and competitive advantage development
2. Strategic Partnerships: Alliance building and ecosystem expansion for market reach
3. Future Planning: Long-term positioning and market evolution preparation
**ACTIONS:**
1. Market differentiation establishes unique competitive positioning through proprietary technology, superior outcomes, innovative business model capturing 14% market share within four years. Competitive analysis reveals gaps in customization capabilities, mobile experience, analytics functionality creating differentiation opportunities. Value proposition emphasizes 55% faster implementation, 38% lower total cost, 28% better satisfaction versus leading competitors. Technology differentiation includes patented algorithms, AI automation, industry-specific configurations unavailable elsewhere. Investment of $1.3M funds competitive intelligence ($180K), product differentiation ($650K), marketing positioning ($280K), sales enablement ($190K). Brand positioning targets innovative companies seeking competitive advantage through technology leadership. Messaging framework emphasizes speed, reliability, measurable outcomes supported by customer testimonials, third-party validation. Success metrics include competitive win rate (48% of evaluations), brand differentiation scores (top 2 analyst rankings), premium pricing sustainability (18% price premium).

2. Strategic partnership ecosystem expands market reach through technology vendors, implementation consultants, industry specialists generating 38% total revenue through channels. Partnership portfolio includes 6 technology integrations, 10 implementation partners, 12 industry resellers providing comprehensive solution ecosystem. System integrator relationships with consulting firms provide expertise, credibility while expanding addressable market 65% through partner customer bases. Technology partnerships enable seamless integrations with CRM, ERP, industry-specific applications. Investment totals $680K: partner enablement ($240K), integration development ($280K), channel management ($160K). Revenue sharing models average 22% partner margin with performance bonuses for satisfaction, retention achievements. Co-marketing initiatives include webinars, conferences, content creation amplifying market presence 140%. Success indicators include partner revenue (42% total), satisfaction scores (4.5/5.0), integration quality (4.8/5.0), market coverage expansion (22 additional markets).

3. Future planning strategic positioning prepares organization for market evolution over five-year horizon addressing AI adoption, regulatory changes, industry consolidation. Market trend analysis identifies key drivers shaping competitive landscape enabling proactive strategy development. Strategic scenario planning evaluates technology disruption, new competitor entry, market maturation developing responsive strategies. Investment in emerging technologies totals $950K annually: AI research, blockchain exploration, IoT integration positioning for next-generation requirements. Long-term roadmap extends 30 months incorporating customer feedback, technology trends, competitive intelligence ensuring continued leadership. Organizational capability development includes talent acquisition, strategic partnerships, intellectual property protection through patents, trade secrets. Financial planning supports sustainable growth: 28% annual revenue increases, 32% EBITDA margins, $4M acquisition budget for complementary technologies. Success framework includes innovation metrics, market share trends, customer retention, financial performance against targets. Environmental scanning monitors competitive moves, regulations, technology developments enabling proactive adjustments.

CRITICAL: Every Business Action must be exactly 150-200 words and include specific dollar amounts, percentages, timeframes, market data, and measurable KPIs."""
    
    return prompt

def get_business_context_prompt_with_content(question, custom_keywords="", content=""):
    """Enhanced prompt that includes content analysis"""
    
    max_content_length = 1000  # Optimized to prevent timeout
    if len(content) > max_content_length:
        content = content[:max_content_length] + "... [Content truncated for analysis]"
    
    prompt = f"""You are a senior business strategist. Analyze the provided content and deliver comprehensive strategic insights.

ANALYSIS REQUEST:
Question: {question}
Focus Keywords: {custom_keywords}

CONTENT TO ANALYZE:
{content}

Use the same EXACT format as specified above with 5 keywords and detailed Business Actions (150-200 words each) including specific quantitative data grounded in the provided content."""
    
    return prompt

def parse_enhanced_analysis_response(response):
    try:
        # Handle multiple response formats
        if "**KEYWORDS IDENTIFIED:**" in response:
            # Standard format parsing
            return parse_standard_format(response)
        elif "Keywords:" in response and "**KEYWORDS IDENTIFIED:**" not in response:
            # Handle alternative format
            return parse_alternative_format(response)
        else:
            # Fallback parsing
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
    
    # Extract keywords from numbered format
    for line in lines:
        if line.strip().startswith("Keywords:"):
            keyword_text = line.replace("Keywords:", "").strip()
            # Extract numbered keywords using regex
            keyword_matches = re.findall(r'\d+\.\s*([^0-9]+?)(?=\d+\.|$)', keyword_text)
            keywords = [k.strip().rstrip('()').rstrip(':') for k in keyword_matches if k.strip()]
            break
    
    # Create structured insights from content sections
    current_section = ""
    current_content = []
    
    for line in lines:
        line = line.strip()
        
        # Check if line is a keyword section header
        if any(keyword.lower() in line.lower() for keyword in keywords) and line.endswith(':'):
            # Save previous section
            if current_section and current_content:
                structured_insights[current_section] = {
                    "titles": ["Market Opportunity", "Implementation Strategy", "Investment Analysis"],
                    "insights": current_content
                }
            
            # Start new section
            current_section = line.rstrip(':').strip()
            current_content = []
            
        elif line.startswith('-') and current_section:
            # Add insight to current section
            insight = line.lstrip('- ').strip()
            if insight:
                current_content.append(insight)
    
    # Don't forget the last section
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
    # Extract any technology/business terms as keywords
    common_keywords = ['AI', 'Technology', 'Innovation', 'Market', 'Strategy', 'Digital', 'Growth', 'Customer', 'Business', 'Investment']
    keywords = []
    
    for keyword in common_keywords:
        if keyword.lower() in response.lower():
            keywords.append(keyword)
    
    keywords = keywords[:5]  # Limit to 5
    
    # Split response into chunks for insights
    paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]
    
    structured_insights = {}
    for i, keyword in enumerate(keywords):
        if i < len(paragraphs):
            structured_insights[keyword] = {
                "titles": ["Analysis", "Strategy", "Implementation"],
                "insights": [paragraphs[i][:500]]  # Limit length
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
            question="Analyze this document for strategic business insights and market opportunities",
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
        
        if len(text) > 2500:  # Increased slightly
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
            "error": "URL analysis requires 'requests' and 'beautifulsoup4' packages. Install with: pip install requests beautifulsoup4",
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
            if 150 <= word_count <= 200
