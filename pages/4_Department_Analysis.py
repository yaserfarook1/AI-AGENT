import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils.logger import setup_logger
import os
from dotenv import load_dotenv
import time
import io
from datetime import datetime

# Load environment variables
load_dotenv()

# Setup logger
logger = setup_logger("department_analysis", "logs/app.log")

# Custom CSS for professional styling
st.markdown("""
    <style>
    .main-title {
        font-size: 2.5em;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 0.5em;
    }
    .description {
        font-size: 1.1em;
        color: #4B5563;
        margin-bottom: 1em;
    }
    .card {
        background-color: #F9FAFB;
        padding: 1.5em;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1em;
    }
    .metric-label {
        font-size: 1em;
        color: #6B7280;
    }
    .metric-value {
        font-size: 1.5em;
        font-weight: bold;
        color: #1E3A8A;
    }
    .stButton>button {
        background-color: #1E3A8A;
        color: white;
        border-radius: 5px;
        padding: 0.5em 1em;
    }
    .stButton>button:hover {
        background-color: #3B82F6;
    }
    </style>
""", unsafe_allow_html=True)

# Page UI
st.markdown('<div class="main-title">Department Analysis</div>', unsafe_allow_html=True)
st.markdown('<div class="description">Analyze the departments in your organization and their user distribution.</div>', unsafe_allow_html=True)

# Session state initialization
if "department_metrics" not in st.session_state:
    st.session_state.department_metrics = None
    logger.debug("Initialized department_metrics in session state")
if "last_analysis_data" not in st.session_state:
    st.session_state.last_analysis_data = None
    logger.debug("Initialized last_analysis_data in session state")
if "analysis_metrics" not in st.session_state:
    st.session_state.analysis_metrics = None
    logger.debug("Initialized analysis_metrics in session state")

# Helper function to safely handle None values
def safe_str(value, default="N/A"):
    return str(value).strip().lower() if value is not None else default.strip().lower()

# Check if users_data exists
if "users_data" not in st.session_state or not st.session_state.users_data:
    st.warning("No user data available. Please fetch data from the 'Fetch Data' page first.")
