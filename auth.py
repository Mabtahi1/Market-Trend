print("auth.py is loaded!")
import streamlit as st
import pyrebase
from datetime import datetime, timedelta
import json

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

def show_login():
    if 'user' not in st.session_state:
        st.session_state['user'] = None

    if not st.session_state['user']:
        st.sidebar.subheader("Login / Sign Up")
        choice = st.sidebar.selectbox("Choose Action", ["Login", "Sign Up"])
        email = st.sidebar.text_input("Email")
        password = st.sidebar.text_input("Password", type="password")

        if choice == "Login" and st.sidebar.button("Login"):
            try:
                user = auth.sign_in_with_email_and_password(email, password)
                st.session_state['user'] = user
                # Initialize user data if it doesn't exist
                initialize_user_data(email)
                st.success("Logged in successfully!")
                st.rerun()
            except:
                st.error("Invalid email or password")

        elif choice == "Sign Up" and st.sidebar.button("Sign Up"):
            try:
                user = auth.create_user_with_email_and_password(email, password)
                st.session_state['user'] = user
                # Create initial user data with free trial
                create_user_subscription(email, "trial")
                st.success("Account created successfully!")
                st.rerun()
            except:
                st.error("Account creation failed")

def is_logged_in():
    return st.session_state.get('user') is not None

def initialize_user_data(email):
    """Initialize user data if it doesn't exist"""
    try:
        user_data = db.child("users").child(email.replace(".", "_")).get().val()
        if not user_data:
            create_user_subscription(email, "trial")
    except:
        create_user_subscription(email, "trial")

def create_user_subscription(email, plan_type):
    """Create user subscription data"""
    user_key = email.replace(".", "_")
    
    plans = {
        "trial": {
            "summaries_per_month": 2,
            "sources_limit": 1,
            "has_competitor_tracking": False,
            "has_automation": False,
            "has_forecasting": False
        },
        "basic": {
            "summaries_per_month": 5,
            "sources_limit": 3,
            "has_competitor_tracking": False,
            "has_automation": False,
            "has_forecasting": False
        },
        "pro": {
            "summaries_per_month": "unlimited",
            "sources_limit": "unlimited",
            "has_competitor_tracking": True,
            "has_automation": False,
            "has_forecasting": False
        },
        "onetime": {
            "summaries_per_month": 3,
            "sources_limit": 3,
            "has_competitor_tracking": False,
            "has_automation": False,
            "has_forecasting": False
        },
        "starter": {
            "summaries_per_month": 10,
            "sources_limit": 5,
            "has_competitor_tracking": False,
            "has_automation": True,
            "has_forecasting": False
        },
        "premium": {
            "summaries_per_month": "unlimited",
            "sources_limit": "unlimited",
            "has_competitor_tracking": True,
            "has_automation": True,
            "has_forecasting": True
        }
    }
    
    user_data = {
        "email": email,
        "subscription_type": plan_type,
        "subscription_status": "active" if plan_type != "trial" else "trial",
        "payment_date": datetime.now().isoformat(),
        "usage_limits": plans.get(plan_type, plans["trial"]),
        "current_usage": {
            "summaries_this_month": 0,
            "last_reset_date": datetime.now().replace(day=1).isoformat()
        }
    }
    
    db.child("users").child(user_key).set(user_data)

def check_usage_limits(email, action_type="summary"):
    """Check if user can perform action based on their plan"""
    user_key = email.replace(".", "_")
    
    try:
        user_data = db.child("users").child(user_key).get().val()
        
        if not user_data:
            return False, "No subscription found. Please contact support."
        
        if user_data.get('subscription_status') not in ['active', 'trial']:
            return False, "Subscription expired. Please upgrade your plan."
        
        usage_limits = user_data.get('usage_limits', {})
        current_usage = user_data.get('current_usage', {})
        
        if action_type == "summary":
            limit = usage_limits.get('summaries_per_month', 0)
            current = current_usage.get('summaries_this_month', 0)
            
            if limit != "unlimited" and current >= limit:
                plan_type = user_data.get('subscription_type', 'trial')
                return False, f"Monthly limit of {limit} summaries reached for {plan_type} plan. Please upgrade to continue."
        
        return True, "Access granted"
        
    except Exception as e:
        return False, f"Error checking limits: {str(e)}"

def increment_usage(email, action_type="summary"):
    """Increment user's usage count"""
    user_key = email.replace(".", "_")
    
    try:
        if action_type == "summary":
            current_usage = db.child("users").child(user_key).child("current_usage").child("summaries_this_month").get().val() or 0
            db.child("users").child(user_key).child("current_usage").child("summaries_this_month").set(current_usage + 1)
    except Exception as e:
        st.error(f"Error updating usage: {str(e)}")

def get_user_info(email):
    """Get user subscription info"""
    user_key = email.replace(".", "_")
    
    try:
        user_data = db.child("users").child(user_key).get().val()
        return user_data
    except:
        return None

def show_usage_info():
    """Display user's current usage and limits"""
    if is_logged_in():
        email = st.session_state['user']['email']
        user_info = get_user_info(email)
        
        if user_info:
            plan = user_info.get('subscription_type', 'trial')
            status = user_info.get('subscription_status', 'trial')
            usage_limits = user_info.get('usage_limits', {})
            current_usage = user_info.get('current_usage', {})
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Plan", plan.title())
            
            with col2:
                limit = usage_limits.get('summaries_per_month', 0)
                current = current_usage.get('summaries_this_month', 0)
                if limit == "unlimited":
                    st.metric("Usage", f"{current}/∞")
                else:
                    st.metric("Usage", f"{current}/{limit}")
            
            with col3:
                st.metric("Status", status.title())
            
            if status == "trial":
                st.warning("⚠️ You're on a trial plan. Upgrade for more features!")
                if st.button("🔗 Upgrade Plan"):
                    st.markdown('[Upgrade Now](https://prolexisanalytics.com)')
