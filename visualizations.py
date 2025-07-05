import plotly.express as px
import altair as alt
import pandas as pd
import re

def plot_brand_mentions(brand_counts):
    # brand_counts: dict {brand: count}
    brands = list(brand_counts.keys())
    counts = list(brand_counts.values())
    df = pd.DataFrame({"Brand": brands, "Mentions": counts})
    fig = px.bar(df, x="Brand", y="Mentions", title="Brand Mention Frequency")
    return fig

def compare_brand_mentions(text, brands):
    counts = {}
    for brand in brands:
        pattern = re.compile(r'\\b' + re.escape(brand) + r'\\b', re.IGNORECASE)
        counts[brand] = len(pattern.findall(text))
    return counts.items()

def sentiment_chart(score):
    df = pd.DataFrame({
        'Sentiment': ['Negative', 'Neutral', 'Positive'],
        'Score': [score['neg'], score['neu'], score['pos']]
    })
    chart = alt.Chart(df).mark_bar().encode(
        x='Sentiment',
        y='Score',
        color='Sentiment'
    ).properties(
        title='Sentiment Scores'
    )
    return chart

