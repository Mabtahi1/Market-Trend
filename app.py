import streamlit as st
from summarizer import summarize_trends, analyze_question, clear_cache
from auth import show_login, is_logged_in
import requests
from bs4 import BeautifulSoup
import textract
import hashlib

st.set_page_config(page_title="📈 Market Trend Summarizer")

# Auth check
if not is_logged_in():
    show_login()
    st.stop()

# Initialize session state
if 'last_analysis_hash' not in st.session_state:
    st.session_state.last_analysis_hash = None
if 'last_result' not in st.session_state:
    st.session_state.last_result = None

st.title("📈 Market Trend Summarizer")

# Add cache control
col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🔄 Clear Cache"):
        clear_cache()
        st.session_state.last_analysis_hash = None
        st.session_state.last_result = None
        st.success("Cache cleared!")

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
        try:
            with st.spinner("Fetching URL content..."):
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                paragraphs = soup.find_all("p")
                text = " ".join([p.text.strip() for p in paragraphs if p.text.strip()])
                if text:
                    st.success(f"✅ Extracted {len(text)} characters from URL")
                else:
                    st.warning("No text content found in the URL")
        except Exception as e:
            st.error(f"Failed to fetch URL: {e}")

elif input_type == "Paste Text":
    text = st.text_area("Paste text here:", height=200)
    if text:
        st.info(f"📝 Text length: {len(text)} characters")

elif input_type == "Upload File":
    uploaded_file = st.file_uploader("Choose a file", type=["txt", "pdf", "docx"])
    if uploaded_file:
        try:
            with st.spinner("Processing file..."):
                uploaded_file.seek(0)
                text = textract.process(uploaded_file).decode("utf-8")
                if text:
                    st.success(f"✅ Extracted {len(text)} characters from file")
                else:
                    st.warning("No text content found in the file")
        except Exception as e:
            st.error(f"Failed to process file: {e}")

elif input_type == "Ask a Question":
    question = st.text_input("Ask your question:", placeholder="e.g., What are the latest trends in AI technology?")
    custom_keywords = st.text_input("Optional: Add keywords (comma-separated)", placeholder="e.g., AI, machine learning, automation")

# Create a unique hash for the current input
current_input_hash = None
if input_type == "Ask a Question" and question:
    current_input_hash = hashlib.md5(f"{question}_{custom_keywords}".encode()).hexdigest()
elif text:
    current_input_hash = hashlib.md5(text.encode()).hexdigest()

# Show if we're about to use cached results
if current_input_hash and current_input_hash == st.session_state.last_analysis_hash:
    st.info("🔄 This input was recently analyzed. Results below are from cache.")

# Submit button
if st.button("📊 Analyze", type="primary"):
    if input_type == "Ask a Question" and question:
        # Check if we have cached results
        if (current_input_hash == st.session_state.last_analysis_hash and 
            st.session_state.last_result is not None):
            st.info("📋 Using cached results (identical input detected)")
            result = st.session_state.last_result
        else:
            with st.spinner("🔍 Analyzing question..."):
                try:
                    result = analyze_question(question, custom_keywords)
                    st.session_state.last_analysis_hash = current_input_hash
                    st.session_state.last_result = result
                except Exception as e:
                    st.error(f"Error during analysis: {e}")
                    st.stop()
        
        # Display results
        if result.get("error"):
            st.error(f"❌ Analysis Error: {result['error']}")
        else:
            # Analysis metadata
            if result.get("analysis_id"):
                st.caption(f"🔍 Analysis ID: {result['analysis_id']}")
            
            # Keywords section
            st.subheader("🔑 Extracted Keywords")
            keywords = result.get("keywords", [])
            if keywords:
                st.write(", ".join(keywords))
            else:
                st.warning("No keywords extracted")
            
            # Insights section
            st.subheader("💡 Actionable Insights by Keyword")
            insights = result.get("insights", {})
            
            if insights:
                # Simple expandable sections for each keyword
                for keyword, data in insights.items():
                    with st.expander(f"🔑 {keyword}"):
                        display_keyword_insights(keyword, data)
            else:
                st.warning("⚠️ No insights generated")
            
            # Debug section (collapsible)
            with st.expander("🔧 Debug Information"):
                st.json({
                    "input_hash": current_input_hash,
                    "keywords_count": len(keywords),
                    "insights_count": len(insights),
                    "analysis_id": result.get("analysis_id"),
                    "has_error": bool(result.get("error"))
                })
            
            # Raw response (collapsible)
            with st.expander("📄 Raw Claude Response"):
                st.code(result.get("full_response", "No response"), language="markdown")
    
    elif text:
        # Check if we have cached results
        if (current_input_hash == st.session_state.last_analysis_hash and 
            st.session_state.last_result is not None):
            st.info("📋 Using cached results (identical input detected)")
            summary = st.session_state.last_result
        else:
            with st.spinner("📝 Summarizing content..."):
                try:
                    summary = summarize_trends(text)
                    st.session_state.last_analysis_hash = current_input_hash
                    st.session_state.last_result = summary
                except Exception as e:
                    st.error(f"Error summarizing content: {e}")
                    st.stop()
        
        # Display summary
        st.subheader("📋 Summary of Trends")
        if summary.startswith("Error:"):
            st.error(summary)
        else:
            st.write(summary)
    
    else:
        st.warning("⚠️ Please provide valid input before analyzing.")

def display_keyword_insights(keyword, data):
    """Helper function to display insights for a keyword"""
    titles = data.get("titles", [])
    actions = data.get("insights", [])
    
    if not titles and not actions:
        st.info("No insights found for this keyword.")
        return
    
    # Display insights in a simple format
    for i in range(max(len(titles), len(actions))):
        title = titles[i] if i < len(titles) else "Untitled Insight"
        action = actions[i] if i < len(actions) else "No insight available"
        
        st.markdown(f"**{i + 1}. {title}**")
        st.write(action)
        if i < max(len(titles), len(actions)) - 1:
            st.markdown("---")

# Add footer with tips
st.markdown("---")
st.markdown("""
**💡 Tips for better results:**
- Be specific in your questions
- Use relevant keywords
- Clear cache if you want fresh analysis of the same input
- Check the Analysis ID to track different analyses
""")
