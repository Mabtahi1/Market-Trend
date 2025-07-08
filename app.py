import streamlit as st
import sys
import os

# Add the current directory to the path to import your modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your modules
try:
    from auth import show_login, is_logged_in
    from app2 import (
        analyze_question, 
        summarize_trends, 
        extract_text_from_file, 
        analyze_url_content,
        safe_get_insight,
        clear_cache,
        get_insight_quality_score
    )
    st.success("✅ All modules loaded successfully!")
except ImportError as e:
    st.error(f"❌ Error importing modules: {e}")
    st.error("Make sure auth.py and app2.py are in the same directory as this app.py file")
    st.stop()

def display_analysis_results(result):
    """Display analysis results in a structured format"""
    if result.get("error"):
        st.error(f"Analysis Error: {result['error']}")
        return
    
    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Keywords Found", len(result.get("keywords", [])))
    
    with col2:
        quality_score = get_insight_quality_score(result.get("insights", {}))
        st.metric("Quality Score", f"{quality_score:.1f}/100")
    
    with col3:
        analysis_id = result.get("analysis_id", "N/A")
        st.metric("Analysis ID", analysis_id)
    
    # Display keywords
    if result.get("keywords"):
        st.subheader("🔑 Identified Keywords")
        keyword_cols = st.columns(min(len(result["keywords"]), 5))
        for i, keyword in enumerate(result["keywords"][:5]):
            with keyword_cols[i]:
                st.info(keyword)
    
    # Display detailed insights
    if result.get("insights"):
        st.subheader("📊 Strategic Analysis")
        
        # Create tabs for each keyword
        if result["keywords"]:
            tabs = st.tabs(result["keywords"])
            
            for i, keyword in enumerate(result["keywords"]):
                with tabs[i]:
                    keyword_data = result["insights"].get(keyword, {})
                    titles = keyword_data.get("titles", [])
                    insights = keyword_data.get("insights", [])
                    
                    # Display strategic insights titles
                    if titles:
                        st.markdown("**Strategic Focus Areas:**")
                        for j, title in enumerate(titles, 1):
                            st.markdown(f"{j}. {title}")
                    
                    st.markdown("---")
                    
                    # Display business actions
                    if insights:
                        st.markdown("**Business Actions:**")
                        for j, insight in enumerate(insights, 1):
                            with st.expander(f"Action {j} ({len(insight)} characters)"):
                                st.write(insight)
    
    # Show full response in expander
    if result.get("full_response"):
        with st.expander("📄 View Full Analysis Response"):
            st.text(result["full_response"])

