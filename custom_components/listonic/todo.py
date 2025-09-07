from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.todo import (
    TodoListEntity,
    TodoItem,
    TodoItemStatus,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)

from datetime import timedelta

from .const import DOMAIN, CONF_DEVICE_ID

_LOGGER = logging.getLogger(__name__)


# Replace the async_setup_entry function with this simplified version
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up Listonic todo platform from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    client = data["client"]

    async def _async_update_data():
        """Fetch latest data from Listonic."""
        try:
            lists = await client.get_lists()
            items_by_list = {}
            for lst in lists:
                list_id = lst["Id"]
                items = await client.get_items(list_id)
                items_by_list[list_id] = items
            return {"lists": lists, "items": items_by_list}
        except Exception as err:
            _LOGGER.error("Error updating Listonic data: %s", err)
            return {"lists": [], "items": {}}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="listonic_todo",
        update_method=_async_update_data,
        update_interval=timedelta(seconds=2),  # Increased to 30 seconds for stability
    )

    await coordinator.async_config_entry_first_refresh()

    # Store the coordinator in hass data
    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

    # Create a simple function to update entities
    async def update_entities_simple():
        """Simple function to update entities based on coordinator data."""
        current_entities = hass.data[DOMAIN][entry.entry_id].get("entities", [])
        current_lists = coordinator.data.get("lists", [])
        
        # Get current list IDs
        current_list_ids = {lst["Id"] for lst in current_lists}
        
        # Get existing entity list IDs
        existing_entity_ids = {entity._list_id for entity in current_entities}
        
        # Find new lists to add
        new_list_ids = current_list_ids - existing_entity_ids
        new_entities = []
        for lst in current_lists:
            if lst["Id"] in new_list_ids:
                new_entity = ListonicTodoEntity(coordinator, client, lst)
                new_entities.append(new_entity)
                current_entities.append(new_entity)
        
        # Find lists to remove
        lists_to_remove = existing_entity_ids - current_list_ids
        entities_to_keep = []
        
        # Get the entity registry
        from homeassistant.helpers import entity_registry as er
        ent_reg = er.async_get(hass)
        
        for entity in current_entities:
            if entity._list_id in lists_to_remove:
                # Remove entity from HA entity registry
                entity_id = ent_reg.async_get_entity_id("todo", DOMAIN, entity.unique_id)
                if entity_id:
                    ent_reg.async_remove(entity_id)
                # Also remove the entity object
                await entity.async_remove()
            else:
                entities_to_keep.append(entity)
        
        # Update the stored entities list
        hass.data[DOMAIN][entry.entry_id]["entities"] = entities_to_keep
        
        # Add new entities to HA
        if new_entities:
            async_add_entities(new_entities)

    # Create initial entities
    await update_entities_simple()
    
    # Set up a listener to update entities when data changes
    def update_entities_callback():
        """Callback to update entities when coordinator data changes."""
        hass.async_create_task(update_entities_simple())
    
    coordinator.async_add_listener(update_entities_callback)

    return True

# Replace the update_entities function with this corrected version
async def update_entities(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Update the entities based on the current data."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]["client"]
    current_entities = hass.data[DOMAIN][entry.entry_id].get("entities", [])
    
    # Get current lists from coordinator data
    current_lists = coordinator.data.get("lists", [])
    current_list_ids = {lst["Id"] for lst in current_lists}
    
    # Get existing entity list IDs
    existing_entity_ids = {entity._list_id for entity in current_entities}
    
    # Find new lists to add
    new_list_ids = current_list_ids - existing_entity_ids
    new_entities = []
    for lst in current_lists:
        if lst["Id"] in new_list_ids:
            new_entity = ListonicTodoEntity(coordinator, client, lst)
            new_entities.append(new_entity)
            current_entities.append(new_entity)
    
    # Find lists to remove
    lists_to_remove = existing_entity_ids - current_list_ids
    entities_to_keep = []
    
    # Get the entity registry - FIXED
    from homeassistant.helpers import entity_registry as er
    ent_reg = er.async_get(hass)
    
    for entity in current_entities:
        if entity._list_id in lists_to_remove:
            # Remove entity from HA entity registry
            entity_id = ent_reg.async_get_entity_id("todo", DOMAIN, entity.unique_id)
            if entity_id:
                ent_reg.async_remove(entity_id)
            # Also remove the entity object
            await entity.async_remove()
        else:
            entities_to_keep.append(entity)
    
    # Update the stored entities list
    hass.data[DOMAIN][entry.entry_id]["entities"] = entities_to_keep + new_entities
    
    # Add new entities to HA
    if new_entities:
        async_add_entities(new_entities)

class ListonicTodoEntity(CoordinatorEntity, TodoListEntity):
    """A Listonic shopping list as a Home Assistant todo list."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(self, coordinator: DataUpdateCoordinator, client, list_data: dict[str, Any]):
        # Pass coordinator to CoordinatorEntity
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.client = client
        self._list_id = list_data["Id"]
        self._attr_unique_id = f"listonic_{self._list_id}"
        # Don't set the name here, we'll use a property to get it dynamically
        self._initial_name = list_data.get("Name", "Listonic List")

    @property
    def name(self) -> str:
        """Return the current name of the list."""
        # Get the latest list data from coordinator
        lists = self.coordinator.data.get("lists", [])
        for lst in lists:
            if lst["Id"] == self._list_id:
                return lst.get("Name", self._initial_name)
        return self._initial_name  # Fallback if list not found

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return the current items for this todo list."""
        # Use coordinator.data instead of self.coordinator.data
        items_data = self.coordinator.data.get("items", {}).get(self._list_id, [])
        todo_items: list[TodoItem] = []
        for item in items_data:
            todo_items.append(
                TodoItem(
                    uid=str(item["Id"]),
                    summary=item.get("Name", "Unnamed"),
                    status=TodoItemStatus.COMPLETED if item.get("Checked") else TodoItemStatus.NEEDS_ACTION,
                )
            )
        return todo_items

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add a new item to the list."""
        try:
            await self.client.add_item(self._list_id, item.summary)
            # Refresh coordinator to get latest data
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error creating todo item: %s", err)
            raise

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an item (check/uncheck or rename)."""
        try:
            checked: bool | None = None
            name: str | None = None

            # Translate HA todo status into Listonic "Checked"
            if item.status == TodoItemStatus.COMPLETED:
                checked = True
            elif item.status == TodoItemStatus.NEEDS_ACTION:
                checked = False

            # Translate HA summary into Listonic "Name"
            if item.summary:
                name = item.summary

            # Call the API only if there is something to update
            if checked is not None or name is not None:
                await self.client.update_item(
                    self._list_id,
                    int(item.uid),
                    checked=checked,
                    name=name,
                )

            # Refresh coordinator to get latest data
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error updating todo item: %s", err)
            raise

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete one or more items."""
        try:
            ids = [int(uid) for uid in uids]
            await self.client.delete_items(self._list_id, ids)
            # Refresh coordinator to get latest data
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error deleting todo items: %s", err)
            raise