else:
    # Columns for buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        analyze_button = st.button("Analyze Departments")
    with col2:
        reset_button = st.button("Reset Analysis")

    # Reset functionality
    if reset_button:
        logger.info("Reset Analysis button clicked")
        st.session_state.department_metrics = None
        st.session_state.last_analysis_data = None
        st.session_state.analysis_metrics = None
        st.success("Analysis reset successfully. You can start a new analysis.")
        st.rerun()

    # Analyze departments
    if analyze_button:
        logger.info("Analyze Departments button clicked")
        
        # Check if we can use cached results
        current_data = str(st.session_state.users_data)  # Convert to string for comparison
        if (st.session_state.department_metrics is not None and 
            st.session_state.last_analysis_data == current_data):
            st.info("Using cached analysis results. Click 'Reset Analysis' to start a new analysis.")
        else:
            start_time = time.time()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Simulate progress for better UX
            for i in range(100):
                progress_bar.progress(i + 1)
                status_text.text(f"Analyzing departments... {i + 1}%")
                time.sleep(0.01)  # Simulate work
            
            try:
                # Extract departments directly from users_data without lowercase normalization
                identified_departments = sorted(set(
                    user.get("Department", "N/A") 
                    for user in st.session_state.users_data 
                    if user.get("Department") and user.get("Department") != "N/A"
                ))
                logger.debug(f"Identified departments: {identified_departments}")
                
                # Compute department metrics
                department_counts = {dept: 0 for dept in identified_departments}
                enabled_counts = {dept: 0 for dept in identified_departments}
                user_dept_mapping = []
                
                for user in st.session_state.users_data:
                    dept = user.get("Department", "N/A")
                    if dept and dept != "N/A":  # Only count users with valid departments
                        # Normalize for counting, but preserve original department for display
                        dept_normalized = safe_str(dept)
                        # Map normalized department back to original department
                        found_dept = None
                        for orig_dept in identified_departments:
                            if safe_str(orig_dept) == dept_normalized:
                                found_dept = orig_dept
                                break
                        if found_dept:
                            department_counts[found_dept] += 1
                            enabled = user.get("Account Enabled", False)
                            if isinstance(enabled, str):
                                enabled = enabled.lower() == "true"
                            if enabled:
                                enabled_counts[found_dept] += 1
                            user_dept_mapping.append({
                                "user_principal_name": safe_str(user.get("User Principal Name", "N/A"), "N/A"),
                                "display_name": safe_str(user.get("Display Name", "N/A"), "N/A"),
                                "department": found_dept,  # Use original department name
                                "job_title": safe_str(user.get("Job Title", "N/A"), "N/A"),
                                "account_enabled": enabled
                            })
                        else:
                            logger.debug(f"Department '{dept}' not found in identified departments")
                
                # Compute additional metrics
                total_users = len(st.session_state.users_data)
                users_with_dept = sum(department_counts.values())
                dept_percentages = {dept: (count / users_with_dept * 100) if users_with_dept > 0 else 0 
                                  for dept, count in department_counts.items()}
                enabled_percentages = {dept: (enabled_counts[dept] / count * 100) if count > 0 else 0 
                                     for dept, count in department_counts.items()}
                
                st.session_state.department_metrics = {
                    "counts": department_counts,
                    "enabled_counts": enabled_counts,
                    "percentages": dept_percentages,
                    "enabled_percentages": enabled_percentages,
                    "user_mapping": user_dept_mapping
                }
                st.session_state.last_analysis_data = current_data
                
                # Analysis metrics
                analysis_time = time.time() - start_time
                st.session_state.analysis_metrics = {
                    "total_users": total_users,
                    "users_with_dept": users_with_dept,
                    "total_departments": len(identified_departments),
                    "analysis_time": analysis_time
                }
                logger.info(f"Analysis completed: {len(identified_departments)} departments, {users_with_dept} users with departments in {analysis_time:.2f} seconds")
            
            except Exception as e:
                logger.error(f"Error analyzing departments: {str(e)}")
                st.error(f"Error analyzing departments: {str(e)}")
                st.session_state.department_metrics = None
                st.session_state.analysis_metrics = None
            finally:
                progress_bar.empty()
                status_text.empty()

    # Display results if available
    if st.session_state.department_metrics and st.session_state.analysis_metrics:
        # Summary metrics
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="metric-label">Total Departments</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{st.session_state.analysis_metrics["total_departments"]}</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="metric-label">Users with Department</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{st.session_state.analysis_metrics["users_with_dept"]}</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="metric-label">Analysis Time (seconds)</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{st.session_state.analysis_metrics["analysis_time"]:.2f}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["Overview", "User Details", "Visualization"])

        with tab1:
            st.subheader("Department Overview")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            counts_df = pd.DataFrame([
                {
                    "department": dept,
                    "user_count": count,
                    "percentage_of_users_with_dept": f"{st.session_state.department_metrics['percentages'][dept]:.2f}%",
                    "enabled_users": st.session_state.department_metrics["enabled_counts"][dept],
                    "enabled_percentage": f"{st.session_state.department_metrics['enabled_percentages'][dept]:.2f}%"
                }
                for dept, count in st.session_state.department_metrics["counts"].items()
            ])
            
            # Sorting options
            sort_by = st.selectbox(
                "Sort by:",
                options=["department", "user_count", "percentage_of_users_with_dept", "enabled_users", "enabled_percentage"],
                index=1,
                key="overview_sort"
            )
            sort_ascending = st.checkbox("Sort Ascending", value=False, key="overview_ascending")
            
            if sort_by in ["percentage_of_users_with_dept", "enabled_percentage"]:
                counts_df[sort_by] = counts_df[sort_by].str.rstrip('%').astype(float)
            counts_df = counts_df.sort_values(sort_by, ascending=sort_ascending)
            if sort_by in ["percentage_of_users_with_dept", "enabled_percentage"]:
                counts_df[sort_by] = counts_df[sort_by].apply(lambda x: f"{x:.2f}%")
            
            st.dataframe(counts_df, use_container_width=True)

            # Download button for CSV
            csv_buffer = io.StringIO()
            counts_df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="Download Department Overview as CSV",
                data=csv_buffer.getvalue(),
                file_name=f"department_overview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with tab2:
            st.subheader("Users by Department")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            user_df = pd.DataFrame(st.session_state.department_metrics["user_mapping"])
            
            # Filtering and sorting options
            filter_department = st.multiselect(
                "Filter by Department:",
                options=sorted(set(
                    user.get("Department", "N/A") 
                    for user in st.session_state.users_data 
                    if user.get("Department") and user.get("Department") != "N/A"
                )),
                default=[]
            )
            selected_status = st.selectbox(
                "Filter by Account Status",
                options=["All", "Enabled", "Disabled"],
                key="user_details_status"
            )
            
            filtered_df = user_df.copy()
            if filter_department:
                filtered_df = filtered_df[filtered_df["department"].isin(filter_department)]
            if selected_status != "All":
                filtered_df = filtered_df[filtered_df["account_enabled"] == (selected_status == "Enabled")]
            
            sort_by = st.selectbox(
                "Sort by:",
                options=["user_principal_name", "display_name", "department", "job_title", "account_enabled"],
                index=0,
                key="user_details_sort"
            )
            sort_ascending = st.checkbox("Sort Ascending", value=True, key="user_details_ascending")
            
            try:
                filtered_df = filtered_df.sort_values(sort_by, ascending=sort_ascending)
            except KeyError as e:
                st.error(f"Error sorting table: Column '{e}' not found. Available columns: {list(filtered_df.columns)}")
                logger.error(f"KeyError in sorting user details: {str(e)}")
            
            st.write(f"Showing {len(filtered_df)} out of {len(user_df)} users after filtering.")
            st.dataframe(filtered_df, use_container_width=True)

            # Download button for CSV
            csv_buffer = io.StringIO()
            filtered_df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="Download User Details as CSV",
                data=csv_buffer.getvalue(),
                file_name=f"users_by_department_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with tab3:
            st.subheader("Department Distribution")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            
            chart_type = st.radio(
                "Select Chart Type:",
                options=["Bar Chart", "Pie Chart"],
                index=0
            )
            
            counts_df = pd.DataFrame([
                {
                    "department": dept,
                    "user_count": count
                }
                for dept, count in st.session_state.department_metrics["counts"].items()
            ])
            
            if chart_type == "Bar Chart":
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.bar(counts_df["department"], counts_df["user_count"], color="#1E3A8A")
                ax.set_xlabel("Department")
                ax.set_ylabel("Number of Users")
                ax.set_title("User Distribution Across Departments")
                plt.xticks(rotation=45, ha="right")
                plt.tight_layout()
                st.pyplot(fig)
            else:
                fig, ax = plt.subplots(figsize=(8, 8))
                ax.pie(
                    counts_df["user_count"],
                    labels=counts_df["department"],
                    autopct='%1.1f%%',
                    startangle=140,
                    colors=plt.cm.Paired(range(len(counts_df)))
                )
                ax.set_title("User Distribution Across Departments")
                plt.tight_layout()
                st.pyplot(fig)
            
            st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.info("Click 'Analyze Departments' to start the analysis.")