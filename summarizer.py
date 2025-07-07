import boto3
import json

def debug_analysis_result(result):
    """
    Debug function to show the actual structure of your analysis result
    """
    print("=== DEBUGGING ANALYSIS RESULT ===")
    print(f"Result type: {type(result)}")
    print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
    
    if isinstance(result, dict):
        for key, value in result.items():
            print(f"\nKey: '{key}'")
            print(f"Value type: {type(value)}")
            if isinstance(value, dict):
                print(f"  Nested keys: {list(value.keys())}")
            elif isinstance(value, list):
                print(f"  List length: {len(value)}")
                if value:
                    print(f"  First item: {value[0]}")
            else:
                print(f"  Value: {str(value)[:100]}...")

def correct_way_to_access_insights():
    """
    Show the correct way to access insights from your analysis result
    """
    # Example of what your result structure looks like:
    example_result = {
        "keywords": ["keyword1", "keyword2", "keyword3"],
        "structured_insights": {
            "keyword1": {
                "titles": ["Title 1", "Title 2", "Title 3"],
                "actions": ["Action 1", "Action 2", "Action 3"]
            },
            "keyword2": {
                "titles": ["Title 1", "Title 2", "Title 3"],
                "actions": ["Action 1", "Action 2", "Action 3"]
            }
        },
        "full_response": "The complete Claude response..."
    }
    
    print("=== CORRECT WAY TO ACCESS INSIGHTS ===")
    
    # Method 1: Direct access (with error checking)
    print("\n1. Direct access method:")
    try:
        keywords = example_result["keywords"]
        structured_insights = example_result["structured_insights"]
        
        for keyword in keywords:
            if keyword in structured_insights:
                titles = structured_insights[keyword]["titles"]
                actions = structured_insights[keyword]["actions"]
                
                print(f"\nKeyword: {keyword}")
                print(f"Titles: {titles}")
                print(f"Actions: {actions}")
    except KeyError as e:
        print(f"KeyError: {e}")
    
    # Method 2: Safe access with .get()
    print("\n2. Safe access method:")
    keywords = example_result.get("keywords", [])
    structured_insights = example_result.get("structured_insights", {})
    
    for keyword in keywords:
        keyword_data = structured_insights.get(keyword, {})
        titles = keyword_data.get("titles", [])
        actions = keyword_data.get("actions", [])
        
        print(f"\nKeyword: {keyword}")
        print(f"Titles: {titles}")
        print(f"Actions: {actions}")

def fix_your_code_example():
    """
    Here's how to fix your code if you're getting 'insight' error
    """
    print("\n=== FIXING YOUR CODE ===")
    
    # WRONG WAY (this will cause 'insight' KeyError):
    print("❌ WRONG WAY:")
    print("result['insight']  # This key doesn't exist!")
    print("result['insights']  # This key doesn't exist either!")
    
    # CORRECT WAY:
    print("\n✅ CORRECT WAY:")
    print("result['structured_insights']  # This is the correct key")
    print("result['structured_insights'][keyword]['titles']")
    print("result['structured_insights'][keyword]['actions']")

def safe_insight_extractor(analysis_result):
    """
    A safe function to extract all insights from your analysis result
    """
    try:
        if not isinstance(analysis_result, dict):
            return {"error": "Analysis result is not a dictionary"}
        
        keywords = analysis_result.get("keywords", [])
        structured_insights = analysis_result.get("structured_insights", {})
        
        if not keywords:
            return {"error": "No keywords found in analysis result"}
        
        extracted_insights = {}
        
        for keyword in keywords:
            if keyword in structured_insights:
                keyword_data = structured_insights[keyword]
                extracted_insights[keyword] = {
                    "titles": keyword_data.get("titles", []),
                    "actions": keyword_data.get("actions", [])
                }
            else:
                extracted_insights[keyword] = {
                    "titles": [],
                    "actions": [],
                    "error": f"No insights found for keyword: {keyword}"
                }
        
        return {
            "success": True,
            "keywords": keywords,
            "insights": extracted_insights
        }
        
    except Exception as e:
        return {"error": f"Error extracting insights: {str(e)}"}

