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
            "max_tokens": 3000,  # Reduced for faster processing
            "temperature": 0.2,
            "top_k": 200,
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
    """Generate concise but comprehensive business prompt"""
    
    prompt = f"""You are a strategic business analyst. Provide detailed analysis with specific data and actionable insights.

ANALYSIS REQUEST:
Question: {question}
Focus Keywords: {custom_keywords}

REQUIREMENTS:
- Each Business Action must be 180-250 words with specific numbers
- Include dollar amounts, percentages, timeframes, ROI data
- Provide market sizes, growth rates, implementation costs
- Focus on actionable strategies with measurable outcomes

FORMAT (use exactly):

**KEYWORDS IDENTIFIED:**
[List 5 business keywords separated by commas]

**STRATEGIC ANALYSIS:**

**KEYWORD 1: [Name]**
**KEY INSIGHTS:**
1. Market Opportunity: [Market size and growth analysis]
2. Competitive Position: [Competition and differentiation strategy]
3. Implementation: [Action plan with timeline and resources]
**BUSINESS ACTIONS:**
1. [200+ words] Market opportunity worth $X billion growing at Y% annually. Target customer segments include enterprises (Z% of market, $A average deal) and SMBs (B% of market, $C average deal). Implementation requires $D investment over E months including technology ($F), sales team ($G), marketing ($H). Revenue projections: Year 1: $I, Year 2: $J, Year 3: $K with L% EBITDA margins. Key metrics: M% market penetration in N months, $O customer acquisition cost, $P lifetime value, Q% quarterly growth. Competitive advantage through R technology delivering S% better performance than alternatives. Risk mitigation includes T customer diversification and U strategic partnerships ensuring scalable delivery.

2. [200+ words] Competitive landscape shows V major players controlling W% market share. Primary competitors: Company A ($X revenue, Y% share), Company B ($Z revenue, A% share). Differentiation strategy targets B segment with C% cost reduction through D automation. Customer acquisition: E digital marketing, F partnerships, G direct sales team. Brand positioning emphasizes H benefits with I implementation time vs J industry average. Success metrics: K% brand awareness in L months, M% shorter sales cycles, N customer satisfaction score, O% market share in P years. Pricing strategy: Q% premium justified by R superior outcomes and S faster deployment.

3. [200+ words] Implementation roadmap requires T-person team: U engineers, V sales, W marketing, X customer success. Technology investment: $Y total including platform ($Z), security ($A), integrations ($B). Operational processes: C% faster onboarding, D% first-contact resolution, E predictive analytics. Milestones: F beta testing (months G-H), I limited release (month J), K full launch (month L). Quality targets: M% uptime, N response times, O security compliance. Risk management: P development approach, Q pricing flexibility, R retention programs addressing S challenges.

**KEYWORD 2: [Name]**
**KEY INSIGHTS:**
1. Revenue Impact: [Financial analysis and growth projections]
2. Customer Behavior: [User patterns and engagement strategies]
3. Operations: [Process optimization and efficiency gains]
**BUSINESS ACTIONS:**
[Continue same detailed format for remaining keywords...]

**KEYWORD 3: [Name]**
**KEY INSIGHTS:**
1. Innovation: [Technology trends and development opportunities]
2. Partnerships: [Alliance strategies and ecosystem development]
3. Risk Management: [Threat assessment and mitigation strategies]
**BUSINESS ACTIONS:**
[Continue same format...]

**KEYWORD 4: [Name]**
**KEY INSIGHTS:**
1. Market Expansion: [Geographic and demographic growth]
2. Digital Strategy: [Technology adoption and optimization]
3. Sustainability: [ESG considerations and green opportunities]
**BUSINESS ACTIONS:**
[Continue same format...]

**KEYWORD 5: [Name]**
**KEY INSIGHTS:**
1. Financial Performance: [Investment strategy and planning]
2. Talent Strategy: [Human capital and organizational development]
3. Future Planning: [Long-term positioning and scenario planning]
**BUSINESS ACTIONS:**
[Continue same format...]

CRITICAL: Every Business Action must include specific numbers, dollar amounts, percentages, timeframes, and measurable KPIs."""
    
    return prompt

def get_business_context_prompt_with_content(question, custom_keywords="", content=""):
    """Enhanced prompt that includes content analysis"""
    
    max_content_length = 1500  # Reduced to prevent timeout
    if len(content) > max_content_length:
        content = content[:max_content_length] + "... [Content truncated]"
    
    prompt = f"""Analyze the provided content and deliver strategic business insights.

QUESTION: {question}
KEYWORDS: {custom_keywords}

CONTENT:
{content}

Provide detailed analysis using the same format as specified above. Each Business Action must be 180-250 words with specific data grounded in the content."""
    
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

            elif line.startswith("**KEY INSIGHTS:**"):
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
        
        if len(text) > 3000:  # Reduced to prevent timeout
            text = text[:3000] + "..."
        
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
            
            # Word count scoring (prefer 180-250 words)
            if 180 <= word_count <= 250:
                score += 70
            elif 150 <= word_count < 180:
                score += 55
            elif 120 <= word_count < 150:
                score += 40
            elif word_count >= 250:
                score += 60
            else:
                score += 20
            
            # Financial terms
            financial_terms = ['roi', 'revenue', 'profit', 'cost', 'investment', 'budget', 'margin', '$', '%', 'million', 'billion']
            financial_count = sum(1 for term in financial_terms if term in insight_lower)
            score += min(financial_count * 4, 25)
            
            # Market terms
            market_terms = ['market', 'competitive', 'competitor', 'customer', 'growth', 'share', 'segment', 'analysis']
            market_count = sum(1 for term in market_terms if term in insight_lower)
            score += min(market_count * 2, 15)
            
            # Strategy terms
            strategy_terms = ['strategy', 'implementation', 'approach', 'timeline', 'roadmap', 'metrics', 'kpi']
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
    print("✅ Optimized for faster processing")
    print("✅ Ready for Streamlit integration")

if __name__ == "__main__":
    test_functions()
