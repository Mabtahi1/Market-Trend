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
    """Enhanced version that uses the same format as analyze_question
    
    Args:
        text: Text content to analyze
        question: Analysis question
        keyword: Keywords to focus on
        return_format: "dict" for new format, "string" for legacy format
    """
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
            # For legacy compatibility, return the full response as string
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
    """Enhanced version that returns structured analysis instead of just text
    
    Args:
        uploaded_file: File to process
        return_format: "dict" for new format, "string" for legacy format
    """
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
            # For legacy compatibility, return just the extracted text
            return text
        
        # For new format, analyze the extracted text
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
    """New function to analyze URL content with enhanced format"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # Fetch the URL content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract text content
        for script in soup(["script", "style"]):
            script.extract()
        
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Truncate if too long
        if len(text) > 5000:
            text = text[:5000] + "..."
        
        # Analyze the extracted content
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

        # Create a hash of the prompt to cache responses
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        
        # Check cache first
        if prompt_hash in _response_cache:
            logger.info("Using cached response")
            return _response_cache[prompt_hash]

        bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
        
        # Enhanced parameters for better, more detailed responses
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4096,
            "temperature": 0.1,  # Lower temperature for more consistent format following
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
        
        # Cache the response
        _response_cache[prompt_hash] = response_text
        
        return response_text

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return f"Error decoding Claude response: {str(e)}"
    except Exception as e:
        logger.error(f"Error calling Claude: {str(e)}")
        return f"Error calling Claude: {str(e)}"

def get_business_context_prompt(question, custom_keywords=""):
    """Generate enhanced business-focused prompt with stricter formatting requirements"""
    
    # Detect question type and customize approach
    question_lower = question.lower()
    
    # Industry-specific prompts
    industry_context = ""
    if any(word in question_lower for word in ['retail', 'ecommerce', 'shopping', 'consumer']):
        industry_context = "Focus on retail/ecommerce implications, customer behavior, and sales impact."
    elif any(word in question_lower for word in ['tech', 'ai', 'digital', 'software']):
        industry_context = "Focus on technology adoption, digital transformation, and innovation opportunities."
    elif any(word in question_lower for word in ['healthcare', 'medical', 'pharma']):
        industry_context = "Focus on healthcare implications, regulatory considerations, and patient outcomes."
    elif any(word in question_lower for word in ['finance', 'fintech', 'banking']):
        industry_context = "Focus on financial services impact, regulatory changes, and market dynamics."
    
    # Time-sensitive context
    time_context = "Focus on 2024-2025 trends and emerging opportunities."
    if any(word in question_lower for word in ['2024', '2025', 'future', 'upcoming']):
        time_context = "Emphasize forward-looking insights and predictive analysis."
    
    prompt = f"""You are a senior strategic market research analyst providing executive-level insights for business leaders. You MUST follow the exact format specified below.

QUESTION: {question}
CUSTOM KEYWORDS: {custom_keywords}

ANALYSIS CONTEXT:
{industry_context}
{time_context}

CRITICAL FORMATTING REQUIREMENTS:
- Each Business Action MUST be exactly 200-300 words
- Include specific dollar amounts, percentages, and timeframes when possible
- Mention ROI, revenue growth, market share, implementation costs
- Include competitive analysis and customer behavior insights
- Provide measurable KPIs and success metrics
- Reference real market data and trends

Respond using EXACTLY this format with NO deviations:

**KEYWORDS IDENTIFIED:**
[List exactly 5 business keywords separated by commas]

**STRATEGIC MARKET ANALYSIS:**

**KEYWORD 1: [First Keyword]**
**STRATEGIC INSIGHTS:**
1. Market Opportunity Assessment: [Market size, growth rate, and revenue potential]
2. Competitive Intelligence: [Key players, market positioning, and competitive advantages]  
3. Implementation Strategy: [Step-by-step approach with timeline and resources]
**BUSINESS ACTIONS:**
1. [EXACTLY 200-300 words] Market opportunity analysis including specific market size data (e.g., "$X billion market growing at Y% annually"), target customer segments with demographic details, revenue projections with realistic timelines, implementation costs and ROI calculations, competitive positioning strategies, customer acquisition metrics, and risk mitigation approaches with contingency planning.

2. [EXACTLY 200-300 words] Competitive intelligence covering detailed competitor analysis with market share percentages, differentiation strategies that highlight unique value propositions, pricing strategies with specific price points and models, customer retention tactics with measurable outcomes, brand positioning approaches, partnership opportunities, and strategic recommendations for market penetration with timeline.

