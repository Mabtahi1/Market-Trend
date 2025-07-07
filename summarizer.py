import boto3
import json
import os

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

def claude_messages(prompt):
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024
    })
    response = bedrock.invoke_model(
        modelId="anthropic.claude-3-sonnet-20240229",
        body=body,
        contentType="application/json",
    )
    result = json.loads(response['body'].read())
    return result['content'][0]['text']

def summarize_trends(text):
    prompt = f"Summarize the following market-related content:\n\n{text}\n\nProvide a short and clear summary of key trends."
    return claude_messages(prompt)

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
