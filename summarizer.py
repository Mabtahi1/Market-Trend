import boto3
import json
import os
import re
import requests
from bs4 import BeautifulSoup

# Use Claude 3 Haiku for faster and cheaper results (you can change to Sonnet or Opus if needed)
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
REGION = "us-east-1"

# Claude 3 models require the Messages API
bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)

def get_text_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        return "\n".join(p.get_text() for p in paragraphs)
    except Exception as e:
        return f"Error fetching URL content: {e}"

def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def summarize_trends(text, brands=None):
    try:
        prompt = f"""
        You are a market trend analyst. Read the following article and provide:
        1. A brief summary in bullet points
        2. Key trends mentioned
        3. Any brand names referenced

        Text:
        \"\"\"{text}\"\"\"
        """

        if brands:
            prompt += f"\nSpecifically track these brands: {', '.join(brands)}."

        body = {
           "anthropic_version": "bedrock-2023-05-31",
           "max_tokens": 1000,
           "messages": [
               {
                  "role": "user",
                  "content": prompt
               }
          ],
          "temperature": 0.7
        }

        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )

        result = json.loads(response["body"].read())
        return result["content"][0]["text"]

    except Exception as e:
        return f"Error summarizing content: {e}"
