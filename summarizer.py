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

def summarize_trends(text=None, question=None, keyword=None):
    try:
        if not any([text, question, keyword]):
            return "Error: At least one parameter (text, question, or keyword) must be provided"

        prompt_parts = []
        if question:
            prompt_parts.append(f"User Question: {question}\n")
        if keyword:
            prompt_parts.append(f"User Keyword: {keyword}\n")
        if text:
            prompt_parts.append(f"Content to Analyze:\n{text}\n")

        prompt_parts.append("""
From the above content:
1. Extract hot keywords.
2. Provide clear and concise actionable insights.
Return the results in a readable format with two sections: Keywords and Insights.
""")
        prompt = "\n".join(prompt_parts)

        response = claude_messages(prompt)
        return response

    except Exception as e:
        logger.error(f"Error in summarize_trends: {str(e)}")
        return f"Error summarizing content: {str(e)}"

def extract_text_from_file(uploaded_file):
    tmp_path = None
    try:
        if not uploaded_file:
            return "Error: No file provided"

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        text = textract.process(tmp_path).decode("utf-8")
        return text

    except Exception as e:
        logger.error(f"Error extracting text from file: {str(e)}")
        return f"Error extracting text: {str(e)}"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as cleanup_error:
                logger.warning(f"Could not clean up temp file: {cleanup_error}")

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
    """Calculate a quality score for the insights"""
    if not insights_data:
        return 0
    
    total_score = 0
    total_insights = 0
    
    for keyword, data in insights_data.items():
        insights = data.get("insights", [])
        for insight in insights:
            score = 0
            length = len(insight)
            
            # Length scoring (prefer 150-250 words)
            if 150 <= length <= 250:
                score += 40
            elif 100 <= length < 150:
                score += 30
            elif 75 <= length < 100:
                score += 20
            
            # Content quality indicators
            if any(word in insight.lower() for word in ['roi', 'revenue', 'growth', 'market share']):
                score += 15
            if any(word in insight.lower() for word in ['strategy', 'implementation', 'approach']):
                score += 10
            if any(word in insight.lower() for word in ['customers', 'clients', 'users']):
                score += 10
            if any(word in insight.lower() for word in ['competitive', 'advantage', 'positioning']):
                score += 15
            if any(word in insight.lower() for word in ['metrics', 'kpi', 'measurement']):
                score += 10
            
            total_score += score
            total_insights += 1
    
    return (total_score / total_insights) if total_insights > 0 else 0

def test_functions():
    print("✅ Enhanced summarize_trends function loaded")
    print("✅ Enhanced analyze_question function loaded")
    print("✅ extract_text_from_file function loaded")
    print("✅ Enhanced claude_messages function loaded")
    print("✅ safe_get_insight function loaded")
    print("✅ clear_cache function loaded")
    print("✅ get_insight_quality_score function loaded")

    # Enhanced test run
    test_question = "What are the key market opportunities in sustainable packaging for food companies in 2024?"
    
    print(f"\n🔍 Testing enhanced analysis with question: {test_question}")
    result = analyze_question(test_question)

    if result["error"]:
        print("❌ Claude error:", result["error"])
        return

    print(f"\n📊 Analysis ID: {result.get('analysis_id', 'N/A')}")
    print("🔑 Keywords identified:", result["keywords"])
    print(f"📈 Total insights structure: {len(result['insights'])} keywords")
    
    # Calculate quality score
    quality_score = get_insight_quality_score(result['insights'])
    print(f"🎯 Insight Quality Score: {quality_score:.1f}/100")

    # Show first insight for each keyword with length info
    for kw in result["keywords"][:2]:  # Show first 2 keywords
        title = safe_get_insight(result, kw, "titles", 0)
        insight = safe_get_insight(result, kw, "insights", 0)
        print(f"\n🔹 Keyword: {kw}")
        print(f"   📝 Title: {title}")
        print(f"   💡 Insight Length: {len(insight)} characters")
        print(f"   💡 Insight Preview: {insight[:200]}...")

if __name__ == "__main__":
    test_functions()
