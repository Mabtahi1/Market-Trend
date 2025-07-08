import boto3
import json
import textract
import tempfile
import os
import logging
import hashlib
import time

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
            "max_tokens": 4096,
            "temperature": 0.1,
            "top_k": 200,
            "top_p": 0.8,
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
    """Generate enhanced business-focused prompt"""
    
    prompt = f"""You are a senior strategic market research analyst providing executive-level insights. 

QUESTION: {question}
KEYWORDS: {custom_keywords}

REQUIREMENTS:
- Provide comprehensive business analysis with specific data
- Include dollar amounts, percentages, timeframes, and ROI calculations
- Each insight should be 200-300 words with actionable strategies
- Focus on market opportunities, competitive analysis, and implementation plans

Use EXACTLY this format:

**KEYWORDS IDENTIFIED:**
Market Opportunities, Digital Transformation, Customer Experience, Revenue Growth, Competitive Strategy

**STRATEGIC MARKET ANALYSIS:**

**KEYWORD 1: Market Opportunities**
**STRATEGIC INSIGHTS:**
1. Market Opportunity Assessment: Analyze market size, growth potential, and revenue opportunities
2. Competitive Intelligence: Evaluate competitive landscape and positioning strategies  
3. Implementation Strategy: Develop actionable roadmap with timeline and resources
**BUSINESS ACTIONS:**
1. Market opportunity analysis reveals a $2.8 billion addressable market growing at 16% annually through 2027. Enterprise segment represents 65% of market value with average contract values of $150,000, while SMB segment accounts for 35% with $35,000 average deals. Geographic expansion targets include North America ($1.2B market), Europe ($900M), and Asia-Pacific ($700M). Implementation requires $2.5M investment over 18 months including technology development ($1.4M), market entry ($600M), and team expansion ($500K). Revenue projections show $1.8M year one, scaling to $9.5M by year three with 25% EBITDA margins. Key metrics include 6% market penetration within 36 months, $10K customer acquisition cost, $200K lifetime value, and 12% quarterly growth minimum. Competitive advantage through proprietary algorithms delivering 30% faster processing than existing solutions. Risk mitigation includes customer diversification across five industries and partnerships with major technology vendors.

2. Competitive analysis shows fragmented market with top three players controlling 40% share, creating disruption opportunity. Primary competitors include TechLeader Corp ($120M revenue, 15% share), Innovation Systems ($95M, 12% share), and Digital Solutions ($85M, 13% share). Differentiation strategy targets underserved mid-market with 35% cost reduction through automation and cloud architecture. Customer acquisition combines digital marketing, industry partnerships, and direct sales team of 10 representatives. Brand positioning emphasizes speed, reliability, and rapid deployment with 4-month implementation versus 12-month industry average. Success metrics include 20% brand awareness within 18 months, 25% shorter sales cycles, 4.5/5.0 customer satisfaction, and 10% market share in five years. Pricing employs value-based model with 15% premium justified by superior outcomes.

3. Implementation roadmap requires 24-person team including 10 engineers, 6 sales specialists, 4 marketing professionals, and 4 customer success managers. Technology investment totals $1.8M including platform development ($800K), security certifications ($350K), integrations ($400K), and analytics ($250K). Operational processes include automated onboarding reducing setup 50%, AI support achieving 80% first-contact resolution, and predictive analytics for proactive customer success. Milestones include beta testing (months 3-6), limited release (month 9), full launch (month 12), international expansion (month 18). Quality targets include 99.9% uptime, sub-second response times, enterprise security compliance. Risk mitigation addresses development delays, pricing pressure, talent acquisition through agile methodology, flexible pricing, comprehensive retention programs.

**KEYWORD 2: Digital Transformation**
**STRATEGIC INSIGHTS:**
1. Revenue Impact Analysis: Calculate ROI from digital initiatives and technology investments
2. Customer Behavior Trends: Understand digital engagement patterns and user preferences
3. Operational Excellence: Optimize processes through automation and digital tools
**BUSINESS ACTIONS:**
1. Digital transformation generates 220% ROI within 24 months through efficiency gains and new revenue streams. Revenue impact includes 30% customer lifetime value increase through personalization, 20% acquisition cost reduction via digital channels, 35% sales conversion improvement through automation. Investment totals $2.8M including platforms ($1.5M), training ($700K), change management ($600K). Financial projections show $6.5M incremental revenue year one, growing to $12M by year three. KPIs include digital engagement scores, automation percentages, customer satisfaction improvements. Market analysis shows 75% of competitors initiating similar transformations, requiring rapid execution for competitive advantage. Success factors include executive sponsorship, comprehensive training, phased rollout minimizing disruption.

2. Customer behavior analysis reveals 70% preference for self-service digital interactions, 40% mobile-first engagement, 55% real-time response expectations. Digital adoption shows 80% email engagement, 55% social media interaction, 35% mobile app utilization. Personalization drives 25% higher engagement, 18% increased purchase frequency. Customer journey optimization identifies 6 key touchpoints requiring enhancement, enabling 25% conversion improvement. Customer data platform investment ($450K) plus analytics tools ($280K) enables predictive modeling, behavioral segmentation. 12-month implementation with quarterly reviews. Success metrics include NPS improvement (+12 points), effort score reduction (-20%), digital adoption (75% transactions).

3. Operational excellence through automation delivers 25% cost reduction, 40% efficiency improvement. Technology stack includes process automation ($350K), ERP upgrade ($650K), business intelligence ($250K). Automation targets include invoice processing (85% automation), customer onboarding (70% automation), reporting (90% automation). Change management addresses workforce transformation through reskilling 100 employees, 80% retention target. Performance framework tracks cycle times, error rates, productivity metrics. Implementation phases: assessment (months 1-2), pilots (months 3-6), full deployment (months 7-12). Risk mitigation covers data security, business continuity, vendor management ensuring smooth transition.

**KEYWORD 3: Customer Experience**
**STRATEGIC INSIGHTS:**
1. Innovation Opportunities: Develop customer-centric solutions and service enhancements
2. Partnership Ecosystem: Build alliances for comprehensive customer value delivery
3. Risk Management: Address satisfaction challenges and retention optimization
**BUSINESS ACTIONS:**
1. Innovation focus on AI-powered personalization, omnichannel integration, predictive service delivery. $1M customer experience platform investment enables 360-degree view, real-time tracking, automated responses. Product roadmap includes mobile enhancement (Q1), chatbot integration (Q2), loyalty program (Q3). Revenue impact projects 18% retention increase, 12% average order value growth, 20% cross-selling improvement. Research shows experience leaders achieve 1.8x revenue growth versus laggards. Technology partnerships with CRM and analytics vendors accelerate implementation. Success metrics include satisfaction scores (4.3/5.0), first-call resolution (75%), effort scores (<2.5).

2. Partnership ecosystem creates comprehensive value through strategic alliances with complementary providers. Portfolio includes technology integrators (4 partners), consultants (6 partners), solution vendors (10 partners). Revenue sharing averages 12% commission with performance bonuses for satisfaction achievements. Joint go-to-market targets enterprise accounts through coordinated sales, shared marketing. Partner enablement includes certification, tools, support resources. Combined reach expands addressable market 35% through channels. 6-month onboarding with quarterly reviews. Success indicators include partner revenue (25% of total), satisfaction scores (4.0/5.0), joint retention (92%).

3. Risk management addresses satisfaction challenges through proactive monitoring, rapid response, continuous improvement. Satisfaction tracking includes NPS surveys (monthly), effort measurements (quarterly), churn analysis (weekly). Response protocols ensure 24-hour critical issue resolution, 4-hour standard response. Customer success investment ($500K annually) includes dedicated managers for enterprise clients, automated tracking for SMB customers. Predictive analytics identify at-risk customers 45 days before churn, enabling intervention. Retention programs include health scoring, outreach campaigns, value-added services. Success targets include 92% retention, 85% satisfaction, 40% complaint reduction.

**KEYWORD 4: Revenue Growth**
**STRATEGIC INSIGHTS:**
1. Market Expansion: Geographic and demographic growth opportunity identification
2. Digital Optimization: Technology-driven revenue enhancement strategies
3. Sustainability Impact: ESG considerations and green business opportunities
**BUSINESS ACTIONS:**
1. Market expansion targets three high-growth regions with $1.5B combined potential, 20% annual growth. Primary markets include Asia-Pacific ($650M opportunity), Europe ($500M), Latin America ($350M). Entry strategy requires $2M investment including partnerships ($600K), compliance ($400K), research ($250K), sales teams ($750K). Revenue projections show $4M year-one sales growing to $18M by year three. Localization includes product adaptation, translation, cultural customization across 6 countries. Distribution channels include direct sales (45%), partners (35%), digital platforms (20%). Success metrics include 4% market penetration within 24 months, $7K acquisition costs, 25% local revenue contribution by year three.

2. Digital optimization drives revenue through automated sales processes, dynamic pricing, customer analytics. Technology investment $1.5M includes sales automation ($500K), pricing optimization ($350K), business intelligence ($650K). Revenue impact includes 15% sales efficiency improvement, 10% average price increases, 20% upselling growth. Sales automation reduces cycle time 30%, improves lead qualification 35%. Dynamic pricing optimizes margins across 400+ SKUs based on market conditions, competition, demand. Customer analytics enable targeted campaigns with 2x higher conversion versus generic approaches. 12-month implementation with monthly reviews. Success indicators include productivity metrics, margin improvements, lifetime value growth.

3. Sustainability initiatives create revenue through ESG-focused development, green technology, social impact programs. Research shows 60% customers prioritize sustainable practices, creating $350M addressable opportunity. Product expansion includes eco-friendly alternatives capturing 12% price premium, targeting $1.5M incremental revenue. Operational changes reduce environmental impact 25% while achieving $250K annual savings through efficiency, waste reduction. ESG reporting attracts institutional customers with sustainability requirements. Investment totals $900K including renewable systems ($400K), sustainable packaging ($150K), compliance tools ($350K). Carbon offset programs, community partnerships enhance reputation, loyalty. Success metrics include certifications achieved, footprint reduction, ESG-driven revenue growth.

**KEYWORD 5: Competitive Strategy**
**STRATEGIC INSIGHTS:**
1. Financial Performance: Investment optimization and strategic financial planning
2. Talent Development: Human capital and organizational capability building
3. Future Positioning: Long-term strategic planning and market evolution preparation
**BUSINESS ACTIONS:**
1. Financial optimization requires strategic investment allocation across growth, operations, risk mitigation. Capital framework prioritizes projects with 18-month payback, 20%+ IRR. Investment portfolio includes technology (40%, $2M), market expansion (30%, $1.5M), talent (20%, $1M), contingency (10%, $500K). Financial projections show 30% revenue growth over three years, EBITDA margins improving from 15% to 22%. Cash flow management ensures operational sustainability while funding growth through retained earnings (65%) and strategic financing (35%). Performance monitoring includes monthly reviews, quarterly board presentations, annual strategic planning. Key metrics encompass growth rates, profitability margins, cash conversion, return on invested capital.

2. Talent strategy focuses on capability development, retention, cultural transformation supporting growth objectives. Workforce expansion adds 35 professionals over 24 months including 12 technical specialists, 10 sales representatives, 6 customer success managers, 7 operations staff. Compensation benchmarking ensures competitive positioning within 70th percentile for critical roles. Training investment $350K annually includes certifications, leadership development, customer service excellence. Employee retention targets 88% through career development, performance bonuses, flexible arrangements. Cultural transformation emphasizes innovation, customer focus, continuous learning through engagement surveys, recognition programs, collaboration projects. Succession planning identifies high-potential employees with individualized development. Success metrics include satisfaction scores (4.0/5.0), retention by role, internal promotions (65% leadership positions).

3. Future planning incorporates scenario analysis, strategic options, adaptive capabilities for sustained advantage. Strategic scenarios include market expansion ($40M revenue potential), technology disruption ($8M defensive investment), competitive consolidation ($20M acquisition budget). Long-term positioning emphasizes platform business model enabling ecosystem partnerships, recurring revenue. Innovation pipeline includes next-generation development ($2.5M R&D), emerging technology adoption (AI/ML), adjacent market exploration (two new verticals). Competitive monitoring tracks developments, patents, market share enabling rapid responses. Organizational agility includes decision acceleration, resource reallocation, partnership flexibility. Five-year projections target $80M revenue, 25% EBITDA margins through organic growth (75%) and acquisitions (25%)."""
    
    return prompt

