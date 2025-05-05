import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils.data_fetcher import fetch_signin_logs
from utils.ai_analyzer import analyze_inactive_users
from utils.logger import setup_logger
import os
from dotenv import load_dotenv
import time
import io
from datetime import datetime

# Load environment variables
load_dotenv()
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Setup logger
logger = setup_logger("inactive_users", "logs/app.log")

# Page UI
st.title("Inactive Users Analysis")
st.markdown("Identify users who have not signed in within a specified period and analyze the results.")

# Session state initialization
if "inactive_users" not in st.session_state:
    st.session_state.inactive_users = None
    logger.debug("Initialized inactive_users in session state")
if "inactivity_days" not in st.session_state:
    st.session_state.inactivity_days = 30
    logger.debug("Initialized inactivity_days in session state with value 30")
if "last_analysis_params" not in st.session_state:
    st.session_state.last_analysis_params = None
    logger.debug("Initialized last_analysis_params in session state")
if "analysis_metrics" not in st.session_state:
    st.session_state.analysis_metrics = None
    logger.debug("Initialized analysis_metrics in session state")

# Check if users_data exists
if "users_data" not in st.session_state or not st.session_state.users_data:
    st.warning("No user data available. Please fetch data from the 'Fetch Data' page first.")
else:
    # Input for inactivity days
    st.session_state.inactivity_days = st.number_input(
        "Enter the number of days for inactivity analysis (e.g., 30):",
        min_value=1,
        max_value=90,
        value=st.session_state.inactivity_days,
        help="Specify the number of days to consider a user inactive. For example, 30 days means users who haven't signed in for 30 days or more."
    )

    # Columns for buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        analyze_button = st.button("Analyze Inactive Users")
    with col2:
        reset_button = st.button("Reset Analysis")

    # Reset functionality
    if reset_button:
        logger.info("Reset Analysis button clicked")
        st.session_state.inactive_users = None
        st.session_state.last_analysis_params = None
        st.session_state.analysis_metrics = None
        st.success("Analysis reset successfully. You can start a new analysis.")
        st.rerun()

    # Analyze inactive users
    if analyze_button:
        logger.info("Analyze Inactive Users button clicked")
        
        # Check if we can use cached results
        current_params = {"inactivity_days": st.session_state.inactivity_days}
        if (st.session_state.inactive_users is not None and 
            st.session_state.last_analysis_params == current_params):
            st.info("Using cached analysis results. Click 'Reset Analysis' to start a new analysis.")
        else:
            # Fetch sign-in logs with retry logic
            max_retries = 3
            fetch_success = False
            for attempt in range(max_retries):
                with st.spinner(f"Fetching recent sign-in logs (Attempt {attempt + 1}/{max_retries})..."):
                    try:
                        fetch_success = fetch_signin_logs(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
                        if fetch_success:
                            logger.info("Successfully fetched sign-in logs")
                            break
                        else:
                            logger.warning(f"Attempt {attempt + 1}: Failed to fetch sign-in logs")
                    except Exception as e:
                        logger.error(f"Attempt {attempt + 1}: Error fetching sign-in logs: {str(e)}")
                time.sleep(2)  # Wait before retrying

            if not fetch_success:
                st.error("Failed to fetch sign-in logs after multiple attempts. Please check your credentials and network connection.")
                logger.error("Failed to fetch sign-in logs after all retries")
            else:
                # Analyze inactive users
                start_time = time.time()
                total_users = len(st.session_state.users_data)
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Simulate progress for better UX
                for i in range(100):
                    progress_bar.progress(i + 1)
                    status_text.text(f"Analyzing inactive users... {i + 1}%")
                    time.sleep(0.01)  # Simulate work
                
                try:
                    st.session_state.inactive_users = analyze_inactive_users(
                        st.session_state.users_data,
                        inactivity_days=st.session_state.inactivity_days
                    )
                    st.session_state.last_analysis_params = current_params
                    
                    # Compute analysis metrics
                    analysis_time = time.time() - start_time
                    inactive_count = len(st.session_state.inactive_users) if st.session_state.inactive_users else 0
                    inactive_percentage = (inactive_count / total_users * 100) if total_users > 0 else 0
                    st.session_state.analysis_metrics = {
                        "total_users": total_users,
                        "inactive_count": inactive_count,
                        "inactive_percentage": inactive_percentage,
                        "analysis_time": analysis_time
                    }
                    logger.info(f"Analysis completed: {inactive_count} inactive users out of {total_users} total users in {analysis_time:.2f} seconds")
                except Exception as e:
                    logger.error(f"Error analyzing inactive users: {str(e)}")
                    st.error(f"Error analyzing inactive users: {str(e)}")
                    st.session_state.inactive_users = None
                    st.session_state.analysis_metrics = None
                finally:
                    progress_bar.empty()
                    status_text.empty()

    # Display analysis results
    if st.session_state.inactive_users is not None:
        if st.session_state.inactive_users:
            try:
                # Convert to DataFrame
                df_inactive = pd.DataFrame(st.session_state.inactive_users)
                
                # Display metrics
                metrics = st.session_state.analysis_metrics
                st.markdown("### Analysis Summary")
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Users Analyzed", metrics["total_users"])
                col2.metric("Inactive Users", metrics["inactive_count"])
                col3.metric("Inactive Percentage", f"{metrics['inactive_percentage']:.2f}%")
                st.markdown(f"**Analysis Time:** {metrics['analysis_time']:.2f} seconds")

                # Sorting and Filtering Options
                st.markdown("### Inactive Users Table")
                sort_by = st.selectbox(
                    "Sort by:",
                    options=["Days Since Last Sign-In", "Display Name", "User ID"],
                    index=0
                )
                sort_ascending = st.checkbox("Sort Ascending", value=False)
                
                filter_department = st.multiselect(
                    "Filter by Department:",
                    options=sorted(set(user.get("Department", "N/A") for user in st.session_state.users_data if user.get("Department"))),
                    default=[]
                )

                # Apply sorting and filtering
                df_filtered = df_inactive.copy()
                if filter_department:
                    # Match user IDs with departments from users_data
                    user_dept_map = {user["User ID"]: user.get("Department", "N/A") for user in st.session_state.users_data}
                    df_filtered["Department"] = df_filtered["User ID"].map(user_dept_map)
                    df_filtered = df_filtered[df_filtered["Department"].isin(filter_department)]
                
                if sort_by:
                    # Handle sorting for "Days Since Last Sign-In"
                    if sort_by == "Days Since Last Sign-In":
                        df_filtered["Sort Key"] = df_filtered["Days Since Last Sign-In"].apply(
                            lambda x: float('inf') if x == "No sign-in recorded" else int(x)
                        )
                        df_filtered = df_filtered.sort_values("Sort Key", ascending=sort_ascending)
                        df_filtered = df_filtered.drop(columns=["Sort Key"])
                    else:
                        df_filtered = df_filtered.sort_values(sort_by, ascending=sort_ascending)

                st.write(
                    f"**Identified Inactive Users (No sign-ins in the last {st.session_state.inactivity_days} days):** "
                    f"Showing {len(df_filtered)} out of {len(st.session_state.inactive_users)} users after filtering."
                )
                st.dataframe(df_filtered)

                # Download button for CSV
                csv_buffer = io.StringIO()
                df_filtered.to_csv(csv_buffer, index=False)
                st.download_button(
                    label="Download Inactive Users as CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"inactive_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

                # Visual Summary: Inactive Users by Department
                if len(df_filtered) > 0:
                    st.markdown("### Inactive Users by Department")
                    user_dept_map = {user["User ID"]: user.get("Department", "N/A") for user in st.session_state.users_data}
                    df_filtered["Department"] = df_filtered["User ID"].map(user_dept_map)
                    dept_counts = df_filtered["Department"].value_counts().reset_index()
                    dept_counts.columns = ["Department", "Inactive Users"]
                    
                    # Create bar chart using matplotlib
                    plt.figure(figsize=(10, 6))
                    plt.bar(dept_counts["Department"], dept_counts["Inactive Users"], color='skyblue')
                    plt.xlabel("Department")
                    plt.ylabel("Number of Inactive Users")
                    plt.title("Inactive Users by Department")
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    
                    # Display the plot in Streamlit
                    st.pyplot(plt)

            except Exception as e:
                logger.error(f"Error displaying inactive users: {str(e)}")
                st.error(f"Error displaying inactive users: {str(e)}")
                st.write("Debug: Raw inactive users response:", st.session_state.inactive_users)
        else:
            logger.warning("No inactive users detected or analysis failed")
            st.write("No inactive users detected or analysis failed. Ensure sign-in logs are available.")