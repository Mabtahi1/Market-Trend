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

        # Create a comprehensive analysis question from the inputs
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
        else:  # keyword only
            analysis_question = f"Provide strategic market analysis and business insights related to {keyword}"
            custom_keywords = keyword

        # Use the enhanced business analysis with the content
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
    """Generate enhanced business-focused prompt with stricter formatting requirements"""
    
    prompt = f"""You are a senior strategic market research analyst. You MUST provide detailed, comprehensive business insights.

QUESTION: {question}
KEYWORDS: {custom_keywords}

CRITICAL REQUIREMENTS:
- Each Business Action must be 200-300 words with specific data
- Include dollar amounts, percentages, timeframes, ROI calculations
- Mention market size, growth rates, competitive analysis
- Provide implementation costs, revenue projections, KPIs

Use EXACTLY this format:

**KEYWORDS IDENTIFIED:**
Market Opportunities, Digital Transformation, Customer Experience, Revenue Growth, Competitive Strategy

**STRATEGIC MARKET ANALYSIS:**

**KEYWORD 1: Market Opportunities**
**STRATEGIC INSIGHTS:**
1. Market Opportunity Assessment: Analyze total addressable market size and growth potential
2. Competitive Intelligence: Evaluate competitive landscape and positioning strategies  
3. Implementation Strategy: Develop actionable implementation roadmap with timeline
**BUSINESS ACTIONS:**
1. The market opportunity represents a significant revenue potential of $2.5 billion globally, growing at 15% annually through 2026. Target customer segments include enterprise clients (65% of market) and SMBs (35% of market), with average deal sizes of $150K and $25K respectively. Implementation requires 6-month development phase with $2M initial investment, projected 18-month payback period, and 35% gross margins. Key success metrics include 15% market share capture within 24 months, customer acquisition cost under $15K, and customer lifetime value exceeding $200K. Competitive differentiation focuses on proprietary technology stack providing 40% faster processing speeds than competitors. Risk mitigation includes diversified customer base across 5 industry verticals and strategic partnerships with 3 major technology vendors to ensure scalable delivery capabilities.

2. Competitive analysis reveals three major players controlling 60% market share, creating opportunity for disruptive innovation in underserved segments. Primary competitors include EstablishedCorp ($500M revenue, 25% market share), TechGiant ($400M revenue, 20% market share), and InnovativeCo ($300M revenue, 15% market share). Our differentiation strategy targets price-sensitive SMB segment with 30% cost reduction through automated delivery model. Customer acquisition approach includes digital marketing campaigns targeting CFOs and IT directors, trade show presence at 8 major industry events annually, and partner channel development with 25 system integrators. Brand positioning emphasizes reliability, affordability, and rapid deployment capabilities. Success metrics include 20% customer retention improvement, 50% reduction in sales cycle length, and 25% increase in average deal size through upselling strategies.

3. Implementation strategy requires cross-functional team of 15 professionals including 5 engineers, 3 sales representatives, 2 marketing specialists, 3 customer success managers, and 2 project managers. Technology infrastructure investment of $1.5M includes cloud platform development, security certifications, and integration capabilities. Operational processes encompass customer onboarding automation, support ticket management system, and performance monitoring dashboard. Key milestones include beta testing with 10 pilot customers (month 3), full product launch (month 6), 100 customers milestone (month 12), and profitability achievement (month 18). Risk assessment identifies technology development delays, competitive pricing pressure, and customer churn as primary concerns. Mitigation strategies include agile development methodology, flexible pricing models, and proactive customer success programs with quarterly business reviews.

**KEYWORD 2: Digital Transformation**
**STRATEGIC INSIGHTS:**
1. Revenue Impact Analysis: Calculate ROI from digital initiatives and automation
2. Customer Behavior Trends: Understand digital engagement patterns and preferences
3. Operational Excellence: Optimize processes through technology integration
**BUSINESS ACTIONS:**
1. Digital transformation initiatives generate average ROI of 250% within 18 months through operational efficiency gains and new revenue streams. Revenue impact includes 35% increase in customer lifetime value through personalized experiences, 25% reduction in customer acquisition costs via digital channels, and 40% improvement in sales conversion rates through automated nurturing. Investment requirements total $3.2M including technology platforms ($1.8M), training programs ($0.8M), and change management ($0.6M). Financial projections show $8M incremental revenue in year one, growing to $15M by year three. Key performance indicators include digital engagement scores, automation rate percentages, and customer satisfaction improvements. Market analysis indicates 78% of competitors have initiated similar transformations, making rapid execution critical for competitive positioning. Success factors include executive sponsorship, employee training programs, and phased rollout approach minimizing business disruption.

2. Customer behavior analysis reveals 73% preference for self-service digital interactions, 45% mobile-first engagement patterns, and 60% expectation for real-time response capabilities. Digital channel adoption shows 85% email engagement, 62% social media interaction, and 38% mobile app utilization rates. Personalization engines drive 28% higher engagement rates and 22% increased purchase frequency. Customer journey mapping identifies 7 key touchpoints requiring optimization, with potential 30% improvement in conversion rates through enhanced digital experiences. Investment in customer data platform ($500K) and analytics tools ($300K) enables predictive modeling and behavioral segmentation. Implementation timeline spans 12 months with quarterly milestone reviews. Success metrics include Net Promoter Score improvement (target: +15 points), customer effort score reduction (target: -25%), and digital adoption rates (target: 80% of transactions).

3. Operational excellence roadmap focuses on process automation, data integration, and performance optimization delivering 30% cost reduction and 50% efficiency improvement. Technology stack includes robotic process automation ($400K), enterprise resource planning upgrade ($800K), and business intelligence platform ($300K). Automation targets include invoice processing (90% automation rate), customer onboarding (75% automation), and report generation (95% automation). Change management program addresses workforce transformation through reskilling initiatives for 120 employees, with 85% retention target. Performance measurement framework tracks operational KPIs including process cycle time, error rates, and employee productivity metrics. Implementation phases include assessment (months 1-2), pilot programs (months 3-6), and full deployment (months 7-12). Risk mitigation covers data security protocols, business continuity planning, and vendor management strategies ensuring smooth transition.

**KEYWORD 3: Customer Experience**
**STRATEGIC INSIGHTS:**
1. Innovation Opportunities: Develop customer-centric solutions and service improvements
2. Partnership & Ecosystem: Build strategic alliances for enhanced customer value
3. Risk Management: Address customer satisfaction and retention challenges
**BUSINESS ACTIONS:**
1. Innovation opportunities focus on customer experience enhancement through AI-powered personalization, omnichannel integration, and predictive service delivery. Investment of $1.2M in customer experience platform enables 360-degree customer view, real-time interaction tracking, and automated response capabilities. Product development roadmap includes mobile app enhancement (Q1), chatbot integration (Q2), and loyalty program launch (Q3). Revenue impact projects 20% increase in customer retention, 15% growth in average order value, and 25% improvement in cross-selling success rates. Market research indicates customer experience leaders achieve 2x revenue growth compared to laggards. Technology partnerships with CRM providers and analytics vendors accelerate implementation timeline. Success metrics include customer satisfaction scores (target: 4.5/5.0), first-call resolution rates (target: 80%), and customer effort scores (target: <2.0 on 5-point scale).

2. Partnership ecosystem development creates comprehensive customer value proposition through strategic alliances with complementary service providers. Partnership portfolio includes technology integrators (5 partners), industry consultants (8 partners), and solution vendors (12 partners). Revenue sharing models average 15% partner commission with performance bonuses for customer satisfaction achievements. Joint go-to-market strategies target enterprise accounts through coordinated sales efforts and shared marketing investments. Partner enablement program includes training certification, sales tools, and technical support resources. Combined market reach expands addressable market by 40% through partner channels. Implementation requires 6-month partner onboarding process with quarterly business reviews. Success indicators include partner-generated revenue (target: 30% of total), partner satisfaction scores (target: 4.0/5.0), and joint customer retention rates (target: 95%). Risk management addresses partner conflicts, quality control, and competitive positioning challenges.

3. Risk management framework addresses customer satisfaction challenges through proactive monitoring, rapid response protocols, and continuous improvement processes. Customer satisfaction tracking includes NPS surveys (monthly), customer effort measurements (quarterly), and churn analysis (weekly). Response protocols ensure 24-hour resolution for critical issues and 4-hour response time for standard inquiries. Investment in customer success team ($600K annually) includes dedicated account managers for enterprise clients and automated success tracking for SMB customers. Predictive analytics identify at-risk customers 60 days before potential churn, enabling proactive intervention strategies. Retention programs include customer health scoring, personalized outreach campaigns, and value-added services. Success metrics target 95% customer retention rate, 90% satisfaction scores, and 50% reduction in customer complaints. Continuous improvement processes incorporate customer feedback loops, employee training programs, and technology platform enhancements ensuring sustained service excellence.

**KEYWORD 4: Revenue Growth**
**STRATEGIC INSIGHTS:**
1. Market Expansion: Identify geographic and demographic growth opportunities
2. Digital Transformation: Leverage technology for revenue optimization
3. Sustainability & ESG: Address environmental and social responsibility factors
**BUSINESS ACTIONS:**
1. Market expansion strategy targets three high-growth regions with combined market potential of $1.8B and 22% annual growth rates. Primary markets include Asia-Pacific ($800M opportunity), European Union ($600M opportunity), and Latin America ($400M opportunity). Entry strategy requires $2.5M investment including local partnerships ($800K), regulatory compliance ($500K), market research ($300K), and sales team establishment ($900K). Revenue projections show $5M year-one sales growing to $25M by year three. Localization requirements include product adaptation, language translation, and cultural customization across 8 target countries. Distribution channels include direct sales (40%), partner networks (35%), and digital platforms (25%). Success metrics include market penetration rates (target: 5% within 24 months), customer acquisition costs (target: <$8K), and local revenue contribution (target: 30% of total by year three). Risk factors include regulatory changes, currency fluctuations, and competitive responses requiring flexible strategy adaptation.

2. Digital transformation initiatives drive revenue optimization through automated sales processes, dynamic pricing models, and customer analytics platforms. Technology investment of $1.8M includes sales automation tools ($600K), pricing optimization software ($400K), and business intelligence platform ($800K). Revenue impact includes 18% improvement in sales efficiency, 12% increase in average selling prices, and 25% growth in upselling success rates. Sales process automation reduces cycle time by 35% while improving lead qualification accuracy by 40%. Dynamic pricing algorithms optimize margins across 500+ product SKUs based on market conditions, competitor analysis, and demand patterns. Customer analytics enable targeted campaigns with 2.3x higher conversion rates compared to generic approaches. Implementation timeline spans 15 months with monthly performance reviews. Success indicators include sales productivity metrics, margin improvement percentages, and customer lifetime value growth. Technology partnerships ensure scalable platform architecture supporting 10x transaction volume growth.

3. Sustainability initiatives create revenue opportunities through ESG-focused product development, green technology adoption, and social impact programs. Market research indicates 67% of customers prioritize sustainable business practices, creating $400M addressable market opportunity. Product portfolio expansion includes eco-friendly alternatives capturing 15% price premium and targeting $2M incremental revenue. Operational changes reduce environmental footprint by 30% while achieving $300K annual cost savings through energy efficiency and waste reduction. ESG reporting capabilities attract institutional customers with stringent sustainability requirements. Investment requirements total $1.1M including renewable energy systems ($500K), sustainable packaging ($200K), and ESG compliance tools ($400K). Carbon offset programs and community partnerships enhance brand reputation and customer loyalty. Success metrics include sustainability certifications achieved, carbon footprint reduction percentages, and ESG-driven revenue growth. Long-term positioning establishes competitive differentiation as sustainability regulations increase industry requirements.

**KEYWORD 5: Competitive Strategy**
**STRATEGIC INSIGHTS:**
1. Financial Performance: Optimize investment allocation and financial planning
2. Talent & Workforce: Develop human capital and organizational capabilities
3. Future Outlook: Plan long-term strategic positioning and growth scenarios
**BUSINESS ACTIONS:**
1. Financial performance optimization requires strategic investment allocation across growth initiatives, operational improvements, and risk mitigation strategies. Capital allocation framework prioritizes high-ROI projects with payback periods under 18 months and IRR exceeding 25%. Investment portfolio includes technology platforms (40% allocation, $2.4M), market expansion (30% allocation, $1.8M), and talent acquisition (20% allocation, $1.2M), with 10% reserved for contingency planning. Financial projections show 35% revenue growth over three years with EBITDA margins improving from 18% to 25%. Cash flow management ensures operational sustainability while funding growth initiatives through combination of retained earnings (60%) and strategic financing (40%). Performance monitoring includes monthly financial reviews, quarterly board presentations, and annual strategic planning cycles. Key metrics encompass revenue growth rates, profitability margins, cash conversion cycles, and return on invested capital measurements.

2. Talent and workforce strategy focuses on capability development, retention programs, and cultural transformation supporting business growth objectives. Workforce expansion plan adds 45 professionals over 24 months including 15 technical specialists, 12 sales representatives, 8 customer success managers, and 10 operations staff. Compensation benchmarking ensures competitive positioning within top 75th percentile for critical roles. Training investment of $400K annually includes technical certifications, leadership development, and customer service excellence programs. Employee retention initiatives target 90% retention rate through career development pathways, performance-based bonuses, and flexible work arrangements. Cultural transformation emphasizes innovation, customer focus, and continuous learning through employee engagement surveys, recognition programs, and cross-functional collaboration projects. Succession planning identifies high-potential employees for leadership roles with individualized development plans. Success metrics include employee satisfaction scores (target: 4.2/5.0), retention rates by role category, and internal promotion percentages (target: 70% of leadership positions filled internally).

3. Future outlook planning incorporates scenario analysis, strategic option evaluation, and adaptive capability development for sustained competitive advantage. Strategic scenarios include market expansion opportunities ($50M revenue potential), technology disruption risks ($10M defensive investment), and competitive consolidation responses ($25M acquisition budget). Long-term positioning emphasizes platform-based business model enabling ecosystem partnerships and recurring revenue streams. Innovation pipeline includes next-generation product development ($3M R&D investment), emerging technology adoption (AI/ML capabilities), and adjacent market exploration (three new verticals identified). Competitive monitoring system tracks industry developments, patent filings, and market share changes enabling rapid strategic responses. Organizational agility initiatives include decision-making acceleration, resource reallocation capabilities, and strategic partnership flexibility. Five-year financial projections target $100M revenue with 30% EBITDA margins through organic growth (70%) and strategic acquisitions (30%). Risk management encompasses competitive threats, technology disruption, and regulatory changes with corresponding mitigation strategies and contingency plans."""
    
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

