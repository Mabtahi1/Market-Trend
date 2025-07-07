import boto3
import json
import textract
import tempfile
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def summarize_trends(text=None, question=None, keyword=None):
    """
    Summarize trends from text content with improved error handling
    """
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
    """
    Extract text from uploaded file with improved error handling
    """
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
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as cleanup_error:
                logger.warning(f"Could not clean up temp file: {cleanup_error}")

def claude_messages(prompt):
    """
    Helper function to call Claude 3 with proper formatting and error handling
    """
    try:
        if not prompt or not prompt.strip():
            return "Error: Empty prompt provided"
        
        bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_k": 250,
            "top_p": 1,
        }
        
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        
        result = json.loads(response["body"].read())
        
        # Validate response structure
        if not result or "content" not in result:
            return "Error: Invalid response structure from Claude"
        
        if not result["content"] or len(result["content"]) == 0:
            return "Error: Empty response from Claude"
        
        return result["content"][0]["text"]
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return f"Error decoding Claude response: {str(e)}"
    except Exception as e:
        logger.error(f"Error calling Claude: {str(e)}")
        return f"Error calling Claude: {str(e)}"

def analyze_question(question, custom_keywords=""):
    """
    Analyze question with enhanced error handling and validation
    """
    try:
        if not question or not question.strip():
            return {
                "error": "Question cannot be empty",
                "keywords": [],
                "structured_insights": {},
                "full_response": ""
            }
        
        full_prompt = f"""You're a senior market analyst with 15+ years of experience. A client asked this question:
{question}

Custom keywords to consider: {custom_keywords}

Please provide a comprehensive analysis following these steps:

Step 1: Extract 5-7 relevant keywords from the question and custom keywords.
Step 2: Order keywords by importance and relevance to the client's question (most important first).
Step 3: For each keyword, provide 3-5 SPECIFIC, NON-GENERIC actionable insights with clear titles.
Step 4: Order insights within each keyword by importance (most important first).

IMPORTANT: Make insights highly specific and actionable. Avoid generic advice like "conduct market research" or "analyze competitors." Instead provide concrete, specific recommendations with:
- Exact numbers, percentages, or timeframes when possible
- Specific tools, platforms, or methodologies to use
- Particular market segments or customer groups to target
- Concrete steps with measurable outcomes
- Industry-specific tactics and strategies

Return response in this EXACT format (follow this structure precisely):

**KEYWORDS IDENTIFIED:**
Keyword 1, Keyword 2, Keyword 3, Keyword 4, Keyword 5

**ANALYSIS BY KEYWORD** (Ordered by Importance):

**KEYWORD 1: [Most Important Keyword Name]**

**TITLES:**
1. [Most Important Title for This Keyword]
2. [Second Most Important Title for This Keyword]
3. [Third Most Important Title for This Keyword]

**ACTIONS:**
1. [Highly specific actionable insight with concrete recommendations, numbers, tools, or exact steps for Title 1]
2. [Highly specific actionable insight with concrete recommendations, numbers, tools, or exact steps for Title 2]
3. [Highly specific actionable insight with concrete recommendations, numbers, tools, or exact steps for Title 3]

**KEYWORD 2: [Second Most Important Keyword Name]**

**TITLES:**
1. [Most Important Title for This Keyword]
2. [Second Most Important Title for This Keyword]
3. [Third Most Important Title for This Keyword]

**ACTIONS:**
1. [Highly specific actionable insight for Title 1]
2. [Highly specific actionable insight for Title 2]
3. [Highly specific actionable insight for Title 3]

[Continue this pattern for all keywords...]

**ANALYSIS METHODOLOGY:**
This analysis is based on:
- Market trend analysis and pattern recognition
- Strategic business frameworks and best practices
- Industry benchmarking and competitive intelligence
- Economic indicators and market dynamics
- Historical data patterns and emerging trends

**RELIABILITY & SOURCES:**
- Analysis confidence level: [High/Medium/Low] based on available data
- Recommendations should be validated with current market research
- Consider consulting industry-specific databases and reports
- Verify insights with recent financial reports and market studies
- Cross-reference with competitor analysis and customer feedback

**NEXT STEPS:**
1. Validate these insights with real-time market data
2. Conduct deeper research on the top 3 priority areas
3. Develop implementation timeline and resource requirements
"""
        
        response = claude_messages(full_prompt)
        
        # Check if response contains an error
        if response.startswith("Error:"):
            return {
                "error": response,
                "keywords": [],
                "structured_insights": {},
                "full_response": response
            }
        
        # Parse the response to extract keywords and structured insights
        parsed_result = parse_analysis_response(response)
        
        return {
            "keywords": parsed_result.get("keywords", []),
            "structured_insights": parsed_result.get("structured_insights", {}),
            "full_response": response,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error in analyze_question: {str(e)}")
        return {
            "error": f"Error analyzing question: {str(e)}",
            "keywords": [],
            "structured_insights": {},
            "full_response": ""
        }

def parse_analysis_response(response):
    """
    Parse the Claude response to extract structured data
    """
    try:
        lines = response.strip().split("\n")
        keywords = []
        structured_insights = {}
        current_keyword = None
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Extract keywords from the KEYWORDS IDENTIFIED section
            if line.startswith("**KEYWORDS IDENTIFIED:**"):
                continue
            elif line and not line.startswith("**") and ":" not in line and current_keyword is None:
                # This is likely the keywords line
                keywords = [k.strip() for k in line.split(",") if k.strip()]
                continue
            
            # Identify keyword sections
            if line.startswith("**KEYWORD") and ":" in line:
                try:
                    current_keyword = line.split(":")[1].strip().replace("**", "")
                    if current_keyword not in structured_insights:
                        structured_insights[current_keyword] = {"titles": [], "actions": []}
                    current_section = None
                except IndexError:
                    logger.warning(f"Could not parse keyword line: {line}")
                continue
            
            # Identify subsections
            if line == "**TITLES:**":
                current_section = "titles"
                continue
            elif line == "**ACTIONS:**":
                current_section = "actions"
                continue
            
            # Extract titles and actions
            if current_keyword and current_section and line and line[0].isdigit():
                try:
                    content = line.split(".", 1)[1].strip() if "." in line else line
                    structured_insights[current_keyword][current_section].append(content)
                except IndexError:
                    logger.warning(f"Could not parse content line: {line}")
        
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

def safe_get_insight(analysis_result, keyword, insight_type="actions", index=0):
    """
    Safely get an insight from the analysis result
    """
    try:
        if not analysis_result or "structured_insights" not in analysis_result:
            return "No analysis result available"
        
        structured_insights = analysis_result["structured_insights"]
        
        if keyword not in structured_insights:
            return f"Keyword '{keyword}' not found in analysis"
        
        if insight_type not in structured_insights[keyword]:
            return f"Insight type '{insight_type}' not found for keyword '{keyword}'"
        
        insights_list = structured_insights[keyword][insight_type]
        
        if index >= len(insights_list):
            return f"Index {index} out of range for {insight_type} in keyword '{keyword}'"
        
        return insights_list[index]
        
    except Exception as e:
        logger.error(f"Error getting insight: {str(e)}")
        return f"Error retrieving insight: {str(e)}"

# Example usage with error handling
def example_usage():
    """
    Example of how to use the functions safely
    """
    try:
        # Analyze a question
        question = "How can I improve my e-commerce conversion rates?"
        result = analyze_question(question)
        
        # Check for errors
        if result.get("error"):
            print(f"Analysis error: {result['error']}")
            return
        
        # Safely access results
        keywords = result.get("keywords", [])
        print(f"Keywords found: {keywords}")
        
        # Safely get insights
        if keywords:
            first_keyword = keywords[0]
            first_insight = safe_get_insight(result, first_keyword, "actions", 0)
            print(f"First insight for '{first_keyword}': {first_insight}")
        
    except Exception as e:
        logger.error(f"Error in example usage: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    example_usage()
