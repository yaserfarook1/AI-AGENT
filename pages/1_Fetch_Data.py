import streamlit as st
import pandas as pd
from utils.data_fetcher import fetch_signin_logs, fetch_users
from utils.logger import setup_logger
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Setup logger
logger = setup_logger("fetch_data", "logs/app.log")

# Page UI
st.title("Fetch Data")
st.markdown("Fetch user and sign-in data from Microsoft Graph to begin analysis.")

# Session state initialization
if "users_data" not in st.session_state:
    st.session_state.users_data = []
    logger.debug("Initialized users_data in session state")

# Fetch data
if st.button("Fetch Data"):
    logger.info("Fetch Data button clicked")
    with st.spinner("Fetching data from Microsoft Graph..."):
        fetch_success = fetch_signin_logs(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
        if fetch_success:
            logger.info("Successfully fetched and created new sign-in logs file")
        else:
            logger.warning("Failed to fetch sign-in logs, proceeding with user fetch")
        st.session_state.users_data = fetch_users(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
        if st.session_state.users_data:
            logger.info(f"Successfully retrieved {len(st.session_state.users_data)} users")
            st.success(f"✅ Successfully retrieved {len(st.session_state.users_data)} users!")
        else:
            logger.error("Failed to retrieve user data")
            st.error("❌ Failed to retrieve user data.")

# Display fetched users
if st.session_state.users_data:
    df_users = pd.DataFrame(st.session_state.users_data)
    all_groups = [g for user in st.session_state.users_data for g in user["Groups"].split(", ") if user["Groups"] != "No groups"]
    unique_groups = set(all_groups)
    logger.debug(f"Total users: {len(df_users)}, Total groups: {len(unique_groups)}")
    st.write(f"**Total Users**: {len(df_users)} | **Total Groups**: {len(unique_groups)}")
    st.subheader("User Details")
    st.dataframe(df_users)
else:
    st.info("No user data available. Click 'Fetch Data' to connect to Microsoft Graph.")