import boto3

def find_exact_model_ids():
    """Find the exact model IDs you have access to"""
    
    # Your region (change if needed)
    region = "us-east-1"
    
    try:
        bedrock = boto3.client("bedrock", region_name=region)
        response = bedrock.list_foundation_models()
        
        print(f"🔍 Searching for Anthropic models in {region}...")
        print(f"{'='*80}")
        
        anthropic_models = []
        for model in response['modelSummaries']:
            if 'anthropic' in model['modelId'].lower():
                anthropic_models.append(model)
                print(f"Model ID: {model['modelId']}")
                print(f"Model Name: {model.get('modelName', 'N/A')}")
                print(f"Provider: {model.get('providerName', 'N/A')}")
                print(f"Status: Available")
                print("-" * 80)
        
        if anthropic_models:
            print(f"\n✅ Found {len(anthropic_models)} Anthropic models")
            print("\n🔧 Try these model IDs in your code:")
            for i, model in enumerate(anthropic_models[:3], 1):
                print(f"{i}. {model['modelId']}")
                
        else:
            print("❌ No Anthropic models found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Try changing the region to us-west-2 or eu-west-1")

if __name__ == "__main__":
    find_exact_model_ids()
