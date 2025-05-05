import streamlit as st
from utils.ai_analyzer import read_signin_logs
from utils.logger import setup_logger
import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.memory import ConversationBufferMemory
import pandas as pd
from datetime import datetime, timedelta, timezone
import json

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
OPENAI_DEPLOYMENT_NAME = os.getenv("OPENAI_DEPLOYMENT_NAME")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION")

# Setup logger
logger = setup_logger("nlp_query", "logs/app.log")

# Initialize sign-in data and inactive users once
if "signin_data" not in st.session_state:
    st.session_state.signin_data = read_signin_logs()
    logger.debug(f"Initialized sign-in data in session state: {len(st.session_state.signin_data)} records")

if "inactive_users" not in st.session_state and "users_data" in st.session_state:
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
    logger.debug(f"Cutoff date for inactive users: {cutoff_date}")
    inactive_users = []
    for user in st.session_state.users_data:
        user_id = user["User ID"]
        last_signin = st.session_state.signin_data.get(user_id)
        logger.debug(f"User {user_id}: Last sign-in = {last_signin}")
        if last_signin is None or last_signin < cutoff_date:
            inactive_users.append(user)
    st.session_state.inactive_users = inactive_users
    logger.info(f"Initialized {len(inactive_users)} inactive users in session state")

# Helper function to normalize job titles
def normalize_role(role):
    if not role:
        return None
    role = role.lower()
    role = role.replace("engeer", "engineer")
    role = role.replace("enginner", "engineer")
    return role.strip()

# Helper function to validate roles
def is_valid_role(role):
    if not role or len(role) < 2:
        return False
    invalid_patterns = ["...", "plaintext", "summary", "metadata", "```"]
    role_lower = role.lower()
    if any(pattern in role_lower for pattern in invalid_patterns):
        return False
    return True

