import streamlit as st
from summarizer import (
    summarize_trends,
    analyze_question,
    extract_text_from_file,
    safe_get_insight,
    get_insight_quality_score
)

st.set_page_config(page_title="Market Insight Generator", layout="wide")
st.title("🔍 Market Insight Generator")
st.markdown("Upload documents, paste content, or ask questions to generate strategic business insights powered by Claude 3 via AWS Bedrock.")

# Input mode selector
mode = st.radio("Choose Input Method:", ["Ask a Question", "Paste Text", "Upload File"])

question = ""
text_input = ""
file_result = None
result = None

# Input areas based on mode
if mode == "Ask a Question":
    question = st.text_area("🧠 Enter your business question:")
elif mode == "Paste Text":
    text_input = st.text_area("📄 Paste your content here:")
    question = st.text_input("Optional: What would you like to analyze?")
elif mode == "Upload File":
    uploaded_file = st.file_uploader("📁 Upload a document (PDF, DOCX, etc.)")
    question = st.text_input("Optional: What would you like to analyze in the file?")

# Optional keyword focus
keyword_input = st.text_input("Optional: Focus on specific keyword(s) (comma-separated)")

# Analyze button
if st.button("🚀 Analyze Now"):
    with st.spinner("Analyzing with Claude..."):

        if mode == "Ask a Question" and question:
            result = analyze_question(question, custom_keywords=keyword_input)

        elif mode == "Paste Text" and text_input:
            result = summarize_trends(
                text=text_input,
                question=question or "Analyze and summarize trends from this content",
                keyword=keyword_input,
                return_format="dict"
            )

        elif mode == "Upload File" and uploaded_file:
            file_result = extract_text_from_file(uploaded_file)
            if file_result.get("error"):
                st.error(file_result["error"])
            else:
                result = file_result

        else:
            st.warning("Please provide valid input for analysis.")
            st.stop()

    # Display results
    if result.get("error"):
        st.error(f"❌ Error: {result['error']}")
    else:
        st.success("✅ Analysis completed!")

        st.markdown(f"**🆔 Analysis ID:** `{result.get('analysis_id')}`")
        st.markdown(f"**🧠 Keywords Identified:** {', '.join(result['keywords'])}")

        score = get_insight_quality_score(result.get("insights", {}))
        st.markdown(f"**📊 Insight Quality Score:** `{score:.1f}/100`")

        for kw in result["keywords"]:
            st.subheader(f"🔑 Keyword: {kw}")
            keyword_data = result["insights"].get(kw, {})

            for i, title in enumerate(keyword_data.get("titles", [])):
                insight = safe_get_insight(result, kw, "insights", i)
                if not insight.startswith("Error"):
                    st.markdown(f"**{i+1}. {title}**")
                    st.markdown(insight)
                else:
                    st.warning(insight)

        # Show full Claude response
        with st.expander("📄 View Raw Claude Output"):
            st.code(result.get("full_response", "")[:5000], language="markdown")
