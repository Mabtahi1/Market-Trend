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
            "max_tokens": 4096,  # Increased for longer, more detailed responses
            "temperature": 0.2,  # Slightly higher for more creativity while maintaining consistency
            "top_k": 250,
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
    """Generate enhanced business-focused prompt with context gathering"""
    
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
    
    return f"""You are a senior strategic market research analyst providing executive-level insights for business leaders. Your responses must be comprehensive, actionable, and business-focused.

QUESTION: {question}
CUSTOM KEYWORDS: {custom_keywords}

ANALYSIS CONTEXT:
{industry_context}
{time_context}

RESPONSE REQUIREMENTS:
- Each insight must be 150-250 words (substantial and detailed)
- Include specific business implications and opportunities
- Provide quantifiable metrics and trends when possible
- Focus on actionable strategies and competitive positioning
- Include customer behavior insights and market dynamics
- Mention potential risks and mitigation strategies

Respond using EXACTLY this format:

**KEYWORDS IDENTIFIED:**
[List exactly 5 highly relevant business keywords separated by commas]

**STRATEGIC MARKET ANALYSIS:**

**KEYWORD 1: [First Keyword]**
**STRATEGIC INSIGHTS:**
1. Market Opportunity Assessment: [Detailed market opportunity analysis with specific business implications]
2. Competitive Intelligence: [Competitive landscape analysis with positioning strategies]
3. Implementation Strategy: [Actionable steps for businesses to capitalize on this trend]
**BUSINESS ACTIONS:**
1. [Comprehensive 150-250 word insight covering market opportunity, specific strategies, potential ROI, implementation timeline, and success metrics for the first insight]
2. [Comprehensive 150-250 word insight covering competitive analysis, market positioning, differentiation strategies, and customer acquisition approaches for the second insight]
3. [Comprehensive 150-250 word insight covering tactical implementation, resource requirements, risk mitigation, and measurement frameworks for the third insight]

**KEYWORD 2: [Second Keyword]**
**STRATEGIC INSIGHTS:**
1. Revenue Impact Analysis: [Detailed revenue and growth potential analysis]
2. Customer Behavior Trends: [Deep dive into customer behavior changes and implications]
3. Operational Excellence: [Operational improvements and efficiency gains]
**BUSINESS ACTIONS:**
1. [Comprehensive 150-250 word insight covering revenue opportunities, market sizing, customer segments, and monetization strategies]
2. [Comprehensive 150-250 word insight covering customer behavior shifts, engagement strategies, and retention tactics]
3. [Comprehensive 150-250 word insight covering operational optimization, cost reduction, and efficiency improvements]

**KEYWORD 3: [Third Keyword]**
**STRATEGIC INSIGHTS:**
1. Innovation Opportunities: [Emerging innovation areas and R&D directions]
2. Partnership & Ecosystem: [Strategic partnership opportunities and ecosystem development]
3. Risk Management: [Potential risks and mitigation strategies]
**BUSINESS ACTIONS:**
1. [Comprehensive 150-250 word insight covering innovation opportunities, technology adoption, product development, and market disruption potential]
2. [Comprehensive 150-250 word insight covering strategic partnerships, ecosystem development, and collaborative opportunities]
3. [Comprehensive 150-250 word insight covering risk assessment, regulatory considerations, and mitigation strategies]

**KEYWORD 4: [Fourth Keyword]**
**STRATEGIC INSIGHTS:**
1. Market Expansion: [Geographic and demographic expansion opportunities]
2. Digital Transformation: [Technology adoption and digital strategy implications]
3. Sustainability & ESG: [Environmental and social responsibility considerations]
**BUSINESS ACTIONS:**
1. [Comprehensive 150-250 word insight covering market expansion strategies, target demographics, and geographic opportunities]
2. [Comprehensive 150-250 word insight covering digital transformation initiatives, technology stack, and automation opportunities]
3. [Comprehensive 150-250 word insight covering sustainability initiatives, ESG compliance, and brand positioning advantages]

**KEYWORD 5: [Fifth Keyword]**
**STRATEGIC INSIGHTS:**
1. Financial Performance: [Financial impact and investment considerations]
2. Talent & Workforce: [Human capital and workforce development needs]
3. Future Outlook: [Long-term strategic positioning and scenario planning]
**BUSINESS ACTIONS:**
1. [Comprehensive 150-250 word insight covering financial projections, investment requirements, ROI expectations, and budget allocation strategies]
2. [Comprehensive 150-250 word insight covering talent acquisition, skills development, organizational change, and workforce planning]
3. [Comprehensive 150-250 word insight covering future market scenarios, strategic positioning, and long-term competitive advantages]

CRITICAL: Each Business Action must be exactly 150-250 words and include:
- Specific business strategies and tactics
- Quantifiable metrics and KPIs where possible
- Implementation timelines and resource requirements
- Potential challenges and solutions
- Success measurement criteria
- Real-world examples or case studies when relevant"""

