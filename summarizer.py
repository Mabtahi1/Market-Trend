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
Step 2: For each keyword, provide 3-5 SPECIFIC, NON-GENERIC actionable insights with clear titles.
Step 3: Order insights by importance and relevance to the client's question.
Step 4: Include a brief methodology note about your analysis approach.

IMPORTANT: Make insights highly specific and actionable. Avoid generic advice like "conduct market research" or "analyze competitors." Instead provide concrete, specific recommendations with:
- Exact numbers, percentages, or timeframes when possible
- Specific tools, platforms, or methodologies to use
- Particular market segments or customer groups to target
- Concrete steps with measurable outcomes
- Industry-specific tactics and strategies

Return response in this EXACT format:

**KEYWORDS IDENTIFIED:**
- Keyword 1, Keyword 2, Keyword 3, [etc.]

**ACTIONABLE INSIGHTS** (Ordered by Priority):

**KEYWORD: [Keyword Name]**
1. **[Specific Insight Title]**: [Highly specific actionable insight with concrete recommendations, numbers, tools, or exact steps to take]
2. **[Specific Insight Title]**: [Highly specific actionable insight with concrete recommendations, numbers, tools, or exact steps to take]
3. **[Specific Insight Title]**: [Highly specific actionable insight with concrete recommendations, numbers, tools, or exact steps to take]

**KEYWORD: [Next Keyword]**
1. **[Insight Title]**: [Detailed actionable insight with specific recommendations]
[Continue for all keywords...]

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
    lines = response.strip().split("\n")
    keywords = []
    insights = []
    
    for line in lines:
        if line.lower().startswith("- keywords"):
            keywords = line.split(":")[1].strip()
        elif line.strip().startswith(("1.", "2.", "3.")):
            insights.append(line.strip())
    
    return {"keywords": keywords, "insight": "\n".join(insights)}
