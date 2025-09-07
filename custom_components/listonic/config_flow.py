from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow, selector
from homeassistant.core import callback
from .const import DOMAIN, CONF_LIST_IDS

_LOGGER = logging.getLogger(__name__)


class ListonicConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Handle a config flow for Listonic."""

    VERSION = 1
    DOMAIN = DOMAIN
    SCOPE = "openid email profile"

    @property
    def logger(self) -> logging.Logger:
        """Return the logger required by AbstractOAuth2FlowHandler."""
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict:
        """Request offline access to get a refresh token."""
        return {
            "scope": self.SCOPE,
            "access_type": "offline",  # This ensures we get a refresh token
            "prompt": "consent",  # This ensures we always get a refresh token
        }

    async def async_step_user(self, user_input: Optional[dict[str, Any]] = None) -> FlowResult:
        """Start config flow. Pick OAuth implementation."""
        implementations = await config_entry_oauth2_flow.async_get_implementations(self.hass, DOMAIN)
        if not implementations:
            _LOGGER.error(
                "No application credentials found for %s; add one under Settings → Devices & Services → Application Credentials",
                DOMAIN,
            )
            return self.async_abort(reason="missing_credentials")

        return await self.async_step_pick_implementation()

    # Add this method to the ListonicConfigFlow class
    async def async_step_options(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current lists from the API
        # This would require accessing the client, which might be complex in the config flow
        # For simplicity, we'll just show a form with manual list management
        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema({
                vol.Optional(CONF_LIST_IDS): selector.TextSelector(),
            }),
        )
    
    @callback
    def async_oauth_create_entry(self, data: dict) -> FlowResult:
        """Create config entry after OAuth2 flow finishes."""
        return super().async_oauth_create_entry(data)

    async def async_step_reauth(self, entry_data: dict) -> FlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: Optional[dict[str, Any]] = None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()