# Custom tool to query user data
@tool
def query_user_data(query: str) -> str:
    """Query user data using natural language or SQL-like syntax. Returns results as a string or table."""
    logger.info(f"Executing query_user_data tool with query: {query}")
    if "users_data" not in st.session_state or not st.session_state.users_data:
        return "No user data available. Please fetch data from the 'Fetch Data' page first."

    signin_data = st.session_state.signin_data

    try:
        query_lower = query.lower()

        # Handle queries for users who signed in today
        if "signed in today" in query_lower or "sign-in today" in query_lower or "signin today" in query_lower or "sign-in'ed today" in query_lower:
            today = datetime.now(timezone.utc).date()
            users_signed_in_today = set()
            for user_id, last_signin in signin_data.items():
                if last_signin and last_signin.date() == today:
                    users_signed_in_today.add(user_id)
            logger.debug(f"Users who signed in today: {len(users_signed_in_today)}")
            return f"There are {len(users_signed_in_today)} users who signed in today."

        # Handle natural language queries for inactive users
        if ("no sign-ins" in query_lower or 
            "haven't signed in" in query_lower or 
            "haven't sign-in" in query_lower or 
            "haven't signed-in" in query_lower) and ("last 30 days" in query_lower or "past 30 days" in query_lower):
            inactive_users = st.session_state.inactive_users
            logger.debug(f"Inactive users count: {len(inactive_users)}")
            return f"There are {len(inactive_users)} users who have not signed in during the last 30 days."

        # Handle SQL-like count queries for inactive users
        if ("select count(*)" in query_lower and 
            ("last_sign_in_date" in query_lower or "lastsignindate" in query_lower) and 
            "30 day" in query_lower and 
            any(op in query_lower for op in ["<", "<=", "is null", "date_sub", "now() - interval", "current_date - interval", "dateadd", "getdate() -"])):
            inactive_users = st.session_state.inactive_users
            logger.debug(f"Inactive users count: {len(inactive_users)}")
            return f"There are {len(inactive_users)} users who have not signed in during the last 30 days."

        # Handle SQL-like queries for total users
        if "select count(*)" in query_lower and "from users" in query_lower and "last_sign_in_date" not in query_lower and "lastsignindate" not in query_lower and "department" not in query_lower and "status" not in query_lower:
            total_users = len(st.session_state.users_data)
            return f"There are {total_users} users in your tenant."

        # Total users in the tenant (natural language)
        if "total users" in query_lower or "how many users" in query_lower or "count all users" in query_lower:
            total_users = len(st.session_state.users_data)
            return f"There are a total of {total_users} users in your tenant."

        # Handle SQL-like queries for total roles (job titles)
        if "select count(distinct role)" in query_lower and "from roles" in query_lower:
            raw_roles = set()
            for user in st.session_state.users_data:
                job_title = user.get("Job Title", None)
                normalized_title = normalize_role(job_title)
                if normalized_title:
                    raw_roles.add(normalized_title)
            identified_roles = [role for role in raw_roles if is_valid_role(role)]
            logger.debug(f"Distinct roles after normalization and filtering: {sorted(identified_roles)}")
            return f"Number of distinct job titles: {len(identified_roles)}"

        # Handle natural language queries for total roles (job titles)
        if "how many total roles" in query_lower or "distinct roles" in query_lower:
            raw_roles = set()
            for user in st.session_state.users_data:
                job_title = user.get("Job Title", None)
                normalized_title = normalize_role(job_title)
                if normalized_title:
                    raw_roles.add(normalized_title)
            identified_roles = [role for role in raw_roles if is_valid_role(role)]
            logger.debug(f"Distinct roles after normalization and filtering: {sorted(identified_roles)}")
            return f"There are {len(identified_roles)} distinct roles (job titles) in the dataset."

        # Handle queries to list all distinct roles
        if "list all distinct roles" in query_lower:
            raw_roles = set()
            for user in st.session_state.users_data:
                job_title = user.get("Job Title", None)
                normalized_title = normalize_role(job_title)
                if normalized_title:
                    raw_roles.add(normalized_title)
            identified_roles = sorted([role for role in raw_roles if is_valid_role(role)])
            logger.debug(f"Distinct roles after normalization and filtering: {identified_roles}")
            if not identified_roles:
                return "No distinct roles found in the dataset."
            return "Distinct roles (job titles) in the dataset:\n" + "\n".join(f"{i+1}. {role}" for i, role in enumerate(identified_roles))

        # Handle SQL-like queries for total groups
        if "select count(*)" in query_lower and "from groups" in query_lower:
            all_groups = set()
            for user in st.session_state.users_data:
                groups = user.get("Groups", "").split(", ") if user.get("Groups") else []
                all_groups.update(groups)
            all_groups = sorted([group for group in all_groups if group])
            return f"There are {len(all_groups)} unique groups in your tenant."

        # Number of groups (natural language)
        if "groups are there" in query_lower or "how many total groups" in query_lower:
            all_groups = set()
            for user in st.session_state.users_data:
                groups = user.get("Groups", "").split(", ") if user.get("Groups") else []
                all_groups.update(groups)
            all_groups = sorted([group for group in all_groups if group])
            return f"There are {len(all_groups)} unique groups in your tenant."

        # Handle SQL-like queries for total departments
        if "select count(distinct department)" in query_lower and "from users" in query_lower:
            all_departments = set(user.get("Department") for user in st.session_state.users_data if user.get("Department"))
            return f"There are {len(all_departments)} unique departments in your tenant."

        # Number of departments (natural language)
        if "how many total departments" in query_lower or "departments are there" in query_lower:
            all_departments = set(user.get("Department") for user in st.session_state.users_data if user.get("Department"))
            return f"There are {len(all_departments)} unique departments in your tenant."

        # Handle queries for disabled users (SQL-like)
        if "select count(*)" in query_lower and "from users" in query_lower and "status = 'disabled'" in query_lower:
            disabled_users = [user for user in st.session_state.users_data if user['Account Enabled'] == 'false']
            return f"There are {len(disabled_users)} disabled users in your tenant."

        # Handle queries for disabled users (natural language)
        if "how many disabled users" in query_lower or "active and disabled users" in query_lower:
            active_users = [user for user in st.session_state.users_data if user['Account Enabled'] == 'true']
            disabled_users = [user for user in st.session_state.users_data if user['Account Enabled'] == 'false']
            if "active and disabled users" in query_lower:
                return (
                    f"The total number of active and disabled users in your tenant is as follows:\n"
                    f"- Active Users: {len(active_users)}\n"
                    f"- Disabled Users: {len(disabled_users)}"
                )
            return f"There are {len(disabled_users)} disabled users in your tenant."

        # Handle SQL-like queries for users with a specific name (e.g., SELECT * FROM users WHERE user_principal_name LIKE '%santhosh%')
        if "select" in query_lower and "from users" in query_lower and "user_principal_name like" in query_lower:
            search_term = query_lower.split("like '%")[1].split("%'")[0]
            matching_users = []
            for user in st.session_state.users_data:
                if search_term.lower() in user['User Principal Name'].lower():
                    user_id = user["User ID"]
                    last_signin = signin_data.get(user_id)
                    last_signin_date = last_signin.strftime("%Y-%m-%dT%H:%M:%SZ") if last_signin else "N/A"
                    user_info = (
                        f"User: {user['User Principal Name']}, "
                        f"Department: {user['Department']}, "
                        f"Job Title: {user['Job Title']}, "
                        f"Account Enabled: {user['Account Enabled']}, "
                        f"User Type: {user['User Type']}, "
                        f"Last Sign-In Date: {last_signin_date}, "
                        f"Groups: {user['Groups']}"
                    )
                    matching_users.append(user_info)
            if matching_users:
                return f"Found {len(matching_users)} user(s) matching '{search_term}':\n" + "\n".join(matching_users)
            return f"No users found matching '{search_term}'."

        # Handle SQL-like queries for users with a specific name among inactive users
        if ("select" in query_lower and 
            "from users" in query_lower and 
            "user_principal_name like" in query_lower and 
            ("last_sign_in_date" in query_lower or "lastsignindate" in query_lower) and 
            "30 day" in query_lower and 
            any(op in query_lower for op in ["<", "<=", "is null"])):
            search_term = query_lower.split("like '%")[1].split("%'")[0]
            inactive_users = st.session_state.inactive_users
            matching_users = [
                user for user in inactive_users
                if search_term.lower() in user['User Principal Name'].lower()
            ]
            if matching_users:
                result = []
                for user in matching_users:
                    user_id = user["User ID"]
                    last_signin = signin_data.get(user_id)
                    last_signin_date = last_signin.strftime("%Y-%m-%dT%H:%M:%SZ") if last_signin else "N/A"
                    result.append(
                        f"User: {user['User Principal Name']}, "
                        f"Department: {user['Department']}, "
                        f"Job Title: {user['Job Title']}, "
                        f"Last Sign-In Date: {last_signin_date}"
                    )
                return f"Found {len(matching_users)} inactive user(s) matching '{search_term}':\n" + "\n".join(result)
            return f"No inactive users found matching '{search_term}'."

        # Handle SQL-like queries for users with a specific name who signed in within a time frame
        if ("select" in query_lower and 
            "from users" in query_lower and 
            "user_principal_name like" in query_lower and 
            ("last_sign_in_date" in query_lower or "lastsignindate" in query_lower) and 
            any(op in query_lower for op in [">=", "date_sub", "now() - interval", "current_date - interval", "dateadd", "getdate() -"])):
            search_term = query_lower.split("like '%")[1].split("%'")[0]
            days = 30  # Default to 30 days if not specified
            if "interval" in query_lower:
                days = int(query_lower.split("interval")[1].split("day")[0].strip())
            elif "dateadd" in query_lower or "getdate() -" in query_lower:
                days = int(query_lower.split("day, -")[1].split(",")[0].strip())
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            matching_users = []
            for user in st.session_state.users_data:
                if search_term.lower() in user['User Principal Name'].lower():
                    user_id = user["User ID"]
                    last_signin = signin_data.get(user_id)
                    if last_signin and last_signin >= cutoff_date:
                        last_signin_date = last_signin.strftime("%Y-%m-%dT%H:%M:%SZ")
                        user_info = (
                            f"User: {user['User Principal Name']}, "
                            f"Last Sign-In Date: {last_signin_date}"
                        )
                        matching_users.append(user_info)
            if matching_users:
                return f"Found {len(matching_users)} user(s) matching '{search_term}' who signed in within the last {days} days:\n" + "\n".join(matching_users)
            return f"No users matching '{search_term}' have signed in within the last {days} days."

        # Handle queries for a specific user's department (natural language)
        if "is from which department" in query_lower or "whcih department" in query_lower:
            if "is from which department" in query_lower:
                search_term = query_lower.split("is from which department")[0].strip()
            else:
                search_term = query_lower.split("whcih department")[0].strip()
            search_term = search_term.replace("is ", "").strip()
            matching_users = []
            for user in st.session_state.users_data:
                if search_term.lower() in user['User Principal Name'].lower():
                    user_id = user["User ID"]
                    last_signin = signin_data.get(user_id)
                    last_signin_date = last_signin.strftime("%Y-%m-%dT%H:%M:%SZ") if last_signin else "N/A"
                    user_info = (
                        f"User: {user['User Principal Name']}, "
                        f"Department: {user['Department']}, "
                        f"Job Title: {user['Job Title']}, "
                        f"Account Enabled: {user['Account Enabled']}, "
                        f"User Type: {user['User Type']}, "
                        f"Last Sign-In Date: {last_signin_date}, "
                        f"Groups: {user['Groups']}"
                    )
                    matching_users.append(user_info)
            if matching_users:
                return f"Found {len(matching_users)} user(s) matching '{search_term}':\n" + "\n".join(matching_users)
            return f"No users found matching '{search_term}'."

        # Handle SQL-like queries for user details (e.g., SELECT * FROM users WHERE name = 'santhosh')
        if ("select" in query_lower and 
            "from users" in query_lower and 
            any(field in query_lower for field in ["name =", "username =", "email ="])):
            search_term = query_lower.split("= '")[1].split("'")[0]
            matching_users = []
            for user in st.session_state.users_data:
                if search_term.lower() in user['User Principal Name'].lower():
                    user_id = user["User ID"]
                    last_signin = signin_data.get(user_id)
                    last_signin_date = last_signin.strftime("%Y-%m-%dT%H:%M:%SZ") if last_signin else "N/A"
                    user_info = (
                        f"User: {user['User Principal Name']}, "
                        f"Department: {user['Department']}, "
                        f"Job Title: {user['Job Title']}, "
                        f"Account Enabled: {user['Account Enabled']}, "
                        f"User Type: {user['User Type']}, "
                        f"Last Sign-In Date: {last_signin_date}, "
                        f"Groups: {user['Groups']}"
                    )
                    matching_users.append(user_info)
            if matching_users:
                return f"Found {len(matching_users)} user(s) matching '{search_term}':\n" + "\n".join(matching_users)
            return f"No users found with name, username, or email matching '{search_term}'."

        # Detailed list of users with no sign-ins in the last 30 days
        if "list users" in query_lower and "no sign-ins" in query_lower and "last 30 days" in query_lower:
            inactive_users = st.session_state.inactive_users
            if not inactive_users:
                return "No users found with no sign-ins in the last 30 days."
            result = []
            for user in inactive_users[:10]:
                user_id = user["User ID"]
                last_signin = signin_data.get(user_id)
                last_signin_date = last_signin.strftime("%Y-%m-%dT%H:%M:%SZ") if last_signin else "N/A"
                result.append(
                    f"{user['User Principal Name']}, {user['Account Enabled']}, {user['Job Title']}, "
                    f"{user['Department']}, {user['User Type']}, {last_signin_date}"
                )
            return f"There are {len(inactive_users)} users who have not signed in during the last 30 days.\n" + "\n".join(result)

        # Top 10 users with no sign-ins
        if "top 10" in query_lower and "not signed in" in query_lower:
            inactive_users = st.session_state.inactive_users
            if not inactive_users:
                return "No users found with no sign-ins in the last 30 days."
            result = []
            for i, user in enumerate(inactive_users[:10], 1):
                result.append(f"{i}. **{user['User Principal Name']}** - Department: {user['Department']}")
            return "Here are the top 10 users who have not signed in during the last 30 days:\n" + "\n".join(result)

        # Check for a specific user in the list of inactive users (natural language)
        if ("is " in query_lower and " in " in query_lower and "list" in query_lower) or \
           ("is there any user named" in query_lower and "list" in query_lower):
            if "is there any user named" in query_lower:
                search_term = query_lower.split("is there any user named")[1].split("in that list")[0].strip()
            else:
                search_term = query_lower.split("is ")[1].split(" in ")[0].strip()
            inactive_users = st.session_state.inactive_users
            found = any(search_term.lower() in user['User Principal Name'].lower() for user in inactive_users)
            return f"{'Yes' if found else 'No'}, '{search_term}' {'is' if found else 'is not'} in the list of users who have not signed in during the last 30 days."

        # List inactive users with a specific name (natural language)
        if ("inactive users" in query_lower and ("name" in query_lower or "named" in query_lower)) or \
           ("list all users who have not signed in" in query_lower and "name" in query_lower):
            search_term = None
            if "name containing" in query_lower:
                search_term = query_lower.split("name containing")[1].strip("'").strip()
            elif "name contains" in query_lower:
                search_term = query_lower.split("name contains")[1].strip("'").strip()
            elif "with the name" in query_lower:
                search_term = query_lower.split("with the name")[1].strip("'").strip()
            elif "named" in query_lower:
                search_term = query_lower.split("named")[1].strip("'").strip()
            elif "name" in query_lower:
                search_term = query_lower.split("name")[1].strip("'").strip()

            if search_term:
                inactive_users = st.session_state.inactive_users
                if not inactive_users:
                    return "No users found with no sign-ins in the last 30 days."
                
                matching_users = [
                    user for user in inactive_users
                    if search_term.lower() in user['User Principal Name'].lower()
                ]

                if not matching_users:
                    return f"No inactive users found with the name '{search_term}'."

                result = []
                for user in matching_users:
                    user_id = user["User ID"]
                    last_signin = signin_data.get(user_id)
                    last_signin_date = last_signin.strftime("%Y-%m-%dT%H:%M:%SZ") if last_signin else "N/A"
                    result.append(
                        f"User: {user['User Principal Name']}, "
                        f"Department: {user['Department']}, "
                        f"Job Title: {user['Job Title']}, "
                        f"Last Sign-In Date: {last_signin_date}"
                    )
                return f"Found {len(matching_users)} inactive user(s) with the name '{search_term}':\n" + "\n".join(result)
            else:
                return "Unable to extract the name from the query. Please try rephrasing, e.g., 'List all inactive users with the name Santhosh'."

        # Handle natural language queries for sign-in status (e.g., "Have Santhosh sign-in'ed?")
        if "sign-in'ed" in query_lower or "signed in" in query_lower:
            search_term = None
            if "have " in query_lower and " sign-in'ed" in query_lower:
                search_term = query_lower.split("have ")[1].split(" sign-in'ed")[0].strip()
            elif "has " in query_lower and " signed in" in query_lower:
                search_term = query_lower.split("has ")[1].split(" signed in")[0].strip()
            
            if search_term:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
                matching_users = []
                for user in st.session_state.users_data:
                    if search_term.lower() in user['User Principal Name'].lower():
                        user_id = user["User ID"]
                        last_signin = signin_data.get(user_id)
                        if last_signin:
                            last_signin_date = last_signin.strftime("%Y-%m-%dT%H:%M:%SZ")
                            if last_signin >= cutoff_date:
                                user_info = (
                                    f"User: {user['User Principal Name']}, "
                                    f"Last Sign-In Date: {last_signin_date} (within the last 30 days)"
                                )
                            else:
                                user_info = (
                                    f"User: {user['User Principal Name']}, "
                                    f"Last Sign-In Date: {last_signin_date} (more than 30 days ago)"
                                )
                        else:
                            user_info = (
                                f"User: {user['User Principal Name']}, "
                                f"Last Sign-In Date: N/A (never signed in)"
                            )
                        matching_users.append(user_info)
                if matching_users:
                    return f"Sign-in status for user(s) matching '{search_term}':\n" + "\n".join(matching_users)
                return f"No users found matching '{search_term}'."
            return "Unable to extract the name from the query. Please try rephrasing, e.g., 'Have Santhosh sign-in'ed?'"

        # Fallback for other queries
        else:
            return f"Query not recognized: {query}. Please try a more specific query, such as 'How many users have no sign-ins in the last 30 days?' or 'How many total groups?'."
    except Exception as e:
        logger.error(f"Error in query_user_data: {str(e)}")
        return f"Error processing query: {str(e)}"