def main():
    st.set_page_config(
        page_title="Business Intelligence Analyzer",
        page_icon="📊",
        layout="wide"
    )

    st.title("📊 Business Intelligence Analyzer")
    st.markdown("Advanced AI-powered business analysis and trend identification")

    # Authentication
    show_login()
    
    if not is_logged_in():
        st.warning("⚠️ Please log in to access the Business Intelligence Analyzer")
        st.info("Use the sidebar to login or sign up for an account")
        st.stop()

    # User info
    user_info = st.session_state.get('user', {})
    user_email = user_info.get('email', 'Unknown User')
    st.sidebar.success(f"👤 Logged in as: {user_email}")
    
    # Logout button
    if st.sidebar.button("🚪 Logout"):
        st.session_state['user'] = None
        st.rerun()

    # Sidebar for user options
    st.sidebar.title("Analysis Options")
    
    analysis_type = st.sidebar.selectbox(
        "Choose Analysis Type",
        ["Question Analysis", "File Analysis", "URL Analysis", "Text Analysis"]
    )

    # Cache management
    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Clear Cache"):
        clear_cache()
        st.sidebar.success("Cache cleared!")

    # Main content area
    if analysis_type == "Question Analysis":
        st.header("🔍 Strategic Question Analysis")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            question = st.text_area(
                "Enter your business question:",
                placeholder="e.g., What are the emerging opportunities in sustainable packaging for 2024?",
                height=100
            )
        
        with col2:
            custom_keywords = st.text_input(
                "Custom Keywords (optional):",
                placeholder="e.g., sustainability, packaging, innovation"
            )
        
        if st.button("🔍 Analyze Question", type="primary"):
            if question.strip():
                with st.spinner("🤖 Analyzing your question..."):
                    try:
                        result = analyze_question(question, custom_keywords)
                        display_analysis_results(result)
                    except Exception as e:
                        st.error(f"Error during analysis: {str(e)}")
            else:
                st.warning("Please enter a question to analyze")

    elif analysis_type == "File Analysis":
        st.header("📄 Document Analysis")
        
        uploaded_file = st.file_uploader(
            "Upload a document for analysis",
            type=['pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg'],
            help="Supported formats: PDF, DOCX, TXT, PNG, JPG, JPEG"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            custom_question = st.text_input(
                "Analysis Focus (optional):",
                placeholder="e.g., What are the key business opportunities?"
            )
        
        with col2:
            file_keywords = st.text_input(
                "Keywords to focus on (optional):",
                placeholder="e.g., market trends, innovation"
            )
        
        if uploaded_file and st.button("📄 Analyze Document", type="primary"):
            with st.spinner("📄 Extracting and analyzing document content..."):
                try:
                    # Reset file pointer
                    uploaded_file.seek(0)
                    
                    # Extract and analyze
                    result = extract_text_from_file(uploaded_file, return_format="dict")
                    
                    if not result.get("error"):
                        # If we have custom parameters, re-analyze with them
                        if custom_question or file_keywords:
                            uploaded_file.seek(0)  # Reset again
                            text_result = extract_text_from_file(uploaded_file, return_format="string")
                            if not text_result.startswith("Error:"):
                                result = summarize_trends(
                                    text=text_result,
                                    question=custom_question,
                                    keyword=file_keywords,
                                    return_format="dict"
                                )
                    
                    display_analysis_results(result)
                    
                except Exception as e:
                    st.error(f"Error analyzing document: {str(e)}")

    elif analysis_type == "URL Analysis":
        st.header("🌐 Web Content Analysis")
        
        url = st.text_input(
            "Enter URL to analyze:",
            placeholder="https://example.com/article"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            url_question = st.text_input(
                "Analysis Focus (optional):",
                placeholder="e.g., What business insights can be derived?"
            )
        
        with col2:
            url_keywords = st.text_input(
                "Keywords to focus on (optional):",
                placeholder="e.g., technology, market trends"
            )
        
        if url and st.button("🌐 Analyze URL", type="primary"):
            if url.startswith(('http://', 'https://')):
                with st.spinner("🌐 Fetching and analyzing web content..."):
                    try:
                        result = analyze_url_content(url, url_question, url_keywords)
                        display_analysis_results(result)
                    except Exception as e:
                        st.error(f"Error analyzing URL: {str(e)}")
            else:
                st.warning("Please enter a valid URL starting with http:// or https://")

    elif analysis_type == "Text Analysis":
        st.header("📝 Direct Text Analysis")
        
        text_content = st.text_area(
            "Paste your content here:",
            height=200,
            placeholder="Enter or paste the text content you want to analyze..."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            text_question = st.text_input(
                "Analysis Focus (optional):",
                placeholder="e.g., What are the key strategic insights?"
            )
        
        with col2:
            text_keywords = st.text_input(
                "Keywords to focus on (optional):",
                placeholder="e.g., innovation, growth, strategy"
            )
        
        if text_content and st.button("📝 Analyze Text", type="primary"):
            with st.spinner("📝 Analyzing text content..."):
                try:
                    result = summarize_trends(
                        text=text_content,
                        question=text_question,
                        keyword=text_keywords,
                        return_format="dict"
                    )
                    display_analysis_results(result)
                except Exception as e:
                    st.error(f"Error analyzing text: {str(e)}")

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
            <p>Business Intelligence Analyzer | Powered by Claude AI on AWS Bedrock</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
