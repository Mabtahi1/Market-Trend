import streamlit as st
from summarizer import summarize_trends
from sentiment import analyze_sentiment
from keywords import extract_keywords
from utils import fetch_text_from_url
from visualizations import plot_brand_mentions, sentiment_chart
from auth import show_login, is_logged_in

st.set_page_config(page_title="Market Trend Summarizer", layout="wide")

show_login()

if not is_logged_in():
    st.stop()

st.title("📈 Market Trend Summarizer")

input_method = st.radio("Choose Input Type:", ["Paste URL", "Paste Text"])

brands = st.text_input("Optional: Enter brands to track (comma-separated):", "")

if input_method == "Paste URL":
    url = st.text_input("Enter URL:")
    if st.button("Summarize from URL"):
        text = fetch_text_from_url(url)
        summary = summarize_trends(text)
        sentiment, score = analyze_sentiment(text)
        hashtags = extract_keywords(text)
        brand_list = [b.strip() for b in brands.split(",") if b.strip()]
        brand_counts = {} if not brand_list else dict(plot_brand_mentions.compare_brand_mentions(text, brand_list))

        st.subheader("📋 Summary of Trends")
        st.markdown(summary)

        st.subheader("💬 Sentiment")
        st.markdown(f"**Sentiment:** {sentiment}")
        st.altair_chart(sentiment_chart(score))

        st.subheader("🏷 Suggested Hashtags")
        st.markdown(" ".join(hashtags))

        if brand_counts:
            st.subheader("🏢 Brand Mentions")
            st.plotly_chart(plot_brand_mentions.plot_brand_mentions(brand_counts))

else:
    raw_text = st.text_area("Paste the content here:")
    if st.button("Summarize Text"):
        summary = summarize_trends(raw_text)
        sentiment, score = analyze_sentiment(raw_text)
        hashtags = extract_keywords(raw_text)
        brand_list = [b.strip() for b in brands.split(",") if b.strip()]
        brand_counts = {} if not brand_list else dict(plot_brand_mentions.compare_brand_mentions(raw_text, brand_list))

        st.subheader("📋 Summary of Trends")
        st.markdown(summary)

        st.subheader("💬 Sentiment")
        st.markdown(f"**Sentiment:** {sentiment}")
        st.altair_chart(sentiment_chart(score))

        st.subheader("🏷 Suggested Hashtags")
        st.markdown(" ".join(hashtags))

        if brand_counts:
            st.subheader("🏢 Brand Mentions")
            st.plotly_chart(plot_brand_mentions.plot_brand_mentions(brand_counts))