3. [EXACTLY 200-300 words] Implementation strategy detailing tactical execution plan with specific milestones, resource requirements including budget allocations and team structure, technology stack recommendations, operational processes and workflows, measurement frameworks with specific KPIs and metrics, success criteria with quantifiable targets, risk assessment with mitigation strategies, and expected outcomes with realistic timelines.

**KEYWORD 2: [Second Keyword]**
**STRATEGIC INSIGHTS:**
1. Revenue Impact Analysis: [Financial projections, profit margins, and growth opportunities]
2. Customer Behavior Trends: [Consumer patterns, preferences, and engagement strategies]
3. Operational Excellence: [Process improvements, cost reductions, and efficiency gains]
**BUSINESS ACTIONS:**
1. [EXACTLY 200-300 words] Revenue impact analysis including detailed financial projections with quarterly breakdowns, profit margin calculations with cost structures, pricing optimization strategies, customer lifetime value analysis, market penetration rates, sales funnel optimization, revenue diversification opportunities, and financial risk assessment with scenario planning.

2. [EXACTLY 200-300 words] Customer behavior analysis covering demographic and psychographic insights, purchasing patterns with seasonal trends, digital engagement preferences, customer journey mapping, retention strategies with specific tactics, loyalty program recommendations, personalization approaches, and customer satisfaction metrics with improvement strategies.

3. [EXACTLY 200-300 words] Operational excellence roadmap including process automation opportunities, cost reduction initiatives with specific savings targets, supply chain optimization, quality improvement measures, technology integration strategies, workforce development plans, performance measurement systems, and scalability considerations with growth planning.

**KEYWORD 3: [Third Keyword]**
**STRATEGIC INSIGHTS:**
1. Innovation Opportunities: [R&D directions, technology trends, and product development]
2. Partnership & Ecosystem: [Strategic alliances, vendor relationships, and collaborations]
3. Risk Management: [Market risks, regulatory compliance, and mitigation strategies]
**BUSINESS ACTIONS:**
1. [EXACTLY 200-300 words] Innovation strategy encompassing emerging technology adoption, R&D investment priorities with budget allocations, product development roadmaps, intellectual property strategies, market disruption opportunities, innovation partnerships, technology transfer possibilities, and competitive innovation analysis with strategic responses.

2. [EXACTLY 200-300 words] Partnership ecosystem development including strategic alliance identification, vendor evaluation criteria, collaboration frameworks, partnership models with revenue sharing, ecosystem mapping, integration strategies, relationship management approaches, and partnership performance metrics with optimization strategies.

3. [EXACTLY 200-300 words] Risk management framework covering market volatility assessment, regulatory compliance requirements, operational risk mitigation, financial risk controls, cybersecurity considerations, business continuity planning, insurance strategies, and crisis management protocols with response procedures.

**KEYWORD 4: [Fourth Keyword]**
**STRATEGIC INSIGHTS:**
1. Market Expansion: [Geographic opportunities, demographic targeting, and growth strategies]
2. Digital Transformation: [Technology adoption, digital capabilities, and automation]
3. Sustainability & ESG: [Environmental impact, social responsibility, and governance]
**BUSINESS ACTIONS:**
1. [EXACTLY 200-300 words] Market expansion strategy including geographic market analysis with specific countries/regions, demographic targeting with detailed customer profiles, market entry strategies with timeline and investment requirements, localization considerations, regulatory compliance requirements, competitive landscape analysis, distribution channel development, and success metrics with tracking methodologies.

2. [EXACTLY 200-300 words] Digital transformation roadmap covering technology assessment with current state analysis, digital capability development, automation opportunities with ROI calculations, data analytics implementation, cloud migration strategies, cybersecurity enhancements, digital customer experience improvements, and change management approaches with training programs.

3. [EXACTLY 200-300 words] Sustainability and ESG strategy including environmental impact assessment, sustainable business practices implementation, ESG reporting requirements, stakeholder engagement strategies, regulatory compliance considerations, sustainable supply chain development, social responsibility initiatives, and ESG performance metrics with improvement targets.

**KEYWORD 5: [Fifth Keyword]**
**STRATEGIC INSIGHTS:**
1. Financial Performance: [Investment requirements, funding strategies, and financial planning]
2. Talent & Workforce: [Human capital development, skills requirements, and culture]
3. Future Outlook: [Long-term strategic positioning and scenario planning]
**BUSINESS ACTIONS:**
1. [EXACTLY 200-300 words] Financial performance optimization including investment requirement analysis with detailed budget breakdowns, funding strategy recommendations, cash flow projections with quarterly forecasts, profit optimization initiatives, cost management strategies, financial controls implementation, investor relations approaches, and financial performance metrics with benchmarking analysis.

2. [EXACTLY 200-300 words] Talent and workforce strategy covering skills gap analysis, recruitment strategies with specific talent acquisition plans, employee development programs, compensation and benefits optimization, performance management systems, organizational culture development, succession planning, and workforce analytics with productivity measurements.

3. [EXACTLY 200-300 words] Future outlook and strategic positioning including scenario planning with multiple market conditions, long-term strategic objectives, competitive positioning strategies, market trend analysis, technology roadmap planning, innovation pipeline development, strategic option evaluation, and adaptive strategy frameworks with contingency planning.

ABSOLUTE REQUIREMENTS:
- Every Business Action must be 200-300 words minimum
- Include specific numbers, percentages, dollar amounts
- Mention ROI, market share, growth rates, timeframes
- Reference customer segments, competitive analysis, implementation costs
- Provide measurable KPIs and success criteria"""
    
    return prompt

def get_business_context_prompt_with_content(question, custom_keywords="", content=""):
    """Enhanced prompt that includes content analysis with stricter formatting"""
    
    # Detect question type and customize approach
    question_lower = question.lower()
    
    # Industry-specific prompts
    industry_context = ""
    if any(word in question_lower for word in ['retail', 'ecommerce', 'shopping', 'consumer']):
        industry_context = "Focus on retail/ecommerce implications, customer behavior, and sales impact."
    elif any(word in question_lower for word in ['tech', 'ai', 'digital', 'software']):
        industry_context = "Focus on technology adoption, digital transformation, and innovation opportunities."
    elif any(word in question_lower for word in ['healthcare', 'medical', 'pharma']):
        industry_context = "Focus on healthcare implications, regulatory considerations, and patient outcomes."
    elif any(word in question_lower for word in ['finance', 'fintech', 'banking']):
        industry_context = "Focus on financial services impact, regulatory changes, and market dynamics."
    
    # Time-sensitive context
    time_context = "Focus on 2024-2025 trends and emerging opportunities."
    if any(word in question_lower for word in ['2024', '2025', 'future', 'upcoming']):
        time_context = "Emphasize forward-looking insights and predictive analysis."
    
    # Truncate content if too long to fit in prompt
    max_content_length = 2500
    if len(content) > max_content_length:
        content = content[:max_content_length] + "... [Content truncated for analysis]"
    
    prompt = f"""You are a senior strategic market research analyst providing executive-level insights for business leaders. You MUST follow the exact format specified below.

QUESTION: {question}
CUSTOM KEYWORDS: {custom_keywords}

CONTENT TO ANALYZE:
{content}

ANALYSIS CONTEXT:
{industry_context}
{time_context}

CRITICAL FORMATTING REQUIREMENTS:
- Each Business Action MUST be exactly 200-300 words
- Ground insights in the provided content while expanding with market context
- Include specific dollar amounts, percentages, and timeframes when possible
- Mention ROI, revenue growth, market share, implementation costs
- Include competitive analysis and customer behavior insights
- Provide measurable KPIs and success metrics
- Reference real market data and trends

