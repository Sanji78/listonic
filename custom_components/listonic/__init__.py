from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN, PLATFORMS, CONF_LISTONIC_REFRESH_TOKEN
from .listonic_api import ListonicClient
from .oauth2 import get_oauth_implementation
# from .list_management import async_setup_list_management

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Listonic from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # --- Step 1: create client with OAuth session ---
    try:
        implementation = get_oauth_implementation(hass, entry)
        session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
        client = ListonicClient(hass, session, entry)
        
        # If we have a stored refresh token, set it in the client
        if CONF_LISTONIC_REFRESH_TOKEN in entry.data:
            client._listonic_refresh_token = entry.data[CONF_LISTONIC_REFRESH_TOKEN]
            
    except Exception as err:
        raise ConfigEntryNotReady(f"Listonic client not ready: {err}") from err

    hass.data[DOMAIN][entry.entry_id] = {"client": client}
    
    # --- Register services ---
    async def _svc_get_lists(call: ServiceCall) -> dict:
        try:
            lists = await client.get_lists()
            hass.states.async_set(f"{DOMAIN}.lists", "ok", {"lists": lists})
            return {"lists": lists}
        except ConfigEntryNotReady as err:
            _LOGGER.error("OAuth2 token not ready: %s", err)
            raise ServiceValidationError("OAuth2 token not ready. Please check the integration configuration.") from err

    async def _svc_add_item(call: ServiceCall) -> None:
        list_id = call.data["list_id"]
        name = call.data["name"]
        await client.add_item(list_id, name)

    async def _svc_get_items(call: ServiceCall) -> dict:
        list_id = call.data.get("list_id")
        if not list_id:
            raise ValueError("list_id is required")
        items = await client.get_items(list_id)
        hass.states.async_set(f"{DOMAIN}.items_{list_id}", "ok", {"items": items})
        hass.bus.async_fire("listonic_items", {"list_id": list_id, "items": items})
        return {"items": items}

    async def _svc_delete_items(call: ServiceCall) -> None:
        list_id = call.data.get("list_id")
        ids = call.data.get("ids", [])
        await client.delete_items(list_id, ids)

    async def _svc_refresh_data(call: ServiceCall) -> None:
        """Manual refresh of Listonic data."""
        if "coordinator" in hass.data[DOMAIN][entry.entry_id]:
            await hass.data[DOMAIN][entry.entry_id]["coordinator"].async_refresh()
            _LOGGER.debug("Manually refreshed Listonic data")
        else:
            _LOGGER.error("No coordinator found for manual refresh")

    async def _svc_create_list(call: ServiceCall) -> None:
        name = call.data["name"]
        try:
            result = await client.create_list(name)
            _LOGGER.debug("Created list: %s", result)
            # Refresh data to include the new list
            if "coordinator" in hass.data[DOMAIN][entry.entry_id]:
                await hass.data[DOMAIN][entry.entry_id]["coordinator"].async_refresh()
        except Exception as err:
            _LOGGER.error("Error creating list: %s", err)
            raise

    async def _svc_delete_list(call: ServiceCall) -> None:
        list_id = call.data["list_id"]
        try:
            result = await client.delete_list(list_id)
            _LOGGER.debug("Deleted list: %s", result)
            # Refresh data to remove the deleted list
            if "coordinator" in hass.data[DOMAIN][entry.entry_id]:
                await hass.data[DOMAIN][entry.entry_id]["coordinator"].async_refresh()
            
            # Also remove the entity from HA
            from homeassistant.helpers import entity_registry as er
            ent_reg = er.async_get(hass)

            entity_id = ent_reg.async_get_entity_id("todo", DOMAIN, f"listonic_{list_id}")
            if entity_id:
                ent_reg.async_remove(entity_id)
        except Exception as err:
            _LOGGER.error("Error deleting list: %s", err)
            raise

    async def _svc_update_list(call: ServiceCall) -> None:
        list_id = call.data["list_id"]
        name = call.data["name"]
        try:
            result = await client.update_list(list_id, name)
            _LOGGER.debug("Updated list: %s", result)
            # Refresh data to get the updated list name
            if "coordinator" in hass.data[DOMAIN][entry.entry_id]:
                await hass.data[DOMAIN][entry.entry_id]["coordinator"].async_refresh()
        except Exception as err:
            _LOGGER.error("Error updating list: %s", err)
            raise

    # Register the new services
    hass.services.async_register(DOMAIN, "update_list", _svc_update_list)
    hass.services.async_register(DOMAIN, "create_list", _svc_create_list)
    hass.services.async_register(DOMAIN, "delete_list", _svc_delete_list)
    hass.services.async_register(DOMAIN, "get_lists", _svc_get_lists, supports_response=True)
    hass.services.async_register(DOMAIN, "add_item", _svc_add_item)
    hass.services.async_register(DOMAIN, "get_items", _svc_get_items, supports_response=True)
    hass.services.async_register(DOMAIN, "delete_items", _svc_delete_items)
    hass.services.async_register(DOMAIN, "refresh_data", _svc_refresh_data)  # New service

    # async_setup_list_management(hass)
    
    # Forward platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Listonic config entry."""
    # Remove the items coordinator if it exists
    if "items_coordinator" in hass.data[DOMAIN][entry.entry_id]:
        hass.data[DOMAIN][entry.entry_id].pop("items_coordinator", None)
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok