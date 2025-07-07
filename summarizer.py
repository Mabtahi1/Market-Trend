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
            modelId="anthropic.claude-3-sonnet-20240229",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )

        result = json.loads(response["body"].read())
        return result["content"]

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
