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
    """Display analysis results with clickable keywords"""
    if result.get("error"):
        st.error(f"Analysis Error: {result['error']}")
        return
    
    # Store analysis results in session state
    st.session_state.analysis_result = result
    
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
    
    # Display clickable keywords and insights
    if result.get("keywords") and result.get("insights"):
        st.subheader("🔑 Strategic Keywords Analysis")
        st.markdown("*Click on any keyword below to view detailed insights:*")
        
        # Initialize session state for selected keyword if not exists
        if 'selected_keyword' not in st.session_state:
            st.session_state.selected_keyword = None
        
        # Create clickable keyword buttons
        keyword_cols = st.columns(min(len(result["keywords"]), 5))
        
        for i, keyword in enumerate(result["keywords"][:5]):
            with keyword_cols[i]:
                # Create a unique button for each keyword
                if st.button(
                    f"📌 {keyword}",
                    key=f"keyword_btn_{i}",
                    help=f"Click to view insights for {keyword}",
                    use_container_width=True
                ):
                    st.session_state.selected_keyword = keyword
                    st.rerun()
        
        # Display insights for selected keyword
        if st.session_state.selected_keyword:
            selected_keyword = st.session_state.selected_keyword
            
            # Check if the selected keyword exists in insights
            if selected_keyword in result["insights"]:
                st.markdown("---")
                
                # Header for selected keyword
                st.markdown(f"### 🎯 **{selected_keyword}** - Strategic Analysis")
                
                keyword_data = result["insights"][selected_keyword]
                titles = keyword_data.get("titles", [])
                insights = keyword_data.get("insights", [])
                
                # Display strategic insights titles
                if titles:
                    st.markdown("#### **Strategic Focus Areas:**")
                    for j, title in enumerate(titles, 1):
                        st.markdown(f"**{j}.** {title}")
                
                st.markdown("---")
                
                # Display business actions with better formatting
                if insights:
                    st.markdown("#### **📋 Business Actions & Recommendations:**")
                    
                    for j, insight in enumerate(insights, 1):
                        # Create expandable sections for each insight
                        with st.expander(
                            f"🔍 **Action {j}** | {len(insight.split())} words | {len(insight)} characters",
                            expanded=True  # Show first insight expanded by default
                        ):
                            # Add some styling to the insight text
                            st.markdown(f"<div style='text-align: justify; line-height: 1.6;'>{insight}</div>", 
                                      unsafe_allow_html=True)
                            
                            # Add word count and character count info
                            word_count = len(insight.split())
                            char_count = len(insight)
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.caption(f"📝 Words: {word_count}")
                            with col_b:
                                st.caption(f"🔤 Characters: {char_count}")
                
                # Add a button to clear selection
                if st.button("🔄 Clear Selection", key="clear_selection"):
                    st.session_state.selected_keyword = None
                    st.rerun()
                    
            else:
                st.warning(f"No insights found for keyword: {selected_keyword}")
        
        else:
            # Show instruction when no keyword is selected
            st.info("👆 **Click on any keyword above to view detailed strategic insights and business actions.**")
    
    elif result.get("keywords"):
        # If we have keywords but no insights
        st.subheader("🔑 Identified Keywords")
        keyword_cols = st.columns(min(len(result["keywords"]), 5))
        for i, keyword in enumerate(result["keywords"][:5]):
            with keyword_cols[i]:
                st.info(keyword)
        st.warning("No detailed insights available for these keywords.")
    
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
                    # Get user email
                    user_email = st.session_state.get('user', {}).get('email')
        
                    # Check usage limits
                    can_use, message = check_usage_limits(user_email, "summary")
        
                    if not can_use:
                       st.error(f"❌ {message}")
                       st.info("💳 Please upgrade your plan to continue.")
                       if st.button("🔗 Go to Pricing"):
                           st.markdown('[Upgrade Plan](https://prolexisanalytics.com/pricing)')
                       else:
                           with st.spinner("🤖 Analyzing your question..."):
                               try:
                                    result = analyze_question(question, custom_keywords)
                    
                                    # Increment usage count after successful analysis
                                    increment_usage(user_email, "summary")
                    
                                    # Clear previous keyword selection when new analysis starts
                                    st.session_state.selected_keyword = None
                                    display_analysis_results(result)
                    
                                    # Show success message with remaining usage
                                    st.success("✅ Analysis complete!")
                    
                               except Exception as e:
                                    st.error(f"Error during analysis: {str(e)}")
            else:
               st.warning("Please enter a question to analyze")
        
        # Display previous analysis results if they exist
        if 'analysis_result' in st.session_state and st.session_state.analysis_result:
            display_analysis_results(st.session_state.analysis_result)

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
                    
                    # Clear previous keyword selection when new analysis starts
                    st.session_state.selected_keyword = None
                    display_analysis_results(result)
                    
                except Exception as e:
                    st.error(f"Error analyzing document: {str(e)}")
        
        # Display previous analysis results if they exist
        if 'analysis_result' in st.session_state and st.session_state.analysis_result:
            display_analysis_results(st.session_state.analysis_result)

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
                        # Clear previous keyword selection when new analysis starts
                        st.session_state.selected_keyword = None
                        display_analysis_results(result)
                    except Exception as e:
                        st.error(f"Error analyzing URL: {str(e)}")
            else:
                st.warning("Please enter a valid URL starting with http:// or https://")
        
        # Display previous analysis results if they exist
        if 'analysis_result' in st.session_state and st.session_state.analysis_result:
            display_analysis_results(st.session_state.analysis_result)

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
                    # Clear previous keyword selection when new analysis starts
                    st.session_state.selected_keyword = None
                    display_analysis_results(result)
                except Exception as e:
                    st.error(f"Error analyzing text: {str(e)}")
        
        # Display previous analysis results if they exist
        if 'analysis_result' in st.session_state and st.session_state.analysis_result:
            display_analysis_results(st.session_state.analysis_result)

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
