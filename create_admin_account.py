import pyrebase
from datetime import datetime

firebase_config = {
    "apiKey": "AIzaSyDt6y7YRFVF_zrMTYPn4z4ViHjLbmfMsLQ",
    "authDomain": "trend-summarizer-6f28e.firebaseapp.com",
    "projectId": "trend-summarizer-6f28e",
    "storageBucket": "trend-summarizer-6f28e.firebasestorage.app",
    "messagingSenderId": "655575726457",
    "databaseURL": "https://trend-summarizer-6f28e-default-rtdb.firebaseio.com",
    "appId": "1:655575726457:web:9ae1d0d363c804edc9d7a8",
    "measurementId": "G-HHY482GQKZ"
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database()

def create_admin_account():
    email = "abtahimehdi8@gmail.com"
    user_key = email.replace(".", "_")
    
    # Create user data
    user_data = {
        "email": email,
        "subscription_type": "premium",
        "subscription_status": "active",
        "payment_date": datetime.now().isoformat(),
        "usage_limits": {
            "summaries_per_month": "unlimited",
            "sources_limit": "unlimited",
            "has_competitor_tracking": True,
            "has_automation": True,
            "has_forecasting": True
        },
        "current_usage": {
            "summaries_this_month": 0,
            "last_reset_date": datetime.now().replace(day=1).isoformat()
        }
    }
    
    try:
        # Add to database
        db.child("users").child(user_key).set(user_data)
        print(f"✅ Successfully created admin account for {email}")
        print(f"Account type: Premium")
        print(f"Status: Active")
        
        # Verify it was created
        result = db.child("users").child(user_key).get()
        if result.val():
            print("✅ Account verified in database!")
            print(f"Data: {result.val()}")
        else:
            print("❌ Account not found after creation")
            
    except Exception as e:
        print(f"❌ Error creating account: {e}")

if __name__ == "__main__":
    create_admin_account()
