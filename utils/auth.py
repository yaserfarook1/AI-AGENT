from azure.identity import ClientSecretCredential
import streamlit as st
from utils.logger import setup_logger

# Setup logger
logger = setup_logger("auth", "logs/app.log")

def get_access_token(tenant_id, client_id, client_secret):
    """
    Get an access token for Microsoft Graph API.
    
    Args:
        tenant_id (str): Azure tenant ID
        client_id (str): Azure client ID
        client_secret (str): Azure client secret
    
    Returns:
        str: Access token, or None if failed
    """
    scope = "https://graph.microsoft.com/.default"
    logger.debug(f"Attempting to get access token for scope: {scope}")
    try:
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        token = credential.get_token(scope)
        logger.info("Successfully obtained access token")
        return token.token
    except Exception as e:
        logger.error(f"Error getting access token: {str(e)}")
        st.error(f"Error getting access token: {str(e)}")
        return None