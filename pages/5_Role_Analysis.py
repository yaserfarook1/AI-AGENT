import streamlit as st
from utils.logger import setup_logger
import pandas as pd
import matplotlib.pyplot as plt
import time
import io
from datetime import datetime

# Setup logger
logger = setup_logger("role_analysis", "logs/app.log")

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
st.markdown('<div class="main-title">Role Analysis</div>', unsafe_allow_html=True)
st.markdown('<div class="description">Analyze roles within your organization based on job titles.</div>', unsafe_allow_html=True)

# Session state initialization
if "identified_roles" not in st.session_state:
    st.session_state.identified_roles = None
    logger.debug("Initialized identified_roles in session state")
if "role_metrics" not in st.session_state:
    st.session_state.role_metrics = None
    logger.debug("Initialized role_metrics in session state")
if "last_analysis_data" not in st.session_state:
    st.session_state.last_analysis_data = None
    logger.debug("Initialized last_analysis_data in session state")
if "analysis_metrics" not in st.session_state:
    st.session_state.analysis_metrics = None
    logger.debug("Initialized analysis_metrics in session state")

# Helper function to safely handle None values
def safe_str(value, default="N/A"):
    if value is not None:
        return str(value).strip()
    return default if default is None else default.strip()

# Helper function to normalize job titles
def normalize_role(role):
    if not role:
        return None
    # Convert to lowercase and correct common typos
    role = role.lower()
    role = role.replace("engeer", "engineer")  # Fix typos like "Security Engeer"
    role = role.replace("enginner", "engineer")  # Fix typos like "Security Enginner"
    return role.strip()

# Helper function to validate roles
def is_valid_role(role):
    if not role or len(role) < 2:  # Role should have at least 2 characters
        return False
    invalid_patterns = ["...", "plaintext", "summary", "metadata", "```"]
    role_lower = role.lower()
    if any(pattern in role_lower for pattern in invalid_patterns):
        return False
    return True

# Check if users_data exists
if "users_data" not in st.session_state or not st.session_state.users_data:
    st.warning("No user data available. Please fetch data from the 'Fetch Data' page first.")