[Use the same exact format as the previous prompt with 5 keywords, strategic insights, and 200-300 word business actions for each keyword]"""
    
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

        # Create a unique identifier for this analysis
        analysis_id = hashlib.md5(f"{question}_{custom_keywords}".encode()).hexdigest()[:8]
        
        # Use the enhanced business-focused prompt
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

            # Extract keywords
            if line.startswith("**KEYWORDS IDENTIFIED:**"):
                mode = "keywords"
                continue

            elif mode == "keywords" and not line.startswith("**"):
                # Clean up keywords - remove brackets and extra formatting
                keyword_line = line.replace("[", "").replace("]", "")
                keywords = [k.strip() for k in keyword_line.split(",") if k.strip()]
                mode = None
                continue

            # Extract keyword sections
            elif line.startswith("**KEYWORD") and ":" in line:
                # Save previous keyword data if exists
                if current_keyword and (current_titles or current_insights):
                    structured_insights[current_keyword] = {
                        "titles": current_titles,
                        "insights": current_insights
                    }
                
                # Extract keyword name more reliably
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

            # Extract content
            elif mode == "titles" and current_keyword:
                if line and (line[0].isdigit() or line.startswith("- ")):
                    # Handle both numbered and bulleted lists
                    if line[0].isdigit() and "." in line:
                        content = line.split(".", 1)[1].strip()
                    elif line.startswith("- "):
                        content = line[2:].strip()
                    else:
                        content = line.strip()
                    
                    # Remove any remaining formatting
                    content = content.replace("[", "").replace("]", "").strip()
                    
                    if content:
                        current_titles.append(content)

            elif mode == "insights" and current_keyword:
                if line and (line[0].isdigit() or line.startswith("- ")):
                    # Start of a new insight
                    if line[0].isdigit() and "." in line:
                        content = line.split(".", 1)[1].strip()
                    elif line.startswith("- "):
                        content = line[2:].strip()
                    else:
                        content = line.strip()
                    
                    # Remove any remaining formatting
                    content = content.replace("[", "").replace("]", "").strip()
                    
                    if content:
                        current_insights.append(content)
                elif current_insights and not line.startswith("**"):
                    # Continue the current insight (multi-line)
                    current_insights[-1] += " " + line.strip()

        # Don't forget the last keyword
        if current_keyword and (current_titles or current_insights):
            structured_insights[current_keyword] = {
                "titles": current_titles,
                "insights": current_insights
            }

        # Validate that we have the expected structure
        logger.info(f"Parsed {len(keywords)} keywords: {keywords}")
        logger.info(f"Structured insights for {len(structured_insights)} keywords")
        
        # Log insight lengths for debugging
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
                score += 50  # Higher base score for proper length
            elif 150 <= word_count < 200:
                score += 35
            elif 100 <= word_count < 150:
                score += 25
            elif word_count >= 300:
                score += 40  # Still good if longer
            else:
                score += 10  # Low score for short insights
            
            # Financial and business metrics (higher weight)
            financial_terms = ['roi', 'revenue', 'profit', 'cost', 'investment', 'budget', 'margin', 'pricing', 'financial', 'earnings']
            if any(term in insight_lower for term in financial_terms):
                score += 15
            
            # Market and competitive analysis
            market_terms = ['market', 'competitive', 'competitor', 'market share', 'positioning', 'segment', 'customer']
            if any(term in insight_lower for term in market_terms):
                score += 12
            
            # Implementation and strategy content
            strategy_terms = ['strategy', 'implementation', 'approach', 'framework', 'methodology', 'roadmap', 'planning']
            if any(term in insight_lower for term in strategy_terms):
                score += 10
            
            # Quantifiable metrics and numbers
            number_indicators = ['%', '$', 'million', 'billion', 'growth', 'increase', 'decrease', 'quarter', 'annual']
            if any(indicator in insight_lower for indicator in number_indicators):
                score += 12
            
            # KPIs and measurement
            kpi_terms = ['kpi', 'metric', 'measurement', 'tracking', 'performance', 'benchmark', 'target', 'goal']
            if any(term in insight_lower for term in kpi_terms):
                score += 8
            
            # Timeline and urgency
            time_terms = ['timeline', 'month', 'quarter', 'year', 'phase', 'milestone', 'deadline', 'schedule']
            if any(term in insight_lower for term in time_terms):
                score += 8
            
            # Risk and opportunity analysis
            risk_terms = ['risk', 'opportunity', 'threat', 'challenge', 'mitigation', 'contingency']
            if any(term in insight_lower for term in risk_terms):
                score += 8
            
            total_score += min(score, 100)  # Cap individual insight score at 100
            total_insights += 1
    
    final_score = (total_score / total_insights) if total_insights > 0 else 0
    return min(final_score, 100)  # Cap final score at 100

def test_functions():
    print("✅ Enhanced summarize_trends function loaded")
    print("✅ Enhanced analyze_question function loaded")
    print("✅ Enhanced extract_text_from_file function loaded")
    print("✅ Enhanced claude_messages function loaded")
    print("✅ safe_get_insight function loaded")
    print("✅ clear_cache function loaded")
    print("✅ IMPROVED get_insight_quality_score function loaded")
    print("✅ analyze_url_content function loaded")

    # Test both question and text analysis
    test_question = "What are the key market opportunities in sustainable packaging for food companies in 2024?"
    test_text = "The global sustainable packaging market is experiencing unprecedented growth, driven by consumer demand for eco-friendly solutions and regulatory pressure on food companies to reduce plastic waste. Major brands are investing heavily in biodegradable materials and circular economy initiatives."
    
    print(f"\n🔍 Testing enhanced question analysis: {test_question}")
    result1 = analyze_question(test_question)
    
    print(f"\n📄 Testing enhanced text analysis")
    result2 = summarize_trends(text=test_text, question="What business opportunities exist in this market?")

    for i, result in enumerate([result1, result2], 1
