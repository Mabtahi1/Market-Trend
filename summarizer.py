import boto3
import json
import textract
import tempfile
import os

def summarize_trends(text=None, question=None, keyword=None):
    try:
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
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",  # Fixed: Added version suffix
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]  # Fixed: Extract text from content array
        
    except Exception as e:
        return f"Error summarizing content: {e}"

def extract_text_from_file(uploaded_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        text = textract.process(tmp_path).decode("utf-8")
        os.unlink(tmp_path)
        return text
    except Exception as e:
        return f"Error extracting text: {e}"

def claude_messages(prompt):
    """Helper function to call Claude 3 with proper formatting"""
    try:
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
        return result["content"][0]["text"]
        
    except Exception as e:
        return f"Error calling Claude: {e}"

def analyze_question(question, custom_keywords=""):
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
    
    # Parse the response to extract keywords and structured insights
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
            keywords = [k.strip() for k in line.split(",")]
            continue
        
        # Identify keyword sections
        if line.startswith("**KEYWORD") and ":" in line:
            current_keyword = line.split(":")[1].strip().replace("**", "")
            if current_keyword not in structured_insights:
                structured_insights[current_keyword] = {"titles": [], "actions": []}
            current_section = None
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
            content = line.split(".", 1)[1].strip() if "." in line else line
            structured_insights[current_keyword][current_section].append(content)
    
    return {
        "keywords": keywords,
        "structured_insights": structured_insights,
        "full_response": response
    }
