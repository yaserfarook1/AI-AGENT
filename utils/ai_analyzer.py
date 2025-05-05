import csv
from datetime import datetime, timezone, timedelta
import pytz
import logging
import sys
import httpx
from openai import AzureOpenAI
import streamlit as st
from utils.logger import setup_logger

# Configure logging for ai_analyzer.py
logger = setup_logger("ai_analyzer", "logs/ai.log")
logger.info("Starting ai_analyzer module")

# Function to read sign-in logs from a fixed CSV file
def read_signin_logs():
    """
    Read sign-in logs from signin_logs.csv.
    
    Returns:
        dict: Mapping of user IDs to their latest sign-in times (for compatibility with existing code)
              or a list of sign-in entries (for detailed queries in the future)
    """
    csv_file = "signin_logs.csv"
    signin_data = {}
    try:
        with open(csv_file, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            data = list(reader)
            logger.debug(f"Read {len(data)} sign-in records from {csv_file}")
            for row in data:
                # Handle both possible column names: "User ID" (existing) or "userId" (new)
                user_id = row.get("User ID", row.get("userId"))
                if not user_id:
                    logger.warning("Skipping sign-in log with missing user ID")
                    continue

                # Handle both possible date fields: "Sign-In Date" (existing) or "signInDateTime" (new)
                signin_time = row.get("Sign-In Date", row.get("signInDateTime"))
                if signin_time == "N/A":
                    logger.warning(f"Skipping sign-in log with missing signInDateTime for userId: {user_id}")
                    continue

                try:
                    # Handle both formats: "2025-04-28T20:57:03Z" (existing) or ISO with "Z" replacement (new)
                    if "Z" in signin_time:
                        signin_date = datetime.strptime(signin_time, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    else:
                        signin_date = datetime.fromisoformat(signin_time.replace("Z", "+00:00"))
                except ValueError as e:
                    logger.error(f"Error parsing Sign-In Date for user {user_id}: {signin_time}, Error: {str(e)}")
                    continue

                # For compatibility with existing code, store as a single datetime
                if user_id not in signin_data or signin_date > signin_data[user_id]:
                    signin_data[user_id] = signin_date
                logger.debug(f"Loaded sign-in for user {user_id}: {signin_date}")
    except FileNotFoundError:
        logger.error(f"Sign-in logs file {csv_file} not found")
        st.warning(f"Sign-in logs file {csv_file} not found.")
        return {}
    except Exception as e:
        logger.error(f"Error reading sign-in logs: {str(e)}")
        st.error(f"Error reading sign-in logs: {str(e)}")
        return {}
    return signin_data

# Function to analyze departments with Azure OpenAI
def analyze_departments(user_data, api_key, endpoint, deployment_name, api_version):
    """
    Analyze departments using Azure OpenAI.
    
    Args:
        user_data (str): User data string
        api_key (str): Azure OpenAI API key
        endpoint (str): Azure OpenAI endpoint
        deployment_name (str): Azure OpenAI deployment name
        api_version (str): Azure OpenAI API version
    
    Returns:
        list: List of unique departments
    """
    logger.debug("Initializing Azure OpenAI client for department analysis")
    http_client = httpx.Client()
    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
        http_client=http_client
    )

    prompt = f"""
    Analyze the following user data and identify the different departments represented.
    Return a list of unique departments, removing any duplicates or irrelevant entries like 'N/A'.

    Examples:
    User Data:
    User: john.doe@example.com, Department: Sales
    User: jane.smith@example.com, Department: Marketing
    User: bob.johnson@example.com, Department: Sales
    
    Expected Output:
    Sales
    Marketing
    
    User Data:
    User: alice.brown@example.com, Department: Engineering
    User: charlie.wilson@example.com, Department: Human Resources
    User: david.garcia@example.com, Department: N/A
    
    Expected Output:
    Engineering
    Human Resources
    
    Now, analyze the following user data:
    {user_data}
    
    Return the unique departments in the following format:
    Department 1
    Department 2
    ...
    """
    try:
        logger.info("Sending department analysis request to Azure OpenAI")
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[{"role": "user", "content": prompt}],
        )
        departments = response.choices[0].message.content.strip().splitlines()
        departments = [d.strip() for d in departments if d.strip() and d != "N/A"]
        unique_depts = list(set(departments))
        logger.info(f"Identified {len(unique_depts)} unique departments")
        return unique_depts
    except Exception as e:
        logger.error(f"Error analyzing departments with Azure OpenAI: {e}")
        st.error(f"Error analyzing departments with Azure OpenAI: {e}")
        return None
    finally:
        http_client.close()