# Load the prompt from prompt.txt
try:
    with open("pages/prompt.txt", "r") as f:
        logger.info("Yes Prompt is initiated")
        prompt_template = f.read()
except FileNotFoundError:
    logger.error("prompt.txt not found. Using default prompt.")
    prompt_template = """
You are a helpful AI assistant that can query user data using natural language or SQL-like syntax. Use the provided tools to answer queries about the tenant, including users, groups, departments, and sign-in activities. For count queries, return the total count directly unless asked to list records. For user-specific queries, search the dataset and return details.

All data is pre-fetched and stored locally in the system (st.session_state.users_data and st.session_state.signin_data). Do not suggest fetching data from external APIs.

When converting natural language to SQL-like queries:
- Use 'user_principal_name' instead of 'name', 'username', or 'email' for user searches.
- Use 'last_sign_in_date' for sign-in timestamps.
- For inactive user queries, use conditions like 'last_sign_in_date < DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY) OR last_sign_in_date IS NULL'.
- For sign-in activity within a time frame, use conditions like 'last_sign_in_date >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)'.

### Examples (loaded dynamically from learning_examples.json):
{examples}
"""

# Load examples from learning_examples.json
try:
    with open("pages/learning_examples.json", "r") as f:
        examples_data = json.load(f)
    examples_str = ""
    for i, example in enumerate(examples_data, 1):
        examples_str += f"{i}. **Query**: \"{example['query']}\"\n   **Expected Response**: \"{example['expected_response']}\"\n   **Steps**:\n"
        for step in example['steps']:
            examples_str += f"   - {step}\n"
    prompt_text = prompt_template.format(examples=examples_str)
