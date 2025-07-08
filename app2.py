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
            "max_tokens": 2000,  # Much smaller for faster processing
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
    """Simple, fast business prompt"""
    
    prompt = f"""You are a business analyst. Provide strategic insights for this question.

Question: {question}
Keywords: {custom_keywords}

Please respond in exactly this format:

**KEYWORDS IDENTIFIED:**
Market Analysis, Growth Strategy, Customer Experience, Digital Innovation, Competitive Advantage

**STRATEGIC ANALYSIS:**

**KEYWORD 1: Market Analysis**
**INSIGHTS:**
1. Market Opportunity: Current market size and growth potential
2. Target Customers: Key customer segments and their needs
3. Revenue Potential: Financial projections and business model
**ACTIONS:**
1. The market opportunity represents a significant $2.5 billion addressable market growing at 15% annually. Primary customer segments include enterprise clients (60% of market, $120K average contracts) and SMBs (40% of market, $25K average deals). Implementation requires $1.8M investment over 12 months including technology development ($1M), sales team ($500K), and marketing ($300K). Revenue projections show $1.5M in year one, scaling to $8M by year three with 22% EBITDA margins. Key success metrics include 5% market penetration within 24 months, $8K customer acquisition cost, and $180K customer lifetime value.

2. Competitive landscape analysis reveals three major players controlling 45% of total market share, creating opportunities for innovative disruption. Customer acquisition strategy combines digital marketing campaigns targeting decision-makers, strategic partnerships with industry associations, and direct sales approach. Brand positioning emphasizes speed, reliability, and cost-effectiveness with case studies demonstrating 40% faster implementation than competitors. Success metrics include 15% brand awareness within 12 months, 20% shorter sales cycles, and 4.4/5.0 customer satisfaction scores.

3. Implementation roadmap requires cross-functional team of 18 professionals including engineers, sales specialists, and customer success managers. Technology infrastructure investment includes cloud platform development, security certifications, and integration capabilities. Operational processes encompass automated customer onboarding, AI-powered support systems, and performance analytics. Key milestones include beta testing with pilot customers, limited market release, and full product launch within 12-month timeline.

**KEYWORD 2: Growth Strategy**
**INSIGHTS:**
1. Revenue Streams: Multiple income sources and monetization
2. Market Expansion: Geographic and demographic growth
3. Customer Retention: Loyalty and lifetime value optimization
**ACTIONS:**
1. Revenue diversification strategy targets subscription model ($5M annual recurring revenue), professional services ($2M), and marketplace transactions ($1M) generating combined $8M by year three. Subscription pricing ranges from $1,500/month basic to $8,000/month enterprise tiers. Professional services offer implementation consulting and customization at $200/hour average billing rate. Implementation requires dedicated teams with $800K investment in personnel and technology platforms.

2. Market expansion initiative focuses on geographic growth targeting North America ($1.2B market), Europe ($800M), and Asia-Pacific ($600M). Customer expansion includes upselling existing accounts with average 25% annual contract value increases and cross-selling complementary solutions. Investment totals $1.2M including international team establishment, localization, and regulatory compliance.

3. Customer retention program implements success management framework reducing churn from 15% to 8% while increasing lifetime value by 35%. Retention initiatives include quarterly business reviews, proactive support, and loyalty rewards. Investment of $400K includes customer success team expansion and retention technology platform with predictive analytics identifying at-risk accounts.

**KEYWORD 3: Customer Experience**
**INSIGHTS:**
1. User Journey: Touchpoint optimization and satisfaction
2. Service Quality: Support and success measurement
3. Engagement: Community building and advocacy programs
**ACTIONS:**
1. Customer experience enhancement delivers 30% satisfaction improvement through journey optimization, personalized interactions, and proactive support. Investment of $600K includes experience platform, training programs, and measurement systems. Success metrics include Net Promoter Score improvement from 35 to 55, customer effort score reduction of 35%, and support resolution time decrease of 40%.

2. Service quality initiative implements 24/7 support availability, comprehensive knowledge base, and AI-powered assistance achieving 75% first-contact resolution rates. Support technology investment of $300K includes chatbot implementation, ticketing system upgrade, and performance monitoring tools. Quality targets include 99.5% uptime, 2-hour response times, and 4.5/5.0 satisfaction ratings.

3. Community building program creates user ecosystem with online platform hosting discussions, best practices sharing, and peer support. Annual user conference and quarterly webinars strengthen relationships while providing product feedback. Investment of $250K includes community platform, content creation, and event management generating enhanced customer loyalty and advocacy.

**KEYWORD 4: Digital Innovation**
**INSIGHTS:**
1. Technology Trends: Emerging capabilities and adoption
2. Automation: Process optimization and efficiency gains
3. Data Analytics: Intelligence and decision-making enhancement
**ACTIONS:**
1. Technology transformation includes AI integration, mobile optimization, and cloud-native architecture delivering 40% performance improvement and 50% cost reduction. Investment of $1.2M covers platform modernization, AI capabilities, and mobile development. Success metrics include 99.9% system availability, 2-second response times, and 25% productivity improvement.

2. Automation implementation targets operational processes achieving 60% manual effort reduction through robotic process automation, workflow optimization, and intelligent routing. Investment of $500K includes automation software, process reengineering, and employee training. Automation covers customer onboarding (80% automated), support ticket management (70% automated), and reporting (90% automated).

3. Data analytics platform processes customer interactions, system performance, and market indicators generating actionable insights for business optimization. Machine learning algorithms predict customer behavior, identify upselling opportunities, and optimize pricing strategies. Investment of $400K includes analytics platform, data engineering, and visualization tools enabling data-driven decision making.

**KEYWORD 5: Competitive Advantage**
**INSIGHTS:**
1. Differentiation: Unique value proposition development
2. Market Position: Industry leadership and recognition
3. Strategic Planning: Future positioning and adaptation
**ACTIONS:**
1. Competitive differentiation through proprietary technology, superior customer outcomes, and innovative business model capturing 12% market share within three years. Unique value proposition emphasizes 50% faster implementation, 30% lower total cost, and 20% better performance versus alternatives. Investment of $800K funds product differentiation, competitive intelligence, and market positioning initiatives.

2. Market leadership positioning through thought leadership, industry partnerships, and analyst recognition. Brand building includes content marketing, speaking engagements, and strategic partnerships enhancing credibility and market presence. Investment of $400K covers marketing initiatives, partnership development, and analyst relations programs establishing industry authority and customer trust.

3. Strategic planning incorporates market trend analysis, competitive monitoring, and scenario planning for sustained advantage. Long-term roadmap includes technology innovation, market expansion, and acquisition opportunities. Investment in research and development totals $600K annually supporting innovation pipeline and competitive positioning maintenance through continuous improvement and adaptation.

Provide specific numbers, percentages, dollar amounts, and timeframes in every action item."""
    
    return prompt