# Function to analyze roles with Azure OpenAI
def analyze_roles(user_data, api_key, endpoint, deployment_name, api_version):
    """
    Analyze roles using Azure OpenAI.
    
    Args:
        user_data (str): User data string
        api_key (str): Azure OpenAI API key
        endpoint (str): Azure OpenAI endpoint
        deployment_name (str): Azure OpenAI deployment name
        api_version (str): Azure OpenAI API version
    
    Returns:
        list: List of unique roles
    """
    logger.debug("Initializing Azure OpenAI client for role analysis")
    http_client = httpx.Client()
    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
        http_client=http_client
    )

    prompt = f"""
    Analyze the following user data to identify potential roles. Consider the job titles, departments, and group memberships to suggest meaningful roles. Return a list of unique role names, ensuring they are distinct and relevant. Avoid duplicating roles that are essentially the same (e.g., "Engineer" and "Software Engineer" should be standardized if they refer to the same role). Remove any irrelevant entries like 'N/A' or 'No groups'.

    Examples:
    
    User Data:
    User: john.doe@example.com, Job Title: Sales Manager, Department: Sales, Groups: Sales Team
    User: jane.smith@example.com, Job Title: Sales Representative, Department: Sales, Groups: Sales Team
    
    Expected Output:
    Sales Manager
    Sales Representative
    
    User Data:
    User: alice.brown@example.com, Job Title: Software Engineer, Department: Engineering, Groups: Developers
    User: charlie.wilson@example.com, Job Title: HR Specialist, Department: Human Resources, Groups: HR Team
    User: david.garcia@example.com, Job Title: Senior Software Engineer, Department: Engineering, Groups: Developers
    
    Expected Output:
    Software Engineer
    Senior Software Engineer
    HR Specialist
    
    Now, analyze the following user data:
    {user_data}
    
    Return the unique roles in the following format:
    Role Name 1
    Role Name 2
    ...
    """
    try:
        logger.info("Sending role analysis request to Azure OpenAI")
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[{"role": "user", "content": prompt}],
        )
        roles = response.choices[0].message.content.strip().splitlines()
        roles = [role.strip() for role in roles if role.strip() and role not in ["N/A", "No groups"]]
        unique_roles = list(set(roles))
        logger.info(f"Identified {len(unique_roles)} unique roles")
        return unique_roles
    except Exception as e:
        logger.error(f"Error analyzing roles with Azure OpenAI: {e}")
        st.error(f"Error analyzing roles with Azure OpenAI: {e}")
        return None
    finally:
        http_client.close()

# Function to handle NLP-based querying with Azure OpenAI
def nlp_query(user_data, query, api_key, endpoint, deployment_name, api_version):
    """
    Handle NLP-based queries using Azure OpenAI.
    
    Args:
        user_data (str): User data string
        query (str): Natural language query
        api_key (str): Azure OpenAI API key
        endpoint (str): Azure OpenAI endpoint
        deployment_name (str): Azure OpenAI deployment name
        api_version (str): Azure OpenAI API version
    
    Returns:
        str or list: Query result (string for counts, list for entries)
    """
    logger.debug("Initializing Azure OpenAI client for NLP query")
    http_client = httpx.Client()
    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
        http_client=http_client
    )

    prompt = f"""
    You are an assistant that interprets natural language queries about user data and provides answers based on the data provided. The user data includes fields like User Principal Name, Display Name, Job Title, Department, Account Enabled, User Type, Last Sign-In Date, and Groups. Your task is to analyze the query, understand its intent, and provide a concise answer. If the query asks for a count, return a string with the count. If the query asks for a list, return a list of matching entries in the format specified below.

    Examples:

    User Data:
    User: john.doe@example.com, Job Title: Software Engineer, Department: Engineering, Account Enabled: true, User Type: Member, Last Sign-In Date: 2025-04-15T00:00:00Z, Groups: Developers
    User: jane.smith@example.com, Job Title: Sales Manager, Department: Sales, Account Enabled: true, User Type: Member, Last Sign-In Date: 2025-05-01T00:00:00Z, Groups: Sales Team
    User: bob.johnson@example.com, Job Title: N/A, Department: N/A, Account Enabled: false, User Type: Guest, Last Sign-In Date: N/A, Groups: No groups

    Query: "How many disabled accounts are there?"
    Expected Output:
    Number of disabled accounts: 1

    Query: "List all users with no sign-ins in the last 30 days"
    Expected Output:
    bob.johnson@example.com,false,N/A,N/A,Guest,N/A

    Query: "Who is in the Sales department?"
    Expected Output:
    jane.smith@example.com,true,Sales Manager,Sales,Member,2025-05-01T00:00:00Z

    Now, analyze the following user data and answer the query:
    User Data:
    {user_data}
    
    Query:
    {query}
    
    Note: Today is 2025-05-02. For queries involving "last 30 days", consider users with Last Sign-In Date before 2025-04-02 or N/A.
    
    Return the answer in the appropriate format:
    - For counts: "Number of [category]: [number]"
    - For lists: "[User Principal Name],[Account Enabled],[Job Title],[Department],[User Type],[Last Sign-In Date]" (one per line)
    """
    try:
        logger.info(f"Processing NLP query: {query}")
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[{"role": "user", "content": prompt}],
        )
        result = response.choices[0].message.content.strip()
        if "Number of" in result:
            logger.info(f"NLP query result: {result}")
            return result
        else:
            entries = result.splitlines()
            entries = [entry.strip() for entry in entries if entry.strip()]
            logger.info(f"NLP query returned {len(entries)} entries")
            return entries
    except Exception as e:
        logger.error(f"Error processing query with Azure OpenAI: {e}")
        st.error(f"Error processing query with Azure OpenAI: {e}")
        return None
    finally:
        http_client.close()

