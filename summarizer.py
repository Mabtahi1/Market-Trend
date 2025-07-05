import openai

openai.api_key = "YOUR_OPENAI_API_KEY"

def summarize_trends(text):
    prompt = f"""Analyze the following content and extract:
1. Top trends or topics
2. Summary of each trend (1-2 lines)
3. Any competitor mentions
4. Overall brand perception

Content:
{text}

Return in bullet-point format."""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message["content"]