# Updated analyze_question function with better insight extraction
def analyze_question_fixed(question, custom_keywords=""):
    """
    Fixed version of analyze_question that handles insights properly
    """
    try:
        if not question or not question.strip():
            return {
                "error": "Question cannot be empty",
                "keywords": [],
                "insights": {},  # Changed from structured_insights to insights
                "full_response": ""
            }
        
        # Your existing prompt code here...
        full_prompt = f"""You're a senior market analyst with 15+ years of experience. A client asked this question:
{question}

Custom keywords to consider: {custom_keywords}

Please provide a comprehensive analysis following these steps:

Step 1: Extract 5-7 relevant keywords from the question and custom keywords.
Step 2: Order keywords by importance and relevance to the client's question (most important first).
Step 3: For each keyword, provide 3-5 SPECIFIC, NON-GENERIC actionable insights with clear titles.
Step 4: Order insights within each keyword by importance (most important first).

Return response in this EXACT format:

**KEYWORDS IDENTIFIED:**
Keyword 1, Keyword 2, Keyword 3, Keyword 4, Keyword 5

**ANALYSIS BY KEYWORD:**

**KEYWORD 1: [Keyword Name]**

**TITLES:**
1. [Title 1]
2. [Title 2]
3. [Title 3]

**ACTIONS:**
1. [Action 1]
2. [Action 2]
3. [Action 3]

[Continue for all keywords...]
"""
        
        response = claude_messages(full_prompt)
        
        if response.startswith("Error:"):
            return {
                "error": response,
                "keywords": [],
                "insights": {},
                "full_response": response
            }
        
        # Parse the response
        parsed_result = parse_analysis_response(response)
        
        return {
            "keywords": parsed_result.get("keywords", []),
            "insights": parsed_result.get("structured_insights", {}),  # Map to 'insights' key
            "full_response": response,
            "error": None
        }
        
    except Exception as e:
        return {
            "error": f"Error analyzing question: {str(e)}",
            "keywords": [],
            "insights": {},
            "full_response": ""
        }

def claude_messages(prompt):
    """Your existing claude_messages function"""
    try:
        bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_k": 250,
            "top_p": 1,
        }
        
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]
        
    except Exception as e:
        return f"Error calling Claude: {str(e)}"

def parse_analysis_response(response):
    """Your existing parse function"""
    try:
        lines = response.strip().split("\n")
        keywords = []
        structured_insights = {}
        current_keyword = None
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("**KEYWORDS IDENTIFIED:**"):
                continue
            elif line and not line.startswith("**") and ":" not in line and current_keyword is None:
                keywords = [k.strip() for k in line.split(",") if k.strip()]
                continue
            
            if line.startswith("**KEYWORD") and ":" in line:
                try:
                    current_keyword = line.split(":")[1].strip().replace("**", "")
                    if current_keyword not in structured_insights:
                        structured_insights[current_keyword] = {"titles": [], "actions": []}
                    current_section = None
                except IndexError:
                    pass
                continue
            
            if line == "**TITLES:**":
                current_section = "titles"
                continue
            elif line == "**ACTIONS:**":
                current_section = "actions"
                continue
            
            if current_keyword and current_section and line and line[0].isdigit():
                try:
                    content = line.split(".", 1)[1].strip() if "." in line else line
                    structured_insights[current_keyword][current_section].append(content)
                except IndexError:
                    pass
        
        return {
            "keywords": keywords,
            "structured_insights": structured_insights
        }
        
    except Exception as e:
        return {"keywords": [], "structured_insights": {}}

# EXAMPLE USAGE - HOW TO USE YOUR FIXED CODE
def example_usage_fixed():
    """
    Example showing how to use the fixed code
    """
    print("=== EXAMPLE USAGE ===")
    
    # Analyze a question
    question = "How can I improve my e-commerce conversion rates?"
    result = analyze_question_fixed(question)
    
    # Debug the result structure
    debug_analysis_result(result)
    
    # Check for errors
    if result.get("error"):
        print(f"Analysis error: {result['error']}")
        return
    
    # CORRECT way to access insights
    keywords = result.get("keywords", [])
    insights = result.get("insights", {})  # Use 'insights' not 'insight'
    
    print(f"\nKeywords found: {keywords}")
    
    # Access insights for each keyword
    for keyword in keywords:
        if keyword in insights:
            keyword_insights = insights[keyword]
            titles = keyword_insights.get("titles", [])
            actions = keyword_insights.get("actions", [])
            
            print(f"\n--- {keyword} ---")
            print("Titles:")
            for i, title in enumerate(titles, 1):
                print(f"  {i}. {title}")
            
            print("Actions:")
            for i, action in enumerate(actions, 1):
                print(f"  {i}. {action}")

if __name__ == "__main__":
    # Run the debug and example
    correct_way_to_access_insights()
    fix_your_code_example()
    # example_usage_fixed()  # Uncomment to test with actual API call
