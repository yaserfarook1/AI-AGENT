import streamlit as st
import os
from dotenv import load_dotenv
from utils.logger import setup_logger

# Setup logger
logger = setup_logger("app", "logs/app.log")

# Load environment variables
load_dotenv()
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
OPENAI_DEPLOYMENT_NAME = os.getenv("OPENAI_DEPLOYMENT_NAME")
OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION")

# Check environment variables
if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET, OPENAI_API_KEY, OPENAI_ENDPOINT, OPENAI_DEPLOYMENT_NAME, OPENAI_API_VERSION]):
    logger.critical("One or more required environment variables are not set. Stopping application.")
    st.error("One or more required environment variables are not set. Please check your .env file.")
    st.stop()

logger.info("Starting FindInactiveUsers application")

# Main page UI
st.title("FindInactiveUsers: Dormant Account Analyzer")
st.markdown("""
Welcome to **FindInactiveUsers**, a tool to identify and analyze inactive or dormant accounts in Entra ID. This multi-page application helps you:

- **Fetch Data**: Retrieve user and sign-in data from Microsoft Graph.
- **Analyze Inactive Users**: Identify users who haven't signed in recently.
- **Query with NLP**: Use natural language to query user data.
- **Analyze Departments**: Understand departmental distribution (optional).
- **Analyze Roles**: Identify roles within your organization (optional).

### Instructions
1. Start by navigating to the **Fetch Data** page to retrieve user and sign-in data.
2. Use the **Inactive Users** page to analyze dormant accounts.
3. Explore other pages for additional insights.

### Troubleshooting
- **Microsoft Graph Issues**:
  - Verify your `TENANT_ID`, `CLIENT_ID`, and `CLIENT_SECRET` in the `.env` file.
  - Ensure permissions (`User.Read.All`, `AuditLog.Read.All`) are granted in Azure Portal.
- **Azure OpenAI Issues**:
  - Check `OPENAI_*` variables in the `.env` file.
  - Ensure your model is deployed in Azure OpenAI.
- **Logs**:
  - Application logs: `logs/app.log`
  - AI operation logs: `logs/ai.log`
""")