except FileNotFoundError:
    logger.error("learning_examples.json not found. Using prompt without examples.")
    prompt_text = prompt_template.format(examples="No examples available.")

# Initialize LangChain agent
llm = AzureChatOpenAI(
    openai_api_key=OPENAI_API_KEY,
    azure_endpoint=OPENAI_ENDPOINT,
    deployment_name=OPENAI_DEPLOYMENT_NAME,
    openai_api_version=OPENAI_API_VERSION,
    temperature=0
)

# Define the prompt with memory
prompt = ChatPromptTemplate.from_messages([
    ("system", prompt_text),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create the agent with tools
tools = [query_user_data]
agent = create_openai_tools_agent(llm, tools, prompt)

# Initialize chat history and memory
if "chat_history" not in st.session_state:
    st.session_state.chat_history = ChatMessageHistory()
    logger.debug("Initialized chat history in session state")

if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferMemory(
        memory_key="chat_history",
        chat_memory=st.session_state.chat_history,
        return_messages=True
    )
    logger.debug("Initialized memory in session state")

# Create the agent executor with memory
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    memory=st.session_state.memory
)

# Page UI
st.title("Chat with User Data AI Agent")
st.markdown("Ask questions about user data (e.g., 'How many users have no sign-ins in the last 30 days?' or 'List the top 10 inactive users').")

# Display chat history
for message in st.session_state.chat_history.messages:
    role = "user" if message.type == "human" else "assistant"
    with st.chat_message(role):
        st.markdown(message.content)

# Chat input
if user_input := st.chat_input("Enter your query:"):
    logger.info(f"User input: {user_input}")
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.spinner("Processing your query..."):
        try:
            response = agent_executor.invoke({"input": user_input})
            logger.info(f"Agent response: {response['output']}")
            with st.chat_message("assistant"):
                if "\n" in response["output"] and "," in response["output"] and "users who have not signed in" in response["output"]:
                    try:
                        parts = response["output"].split("\n", 1)
                        count_message = parts[0]
                        table_data = parts[1] if len(parts) > 1 else ""
                        st.markdown(count_message)
                        if table_data:
                            lines = table_data.split("\n")
                            data = [line.split(", ") for line in lines if line.strip()]
                            if data and len(data[0]) >= 5:
                                df = pd.DataFrame(data, columns=["User Principal Name", "Account Enabled", "Job Title", "Department", "User Type", "Last Sign-In Date"])
                                st.dataframe(df)
                            else:
                                st.markdown(table_data)
                    except Exception as e:
                        logger.error(f"Error displaying table: {str(e)}")
                        st.markdown(response["output"])
                else:
                    st.markdown(response["output"])
        except Exception as e:
            logger.error(f"Error in agent execution: {str(e)}")
            with st.chat_message("assistant"):
                st.error(f"Error processing query: {str(e)}")