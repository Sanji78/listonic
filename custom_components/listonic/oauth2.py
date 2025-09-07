from homeassistant.helpers import config_entry_oauth2_flow
from .const import DOMAIN

def get_oauth_implementation(hass, entry):
    """Return a LocalOAuth2Implementation from HA Application Credentials."""
    # HA stores client_id and secret internally; do not hardcode
    return config_entry_oauth2_flow.LocalOAuth2Implementation(
        hass,
        DOMAIN,
        authorize_url="https://accounts.google.com/o/oauth2/auth",
        token_url="https://oauth2.googleapis.com/token",
        client_id=entry.data.get("client_id"),
        client_secret=entry.data.get("client_secret"),
    )
