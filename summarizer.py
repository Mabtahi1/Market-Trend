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
        
        # Make the prompt more deterministic by setting lower temperature
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1024,
            "temperature": 0.1,  # Lower temperature for more consistent responses
            "top_k": 250,
            "top_p": 0.9,  # Slightly lower for more consistency
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
        
        # More specific and structured prompt
        full_prompt = f"""You are a senior market analyst. Analyze this question with EXACT formatting:

QUESTION: {question}
CUSTOM KEYWORDS: {custom_keywords}

Respond using EXACTLY this format (no variations):

**KEYWORDS IDENTIFIED:**
[List exactly 5 keywords separated by commas]

**ANALYSIS BY KEYWORD:**

**KEYWORD 1: [First Keyword]**
**TITLES:**
1. [Specific title for first insight]
2. [Specific title for second insight]
3. [Specific title for third insight]
**ACTIONS:**
1. [Detailed insight for title 1]
2. [Detailed insight for title 2]
3. [Detailed insight for title 3]

**KEYWORD 2: [Second Keyword]**
**TITLES:**
1. [Specific title for first insight]
2. [Specific title for second insight]
3. [Specific title for third insight]
**ACTIONS:**
1. [Detailed insight for title 1]
2. [Detailed insight for title 2]
3. [Detailed insight for title 3]

[Continue this exact pattern for all 5 keywords]

IMPORTANT: Use this EXACT format with no deviations. Each keyword must have exactly 3 titles and 3 actions.
"""
        
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

        parsed_result = parse_analysis_response(response)
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

def parse_analysis_response(response):
    try:
        lines = response.strip().split("\n")
        keywords = []
        structured_insights = {}
        current_keyword = None
        mode = None

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
                # Extract keyword name more reliably
                if ":" in line:
                    keyword_part = line.split(":", 1)[1].strip()
                    current_keyword = keyword_part.replace("**", "").replace("[", "").replace("]", "").strip()
                    if current_keyword:
                        structured_insights[current_keyword] = {"titles": [], "insights": []}
                continue

            elif line == "**TITLES:**":
                mode = "titles"
                continue

            elif line == "**ACTIONS:**":
                mode = "insights"
                continue

            # Extract content
            elif mode in {"titles", "insights"} and current_keyword:
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
                        structured_insights[current_keyword][mode].append(content)

        # Validate that we have the expected structure
        logger.info(f"Parsed {len(keywords)} keywords: {keywords}")
        logger.info(f"Structured insights for {len(structured_insights)} keywords")
        
        return {
            "keywords": keywords,
            "structured_insights": structured_insights
        }

    except Exception as e:
        logger.error(f"Error parsing analysis response: {str(e)}")
        return {
            "keywords": [],
            "structured_insights": {}
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

def test_functions():
    print("✅ summarize_trends function loaded")
    print("✅ analyze_question function loaded")
    print("✅ extract_text_from_file function loaded")
    print("✅ claude_messages function loaded")
    print("✅ safe_get_insight function loaded")
    print("✅ clear_cache function loaded")

    # Example test run (remove/comment this if using in production)
    test_question = "What are the latest trends in the renewable energy market in 2025?"
    
    print(f"\n🔍 Testing with question: {test_question}")
    result = analyze_question(test_question)

    if result["error"]:
        print("❌ Claude error:", result["error"])
        return

    print(f"\n📊 Analysis ID: {result.get('analysis_id', 'N/A')}")
    print("🔑 Keywords identified:", result["keywords"])
    print(f"📈 Total insights structure: {len(result['insights'])} keywords")

    # Show first insight for each keyword
    for kw in result["keywords"][:3]:  # Show first 3 keywords
        title = safe_get_insight(result, kw, "titles", 0)
        insight = safe_get_insight(result, kw, "insights", 0)
        print(f"\n🔹 Keyword: {kw}")
        print(f"   📝 Title: {title}")
        print(f"   💡 Insight: {insight}")

if __name__ == "__main__":
    test_functions()