REQUIREMENTS:
- Each Business Action must be 200-300 words with specific data
- Ground insights in the provided content
- Include dollar amounts, percentages, timeframes, ROI calculations
- Mention market size, growth rates, competitive analysis
- Provide implementation costs, revenue projections, KPIs

[Use the same format as the previous prompt with 5 keywords and detailed 200-300 word business actions]"""
    
    return prompt

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
        
        for kw, data in structured_insights.items():
            avg_length = sum(len(insight) for insight in data.get("insights", [])) / max(len(data.get("insights", [])), 1)
            logger.info(f"Keyword '{kw}': {len(data.get('insights', []))} insights, avg length: {avg_length:.0f} chars")
        
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

def parse_analysis_response(response):
    """Legacy parser - kept for backward compatibility"""
    return parse_enhanced_analysis_response(response)

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
            length = len(insight)
            words = insight.split()
            word_count = len(words)
            insight_lower = insight.lower()
            
            # Word count scoring (prefer 200-300 words)
            if 200 <= word_count <= 300:
                score += 50
            elif 150 <= word_count < 200:
                score += 35
            elif 100 <= word_count < 150:
                score += 25
            elif word_count >= 300:
                score += 40
            else:
                score += 10
            
            # Financial and business metrics (higher weight)
            financial_terms = ['roi', 'revenue', 'profit', 'cost', 'investment', 'budget', 'margin', 'pricing', 'financial', 'earnings', '$', '%', 'million', 'billion']
            financial_count = sum(1 for term in financial_terms if term in insight_lower)
            score += min(financial_count * 3, 15)
            
            # Market and competitive analysis
            market_terms = ['market', 'competitive', 'competitor', 'market share', 'positioning', 'segment', 'customer', 'growth', 'analysis']
            market_count = sum(1 for term in market_terms if term in insight_lower)
            score += min(market_count * 2, 12)
            
            # Implementation and strategy content
            strategy_terms = ['strategy', 'implementation', 'approach', 'framework', 'methodology', 'roadmap', 'planning', 'timeline', 'phase']
            strategy_count = sum(1 for term in strategy_terms if term in insight_lower)
            score += min(strategy_count * 2,
