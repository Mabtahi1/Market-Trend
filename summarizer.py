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
    full_prompt = f"""You're a market analyst. A client asked this question:
{question}
Step 1: Extract relevant keywords from the question.
Step 2: Add these custom keywords if provided: {custom_keywords}
Step 3: Generate 3–4 actionable insights or strategic suggestions based on the keywords.
Return response in this format:
- Keywords: [...]
- Insights:
1. ...
2. ...
3. ...
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
