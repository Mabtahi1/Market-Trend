import boto3
import json

def summarize_trends(text, brand_names=None):
    if not text.strip():
        return "Error: No text provided for summarization."

    prompt = f"Please summarize the following text for market trends:\n\n{text}"
    if brand_names:
        prompt += f"\n\nFocus on these brands: {', '.join(brand_names)}."

    try:
        # Claude model in Bedrock — update the model ID if needed
        model_id = "anthropic.claude-3-sonnet-20240229"  # or claude-3-haiku, etc.
        
        # Initialize the Bedrock runtime client
        bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")  # Change region if needed

        # Create payload for Claude
        body = {
            "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
            "max_tokens_to_sample": 500,
            "temperature": 0.7,
            "top_k": 250,
            "top_p": 1,
            "stop_sequences": ["\n\nHuman:"]
        }

        # Call Claude through Bedrock
        response = bedrock.invoke_model(
            body=json.dumps(body),
            modelId=model_id,
            contentType="application/json",
            accept="application/json"
        )

        result = json.loads(response["body"].read())
        return result.get("completion", "No summary generated.")

    except Exception as e:
        return f"Error summarizing content: {str(e)}"
