import streamlit as st
from summarizer import summarize_trends, analyze_question
from auth import show_login, is_logged_in

st.set_page_config(page_title="📈 Market Trend Summarizer")

# Auth check
if not is_logged_in():
    show_login()
    st.stop()

st.title("📈 Market Trend Summarizer")

# Input type selection
input_type = st.radio("Choose Input Type:", ["Paste URL", "Paste Text", "Upload File", "Ask a Question"])

text = ""
uploaded_file = None
question = ""
custom_keywords = ""

# Handle input
if input_type == "Paste URL":
    url = st.text_input("Enter URL:")
    if url:
        import requests
        from bs4 import BeautifulSoup
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            paragraphs = soup.find_all("p")
            text = " ".join([p.text for p in paragraphs])
        except Exception as e:
            st.error(f"Failed to fetch URL: {e}")

elif input_type == "Paste Text":
    text = st.text_area("Paste text here:")

elif input_type == "Upload File":
    uploaded_file = st.file_uploader("Choose a file", type=["txt", "pdf", "docx"])
    if uploaded_file:
        import textract
        try:
            text = textract.process(uploaded_file).decode("utf-8")
        except Exception as e:
            st.error(f"Failed to process file: {e}")

elif input_type == "Ask a Question":
    question = st.text_input("Ask your question:")
    custom_keywords = st.text_input("Optional: Add keywords (comma-separated)")

# Submit button
if st.button("Submit"):
    if input_type == "Ask a Question" and question:
        with st.spinner("Analyzing..."):
            try:
                result = analyze_question(question, custom_keywords)

                if result.get("error"):
                    st.error(result["error"])
                else:
                    st.subheader("🔑 Extracted Keywords")
                    st.write(result.get("keywords", []))

                    st.subheader("💡 Actionable Insights by Keyword")
                    insights = result.get("insights", {})
                    if insights:
                        for keyword, data in insights.items():
                            with st.expander(f"🔑 {keyword}"):
                                titles = data.get("titles", [])
                                actions = data.get("insights", [])

                                for i, (title, action) in enumerate(zip(titles, actions), start=1):
                                    st.markdown(f"**{i}. {title}**")
                                    st.write(action)
                    else:
                        st.warning("No insights returned.")

            except Exception as e:
                st.error(f"Error: {e}")

    elif text:
        with st.spinner("Summarizing..."):
            try:
                summary = summarize_trends(text)
                st.subheader("📋 Summary of Trends")
                st.write(summary)
            except Exception as e:
                st.error(f"Error summarizing content: {e}")
    else:
        st.warning("Please provide valid input.")
