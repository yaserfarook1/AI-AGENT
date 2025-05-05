import streamlit as st
import requests
from datetime import datetime, timedelta
import csv
import os
from utils.auth import get_access_token
from utils.logger import setup_logger

# Setup logger
logger = setup_logger("data_fetcher", "logs/app.log")

def fetch_signin_logs(tenant_id, client_id, client_secret):
    """
    Fetch sign-in logs from Microsoft Graph and save to signin_logs.csv.
    
    Args:
        tenant_id (str): Azure tenant ID
        client_id (str): Azure client ID
        client_secret (str): Azure client secret
    
    Returns:
        bool: True if successful, False otherwise
    """
    token = get_access_token(tenant_id, client_id, client_secret)
    if not token:
        logger.error("Failed to obtain access token for sign-in logs")
        st.error("Failed to obtain access token for sign-in logs.")
        return False

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base_url = "https://graph.microsoft.com/v1.0"
    
    # Calculate date range for the last 30 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.debug(f"Fetching sign-in logs from {start_date_str} to {end_date_str}")

    # Use a fixed filename
    csv_file = "signin_logs.csv"
    logger.info(f"Writing to sign-in logs file: {csv_file}")

    # Fetch sign-in logs
    new_logs = []
    try:
        filter_query = f"createdDateTime ge {start_date_str} and createdDateTime le {end_date_str}"
        params = {
            "$select": "id,userId,userDisplayName,createdDateTime",
            "$filter": filter_query,
            "$top": 999
        }
        logger.debug(f"Sending request to {base_url}/auditLogs/signIns with params: {params}")
        response = requests.get(f"{base_url}/auditLogs/signIns", headers=headers, params=params)
        if response.status_code != 200:
            logger.error(f"Error fetching sign-in logs: {response.status_code} - {response.text}")
            st.error(f"Error fetching sign-in logs: {response.status_code} - {response.text}")
            return False
        data = response.json()
        signins = data.get("value", [])
        collection_date = datetime.utcnow().isoformat() + "Z"
        logger.debug(f"Fetched {len(signins)} sign-in records in first page")

        for signin in signins:
            user_id = signin.get("userId", "N/A")
            display_name = signin.get("userDisplayName", "N/A")
            signin_datetime = signin.get("createdDateTime", "N/A")
            if signin_datetime == "N/A":
                logger.warning(f"Skipping sign-in record with missing createdDateTime: {signin}")
                continue
            new_logs.append({
                "userId": user_id,
                "userDisplayName": display_name,
                "signInDateTime": signin_datetime,
                "collectionDate": collection_date
            })

        # Handle pagination
        next_link = data.get("@odata.nextLink")
        page_count = 1
        while next_link:
            page_count += 1
            logger.debug(f"Fetching page {page_count} of sign-in logs: {next_link}")
            response = requests.get(next_link, headers=headers)
            if response.status_code != 200:
                logger.error(f"Error fetching paginated sign-in logs: {response.status_code} - {response.text}")
                st.error(f"Error fetching paginated sign-in logs: {response.status_code} - {response.text}")
                break
            data = response.json()
            signins = data.get("value", [])
            for signin in signins:
                user_id = signin.get("userId", "N/A")
                display_name = signin.get("userDisplayName", "N/A")
                signin_datetime = signin.get("createdDateTime", "N/A")
                if signin_datetime == "N/A":
                    logger.warning(f"Skipping sign-in record with missing createdDateTime: {signin}")
                    continue
                new_logs.append({
                    "userId": user_id,
                    "userDisplayName": display_name,
                    "signInDateTime": signin_datetime,
                    "collectionDate": collection_date
                })
            next_link = data.get("@odata.nextLink")

        # Write new logs to signin_logs.csv
        if new_logs:
            with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=["userId", "userDisplayName", "signInDateTime", "collectionDate"])
                writer.writeheader()
                for log in new_logs:
                    writer.writerow(log)
            logger.info(f"Wrote {len(new_logs)} sign-in logs to {csv_file}")
            st.success(f"Wrote {len(new_logs)} sign-in logs to {csv_file}.")
        else:
            logger.info("No sign-in logs to write")
            st.info("No sign-in logs to write.")
        return True

    except Exception as e:
        logger.error(f"Exception when fetching sign-in logs: {str(e)}")
        st.error(f"Exception when fetching sign-in logs: {str(e)}")
        return False

def fetch_users(tenant_id, client_id, client_secret):
    """
    Fetch users from Microsoft Graph.
    
    Args:
        tenant_id (str): Azure tenant ID
        client_id (str): Azure client ID
        client_secret (str): Azure client secret
    
    Returns:
        list: List of user data dictionaries
    """
    users_data = []
    token = get_access_token(tenant_id, client_id, client_secret)
    if not token:
        logger.error("Failed to obtain access token for user fetching")
        st.error("Failed to obtain access token.")
        return []

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base_url = "https://graph.microsoft.com/v1.0"
    try:
        params = {
            "$select": "id,userPrincipalName,displayName,jobTitle,department,accountEnabled,userType",
            "$expand": "memberOf($select=displayName)"
        }
        logger.debug(f"Sending request to {base_url}/users with params: {params}")
        response = requests.get(f"{base_url}/users", headers=headers, params=params)
        if response.status_code != 200:
            logger.error(f"Error fetching users: {response.status_code} - {response.text}")
            st.error(f"Error fetching users: {response.status_code} - {response.text}")
            return []
        data = response.json()
        users = data.get("value", [])
        for user in users:
            groups = []
            if "memberOf" in user:
                groups = [group["displayName"] for group in user["memberOf"] if group.get("displayName") is not None]
            users_data.append({
                "User ID": user.get("id", "N/A"),
                "User Principal Name": user.get("userPrincipalName", "N/A"),
                "Display Name": user.get("displayName", "N/A"),
                "Job Title": user.get("jobTitle", "N/A"),
                "Department": user.get("department", "N/A"),
                "Account Enabled": str(user.get("accountEnabled", "N/A")).lower(),
                "User Type": user.get("userType", "N/A"),
                "Groups": ", ".join(groups) if groups else "No groups",
            })
        next_link = data.get("@odata.nextLink")
        page_count = 1
        while next_link:
            page_count += 1
            logger.debug(f"Fetching page {page_count} of users: {next_link}")
            response = requests.get(next_link, headers=headers)
            if response.status_code != 200:
                logger.error(f"Error fetching paginated users: {response.status_code} - {response.text}")
                st.error(f"Error fetching paginated users: {response.status_code} - {response.text}")
                break
            data = response.json()
            users = data.get("value", [])
            for user in users:
                groups = []
                if "memberOf" in user:
                    groups = [group["displayName"] for group in user["memberOf"] if group.get("displayName") is not None]
                users_data.append({
                    "User ID": user.get("id", "N/A"),
                    "User Principal Name": user.get("userPrincipalName", "N/A"),
                    "Display Name": user.get("displayName", "N/A"),
                    "Job Title": user.get("jobTitle", "N/A"),
                    "Department": user.get("department", "N/A"),
                    "Account Enabled": str(user.get("accountEnabled", "N/A")).lower(),
                    "User Type": user.get("userType", "N/A"),
                    "Groups": ", ".join(groups) if groups else "No groups",
                })
            next_link = data.get("@odata.nextLink")
        logger.info(f"Fetched {len(users_data)} users successfully")
        st.success(f"Fetched {len(users_data)} users successfully.")
        return users_data
    except Exception as e:
        logger.error(f"Exception when fetching users: {str(e)}")
        st.error(f"Exception when fetching users: {str(e)}")
        return []