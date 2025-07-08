print("auth.py is loaded!")
import streamlit as st
import pyrebase

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
                st.success("Logged in successfully!")
            except:
                st.error("Invalid email or password")

        elif choice == "Sign Up" and st.sidebar.button("Sign Up"):
            try:
                user = auth.create_user_with_email_and_password(email, password)
                st.session_state['user'] = user
                st.success("Account created successfully!")
            except:
                st.error("Account creation failed")

def is_logged_in():
    return st.session_state.get('user') is not None