def get_business_context_prompt_with_content(question, custom_keywords="", content=""):
    """Enhanced prompt that includes content analysis"""
    
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
    max_content_length = 3000
    if len(content) > max_content_length:
        content = content[:max_content_length] + "... [Content truncated for analysis]"
    
    return f"""You are a senior strategic market research analyst providing executive-level insights for business leaders. Your responses must be comprehensive, actionable, and business-focused.

QUESTION: {question}
CUSTOM KEYWORDS: {custom_keywords}

CONTENT TO ANALYZE:
{content}

ANALYSIS CONTEXT:
{industry_context}
{time_context}

RESPONSE REQUIREMENTS:
- Each insight must be 150-250 words (substantial and detailed)
- Include specific business implications and opportunities based on the provided content
- Provide quantifiable metrics and trends when possible
- Focus on actionable strategies and competitive positioning
- Include customer behavior insights and market dynamics
- Mention potential risks and mitigation strategies
- Ground insights in the provided content while expanding with market context

Respond using EXACTLY this format:

**KEYWORDS IDENTIFIED:**
[List exactly 5 highly relevant business keywords separated by commas, derived from the content and question]

**STRATEGIC MARKET ANALYSIS:**

**KEYWORD 1: [First Keyword]**
**STRATEGIC INSIGHTS:**
1. Market Opportunity Assessment: [Detailed market opportunity analysis with specific business implications]
2. Competitive Intelligence: [Competitive landscape analysis with positioning strategies]
3. Implementation Strategy: [Actionable steps for businesses to capitalize on this trend]
**BUSINESS ACTIONS:**
1. [Comprehensive 150-250 word insight covering market opportunity, specific strategies, potential ROI, implementation timeline, and success metrics for the first insight]
2. [Comprehensive 150-250 word insight covering competitive analysis, market positioning, differentiation strategies, and customer acquisition approaches for the second insight]
3. [Comprehensive 150-250 word insight covering tactical implementation, resource requirements, risk mitigation, and measurement frameworks for the third insight]

**KEYWORD 2: [Second Keyword]**
**STRATEGIC INSIGHTS:**
1. Revenue Impact Analysis: [Detailed revenue and growth potential analysis]
2. Customer Behavior Trends: [Deep dive into customer behavior changes and implications]
3. Operational Excellence: [Operational improvements and efficiency gains]
**BUSINESS ACTIONS:**
1. [Comprehensive 150-250 word insight covering revenue opportunities, market sizing, customer segments, and monetization strategies]
2. [Comprehensive 150-250 word insight covering customer behavior shifts, engagement strategies, and retention tactics]
3. [Comprehensive 150-250 word insight covering operational optimization, cost reduction, and efficiency improvements]

**KEYWORD 3: [Third Keyword]**
**STRATEGIC INSIGHTS:**
1. Innovation Opportunities: [Emerging innovation areas and R&D directions]
2. Partnership & Ecosystem: [Strategic partnership opportunities and ecosystem development]
3. Risk Management: [Potential risks and mitigation strategies]
**BUSINESS ACTIONS:**
1. [Comprehensive 150-250 word insight covering innovation opportunities, technology adoption, product development, and market disruption potential]
2. [Comprehensive 150-250 word insight covering strategic partnerships, ecosystem development, and collaborative opportunities]
3. [Comprehensive 150-250 word insight covering risk assessment, regulatory considerations, and mitigation strategies]

**KEYWORD 4: [Fourth Keyword]**
**STRATEGIC INSIGHTS:**
1. Market Expansion: [Geographic and demographic expansion opportunities]
2. Digital Transformation: [Technology adoption and digital strategy implications]
3. Sustainability & ESG: [Environmental and social responsibility considerations]
**BUSINESS ACTIONS:**
1. [Comprehensive 150-250 word insight covering market expansion strategies, target demographics, and geographic opportunities]
2. [Comprehensive 150-250 word insight covering digital transformation initiatives, technology stack, and automation opportunities]
3. [Comprehensive 150-250 word insight covering sustainability initiatives, ESG compliance, and brand positioning advantages]

**KEYWORD 5: [Fifth Keyword]**
**STRATEGIC INSIGHTS:**
1. Financial Performance: [Financial impact and investment considerations]
2. Talent & Workforce: [Human capital and workforce development needs]
3. Future Outlook: [Long-term strategic positioning and scenario planning]
**BUSINESS ACTIONS:**
1. [Comprehensive 150-250 word insight covering financial projections, investment requirements, ROI expectations, and budget allocation strategies]
2. [Comprehensive 150-250 word insight covering talent acquisition, skills development, organizational change, and workforce planning]
3. [Comprehensive 150-250 word insight covering future market scenarios, strategic positioning, and long-term competitive advantages]

CRITICAL: Each Business Action must be exactly