# Function to analyze inactive users
def analyze_inactive_users(users_data, inactivity_days=30):
    """
    Analyze inactive users based on sign-in logs.
    
    Args:
        users_data (list): List of user data dictionaries
        inactivity_days (int): Number of days to consider for inactivity
    
    Returns:
        list: List of inactive user dictionaries
    """
    logger.info(f"Starting inactive users analysis for {inactivity_days} days")
    signin_data = read_signin_logs()
    current_date = datetime.now(pytz.UTC)
    threshold_date = current_date - timedelta(days=inactivity_days)
    logger.debug(f"Current date: {current_date}, Threshold date: {threshold_date}")
    inactive_users = []

    for user in users_data:
        user_id = user["User ID"]
        display_name = user["Display Name"]
        last_signin = signin_data.get(user_id)

        if not last_signin or last_signin < threshold_date:
            if last_signin:
                days_inactive = (current_date - last_signin).days
                logger.debug(f"User {user_id} last signed in {days_inactive} days ago")
            else:
                days_inactive = "No sign-in recorded"
                logger.debug(f"User {user_id} has no sign-in recorded")
            inactive_users.append({
                "User ID": user_id,
                "Display Name": display_name,
                "Days Since Last Sign-In": days_inactive
            })

    logger.info(f"Found {len(inactive_users)} inactive users")
    return inactive_users

# Combined function to dispatch Azure OpenAI queries
def query_azure_openai(user_data, api_key, endpoint, deployment_name, api_version, operation, query=None, inactivity_days=30):
    """
    Dispatch Azure OpenAI queries based on the operation.
    
    Args:
        user_data (str or list): User data (string for analysis, list for inactive users)
        api_key (str): Azure OpenAI API key
        endpoint (str): Azure OpenAI endpoint
        deployment_name (str): Azure OpenAI deployment name
        api_version (str): Azure OpenAI API version
        operation (str): Operation to perform ("analyze_departments", "analyze_roles", "nlp_query", "analyze_inactive_users")
        query (str, optional): Query for NLP operation
        inactivity_days (int, optional): Days for inactive users analysis
    
    Returns:
        Result of the specified operation
    """
    logger.info(f"Executing query_azure_openai with operation: {operation}")
    if operation == "analyze_departments":
        return analyze_departments(user_data, api_key, endpoint, deployment_name, api_version)
    elif operation == "analyze_roles":
        return analyze_roles(user_data, api_key, endpoint, deployment_name, api_version)
    elif operation == "nlp_query":
        if query is None:
            logger.critical("Query parameter is required for nlp_query operation")
            raise ValueError("Query parameter is required for nlp_query operation")
        return nlp_query(user_data, query, api_key, endpoint, deployment_name, api_version)
    elif operation == "analyze_inactive_users":
        return analyze_inactive_users(user_data, inactivity_days)
    else:
        logger.critical(f"Invalid operation: {operation}")
        raise ValueError(f"Invalid operation: {operation}")