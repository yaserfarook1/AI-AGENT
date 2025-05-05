FindInactiveUsers
A Streamlit application to identify and analyze inactive or dormant accounts in Entra ID using Microsoft Graph and Azure OpenAI.
Features

Fetch Data: Retrieve user and sign-in data from Microsoft Graph.
Analyze Inactive Users: Identify users who haven’t signed in within a specified period.
NLP Query: Query user data using natural language (e.g., "List all users who haven’t signed in for 60 days").
Department Analysis: Analyze departments using Azure OpenAI.
Role Analysis: Analyze roles using Azure OpenAI.

Folder Structure
FindInactiveUsers/
├── find_inactive_users.py  # Main app entry point
├── utils/                  # Utility modules
│   ├── auth.py             # Authentication functions
│   ├── data_fetcher.py     # Data fetching functions
│   ├── ai_analyzer.py      # AI analysis functions
│   └── logger.py           # Logger setup
├── pages/                  # Streamlit pages
│   ├── 1_Fetch_Data.py     # Fetch data page
│   ├── 2_Inactive_Users.py # Inactive users analysis page
│   ├── 3_NLP_Query.py      # NLP query page
│   ├── 4_Department_Analysis.py  # Department analysis page
│   ├── 5_Role_Analysis.py  # Role analysis page
├── requirements.txt        # Dependencies
├── .env                    # Environment variables
├── README.md               # This file
├── logs/                   # Log files (generated at runtime)
└── signin_logs.csv         # Sign-in logs CSV (generated at runtime)

Prerequisites

Python 3.9+
Microsoft Entra ID app registration with permissions: User.Read.All, AuditLog.Read.All (admin-consented).
Azure OpenAI service with a deployed model (e.g., gpt-3.5-turbo).

Setup

Clone the Repository:
git clone <repository-url>
cd FindInactiveUsers


Install Dependencies:
pip install -r requirements.txt


Set Up Environment Variables:Create a .env file in the project root with the following:
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret
OPENAI_API_KEY=your-openai-api-key
OPENAI_ENDPOINT=your-openai-endpoint
OPENAI_DEPLOYMENT_NAME=your-deployment-name
OPENAI_API_VERSION=your-api-version


Run the Application:
streamlit run find_inactive_users.py --server.fileWatcherType none



Usage

Open the app in your browser (default: http://localhost:8501).
Navigate to the "Fetch Data" page to retrieve user and sign-in data.
Use other pages to analyze inactive users, query data, or perform department/role analysis.

Troubleshooting

Microsoft Graph Errors:
Verify TENANT_ID, CLIENT_ID, CLIENT_SECRET in .env.
Ensure permissions are granted in Azure Portal.


Azure OpenAI Errors:
Check OPENAI_* variables in .env.
Ensure the model is deployed in Azure OpenAI.


Logs:
Application logs: logs/app.log
AI logs: logs/ai.log



Contributing
Feel free to open issues or submit pull requests for improvements.
License
MIT License
