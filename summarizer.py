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
    try:
        if not question or not question.strip():
            return {
                "error": "Question cannot be empty",
                "keywords": [],
                "insights": {},
                "full_response": ""
            }

        full_prompt = f"""You're a senior market analyst with 15+ years of experience. A client asked this question:
{question}

Custom keywords to consider: {custom_keywords}

Please provide a comprehensive analysis following these steps:

Step 1: Extract 5-7 relevant keywords.
Step 2: Order keywords by importance.
Step 3: For each keyword, provide 3-5 highly specific insights with titles.

Use this format:
**KEYWORDS IDENTIFIED:**
Keyword 1, Keyword 2, ...

**ANALYSIS BY KEYWORD** (Ordered by Importance):

**KEYWORD 1: [Name]**
**TITLES:**
1. [Title]
2. [Title]
**ACTIONS:**
1. [Insight for Title 1]
2. [Insight for Title 2]

... (repeat for each keyword)
"""
        response = claude_messages(full_prompt)
        if response.startswith("Error:"):
            return {
                "error": response,
                "keywords": [],
                "insights": {},
                "full_response": response
            }

        parsed_result = parse_analysis_response(response)
        return {
            "keywords": parsed_result.get("keywords", []),
            "insights": parsed_result.get("structured_insights", {}),
            "full_response": response,
            "error": None
        }

    except Exception as e:
        logger.error(f"Error in analyze_question: {str(e)}")
        return {
            "error": f"Error analyzing question: {str(e)}",
            "keywords": [],
            "insights": {},
            "full_response": ""
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
            if line.startswith("**KEYWORDS IDENTIFIED:**"):
                mode = "keywords"
                continue
            elif mode == "keywords" and line and not line.startswith("**"):
                keywords = [k.strip() for k in line.split(",")]
                mode = None
                continue

            if line.startswith("**KEYWORD") and ":" in line:
                current_keyword = line.split(":")[1].strip().replace("**", "")
                structured_insights[current_keyword] = {"titles": [], "insights": []}
                continue

            if line == "**TITLES:**":
                mode = "titles"
                continue
            elif line == "**ACTIONS:**":
                mode = "insights"
                continue

            if mode in {"titles", "insights"} and line and line[0].isdigit():
                content = line.split(".", 1)[1].strip() if "." in line else line
                structured_insights[current_keyword][mode].append(content)

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
        if insight_type not in {"titles", "insights"}:
            return f"Invalid insight_type '{insight_type}'"

        insights = analysis_result.get("insights", {})
        if not insights:
            return "No insights available"

        if keyword not in insights:
            return f"Keyword '{keyword}' not found in insights"

        items = insights[keyword].get(insight_type, [])
        if index >= len(items):
            return f"Index {index} out of range for '{insight_type}' in keyword '{keyword}'"

        return items[index]

    except Exception as e:
        logger.error(f"Error in safe_get_insight: {str(e)}")
        return f"Error retrieving insight: {str(e)}"

def test_functions():
    print("\u2705 summarize_trends function loaded")
    print("\u2705 analyze_question function loaded")
    print("\u2705 extract_text_from_file function loaded")
    print("\u2705 claude_messages function loaded")
    print("\u2705 All functions imported successfully!")

if __name__ == "__main__":
    test_functions()
