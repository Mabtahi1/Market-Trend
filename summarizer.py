import anthropic

client = anthropic.Anthropic(
    api_key="YOUR_ANTHROPIC_API_KEY"
)

def summarize_trends(text):
    prompt = f"""Analyze the following content and extract:
1. Top trends or topics
2. Summary of each trend (1-2 lines)
3. Any competitor mentions
4. Overall brand perception

Content:
{text}

Return in bullet-point format."""
    
    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1000,
        temperature=0.7,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.content[0].text

