import os
from dotenv import load_dotenv


load_dotenv()

# Feature toggles
ACTIVATE_ACCOUNTS = os.getenv('ACTIVATE_ACCOUNTS', 'True') == 'True'
DAILY_CLAIM = os.getenv('DAILY_CLAIM', 'True') == 'True'

# App constants
PING_INTERVAL = int(os.getenv('PING_INTERVAL', 15))
PING_DURATION = int(os.getenv('PING_DURATION', 1800))

# Debugging
DEBUG = os.getenv('DEBUG', 'False').strip().lower() == 'true'

# Nodepay API endpoints
DOMAIN_API = {

    # Auth Endpoints
    "ACTIVATE": "https://api.nodepay.ai/api/auth/active-account",

    # Network Endpoints
    "PING": ["https://nw.nodepay.org/api/network/ping"],
    "SESSION": "https://api.nodepay.ai/api/auth/session",

    # Earn and Mission Endpoints
    "EARN_INFO": "https://api.nodepay.ai/api/earn/info",
    "MISSION": "https://api.nodepay.ai/api/mission?platform=MOBILE",
    "COMPLETE_MISSION": "https://api.nodepay.ai/api/mission/complete-mission"
}

# Connection states to track account status
CONNECTION_STATES = {
    "NONE_CONNECTION": 3,
    "DISCONNECTED": 2,
    "CONNECTED": 1,
    "FAILED": 0
}
