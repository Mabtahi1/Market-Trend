import boto3
import json

# Correct Claude model ID for AWS Bedrock (Claude 3 Sonnet)
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

bedrock = boto3.client("bedrock-runtime", region_name="us-east-2")  # change region if needed

def summarize_trends(text):
    # Updated prompt format for Claude 3 on Bedrock
    prompt = f"""Analyze the following content and extract:
1. Top trends or topics
2. Summary of each trend (1-2 lines)
3. Any competitor mentions
4. Overall brand perception

Content:
{text}

Return in bullet-point format."""
    
    try:
        # Updated body format for Claude 3 on Bedrock
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }),
            contentType="application/json",
            accept="application/json"
        )
        
        result = json.loads(response['body'].read().decode())
        return result["content"][0]["text"]
        
    except Exception as e:
        return f"Error summarizing content: {e}"
