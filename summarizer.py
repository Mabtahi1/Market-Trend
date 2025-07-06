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
        
        # Model IDs based on your access (try newest first)
        model_ids = [
            "anthropic.claude-3-5-haiku-20241022-v1:0",    # Claude 3.5 Haiku
            "anthropic.claude-3-5-sonnet-20241022-v2:0",   # Claude 3.5 Sonnet v2
            "anthropic.claude-3-haiku-20240307-v1:0",      # Claude 3 Haiku
            "anthropic.claude-3-sonnet-20240229-v1:0",     # Fallback
            "anthropic.claude-instant-v1"                   # Fallback
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
            # Try Claude 3+ format
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
