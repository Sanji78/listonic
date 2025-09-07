import aiohttp
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.exceptions import ConfigEntryNotReady
from .const import DOMAIN, CONF_REGION, CONF_CULTURE, CONF_DEVICE_ID, CONF_LISTONIC_REFRESH_TOKEN

_LOGGER = logging.getLogger(__name__)

# Hardcoded ClientAuthorization value from your working code
CLIENT_AUTH_B64 = "bGlzdG9uaWNhbmRyb2lkOmkxZldYd3dYTzZVSVdlemNaeWt4"


class ListonicClient:
    """Handles communication with Listonic API."""

    def __init__(self, hass: HomeAssistant, oauth_session: config_entry_oauth2_flow.OAuth2Session, entry):
        self.hass = hass
        self.session = oauth_session
        self.entry = entry
        self._listonic_token = None
        self._listonic_refresh_token = None  # Store Listonic refresh token
        
    @classmethod
    async def from_config_entry(cls, hass, entry):
        from .oauth2 import get_oauth_implementation
        implementation = get_oauth_implementation(hass, entry)
        session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
        return cls(hass, session, entry)

    async def _auth_headers(self) -> dict[str, str]:
        """Return headers with valid Listonic token."""
        await self._ensure_listonic_token()
        return {
            "Authorization": f"Bearer {self._listonic_token}",
            "Culture": self.entry.options.get(CONF_CULTURE, "it-IT"),
            "RegionCode": self.entry.options.get(CONF_REGION, "it"),
            "ClientAuthorization": f"Basic {CLIENT_AUTH_B64}",
            "Content-Type": "application/json",
            "DeviceId": self.entry.options.get(CONF_DEVICE_ID, "ha-addon"),
            "Version": "a:8.34.1",  # Example version from working code
        }

    async def _ensure_listonic_token(self):
        if self._listonic_token:
            return

        # First, try to use the Listonic refresh token if we have one
        if self._listonic_refresh_token:
            try:
                headers = {
                    "Content-Type": "text/plain",
                    "Culture": self.entry.options.get(CONF_CULTURE, "it-IT"),
                    "RegionCode": self.entry.options.get(CONF_REGION, "it"),
                    "ClientAuthorization": f"Basic {CLIENT_AUTH_B64}",
                }
                
                payload = f"refresh_token={self._listonic_refresh_token}"
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.listonic.com/api/loginextended?provider=refresh_token",
                        headers=headers,
                        data=payload,
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            self._listonic_token = data.get("access_token")
                            self._listonic_refresh_token = data.get("refresh_token")
                            
                            if self._listonic_token:
                                _LOGGER.debug("Successfully refreshed Listonic token using refresh token")
                                
                                # Update the config entry with the new refresh token
                                if self._listonic_refresh_token and self._listonic_refresh_token != self.entry.data.get(CONF_LISTONIC_REFRESH_TOKEN):
                                    new_data = {**self.entry.data, CONF_LISTONIC_REFRESH_TOKEN: self._listonic_refresh_token}
                                    self.hass.config_entries.async_update_entry(self.entry, data=new_data)
                                
                                return
                # If we get here, the refresh token didn't work
                _LOGGER.warning("Listonic refresh token failed, falling back to Google token")
            except Exception as err:
                _LOGGER.warning("Error refreshing Listonic token with refresh token: %s. Falling back to Google token", err)
        
        # If we don't have a Listonic refresh token or it failed, try with Google token
        # Check if we have a valid token
        if not self.session.token:
            raise ConfigEntryNotReady("OAuth2 token not yet available")

        # Try to ensure token is valid, but handle cases where refresh_token might be missing
        try:
            await self.session.async_ensure_token_valid()
        except KeyError as err:
            if "refresh_token" in str(err):
                raise ConfigEntryNotReady("OAuth2 refresh token not available. Please reauthenticate.") from err
            raise

        google_access_token = self.session.token.get("access_token")
        
        if not google_access_token:
            raise ConfigEntryNotReady("Google OAuth access token not available")

        # Make the login request to Listonic using Google token
        headers = {
            "Content-Type": "text/plain",
            "Culture": self.entry.options.get(CONF_CULTURE, "it-IT"),
            "RegionCode": self.entry.options.get(CONF_REGION, "it"),
            "ClientAuthorization": f"Basic {CLIENT_AUTH_B64}",
        }

        payload = f"token={google_access_token}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.listonic.com/api/loginextended?automerge=1&autodestruct=1&provider=google",
                headers=headers,
                data=payload,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise ConfigEntryNotReady(f"Listonic login failed: {resp.status} {text}")
                
                data = await resp.json()
                self._listonic_token = data.get("access_token")
                self._listonic_refresh_token = data.get("refresh_token")
                
                if not self._listonic_token:
                    raise ConfigEntryNotReady("No access token returned from Listonic")
                
                # Update the config entry with the new refresh token
                if self._listonic_refresh_token and self._listonic_refresh_token != self.entry.data.get(CONF_LISTONIC_REFRESH_TOKEN):
                    new_data = {**self.entry.data, CONF_LISTONIC_REFRESH_TOKEN: self._listonic_refresh_token}
                    self.hass.config_entries.async_update_entry(self.entry, data=new_data)
    # --- API Methods ---

    async def get_sync_configuration(self):
        headers = await self._auth_headers()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.listonic.com/api/syncconfiguration",
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Listonic sync configuration failed: {resp.status} {text}")
                return await resp.json()

    async def get_lists(self):
        headers = await self._auth_headers()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.listonic.com/api/lists",
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"get_lists failed: {resp.status}")
                return await resp.json()

    async def get_items(self, list_id: str):
        headers = await self._auth_headers()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.listonic.com/api/lists/{list_id}/items",
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"get_items failed: {resp.status}")
                return await resp.json()

    async def add_item(self, list_id: str, name: str):
        headers = await self._auth_headers()
        payload = {"Name": name}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.listonic.com/api/lists/{list_id}/items",
                headers=headers,
                json=payload,
            ) as resp:
                # Accept both 200 (OK) and 201 (Created) as success
                if resp.status not in [200, 201]:
                    raise RuntimeError(f"add_item failed: {resp.status}")
                
                # Check if response has JSON content before trying to parse it
                content_type = resp.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    return await resp.json()
                else:
                    # For non-JSON responses, just return an empty dict
                    _LOGGER.debug("Non-JSON response received for add_item, returning empty dict")
                    return {}

    async def delete_items(self, list_id: str, ids: list[int]):
        headers = await self._auth_headers()
        
        # Use the correct endpoint and method from your working example
        url = f"https://api.listonic.com/api/lists/{list_id}/multipleitems"
        
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                url,
                headers=headers,
                json=ids,  # Send the IDs array directly as the request body
            ) as resp:
                # Accept both 200 (OK) and 204 (No Content) as success
                if resp.status not in [200, 204]:
                    text = await resp.text()
                    raise RuntimeError(f"delete_items failed: {resp.status} {text}")
                
                # Check if response has JSON content before trying to parse it
                content_type = resp.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    return await resp.json()
                else:
                    # For non-JSON responses, just return an empty dict
                    _LOGGER.debug("Non-JSON response received for delete_items, returning empty dict")
                    return {}
                    
    async def update_item(self, list_id: str, item_id: int, checked: bool | None = None, name: str | None = None):
        """Update (check/uncheck or rename) a Listonic item."""
        try:
            headers = await self._auth_headers()
            payload: dict[str, object] = {}
            if checked is not None:
                payload["Checked"] = 1 if checked else 0
                _LOGGER.debug("Updating item %s in list %s: checked=%s", item_id, list_id, checked)
            if name is not None:
                payload["Name"] = name
                _LOGGER.debug("Updating item %s in list %s: name=%s", item_id, list_id, name)

            url = f"https://api.listonic.com/api/lists/{list_id}/items/{item_id}"

            async with aiohttp.ClientSession() as session:
                async with session.patch(url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        _LOGGER.error("update_item failed: %s %s", resp.status, text)
                        raise RuntimeError(f"update_item failed: {resp.status} {text}")
                    
                    _LOGGER.debug("Successfully updated item %s in list %s", item_id, list_id)
                    
                    # Check if response has JSON content before trying to parse it
                    content_type = resp.headers.get('Content-Type', '')
                    if 'application/json' in content_type:
                        return await resp.json()
                    else:
                        # For non-JSON responses, just return an empty dict
                        _LOGGER.debug("Non-JSON response received for update_item, returning empty dict")
                        return {}
                    
        except Exception as err:
            _LOGGER.error("Error in update_item: %s", err)
            raise

    async def create_list(self, name: str):
        """Create a new list in Listonic."""
        headers = await self._auth_headers()
        payload = {
            "Name": name,
            "Active": 1,
            "SortMode": 0,
            "SortOrder": 4,  # This might need adjustment based on your needs
            "Shares": [],
            "Items": []
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.listonic.com/api/lists",
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status not in [200, 201]:
                    text = await resp.text()
                    raise RuntimeError(f"create_list failed: {resp.status} {text}")
                
                # Check if response has JSON content before trying to parse it
                content_type = resp.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    return await resp.json()
                else:
                    _LOGGER.debug("Non-JSON response received for create_list, returning empty dict")
                    return {}

    async def delete_list(self, list_id: str):
        """Delete a list in Listonic (set Active: 0)."""
        headers = await self._auth_headers()
        payload = {"Active": 0}
        
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"https://api.listonic.com/api/lists/{list_id}",
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"delete_list failed: {resp.status} {text}")
                
                # Check if response has JSON content before trying to parse it
                content_type = resp.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    return await resp.json()
                else:
                    _LOGGER.debug("Non-JSON response received for delete_list, returning empty dict")
                    return {}

    async def update_list(self, list_id: str, name: str):
        """Update a list's name in Listonic."""
        headers = await self._auth_headers()
        payload = {"Name": name}
        
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"https://api.listonic.com/api/lists/{list_id}",
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"update_list failed: {resp.status} {text}")
                
                # Check if response has JSON content before trying to parse it
                content_type = resp.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    return await resp.json()
                else:
                    _LOGGER.debug("Non-JSON response received for update_list, returning empty dict")
                    return {}