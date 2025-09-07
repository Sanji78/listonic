DOMAIN = "listonic"
PLATFORMS = ["todo"]

CONF_DEVICE_ID = "device_id"
CONF_REGION = "region"
CONF_CULTURE = "culture"
CONF_LIST_IDS = "list_ids"  # which Listonic lists to sync

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
CONF_LISTONIC_REFRESH_TOKEN = "listonic_refresh_token"
GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile",
]

LISTONIC_BASE = "https://api.listonic.com"
LISTONIC_LOGINEXT = f"{LISTONIC_BASE}/api/loginextended"
LISTONIC_SYNC_CONFIG = f"{LISTONIC_BASE}/api/syncconfiguration"