def get_business_context_prompt_with_content(question, custom_keywords="", content=""):
    """Simple prompt with content"""
    
    max_content_length = 800  # Very short to prevent timeout
    if len(content) > max_content_length:
        content = content[:max_content_length] + "..."
    
    prompt = f"""Analyze this content and provide business insights.

Question: {question}
Keywords: {custom_keywords}
Content: {content}

Use the same format as above with 5 keywords and detailed action items including specific numbers and dollar amounts."""
    
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

        logger.info(f"Parsed {len(keywords)} keywords: {keywords}")
        logger.info(f"Structured insights for {len(structured_insights)} keywords")
        
        return {
            "keywords": keywords,
            "structured_insights": structured_insights
        }

    except Exception as e:
        logger.error(f"Error parsing response: {str(e)}")
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
            question="Analyze this document for business insights",
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
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        
        text = soup.get_text()
        text = ' '.join(text.split())
        
        if len(text) > 2000:
            text = text[:2000] + "..."
        
        analysis_result = summarize_trends(
            text=text,
            question=question or "Analyze this web content",
            keyword=keyword,
            return_format="dict"
        )
        
        analysis_result["url"] = url
        return analysis_result
        
    except ImportError:
        return {
            "error": "URL analysis requires 'requests' and 'beautifulsoup4'",
            "keywords": [],
            "insights": {},
            "full_response": "",
            "url": url
        }
    except Exception as e:
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
            
            # Word count scoring
            if 120 <= word_count <= 200:
                score += 80
            elif 80 <= word_count < 120:
                score += 60
            elif word_count >= 200:
                score += 70
            else:
                score += 30
            
            # Content scoring
            if any(term in insight_lower for term in ['$', '%', 'million', 'billion', 'revenue', 'roi']):
                score += 15
            if any(term in insight_lower for term in ['market', 'customer', 'competitive', 'growth']):
                score += 10
            if any(term in insight_lower for term in ['strategy', 'implementation', 'timeline']):
                score += 5
            
            total_score += min(score, 100)
            total_insights += 1
    
    return (total_score / total_insights) if total_insights > 0 else 0

def parse_analysis_response(response):
    return parse_enhanced_analysis_response(response)

def test_functions():
    print("✅ Minimal app2.py loaded successfully")
    print("✅ Optimized for fast processing - no timeouts")

if __name__ == "__main__":
    test_functions()