else:
    # Columns for buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        analyze_button = st.button("Analyze Roles")
    with col2:
        reset_button = st.button("Reset Analysis")

    # Reset functionality
    if reset_button:
        logger.info("Reset Analysis button clicked")
        st.session_state.identified_roles = None
        st.session_state.role_metrics = None
        st.session_state.last_analysis_data = None
        st.session_state.analysis_metrics = None
        st.success("Analysis reset successfully. You can start a new analysis.")
        st.rerun()

    # Analyze roles
    if analyze_button:
        logger.info("Analyze Roles button clicked")
        
        # Check if we can use cached results
        current_data = str(st.session_state.users_data)
        if (st.session_state.identified_roles is not None and 
            st.session_state.last_analysis_data == current_data):
            st.info("Using cached analysis results. Click 'Reset Analysis' to start a new analysis.")
        else:
            start_time = time.time()
            progress_bar = st.progress(0)
            status_text = st.empty()
            status_text.text("Extracting roles from user data...")

            # Extract distinct roles from Job Title field
            raw_roles = set()
            for user in st.session_state.users_data:
                job_title = safe_str(user.get("Job Title", None), default=None)
                normalized_title = normalize_role(job_title)
                if normalized_title:  # Only add non-None normalized job titles
                    raw_roles.add(normalized_title)
            
            # Log raw roles for debugging
            logger.debug(f"Raw roles before filtering: {sorted(raw_roles)}")
            
            # Filter out invalid roles
            identified_roles = [role for role in raw_roles if is_valid_role(role)]
            st.session_state.identified_roles = sorted(identified_roles)
            logger.debug(f"Extracted and filtered roles: {st.session_state.identified_roles}")
            logger.info(f"Successfully identified {len(st.session_state.identified_roles)} roles")

            # Validate the number of roles
            expected_roles_count = 97  # Based on NLP query result
            if len(st.session_state.identified_roles) != expected_roles_count:
                logger.warning(f"Role count mismatch: Expected {expected_roles_count}, but found {len(st.session_state.identified_roles)} roles")
                # st.warning(f"Expected {expected_roles_count} roles, but found {len(st.session_state.identified_roles)}. Please check the data for inconsistencies.")

            # Compute role metrics
            role_counts = {role: 0 for role in st.session_state.identified_roles}
            role_counts["Unassigned"] = 0  # Add Unassigned role for users without a match
            user_role_mapping = []
            unassigned_users = []
            
            # Map users to roles based on Job Title
            for user in st.session_state.users_data:
                user_info = {
                    "user_principal_name": safe_str(user.get("User Principal Name", "N/A")),
                    "display_name": safe_str(user.get("Display Name", "N/A")),
                    "job_title": safe_str(user.get("Job Title", "N/A")),
                    "department": safe_str(user.get("Department", "N/A")),
                    "groups": safe_str(user.get("Groups", "N/A"))
                }
                assigned_role = None
                job_title = normalize_role(user_info["job_title"])
                if job_title and job_title in st.session_state.identified_roles:
                    assigned_role = job_title
                if assigned_role:
                    role_counts[assigned_role] += 1
                else:
                    assigned_role = "Unassigned"
                    role_counts["Unassigned"] += 1
                    unassigned_users.append(user_info["user_principal_name"])
                
                user_role_mapping.append({
                    "user_principal_name": user_info["user_principal_name"],
                    "display_name": user_info["display_name"],
                    "job_title": user_info["job_title"],
                    "department": user_info["department"],
                    "role": assigned_role
                })
            
            # Log unassigned users
            if unassigned_users:
                logger.info(f"Unassigned users: {unassigned_users}")
                st.warning(f"{len(unassigned_users)} users were not assigned to any role and have been categorized as 'Unassigned'.")
            
            # Compute additional metrics
            total_users = len(st.session_state.users_data)
            users_with_role = sum(role_counts[role] for role in role_counts if role != "Unassigned")
            role_percentages = {role: (count / total_users * 100) if total_users > 0 else 0 
                              for role, count in role_counts.items()}
            
            st.session_state.role_metrics = {
                "counts": role_counts,
                "percentages": role_percentages,
                "user_mapping": user_role_mapping
            }
            st.session_state.last_analysis_data = current_data
            
            # Analysis metrics
            analysis_time = time.time() - start_time
            st.session_state.analysis_metrics = {
                "total_users": total_users,
                "users_with_role": users_with_role,
                "total_roles": len(st.session_state.identified_roles) + 1,  # Include Unassigned
                "analysis_time": analysis_time
            }
            logger.info(f"Analysis completed: {len(st.session_state.identified_roles)} roles, {users_with_role} users with roles (excluding Unassigned) in {analysis_time:.2f} seconds")
            
            progress_bar.empty()
            status_text.empty()

    # Display results if available
    if st.session_state.identified_roles is not None and st.session_state.role_metrics and st.session_state.analysis_metrics:
        # Summary metrics
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="metric-label">Total Roles</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{st.session_state.analysis_metrics["total_roles"]}</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="metric-label">Users with Role</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{st.session_state.analysis_metrics["users_with_role"]}</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="metric-label">Analysis Time (seconds)</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-value">{st.session_state.analysis_metrics["analysis_time"]:.2f}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["Overview", "User Details", "Visualization"])

        with tab1:
            st.subheader("Role Overview")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            counts_df = pd.DataFrame([
                {
                    "role": role,
                    "user_count": count,
                    "percentage_of_users": f"{st.session_state.role_metrics['percentages'][role]:.2f}%"
                }
                for role, count in st.session_state.role_metrics["counts"].items()
            ])
            
            # Sorting options
            sort_by = st.selectbox(
                "Sort by:",
                options=["role", "user_count", "percentage_of_users"],
                index=1,
                key="overview_sort"
            )
            sort_ascending = st.checkbox("Sort Ascending", value=False, key="overview_ascending")
            
            if sort_by == "percentage_of_users":
                counts_df[sort_by] = counts_df[sort_by].str.rstrip('%').astype(float)
            counts_df = counts_df.sort_values(sort_by, ascending=sort_ascending)
            if sort_by == "percentage_of_users":
                counts_df[sort_by] = counts_df[sort_by].apply(lambda x: f"{x:.2f}%")
            
            st.dataframe(counts_df, use_container_width=True)

            # Download button for CSV
            csv_buffer = io.StringIO()
            counts_df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="Download Role Overview as CSV",
                data=csv_buffer.getvalue(),
                file_name=f"role_overview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with tab2:
            st.subheader("Users by Role")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            user_df = pd.DataFrame(st.session_state.role_metrics["user_mapping"])
            
            # Filtering and sorting options
            filter_role = st.multiselect(
                "Filter by Role:",
                options=sorted(st.session_state.role_metrics["counts"].keys()),
                default=[]
            )
            
            filtered_df = user_df.copy()
            if filter_role:
                filtered_df = filtered_df[filtered_df["role"].isin(filter_role)]
            
            sort_by = st.selectbox(
                "Sort by:",
                options=["user_principal_name", "display_name", "job_title", "department", "role"],
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
                file_name=f"users_by_role_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with tab3:
            st.subheader("Role Distribution")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            
            # Option to limit the number of roles displayed
            max_roles = st.slider("Select number of top roles to display:", 5, len(st.session_state.role_metrics["counts"]), 10)
            
            chart_type = st.radio(
                "Select Chart Type:",
                options=["Bar Chart", "Pie Chart"],
                index=0
            )
            
            # Prepare data for visualization (sort by user count and limit to top N roles)
            counts_df = pd.DataFrame([
                {
                    "role": role,
                    "user_count": count
                }
                for role, count in st.session_state.role_metrics["counts"].items()
            ])
            counts_df = counts_df.sort_values("user_count", ascending=False).head(max_roles)
            
            if chart_type == "Bar Chart":
                fig, ax = plt.subplots(figsize=(12, 8))
                ax.bar(counts_df["role"], counts_df["user_count"], color="#1E3A8A")
                ax.set_xlabel("Role")
                ax.set_ylabel("Number of Users")
                ax.set_title(f"Top {max_roles} Roles by User Distribution")
                plt.xticks(rotation=45, ha="right")
                plt.tight_layout()
                st.pyplot(fig)
            else:
                fig, ax = plt.subplots(figsize=(10, 10))
                ax.pie(
                    counts_df["user_count"],
                    labels=counts_df["role"],
                    autopct='%1.1f%%',
                    startangle=140,
                    colors=plt.cm.Paired(range(len(counts_df)))
                )
                ax.set_title(f"Top {max_roles} Roles by User Distribution")
                plt.tight_layout()
                st.pyplot(fig)
            
            st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.info("Click 'Analyze Roles' to start the analysis.")