def get_business_context_prompt_with_content(question, custom_keywords="", content=""):
    """Enhanced prompt that includes content analysis"""
    
    max_content_length = 2500
    if len(content) > max_content_length:
        content = content[:max_content_length] + "... [Content truncated for analysis]"
    
    prompt = f"""You are a senior strategic market research analyst. Analyze the provided content and deliver comprehensive business insights.

QUESTION: {question}
KEYWORDS: {custom_keywords}

CONTENT TO ANALYZE:
{content}

Use the same detailed format as above, ensuring each Business Action is 200-300 words with specific quantitative data grounded in the provided content."""
    
    return prompt

def parse_enhanced_analysis_response(response):
    try:
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
                    current_keyword = keyword_part.replace("**", "").replace("[", "").replace("]", "").strip()
                    current_titles = []
                    current_insights = []
                continue

            elif line.startswith("**STRATEGIC INSIGHTS:**"):
                mode = "titles"
                continue

            elif line.startswith("**BUSINESS ACTIONS:**"):
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
                    
                    content = content.replace("[", "").replace("]", "").strip()
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
                    
                    content = content.replace("[", "").replace("]", "").strip()
                    if content:
                        current_insights.append(content)
                elif current_insights and not line.startswith("**"):
                    current_insights[-1] += " " + line.strip()

        if current_keyword and (current_titles or current_insights):
            structured_insights[current_keyword] = {
                "titles": current_titles,
                "insights": current_insights
            }

        logger.info(f"Parsed {len(keywords)} keywords: {keywords}")
        logger.info(f"Structured insights for {len(structured_insights)} keywords")
        
        return {
            "keywords": keywords,
            "structured_insights": structured_insights
        }

    except Exception as e:
        logger.error(f"Error parsing enhanced analysis response: {str(e)}")
        return {
            "keywords": [],
            "structured_insights": {}
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
        
        logger.info(f"Starting enhanced analysis {analysis_id} for question: {question[:50]}...")
        
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
    """Enhanced version that uses the same format as analyze_question"""
    try:
        if not any([text, question, keyword]):
            error_msg = "At least one parameter (text, question, or keyword) must be provided"
            if return_format == "string":
                return f"Error: {error_msg}"
            return {
                "error": error_msg,
                "keywords": [],
                "insights": {},
                "full_response": ""
            }

        if text and question:
            analysis_question = f"Based on the following content, {question}"
            custom_keywords = keyword or ""
        elif text and keyword:
            analysis_question = f"Analyze the following content focusing on {keyword} and related business opportunities"
            custom_keywords = keyword
        elif text:
            analysis_question = "Analyze the following content and identify key business opportunities, trends, and strategic insights"
            custom_keywords = keyword or ""
        elif question:
            analysis_question = question
            custom_keywords = keyword or ""
        else:
            analysis_question = f"Provide strategic market analysis and business insights related to {keyword}"
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
        error_msg = f"Error summarizing content: {str(e)}"
        if return_format == "string":
            return error_msg
        return {
            "error": error_msg,
            "keywords": [],
            "insights": {},
            "full_response": ""
        }

def extract_text_from_file(uploaded_file, return_format="dict"):
    """Enhanced version that returns structured analysis instead of just text"""
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
        
        logger.info(f"Extracted {len(text)} characters from file, analyzing...")
        
        analysis_result = summarize_trends(
            text=text,
            question="Analyze this document and provide strategic business insights and market opportunities",
            return_format="dict"
        )
        
        return analysis_result

    except Exception as e:
        logger.error(f"Error extracting text from file: {str(e)}")
        error_msg = f"Error extracting text: {str(e)}"
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
            except Exception as cleanup_error:
                logger.warning(f"Could not clean up temp file: {cleanup_error}")

def analyze_url_content(url, question=None, keyword=None):
    """Analyze URL content with enhanced format"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.extract()
        
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        if len(text) > 5000:
            text = text[:5000] + "..."
        
        analysis_result = summarize_trends(
            text=text,
            question=question or "Analyze this web content and provide strategic business insights",
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
            return "Error: analysis_result is empty or None"

        if insight_type not in {"titles", "insights"}:
            return f"Error: Invalid insight_type '{insight_type}'"

        insights = analysis_result.get("insights", {})
        if not insights:
            return "Error: No insights found in the analysis result"

        keyword_data = insights.get(keyword)
        if not keyword_data:
            available_keywords = ", ".join(insights.keys())
            return f"Error: Keyword '{keyword}' not found. Available keywords: {available_keywords}"

        items = keyword_data.get(insight_type)
        if not isinstance(items, list):
            return f"Error: Missing or malformed '{insight_type}' data for keyword '{keyword}'"

        if index >= len(items):
            return f"Error: Index {index} out of range for '{insight_type}' in keyword '{keyword}' (total available: {len(items)})"

        return items[index]

    except Exception as e:
        logger.error(f"Error in safe_get_insight: {str(e)}")
        return f"Error retrieving insight: {str(e)}"

def clear_cache():
    """Clear the response cache to force fresh responses"""
    global _response_cache
    _response_cache.clear()
    logger.info("Response cache cleared")

def get_insight_quality_score(insights_data):
    """Calculate an improved quality score for the insights"""
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
            
            # Word count scoring (prefer 200-300 words)
            if 200 <= word_count <= 300:
                score += 60
            elif 150 <= word_count < 200:
                score += 45
            elif 100 <= word_count < 150:
                score += 30
            elif word_count >= 300:
                score += 50
            else:
                score += 15
            
            # Financial terms
            financial_terms = ['roi', 'revenue', 'profit', 'cost', 'investment', 'budget', 'margin', 'pricing', '$', '%', 'million', 'billion']
            financial_count = sum(1 for term in financial_terms if term in insight_lower)
            score += min(financial_count * 3, 20)
            
            # Market terms
            market_terms = ['market', 'competitive', 'competitor', 'customer', 'growth', 'share', 'segment']
            market_count = sum(1 for term in market_terms if term in insight_lower)
            score += min(market_count * 2, 15)
            
            # Strategy terms
            strategy_terms = ['strategy', 'implementation', 'approach', 'framework', 'timeline', 'roadmap']
            strategy_count = sum(1 for term in strategy_terms if term in insight_lower)
            score += min(strategy_count * 2, 10)
            
            total_score += min(score, 100)
            total_insights += 1
    
    final_score = (total_score / total_insights) if total_insights > 0 else 0
    return min(final_score, 100)

def parse_analysis_response(response):
    """Legacy parser - kept for backward compatibility"""
    return parse_enhanced_analysis_response(response)

# Test function
def test_functions():
    print("✅ All functions loaded successfully")
    print("✅ Ready for Streamlit integration")

if __name__ == "__main__":
    test_functions()
