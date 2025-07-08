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
    """Generate enhanced business-focused prompt with comprehensive requirements"""
    
    prompt = f"""You are a senior strategic market research analyst providing executive-level insights. You MUST follow the exact format and provide comprehensive, detailed analysis.

QUESTION: {question}
KEYWORDS: {custom_keywords}

CRITICAL REQUIREMENTS:
- Each Business Action must be 250-350 words with specific quantitative data
- Include dollar amounts, percentages, timeframes, ROI calculations, market sizes
- Mention specific competitors, customer segments, implementation costs
- Provide measurable KPIs, success metrics, and risk assessments
- Use realistic but compelling business data and projections

Use EXACTLY this format:

**KEYWORDS IDENTIFIED:**
Market Analysis, Growth Strategy, Digital Innovation, Customer Engagement, Competitive Positioning

**STRATEGIC MARKET ANALYSIS:**

**KEYWORD 1: Market Analysis**
**STRATEGIC INSIGHTS:**
1. Market Opportunity Assessment: Total addressable market size and growth potential analysis
2. Competitive Intelligence: Key player analysis and market positioning strategies  
3. Implementation Strategy: Detailed roadmap with timeline and resource requirements
**BUSINESS ACTIONS:**
1. The global market opportunity represents $4.2 billion in total addressable market, experiencing 18% compound annual growth rate through 2027. Primary customer segments include enterprise clients (accounting for 68% of market value at average contract value of $180,000) and mid-market companies (32% of market with $45,000 average deals). Geographic expansion targets North America ($1.8B), Europe ($1.4B), and Asia-Pacific ($1.0B) markets. Implementation requires $3.2 million initial investment over 18 months, including technology development ($1.8M), market entry costs ($800K), and team expansion ($600K). Revenue projections show $2.1M in year one, scaling to $12.5M by year three with 28% EBITDA margins. Key performance indicators include market penetration rate (target: 8% within 36 months), customer acquisition cost ($12,000), lifetime value ($240,000), and quarterly revenue growth (minimum 15%). Competitive differentiation focuses on proprietary AI algorithms delivering 35% faster processing than incumbent solutions. Risk mitigation includes diversified customer portfolio across six industry verticals and strategic partnerships with three major technology vendors ensuring scalable delivery infrastructure and market credibility.

2. Competitive landscape analysis reveals fragmented market with top three players controlling 45% market share, creating significant opportunity for disruptive innovation. Primary competitors include MarketLeader Corp ($180M annual revenue, 18% market share), TechGiant Solutions ($140M revenue, 15% share), and Innovation Partners ($110M revenue, 12% share). Our differentiation strategy targets underserved SMB segment with 40% cost reduction through automated delivery model and cloud-based architecture. Customer acquisition approach combines digital marketing campaigns targeting C-suite executives, strategic partnerships with industry associations, and direct sales team of 12 representatives covering key metropolitan areas. Brand positioning emphasizes reliability, innovation, and rapid deployment capabilities with case studies demonstrating 6-month implementation cycles versus industry average of 14 months. Success metrics include brand awareness improvement (target: 25% aided recall within 18 months), sales cycle reduction (target: 30% shorter than competitors), customer satisfaction scores (target: 4.6/5.0), and market share capture (target: 12% within five years). Pricing strategy employs value-based model with 20% premium justified by superior outcomes and faster time-to-value delivery.

3. Implementation roadmap requires cross-functional team of 28 professionals including 12 engineers, 8 sales specialists, 4 marketing professionals, and 4 customer success managers. Technology infrastructure investment totals $2.1 million including cloud platform development ($900K), security certifications ($400K), integration capabilities ($500K), and analytics dashboard ($300K). Operational processes encompass automated customer onboarding reducing setup time by 60%, AI-powered support system achieving 85% first-contact resolution, and predictive analytics platform enabling proactive customer success interventions. Development milestones include beta testing with 15 pilot customers (months 3-6), limited market release (month 9), full product launch (month 12), and international expansion (month 18). Quality assurance protocols ensure 99.9% uptime, sub-second response times, and enterprise-grade security compliance. Risk assessment identifies technology development delays, competitive pricing pressure, and talent acquisition challenges as primary concerns. Mitigation strategies include agile development methodology with bi-weekly sprints, flexible pricing models with performance-based components, and comprehensive employee retention program including equity participation and professional development opportunities.

**KEYWORD 2: Growth Strategy**
**STRATEGIC INSIGHTS:**
1. Revenue Diversification: Multiple revenue stream development and optimization
2. Customer Expansion: Existing account growth and market penetration strategies
3. Innovation Pipeline: Next-generation product development and market positioning
**BUSINESS ACTIONS:**
1. Revenue diversification strategy targets four distinct income streams generating combined $18.7 million annual recurring revenue by year three. Primary subscription model ($12.2M, 65% of total) focuses on SaaS platform with tiered pricing from $2,500/month (basic) to $15,000/month (enterprise). Professional services division ($3.8M, 20% of total) offers implementation consulting, customization projects, and ongoing optimization services at $275/hour average billing rate. Marketplace revenue ($1.9M, 10% of total) creates ecosystem partnerships enabling third-party integrations with 15% revenue sharing model. Training and certification programs ($800K, 5% of total) provide customer education and partner enablement through online courses, workshops, and certification pathways. Financial projections show 32% gross margins on subscription revenue, 65% on professional services, 45% on marketplace transactions, and 85% on training programs. Implementation requires dedicated teams for each revenue stream with combined investment of $1.4 million in personnel, technology platforms, and market development. Success metrics include revenue diversification index (target: no single stream exceeding 70%), customer lifetime value improvement (target: 40% increase), and cross-selling attachment rates (target: 2.3 products per customer). Risk mitigation addresses market saturation, pricing pressure, and execution complexity through phased rollout approach and continuous market feedback integration.

2. Customer expansion initiatives focus on existing account growth through upselling, cross-selling, and retention optimization programs. Account management framework segments customers into Strategic ($100K+ annual value, 15% of base), Growth ($25K-$100K, 35% of base), and Standard (<$25K, 50% of base) tiers with tailored engagement models. Upselling programs target feature upgrades, user expansion, and premium support services with average 38% annual contract value increase for successful conversions. Cross-selling strategy introduces complementary solutions including analytics modules, integration services, and industry-specific extensions with 28% attachment rate objective. Customer success platform leverages predictive analytics to identify expansion opportunities 90 days in advance, enabling proactive engagement and personalized recommendations. Retention initiatives include quarterly business reviews, success metric tracking, and early warning systems for at-risk accounts. Investment requirements total $900K including customer success team expansion (6 additional managers), technology platform enhancements, and customer advisory board establishment. Success indicators encompass net revenue retention (target: 125%), gross revenue retention (target: 95%), expansion revenue percentage (target: 35% of total), and customer health scores (target: average 8.5/10). Implementation timeline spans 12 months with monthly performance reviews and quarterly strategy adjustments based on customer feedback and market dynamics.

3. Innovation pipeline development focuses on next-generation capabilities maintaining competitive advantage and market leadership position. Research and development investment of $2.3 million annually (12% of projected revenue) funds three primary initiatives: artificial intelligence integration, mobile-first user experience, and vertical-specific solutions. AI capabilities include predictive analytics, natural language processing, and automated decision-making features addressing customer workflow optimization needs. Mobile platform development targets field workers and remote teams with offline functionality, real-time synchronization, and enhanced user interface optimized for tablet and smartphone devices. Vertical solutions target healthcare ($500M addressable market), financial services ($380M market), and manufacturing ($420M market) with industry-specific compliance, integrations, and workflows. Product roadmap includes quarterly feature releases, annual major version updates, and continuous platform improvements based on customer usage analytics. Technology partnerships with cloud providers, AI vendors, and industry specialists accelerate development timelines and reduce technical risks. Success metrics include feature adoption rates (target: 65% of customers using new capabilities within 6 months), customer satisfaction with innovations (target: 4.4/5.0), and competitive differentiation scores from third-party analysts. Market validation includes beta testing programs with 25 customer participants and advisory board feedback from industry executives.

**KEYWORD 3: Digital Innovation**
**STRATEGIC INSIGHTS:**
1. Technology Transformation: Platform modernization and capability enhancement
2. Data Analytics: Business intelligence and predictive analytics implementation
3. Automation: Process optimization and efficiency improvement initiatives
**BUSINESS ACTIONS:**
1. Technology transformation initiative modernizes core platform architecture delivering 45% performance improvement and 60% reduction in operational costs. Cloud-native redesign migrates from legacy infrastructure to microservices architecture supporting 10x scalability and 99.99% availability targets. Investment of $1.8 million over 15 months includes platform re-engineering ($800K), cloud migration ($500K), security enhancements ($300K), and testing automation ($200K). Modern technology stack incorporates containerization, API-first design, and serverless computing reducing infrastructure costs by $180K annually while improving deployment speed by 80%. Enhanced capabilities include real-time data processing, advanced integrations with 50+ third-party systems, and mobile-responsive interface optimized for multiple device types. Performance improvements encompass 3-second average page load times (previously 8 seconds), 500ms API response times (previously 1.2 seconds), and support for 50,000 concurrent users (10x current capacity). Implementation follows agile methodology with bi-weekly sprints, continuous integration/deployment pipeline, and comprehensive testing protocols. Success metrics include system uptime (target: 99.95%), customer satisfaction with performance (target: 4.7/5.0), and operational cost reduction (target: 35% within 12 months). Risk mitigation addresses migration complexity, data integrity, and user training through phased rollout, comprehensive backup procedures, and extensive user acceptance testing with customer advisory groups.

2. Data analytics platform implementation transforms business intelligence capabilities enabling data-driven decision making and predictive insights. Advanced analytics infrastructure processes 2.5 million data points daily from customer interactions, system performance metrics, and market indicators generating actionable insights for product development, customer success, and business optimization. Machine learning algorithms identify usage patterns, predict customer churn with 87% accuracy, and recommend personalized feature suggestions improving customer engagement by 42%. Investment of $1.1 million includes analytics platform licensing ($400K), data engineering team ($500K), and visualization tools ($200K). Custom dashboards provide real-time visibility into key performance indicators, customer health scores, and operational metrics accessible to executives, customer success teams, and product managers. Predictive analytics capabilities include revenue forecasting with 95% confidence intervals, customer lifetime value modeling, and market trend analysis supporting strategic planning processes. Data governance framework ensures privacy compliance, security protocols, and ethical AI practices meeting regulatory requirements and customer expectations. Success indicators encompass data quality scores (target: 98% accuracy), analytics adoption rates (target: 85% of users), decision-making speed improvement (target: 50% faster), and business outcome correlation (target: 25% improvement in KPI achievement). Implementation timeline spans 10 months including data infrastructure setup, model development, user training, and continuous optimization based on business feedback and performance monitoring.

3. Automation initiatives streamline operational processes reducing manual effort by 65% and improving consistency across customer-facing activities. Robotic process automation deployment targets invoice processing (95% automation rate), customer onboarding (80% automation), report generation (90% automation), and support ticket routing (85% automation). Investment totals $750K including automation software licensing ($300K), process reengineering ($250K), and employee training programs ($200K). Workflow optimization identifies 23 repetitive tasks suitable for automation with combined time savings of 1,200 hours monthly enabling staff reallocation to high-value activities. Customer onboarding automation reduces setup time from 14 days to 3 days while improving accuracy and consistency through standardized procedures and automated validation checks. Support automation includes chatbot implementation handling 70% of routine inquiries, automated ticket classification, and intelligent routing to appropriate specialists reducing response times by 55%. Process monitoring dashboard tracks automation performance, exception handling, and continuous improvement opportunities ensuring optimal efficiency and quality outcomes. Change management program addresses workforce transformation through skills development, role redefinition, and career advancement opportunities for affected employees. Success metrics include process efficiency improvement (target: 60% reduction in processing time), error rate reduction (target: 80% fewer manual errors), employee satisfaction with new tools (target: 4.2/5.0), and cost savings achievement (target: $400K annually). Implementation follows phased approach with pilot programs, user feedback integration, and gradual expansion across all operational areas.

**KEYWORD 4: Customer Engagement**
**STRATEGIC INSIGHTS:**
1. Experience Optimization: Customer journey enhancement and satisfaction improvement
2. Retention Programs: Loyalty initiatives and churn reduction strategies
3. Community Building: User engagement and advocacy development programs
**BUSINESS ACTIONS:**
1. Customer experience optimization program redesigns entire customer journey delivering 35% improvement in satisfaction scores and 28% reduction in churn rates. Journey mapping identifies 12 critical touchpoints from initial awareness through renewal cycles, implementing targeted improvements at each stage. Onboarding experience enhancement reduces time-to-value from 45 days to 18 days through guided setup wizards, automated configuration, and dedicated success manager assignment for first 90 days. Support experience transformation includes 24/7 chat availability, comprehensive knowledge base with 500+ articles, and AI-powered suggestion engine resolving 68% of inquiries without human intervention. Investment of $920K encompasses experience design consulting ($200K), technology platform upgrades ($400K), training programs ($180K), and performance measurement systems ($140K). Personalization engine delivers customized content, feature recommendations, and communication preferences based on usage patterns and business needs improving engagement by 45%. Feedback collection system captures satisfaction data at every touchpoint through surveys, interviews, and behavioral analytics enabling continuous improvement initiatives. Success indicators include Net Promoter Score improvement (target: increase from 42 to 58), Customer Effort Score reduction (target: 40% improvement), customer satisfaction ratings (target: 4.6/5.0), and support resolution times (target: 25% faster). Implementation spans 8 months with monthly progress reviews and quarterly customer advisory board meetings ensuring alignment with evolving customer expectations and market requirements.

2. Retention program development implements comprehensive loyalty initiatives reducing annual churn from 18% to 8% while increasing customer lifetime value by 42%. Customer success framework segments users based on engagement levels, business outcomes, and growth potential enabling personalized retention strategies. High-value customer program (500+ customers representing 70% of revenue) includes dedicated success managers, quarterly executive briefings, early access to new features, and customized training programs. Risk identification system monitors usage patterns, support ticket frequency, contract renewal timelines, and satisfaction scores triggering proactive interventions for at-risk accounts. Retention initiatives include win-back campaigns for lapsed users, loyalty rewards for long-term customers, and advocacy programs recognizing customer champions. Investment totals $680K including customer success team expansion ($400K), retention technology platform ($180K), and loyalty program development ($100K). Customer health scoring algorithm analyzes 47 variables predicting churn probability with 91% accuracy enabling early intervention 120 days before potential departure. Success recovery programs achieve 73% win-back rate through personalized outreach, service recovery, and value demonstration initiatives. Performance metrics encompass gross retention rate (target: 92%), net retention rate (target: 118%), customer lifetime value (target: $285K average), and advocacy participation (target: 25% of customer base). Continuous optimization includes quarterly cohort analysis, retention strategy refinement, and customer feedback integration ensuring program effectiveness and customer satisfaction alignment.

3. Community building initiative creates engaged user ecosystem fostering peer learning, product advocacy, and collaborative innovation. Online community platform hosts 2,800+ active members participating in discussions, sharing best practices, and providing peer support reducing official support burden by 35%. User-generated content program encourages case study sharing, tutorial creation, and feature request submissions with recognition and rewards for top contributors. Annual user conference brings together 400 customers for networking, training, and product roadmap discussions generating $180K revenue while strengthening customer relationships. Investment of $520K includes community platform development ($200K), content creation ($150K), event planning ($120K), and community management staff ($50K). Customer advisory board comprising 15 strategic accounts provides product feedback, market insights, and strategic guidance influencing 65% of major product decisions. Advocacy program identifies customer champions participating in reference calls, case studies, and industry speaking opportunities with 89% agreement rate for reference requests. Knowledge sharing initiatives include monthly webinars (average 250 attendees), quarterly roundtables for specific industries, and annual awards recognizing innovation and success achievements. Success measurements include community engagement rates (target: 85% monthly active users), user-generated content volume (target: 50 posts weekly), customer advocacy participation (target: 30% of customer base), and community-driven support resolution (target: 40% of inquiries). Continuous community enhancement incorporates member feedback, industry best practices, and evolving engagement preferences ensuring sustained participation and value creation for all community members.

**KEYWORD 5: Competitive Positioning**
**STRATEGIC INSIGHTS:**
1. Market Differentiation: Unique value proposition and competitive advantage development
2. Strategic Partnerships: Alliance building and ecosystem expansion initiatives
3. Future Planning: Long-term positioning and market evolution strategies
**BUSINESS ACTIONS:**
1. Market differentiation strategy establishes unique competitive positioning through proprietary technology, superior customer outcomes, and innovative business model capturing 15% market share within four years. Competitive analysis reveals gaps in current offerings including limited customization capabilities, poor mobile experience, and inadequate analytics functionality creating opportunity for differentiation. Unique value proposition emphasizes 60% faster implementation, 40% lower total cost of ownership, and 25% better customer satisfaction scores compared to leading competitors. Technology differentiation includes patented algorithms, AI-powered automation, and industry-specific configurations unavailable from alternative providers. Investment of $1.6 million funds competitive intelligence ($200K), product differentiation ($800K), marketing positioning ($350K), and sales enablement ($250K). Brand positioning targets innovative companies seeking competitive advantage through technology leadership and operational excellence. Messaging framework emphasizes speed, reliability, and measurable business outcomes supported by customer testimonials and third-party validation. Competitive battlecards equip sales teams with detailed comparisons, objection handling, and win/loss analysis improving competitive win rates by 35%. Success metrics include competitive displacement rate (target: 45% of competitive evaluations), brand differentiation scores (target: top 2 in analyst rankings), and premium pricing sustainability (target: 15% price premium maintenance). Market positioning reinforcement includes thought leadership content, industry speaking engagements, and strategic partnerships enhancing market credibility and competitive differentiation sustainability.

2. Strategic partnership ecosystem expands market reach and capabilities through alliances with technology vendors, implementation consultants, and industry specialists. Partnership portfolio includes 8 technology integrations, 12 implementation partners, and 15 industry resellers generating 35% of total revenue through channel partnerships. System integrator relationships with major consulting firms provide implementation expertise and customer credibility while expanding addressable market by 60% through partner customer bases. Technology partnerships enable seamless integrations with CRM systems, ERP platforms, and industry-specific applications creating comprehensive solution ecosystem. Investment totals $840K including partner enablement ($300K), integration development ($350K), and channel management ($190K). Partner program includes certification requirements, training modules, sales tools, and performance incentives ensuring quality delivery and customer satisfaction. Revenue sharing models average 25% partner margin with performance bonuses for customer satisfaction and retention achievements. Co-marketing initiatives include joint webinars, conference exhibits, and content creation amplifying market presence and lead generation by 150%. Success indicators encompass partner-generated revenue (target: 40% of total), partner satisfaction scores (target: 4.4/5.0), integration quality ratings (target: 4.7/5.0), and market coverage expansion (target: 25 additional markets). Partnership governance includes quarterly business reviews, annual partner summit, and continuous feedback mechanisms ensuring mutual success and strategic alignment with evolving market requirements and customer needs.

3. Future planning and strategic positioning initiative prepares organization for market evolution and emerging opportunities over five-year horizon. Market trend analysis identifies artificial intelligence adoption, regulatory compliance requirements, and industry consolidation as primary drivers shaping competitive landscape. Strategic scenario planning evaluates multiple futures including technology disruption, new competitor entry, and market maturation developing responsive strategies for each possibility. Investment in emerging technologies totals $1.2 million annually including AI research, blockchain exploration, and IoT integration capabilities positioning company for next-generation market requirements. Long-term product roadmap extends 36 months incorporating customer feedback, technology trends, and competitive intelligence ensuring continued market leadership and innovation. Organizational capability development includes talent acquisition in emerging skill areas, strategic partnership cultivation, and intellectual property protection through patent applications and trade secret management. Financial planning supports sustainable growth with 25% annual revenue increases, 30% EBITDA margins, and strategic acquisition budget of $5 million for complementary technologies or market expansion opportunities. Success framework includes innovation pipeline metrics, market share trends, customer retention in evolving market, and financial performance against growth targets. Continuous environmental scanning monitors competitive moves, regulatory changes, technology developments, and customer behavior shifts enabling proactive strategy adjustments and market positioning optimization. Strategic flexibility maintains multiple options for growth including organic expansion, acquisition opportunities, and partnership development ensuring adaptability to changing market conditions and emerging opportunities."""
    
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

Use the same detailed format as specified above, ensuring each Business Action is 250-350 words with specific quantitative data grounded in the provided content."""
    
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

            elif mode == "titles"
