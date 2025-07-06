import boto3
import json

# Claude model ID (Claude 3 Sonnet)
MODEL_ID = "anthropic.claude-3-sonnet-20240229"
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")  # change region if needed

def summarize_trends(text):
    prompt = f"""
    Human: Please provide a concise summary of the following news article or content. Focus on market trends, key events, and entities if available.

    {text}

    Assistant:"""

    try:
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "prompt": prompt,
                "max_tokens": 500,
                "temperature": 0.7,
                "stop_sequences": ["\n\nHuman:"]
            }),
            contentType="application/json",
            accept="application/json"
        )

        result = json.loads(response['body'].read().decode())
        return result.get("completion", "").strip()

    except Exception as e:
        return f"Error summarizing content: {e}"
