from homeassistant.helpers import config_entry_oauth2_flow
from .const import DOMAIN

async def get_oauth_implementation(hass, entry):
    """Return the OAuth implementation registered via Application Credentials."""
    # client_id / client_secret are NOT stored in entry.data: they come from the registered implementation
    return await config_entry_oauth2_flow.async_get_config_entry_implementation(hass, entry)
