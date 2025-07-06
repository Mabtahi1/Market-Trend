import boto3
import json

class SmartBedrockSummarizer:
    def __init__(self):
        self.working_model = None
        self.working_region = None
        self.model_format = None
        self.bedrock_client = None
        
        # Try to find a working model on initialization
        self._find_working_model()
    
    def _find_working_model(self):
        """Automatically find a working Claude model"""
        
        # Common regions where Claude is available
        regions = ["us-east-1", "us-west-2", "eu-west-1"]
        
        # Common Claude model IDs
        model_ids = [
            "anthropic.claude-3-haiku-20240307-v1:0",
            "anthropic.claude-3-sonnet-20240229-v1:0",
            "anthropic.claude-instant-v1",
            "anthropic.claude-v2:1",
            "anthropic.claude-v2"
        ]
        
        print("🔍 Searching for working Claude model...")
        
        for region in regions:
            print(f"  Trying region: {region}")
            
            try:
                bedrock = boto3.client("bedrock-runtime", region_name=region)
                
                for model_id in model_ids:
                    if self._test_model(bedrock, model_id, region):
                        self.bedrock_client = bedrock
                        self.working_model = model_id
                        self.working_region = region
                        print(f"✅ Found working model: {model_id} in {region}")
                        return
                        
            except Exception as e:
                print(f"  ❌ Region {region} failed: {e}")
                continue
        
        print("❌ No working Claude model found!")
        print("Please check your AWS Bedrock model access permissions.")
    
    def _test_model(self, bedrock_client, model_id, region):
        """Test if a model works"""
        try:
            # Try Claude 3 format first
            response = bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 10,
                    "temperature": 0.1,
                    "messages": [{"role": "user", "content": "Test"}]
                }),
                contentType="application/json",
                accept="application/json"
            )
            self.model_format = "claude3"
            return True
            
        except Exception as e1:
            # Try legacy format
            try:
                response = bedrock_client.invoke_model(
                    modelId=model_id,
                    body=json.dumps({
                        "prompt": f"\n\nHuman: Test\n\nAssistant:",
                        "max_tokens": 10,
                        "temperature": 0.1,
                        "stop_sequences": ["\n\nHuman:"]
                    }),
                    contentType="application/json",
                    accept="application/json"
                )
                self.model_format = "legacy"
                return True
                
            except Exception as e2:
                return False
    
    def summarize_trends(self, text):
        """Summarize trends from text content"""
        
        if not self.working_model:
            return "❌ No working Claude model found. Please check your AWS Bedrock access."
        
        prompt = f"""Analyze the following content and extract:
1. Top trends or topics
2. Summary of each trend (1-2 lines)
3. Any competitor mentions
4. Overall brand perception

Content:
{text}

Return in bullet-point format."""
        
        try:
            if self.model_format == "claude3":
                # Claude 3 format
                response = self.bedrock_client.invoke_model(
                    modelId=self.working_model,
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 1000,
                        "temperature": 0.7,
                        "messages": [{"role": "user", "content": prompt}]
                    }),
                    contentType="application/json",
                    accept="application/json"
                )
                
                result = json.loads(response['body'].read().decode())
                return result["content"][0]["text"]
                
            else:
                # Legacy format
                formatted_prompt = f"\n\nHuman: {prompt}\n\nAssistant:"
                
                response = self.bedrock_client.invoke_model(
                    modelId=self.working_model,
                    body=json.dumps({
                        "prompt": formatted_prompt,
                        "max_tokens": 1000,
                        "temperature": 0.7,
                        "stop_sequences": ["\n\nHuman:"]
                    }),
                    contentType="application/json",
                    accept="application/json"
                )
                
                result = json.loads(response['body'].read().decode())
                return result.get("completion", "").strip()
                
        except Exception as e:
            return f"❌ Error summarizing content: {e}"

# Usage
def summarize_trends(text):
    """Simple wrapper function that maintains your original API"""
    summarizer = SmartBedrockSummarizer()
    return summarizer.summarize_trends(text)

# Example usage
if __name__ == "__main__":
    # Test the summarizer
    test_text = """
    The tech industry is seeing major shifts with AI adoption accelerating across sectors. 
    Companies like Microsoft and Google are investing heavily in AI infrastructure. 
    Meanwhile, the electric vehicle market continues to grow with Tesla leading but 
    facing increased competition from traditional automakers.
    """
    
    result = summarize_trends(test_text)
    print("📋 Summary Result:")
    print(result)
